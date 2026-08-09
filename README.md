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
- All numbers are model-based estimates, not counts; the three sources use
  different pipelines, so expect methodological seams at 1990 and 2020.

Regenerate the data files with:

```bash
python scripts/process.py        # countries.json + UN stock fallback (run first)
python scripts/process_abel.py   # 1990-2020 decades (Abel & Cohen flows)
python scripts/process_early.py  # 1960-1990 decades (UNU-CRIS stocks)
python scripts/process_yearly.py # single years 1960-1989 (UNU-CRIS stocks)
python scripts/process_gaskin.py # single years 1990-2023 + 2020-2024 period (run last)
```

(after downloading the source files into `raw/` — see the script docstrings).

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
