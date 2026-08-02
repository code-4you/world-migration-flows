/* World Migration Flows — an open-source rebuild of Max Galka's Metrocosm
 * global immigration map, using UN International Migrant Stock 2024 data.
 * MIT licensed. */

"use strict";

/* Periods shown as buttons (UN International Migrant Stock 2024) */
const PERIODS = [
  { id: "1990_2000", label: "1990–2000" },
  { id: "2000_2010", label: "2000–2010" },
  { id: "2010_2020", label: "2010–2020" },
  { id: "2020_2024", label: "2020–2024" },
];
/* Earlier periods offered in the "Earlier…" dropdown (UNU-CRIS imputed
 * bilateral migration dataset, Standaert & Rayp 2022) */
const EARLY_PERIODS = [
  { id: "1960_1970", label: "1960–1970" },
  { id: "1970_1980", label: "1970–1980" },
  { id: "1980_1990", label: "1980–1990" },
];
const ALL_PERIODS = () => [...EARLY_PERIODS, ...PERIODS];
const DEFAULT_PERIOD = "2020_2024";
const PLAY_STEP_MS = 5000;
const MAX_PARTICLES = 3500;
const BASE_ZOOM = 1.6;

const COLOR_IN = "rgba(64, 120, 255, 0.55)";
const COLOR_IN_STROKE = "rgba(120, 160, 255, 0.9)";
const COLOR_OUT = "rgba(230, 55, 45, 0.5)";
const COLOR_OUT_STROKE = "rgba(255, 110, 100, 0.9)";
const COLOR_SELECTED = "rgba(255, 206, 58, 0.95)";

const state = {
  period: DEFAULT_PERIOD,
  selected: "", // ISO2 or "" for all
  playing: false,
  playTimer: null,
  flows: {}, // periodId -> flows json
  countries: {},
  routes: [], // {from:{lon,lat}, to, mag, p0,p1,p2 (px), len}
  particles: [], // {r: routeIdx, t, dt}
  circles: [], // {iso2, x, y, r, net, gain}
  hover: null,
};

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      carto: {
        type: "raster",
        tiles: [
          "https://a.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png",
          "https://b.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png",
          "https://c.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors © CARTO",
      },
    },
    layers: [{ id: "carto", type: "raster", source: "carto" }],
  },
  center: [12, 24],
  zoom: BASE_ZOOM,
  minZoom: 0.8,
  maxZoom: 5.5,
  renderWorldCopies: false,
  attributionControl: false,
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
map.dragRotate.disable();
map.touchZoomRotate.disableRotation();

const pCanvas = document.getElementById("particles");
const cCanvas = document.getElementById("circles");
const pCtx = pCanvas.getContext("2d");
const cCtx = cCanvas.getContext("2d");
const tooltip = document.getElementById("tooltip");

/* Pre-rendered glow sprite for particles */
const sprite = document.createElement("canvas");
sprite.width = sprite.height = 16;
{
  const g = sprite.getContext("2d");
  const grad = g.createRadialGradient(8, 8, 0, 8, 8, 8);
  grad.addColorStop(0, "rgba(255, 235, 150, 1)");
  grad.addColorStop(0.35, "rgba(255, 206, 58, 0.8)");
  grad.addColorStop(1, "rgba(255, 206, 58, 0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 16, 16);
}

function resizeCanvases() {
  const dpr = window.devicePixelRatio || 1;
  for (const cv of [pCanvas, cCanvas]) {
    cv.width = innerWidth * dpr;
    cv.height = innerHeight * dpr;
    cv.style.width = innerWidth + "px";
    cv.style.height = innerHeight + "px";
    cv.getContext("2d").setTransform(dpr, 0, 0, dpr, 0, 0);
  }
}

function fmt(n) {
  return (n > 0 ? "+" : "") + n.toLocaleString("en-US");
}

/* ---------- data ---------- */

async function loadPeriod(id) {
  if (!state.flows[id]) {
    const res = await fetch(`data/flows_${id}.json`);
    state.flows[id] = await res.json();
  }
  return state.flows[id];
}

/* Shortest-longitude unwrap so routes cross the nearest edge */
function unwrapLon(fromLon, toLon) {
  let d = toLon - fromLon;
  if (d > 180) return toLon - 360;
  if (d < -180) return toLon + 360;
  return toLon;
}

/* Rebuild route list + particles for current period/selection */
function rebuildRoutes() {
  const flows = state.flows[state.period];
  const C = state.countries;
  const sel = state.selected;
  const routes = [];
  const seen = new Set();
  let totalMag = 0;

  for (const a in flows) {
    if (!C[a]) continue;
    for (const b in flows[a]) {
      if (b === a || !C[b]) continue;
      if (sel && a !== sel && b !== sel) continue;
      const key = a < b ? a + b : b + a;
      if (seen.has(key)) continue;
      seen.add(key);
      const net = flows[a][b]; // >0: a gains from b  => particles b->a
      const [from, to] = net > 0 ? [C[b], C[a]] : [C[a], C[b]];
      const mag = Math.abs(net);
      // in the all-countries view, keep only substantial routes for legibility
      if (mag < (sel ? 2000 : 25000)) continue;
      routes.push({ from, to, mag });
      totalMag += mag;
    }
  }

  const perParticle = Math.max(2000, totalMag / MAX_PARTICLES);
  const particles = [];
  routes.forEach((r, i) => {
    const n = Math.max(1, Math.min(600, Math.round(r.mag / perParticle)));
    for (let k = 0; k < n; k++) {
      particles.push({ r: i, t: Math.random() });
    }
  });
  state.routes = routes;
  state.particles = particles;
  projectRoutes();
  pCtx.clearRect(0, 0, innerWidth, innerHeight);
}

/* Project route endpoints to screen px; arc control point perpendicular to the chord */
function projectRoutes() {
  for (const r of state.routes) {
    const p0 = map.project([r.from.lon, r.from.lat]);
    const p2 = map.project([unwrapLon(r.from.lon, r.to.lon), r.to.lat]);
    const dx = p2.x - p0.x, dy = p2.y - p0.y;
    const len = Math.hypot(dx, dy) || 1;
    const bend = Math.min(len * 0.18, 70);
    r.p0 = p0;
    r.p2 = p2;
    r.p1 = { x: (p0.x + p2.x) / 2 - (dy / len) * bend, y: (p0.y + p2.y) / 2 + (dx / len) * bend };
    r.len = len;
  }
}

function rebuildCircles() {
  const flows = state.flows[state.period];
  const C = state.countries;
  const sel = state.selected;
  const circles = [];

  let maxAbs = 1;
  const entries = [];
  for (const iso2 in flows) {
    if (!C[iso2]) continue;
    const net = sel
      ? iso2 === sel
        ? flows[iso2][iso2] || 0
        : -(flows[sel][iso2] || 0) // partner's net vs selected: >0 partner gains
      : flows[iso2][iso2] || 0;
    if (sel && iso2 !== sel && !flows[sel][iso2]) continue;
    entries.push([iso2, net]);
    maxAbs = Math.max(maxAbs, Math.abs(net));
  }

  const zoomScale = Math.pow(2, (map.getZoom() - BASE_ZOOM) * 0.6);
  for (const [iso2, net] of entries) {
    const c = C[iso2];
    const pt = map.project([c.lon, c.lat]);
    const r = (3 + 34 * Math.sqrt(Math.abs(net) / maxAbs)) * zoomScale;
    circles.push({ iso2, x: pt.x, y: pt.y, r, net, gain: net >= 0 });
  }
  circles.sort((a, b) => b.r - a.r); // big first so small stay hoverable
  state.circles = circles;
  drawCircles();
}

/* ---------- drawing ---------- */

function drawCircles() {
  cCtx.clearRect(0, 0, innerWidth, innerHeight);
  for (const c of state.circles) {
    const selectedOne = c.iso2 === state.selected;
    cCtx.beginPath();
    cCtx.arc(c.x, c.y, c.r, 0, Math.PI * 2);
    cCtx.fillStyle = c.gain ? COLOR_IN : COLOR_OUT;
    cCtx.fill();
    cCtx.lineWidth = selectedOne ? 2.5 : 1;
    cCtx.strokeStyle = selectedOne
      ? COLOR_SELECTED
      : c.gain
        ? COLOR_IN_STROKE
        : COLOR_OUT_STROKE;
    cCtx.stroke();
  }
  if (state.hover) drawHoverRing(state.hover);
}

function drawHoverRing(c) {
  cCtx.beginPath();
  cCtx.arc(c.x, c.y, c.r + 2, 0, Math.PI * 2);
  cCtx.lineWidth = 2;
  cCtx.strokeStyle = "rgba(255,255,255,0.9)";
  cCtx.stroke();
}

function frame() {
  // fade previous frame -> particle trails
  pCtx.globalCompositeOperation = "destination-out";
  pCtx.fillStyle = "rgba(0, 0, 0, 0.22)";
  pCtx.fillRect(0, 0, innerWidth, innerHeight);
  pCtx.globalCompositeOperation = "lighter";

  const routes = state.routes;
  for (const p of state.particles) {
    const r = routes[p.r];
    if (!r || !r.p0) continue;
    p.t += 1.6 / r.len; // ~constant px speed
    if (p.t > 1) p.t -= 1;
    const t = p.t, u = 1 - t;
    const x = u * u * r.p0.x + 2 * u * t * r.p1.x + t * t * r.p2.x;
    const y = u * u * r.p0.y + 2 * u * t * r.p1.y + t * t * r.p2.y;
    pCtx.drawImage(sprite, x - 4, y - 4, 8, 8);
  }
  requestAnimationFrame(frame);
}

/* ---------- interaction ---------- */

function hitTest(mx, my) {
  // smallest circle wins so islands inside big circles stay reachable
  let best = null;
  for (const c of state.circles) {
    const d = Math.hypot(mx - c.x, my - c.y);
    if (d <= Math.max(c.r, 6) && (!best || c.r < best.r)) best = c;
  }
  return best;
}

map.getCanvas().parentElement.addEventListener("mousemove", (e) => {
  const c = hitTest(e.clientX, e.clientY);
  if (c !== state.hover) {
    state.hover = c;
    drawCircles();
  }
  if (!c) {
    tooltip.style.display = "none";
    return;
  }
  const name = state.countries[c.iso2].name;
  const label = ALL_PERIODS().find((p) => p.id === state.period).label;
  const cls = c.net >= 0 ? "gain" : "loss";
  const context = state.selected && c.iso2 !== state.selected
    ? ` vs ${state.countries[state.selected].name}`
    : "";
  tooltip.innerHTML =
    `<div class="name">${name}</div>` +
    `<div>Net migration ${label}${context}: <span class="${cls}">${fmt(c.net)}</span></div>`;
  tooltip.style.display = "block";
  tooltip.style.left = Math.min(e.clientX + 14, innerWidth - 250) + "px";
  tooltip.style.top = e.clientY + 14 + "px";
});

async function setPeriod(id) {
  state.period = id;
  await loadPeriod(id);
  document
    .querySelectorAll("#period-buttons button")
    .forEach((b) => b.classList.toggle("active", b.dataset.period === id));
  const era = document.getElementById("era-select");
  era.value = EARLY_PERIODS.some((p) => p.id === id) ? id : "";
  era.classList.toggle("active", era.value !== "");
  rebuildRoutes();
  rebuildCircles();
}

async function setCountry(iso2) {
  if (iso2 && !(state.flows[state.period] || {})[iso2]) iso2 = "";
  state.selected = iso2;
  document.getElementById("country-select").value = iso2;
  rebuildRoutes();
  rebuildCircles();
}

function stopPlay() {
  state.playing = false;
  clearInterval(state.playTimer);
  document.getElementById("play").innerHTML = "&#9654; Play";
}

/* Cycle through every period chronologically, looping forever */
function startPlay() {
  stopPlay();
  state.playing = true;
  document.getElementById("play").innerHTML = "&#9646;&#9646; Stop";
  const seq = ALL_PERIODS();
  let i = 0; // always start from the earliest period
  setPeriod(seq[i].id);
  state.playTimer = setInterval(() => {
    i = (i + 1) % seq.length;
    setPeriod(seq[i].id);
  }, PLAY_STEP_MS);
}

/* ---------- init ---------- */

async function init() {
  resizeCanvases();

  const periodBar = document.getElementById("period-buttons");
  for (const p of PERIODS) {
    const b = document.createElement("button");
    b.textContent = p.label;
    b.dataset.period = p.id;
    b.addEventListener("click", () => {
      stopPlay();
      setPeriod(p.id);
    });
    periodBar.appendChild(b);
  }

  const eraSelect = document.getElementById("era-select");
  for (const p of EARLY_PERIODS) {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = p.label;
    eraSelect.appendChild(o);
  }
  eraSelect.addEventListener("change", () => {
    if (!eraSelect.value) return;
    stopPlay();
    setPeriod(eraSelect.value);
  });

  document.getElementById("play").addEventListener("click", () =>
    state.playing ? stopPlay() : startPlay()
  );

  // click a country circle on the map to select it; click empty space to clear
  let downAt = null;
  const mapEl = map.getCanvas().parentElement;
  mapEl.addEventListener("mousedown", (e) => (downAt = [e.clientX, e.clientY]));
  mapEl.addEventListener("mouseup", (e) => {
    if (!downAt) return;
    const moved = Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]);
    downAt = null;
    if (moved > 5) return; // it was a pan, not a click
    const c = hitTest(e.clientX, e.clientY);
    setCountry(c && c.iso2 !== state.selected ? c.iso2 : "");
  });

  state.countries = await (await fetch("data/countries.json")).json();

  const select = document.getElementById("country-select");
  Object.entries(state.countries)
    .sort((a, b) => a[1].name.localeCompare(b[1].name))
    .forEach(([iso2, c]) => {
      const o = document.createElement("option");
      o.value = iso2;
      o.textContent = c.name;
      select.appendChild(o);
    });
  select.addEventListener("change", () => setCountry(select.value));

  // shareable state: ?p=<period>&c=<ISO2>, e.g. ?p=2010_2020&c=US
  const params = new URLSearchParams(location.search);
  const p = params.get("p");
  const c = (params.get("c") || "").toUpperCase();
  const startPeriod = ALL_PERIODS().some((x) => x.id === p) ? p : DEFAULT_PERIOD;
  await loadPeriod(startPeriod);
  if (c && state.countries[c]) state.selected = c;
  await setPeriod(startPeriod);
  if (state.selected) await setCountry(state.selected);

  map.on("move", () => {
    projectRoutes();
    rebuildCircles();
  });
  window.addEventListener("resize", () => {
    resizeCanvases();
    projectRoutes();
    rebuildCircles();
  });

  requestAnimationFrame(frame);
}

// Not gated on map "load": the overlay only needs map.project(), which works
// from construction — so slow basemap tiles never block the visualization.
init();
