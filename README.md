# World Migration Flows

An open-source, interactive map of global migration — an homage to (and rebuild of)
[Max Galka's Metrocosm global immigration map](https://web.archive.org/web/2018/http://metrocosm.com/global-immigration-map/),
whose original site is no longer online.

**Live map: <https://code-4you.github.io/world-migration-flows/>**

Animated particles show estimated migration flows between countries. An
**Events** dropdown replays named migration episodes — the Syrian refugee
crisis, the Gastarbeiter era, the fall of the Soviet Union and more — each
auto-playing its years with the affected countries highlighted, and each
shareable via `?e=<event>` links (e.g. `?e=ukraine`). Its play button tours
every event in sequence.
Circles show each country's total net migration: **blue = net gain, red = net loss**.
Hover a circle for numbers. Pick a country (USA / China / Germany / Australia, or any
country from the dropdown) to isolate its flows, and press **Play** to step through
every period from 1990 to 2024.

## Data

- **1990–2020:** [Abel & Cohen bilateral migration flow estimates](https://doi.org/10.6084/m9.figshare.7731233)
  (`da_pb_closed` method) — true gross flow estimates from demographic
  accounting, so both directions of every corridor are visible (e.g. Mexico→US
  *and* US→Mexico return migration).
- **2020–2024 (fallback):** [UN DESA, International Migrant Stock 2024](https://www.un.org/development/desa/pd/content/international-migrant-stock)
  is used for `countries.json` and can regenerate a stock-difference version
  of the 2020–2024 period, but the shipped file comes from the Gaskin & Abel
  yearly estimates (2020–2023 summed).
- **1960–1990 decades and single years 1960–1989:** [UNU-CRIS imputed
  bilateral migration dataset](https://riks.cris.unu.edu/annual-bilateral-migration-data)
  (Standaert & Rayp 2022), stock differences over the decade or year.
- **Single years 1990–2023 and the 2020–2024 period:** [Gaskin & Abel
  deep-learning estimates](https://huggingface.co/datasets/ThGaskin/Migration_flows)
  ("[Deep learning four decades of human migration](https://arxiv.org/abs/2506.22821)",
  GPL-3.0) — annual bilateral flows by previous residence for ~230 countries,
  from a neural network integrating UN census stocks, national statistics,
  QuantMig, and [Meta's Facebook-based flow measurements](https://data.humdata.org/dataset/international-migration-flows)
  (Chi et al., PNAS 2025). Unlike the raw Meta data, China and Iran are
  covered. The "Year…" dropdown and its play button (2s per year) step
  through every year from 1960→1961 to 2023→2024.
- **2024 (selected countries only):** officially *reported* statistics —
  [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/migr_imm5prv/default/table)
  immigration/emigration by partner country (calendar 2024, ~19 reporting
  European countries) and [ABS Overseas Migration 2024–25](https://www.abs.gov.au/statistics/people/population/overseas-migration/2024-25)
  arrivals/departures by country of birth (Australia). Because coverage is
  partial, 2024 appears in the Year dropdown **only while a covered country
  is selected**; global views stay capped at the newest complete year.
  Only both-direction sources are used (inflow-only sources like green-card
  counts are excluded). Regenerate with `scripts/process_reported.py`.
- All other numbers are model-based estimates, not counts; the sources use
  different pipelines, so expect methodological seams at 1990 and 2020.
  The most visible one: **emigration from rich countries is under-counted
  before 1990.** The pre-1990 stock-difference method only registers an
  outflow when a country's expatriate stock grows, and deaths of older
  emigrants usually cancel new departures — e.g. US emigration reads as
  ~30k/year through the 1980s, then jumps to ~500k/year from 1990 when the
  flow-based estimates take over. Emigration didn't start in 1990; it just
  becomes visible then. (1990 itself, the first Gaskin & Abel year, runs
  hot — treat that single year's magnitudes with extra caution.)

  The seam is also a **definition change**: before 1990 migrants are tracked
  by *country of birth*; from 1990 by *country of previous residence*. An
  Egyptian guest worker leaving Saudi Arabia is "an Egyptian" to the old
  method — his departure never counts as Saudi emigration — but counts as
  Saudi Arabia→Egypt under the new one. That's why guest-worker states
  (Saudi Arabia, the Gulf) show almost no emigration before 1990 and large
  outflows to Egypt, India and Indonesia from 1990: the same worker
  rotations existed all along, only the newer method can see them. It's
  also what makes return migration (e.g. US→Mexico) visible from 1990 on.

Regenerate the data files with:

```bash
python scripts/process.py        # countries.json + UN stock fallback (run first)
python scripts/process_abel.py   # 1990-2020 decades (Abel & Cohen flows)
python scripts/process_early.py  # 1960-1990 decades (UNU-CRIS stocks)
python scripts/process_yearly.py # single years 1960-1989 (UNU-CRIS stocks)
python scripts/process_gaskin.py # single years 1990-2023 + 2020-2024 period (run last)
```

(after downloading the source files into `raw/` — see the script docstrings).

## How migration is measured (and how much to trust it)

Nobody keeps a worldwide ledger of moves. Migration numbers are built from
imperfect ingredients, and knowing them explains everything odd about the map:

- **Censuses are photos, not videos.** A census shows who lives where *on
  one day* ("born in Nigeria, living in the UK"). Comparing two photos ten
  years apart hints at migration — but two photos cannot tell "nothing
  happened" apart from "one person arrived and one person died." Deaths of
  emigrants abroad silently cancel real migration in the count.
- **That's the pre-1990 weakness.** Our 1960–1990 numbers come from such
  photo-comparisons: the direction and relative size of every flow is
  right, but magnitudes run low (deaths eat part of them), and emigration
  from countries with old diasporas is understated most.
- **Post-1990 data corrects for deaths.** The modern estimates (Abel &
  Cohen; Gaskin & Abel) first compute how many people *should have* died in
  each migrant group using mortality tables, and only call the unexplained
  remainder "migration". Same photos, right answer.
- **Poor-quality censuses are patched by mirror data.** A Nigerian migrant
  doesn't need Nigeria's census to be counted — the UK, US or South African
  census records them as Nigerian-born. Every migrant only has to be
  counted *somewhere*. Refugee flows are covered by UNHCR registration,
  which works even in poor regions.
- **The resulting quality gradient:** flows touching rich countries are the
  most reliable (mirror-counted), refugee crises are well covered
  (registered), and migration *between* two weak-data countries (e.g.
  intra-African labor movement) leans most on modeling.
- **The counting is asymmetric, and it skews the picture.** Rich countries
  count arrivals well, so Africa→Europe is among the best-measured data on
  Earth — while flows *into* Africa and *between* African countries depend
  on weak local statistics and run understated. In reality, most African
  migrants move to other African countries; the popular image of African
  migration as "everyone heading to Europe" is partly a measurement
  artifact — the well-lit corridor looks like the whole story. When a
  corridor connects two weak-statistics countries, treat its number as a
  sketch, not a figure.
- **Tooltips show flows, consistently.** "Net" always equals the displayed
  In − Out. (Earlier versions showed a raw stock-based net in which deaths
  abroad masqueraded as reverse migration — a bug caught by a Reddit
  commenter and fixed.)

## Running locally

Any static file server works:

```bash
python -m http.server 8000
```

then open <http://localhost:8000/>. (Opening `index.html` directly won't work —
the app fetches its JSON data over HTTP.)

## Hosting

The app is fully static (HTML + CSS + JS + JSON), so it runs as-is on GitHub
Pages, Netlify, or any static host. Note: Tableau Public cannot host custom web
apps like this one — it only hosts workbooks built in Tableau's own tools.

## Roadmap

- [x] 2020–2024 flows (latest UN estimates)
- [x] 2010–2020, 2000–2010, 1990–2000 options
- [x] 1960–1990 periods via the "Earlier…" dropdown (UNU-CRIS data)
- [x] Click a country on the map to focus it; all-countries dropdown
- [x] Play button cycling through all periods continuously
- [ ] Pre-1960 periods: no comparable global bilateral dataset exists back to
      1920 — extending further would be limited to a handful of countries with
      long census records
- [ ] Per-country play mode narration / camera movement

## Contributing

Contributions are welcome — the easiest way to start is
[opening an issue](https://github.com/code-4you/world-migration-flows/issues)
for a bug, a data problem, or an idea.

Some good first contributions:

- **Add a migration event.** Events are one-line entries in the `EVENTS`
  array at the top of [app.js](app.js) — an id, a display name, a year range
  (start years, within 1960–2023), and the ISO2 codes of the countries to
  focus. Please check the flows are actually visible in the data for those
  years before submitting.
- **Improve data.** If you know a better public bilateral migration source
  (especially anything past 2023), open an issue with a link. Each source
  has its own script under [scripts/](scripts/) that writes plain JSON into
  `data/`, so new sources slot in without touching the app.
- **Fix or polish the app.** It's dependency-free vanilla JS (MapLibre GL
  from a CDN, two canvas overlays) — no build step.

To run locally: clone, then serve the folder over HTTP (e.g.
`python -m http.server 8000`) and open `http://localhost:8000/` — opening
`index.html` directly won't work because the app fetches its JSON data.
The `data/` files are committed, so you only need Python and the raw source
downloads (see the docstrings in `scripts/`) if you want to regenerate data.

Code is MIT; by contributing you agree your contributions are too. The
underlying datasets keep their own licenses (see Credits).

## Credits

- Concept and original visualization: [Max Galka (Metrocosm)](https://web.archive.org/web/2018/http://metrocosm.com/)
- Creator of this rebuild: [Michael van Diermen](https://mvandiermen.com/)
- Data (1990–2020): Abel, G.J. & Cohen, J.E. (2019), "Bilateral international
  migration flow estimates for 200 countries", *Scientific Data* (updated 2025)
- Data (2020–2024): United Nations, Department of Economic and Social Affairs,
  Population Division — International Migrant Stock 2024 (POP/DB/MIG/Stock/Rev.2024)
- Data (1960–1990): Standaert, S. & G. Rayp (2022), "Where Did They Come From,
  Where Did They Go? Bridging the Gaps in Migration Data", UNU-CRIS
- Data (years 1990–2023, period 2020–2024): Gaskin, T. & G.J. Abel (2025),
  "Deep learning four decades of human migration" (arXiv:2506.22821), GPL-3.0
- Data (model input we previously used directly): Chi, G. et al. (2025),
  "Measuring global migration flows using online data", *PNAS* — © Meta,
  CC BY 4.0, via HDX
- Basemap tiles: © [OpenStreetMap](https://www.openstreetmap.org/copyright)
  contributors, © [CARTO](https://carto.com/attributions)
- Map rendering: [MapLibre GL JS](https://maplibre.org/)
- Country centroids: [world-countries-centroids](https://github.com/gavinr/world-countries-centroids);
  ISO code mapping: [lukes/ISO-3166-Countries-with-Regional-Codes](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes)

Code is MIT licensed (see [LICENSE](LICENSE)). The UN data is © United Nations,
made available for use under its [terms](https://www.un.org/en/about-us/terms-of-use).
