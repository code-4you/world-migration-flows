"""Build data/countries.json (names + centroids) from the UN International
Migrant Stock 2024 destination-origin matrix.

Inputs (in raw/):
  ims2024_matrix.xlsx  UN DESA, International Migrant Stock 2024 (Table 1)
  iso3166.json         M49 numeric -> ISO alpha-2 mapping (lukes/ISO-3166)
  centroids.csv        country centroids (gavinr/world-countries-centroids)

Output (in data/):
  countries.json        {ISO2: {"name": ..., "lon": ..., "lat": ...}}

This script deliberately writes NO flow files. Every flows_*.json has exactly
one owning script (see the README's regeneration order); an earlier version
of this script also wrote stock-difference decade files and once silently
overwrote the Abel & Cohen estimates on a rerun.
"""
import csv
import json
import os
from collections import defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

# Kosovo appears in flow sources but not in ISO 3166 lists / UN data
EXTRA_M49 = {412: ("XK", "Kosovo")}
# override points for countries whose geometric centroid falls OUTSIDE
# their own territory (bent/crescent shapes) - reported by a map user
CENTROID_OVERRIDES = {
    "NO": (8.8, 61.2),
    "HR": (15.9, 45.5),
    "VN": (105.85, 21.0),
}
EXTRA_CENTROIDS = {
    "XK": (20.9, 42.6),
    "HK": (114.17, 22.32),
    "MO": (113.55, 22.19),
    "TW": (120.96, 23.7),
    "EH": (-12.9, 24.2),
}


def load_iso():
    with open(os.path.join(RAW, "iso3166.json"), encoding="utf8") as f:
        entries = json.load(f)
    m49_to_iso2 = {}
    names = {}
    for e in entries:
        m49_to_iso2[int(e["country-code"])] = e["alpha-2"]
        names[e["alpha-2"]] = e["name"]
    for code, (iso2, name) in EXTRA_M49.items():
        m49_to_iso2[code] = iso2
        names[iso2] = name
    return m49_to_iso2, names


def load_centroids():
    cents = dict(EXTRA_CENTROIDS)
    with open(os.path.join(RAW, "centroids.csv"), encoding="utf8") as f:
        for row in csv.DictReader(f):
            iso2 = row["ISO"]
            if iso2 and iso2 not in cents:
                cents[iso2] = (float(row["longitude"]), float(row["latitude"]))
    cents.update(CENTROID_OVERRIDES)
    return cents


def load_stocks(m49_to_iso2):
    """stocks[dest][orig] = [stock values per reference year] (both sexes)."""
    wb = openpyxl.load_workbook(os.path.join(RAW, "ims2024_matrix.xlsx"), read_only=True)
    ws = wb["Table 1"]
    stocks = defaultdict(dict)
    skipped = set()
    for row in ws.iter_rows(min_row=12, values_only=True):
        dest_code, orig_code = row[4], row[6]
        if dest_code is None or orig_code is None:
            continue
        try:
            dest_code, orig_code = int(dest_code), int(orig_code)
        except (TypeError, ValueError):
            continue
        dest = m49_to_iso2.get(dest_code)
        orig = m49_to_iso2.get(orig_code)
        if dest is None or orig is None:
            for c, n in ((dest_code, row[1]), (orig_code, row[5])):
                if c is not None and int(c) < 900 and m49_to_iso2.get(int(c)) is None:
                    skipped.add((c, str(n)))
            continue
        if dest == orig:
            continue
        vals = [int(v) if v is not None else 0 for v in row[7:15]]
        stocks[dest][orig] = vals
    if skipped:
        print("skipped non-ISO locations:", sorted(skipped))
    return stocks


def main():
    os.makedirs(OUT, exist_ok=True)
    m49_to_iso2, names = load_iso()
    cents = load_centroids()
    stocks = load_stocks(m49_to_iso2)
    print(f"{len(stocks)} destination countries loaded")

    used = {"XK"}  # Kosovo: absent from UN data but present in the flow sources
    for dest in stocks:
        used.add(dest)
        used.update(stocks[dest])

    countries = {}
    missing = []
    for iso2 in sorted(used):
        if iso2 in cents:
            lon, lat = cents[iso2]
            countries[iso2] = {"name": names[iso2], "lon": round(lon, 3), "lat": round(lat, 3)}
        else:
            missing.append(iso2)
    if missing:
        print("no centroid for:", missing)
    with open(os.path.join(OUT, "countries.json"), "w", encoding="utf8") as f:
        json.dump(countries, f, separators=(",", ":"))
    print(f"countries.json: {len(countries)} countries")


if __name__ == "__main__":
    main()
