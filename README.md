# World Migration Flows

An open-source, interactive map of global migration — an homage to (and rebuild of)
[Max Galka's Metrocosm global immigration map](https://web.archive.org/web/2018/http://metrocosm.com/global-immigration-map/),
whose original site is no longer online.

Animated particles show estimated net migration flows between countries.
Circles show each country's total net migration: **blue = net gain, red = net loss**.
Hover a circle for numbers. Pick a country (USA / China / Germany / Australia, or any
country from the dropdown) to isolate its flows, and press **Play** to step through
every period from 1990 to 2024.

## Data

- **Source:** [UN DESA, International Migrant Stock 2024](https://www.un.org/development/desa/pd/content/international-migrant-stock)
  (destination-and-origin matrix, revisions for 1990–2024, 230+ countries).
- **Method:** net flow between two countries over a period is estimated as the
  change in bilateral migrant stocks — the same approximation the original map
  used. It ignores deaths and return/onward migration, so treat the numbers as
  estimates, not counts.
- **Periods:** 1990–2000, 2000–2010, 2010–2020, 2020–2024 (the latest UN estimate).
  Pre-1990 data is not part of the UN bilateral series; extending further back
  would need a different source (see roadmap).

Regenerate the data files with:

```bash
python scripts/process.py
```

(after downloading the UN matrix file into `raw/` — see the script docstring).

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
- [x] Country focus buttons + all-countries dropdown
- [x] Play button stepping through periods
- [ ] Pre-1990 periods (needs a non-UN historical source; global bilateral data
      back to 1920 does not exist in comparable form — likely limited to a
      handful of countries with long census records)
- [ ] Per-country play mode narration / camera movement

## Credits

- Concept and original visualization: [Max Galka (Metrocosm)](https://web.archive.org/web/2018/http://metrocosm.com/)
- Data: United Nations, Department of Economic and Social Affairs, Population
  Division — International Migrant Stock 2024 (POP/DB/MIG/Stock/Rev.2024)
- Basemap tiles: © [OpenStreetMap](https://www.openstreetmap.org/copyright)
  contributors, © [CARTO](https://carto.com/attributions)
- Map rendering: [MapLibre GL JS](https://maplibre.org/)
- Country centroids: [world-countries-centroids](https://github.com/gavinr/world-countries-centroids);
  ISO code mapping: [lukes/ISO-3166-Countries-with-Regional-Codes](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes)

Code is MIT licensed (see [LICENSE](LICENSE)). The UN data is © United Nations,
made available for use under its [terms](https://www.un.org/en/about-us/terms-of-use).
