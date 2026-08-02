"""Build per-period net migration flow JSONs from the UN International
Migrant Stock 2024 destination-origin matrix.

Inputs (in raw/):
  ims2024_matrix.xlsx  UN DESA, International Migrant Stock 2024 (Table 1)
  iso3166.json         M49 numeric -> ISO alpha-2 mapping (lukes/ISO-3166)
  centroids.csv        country centroids (gavinr/world-countries-centroids)

Outputs (in data/):
  flows_<t1>_<t2>.json  {ISO2: {ISO2: totalNet | pairNet, ...}} where
                        flows[A][B] = net migration into A from B over the
                        period (stock-difference estimate) and
                        flows[A][A] = A's total net over all partners.
  countries.json        {ISO2: {"name": ..., "lon": ..., "lat": ...}}

Method: same approximation as Max Galka's original Metrocosm map — the net
flow between two countries over a period is estimated as the change in
migrant stocks between them (ignores deaths and onward migration).
"""
import csv
import json
import os
from collections import defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

YEARS = [1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024]
PERIODS = [(1990, 2000), (2000, 2010), (2010, 2020), (2020, 2024)]
PAIR_THRESHOLD = 500  # drop pair entries smaller than this to keep files lean

# Kosovo appears in UN data but not in ISO 3166 lists
EXTRA_M49 = {412: ("XK", "Kosovo")}
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
    return cents


def load_stocks(m49_to_iso2):
    """stocks[dest][orig] = [values for YEARS] (both sexes)."""
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


def build_period(stocks, t1, t2):
    """flows[A][B] = gross migration B->A over the period (stock increase of
    B-born living in A, clamped at 0), so both directions of a pair are kept.
    flows[A][A] = A's total net (sum of raw pairwise deltas, unclamped)."""
    i1, i2 = YEARS.index(t1), YEARS.index(t2)
    flows = defaultdict(dict)
    totals = defaultdict(int)
    for a in stocks:
        for b in stocks[a]:
            vals = stocks[a][b]
            d = vals[i2] - vals[i1]  # change in B-born living in A
            totals[a] += d
            totals[b] -= d
            if d >= PAIR_THRESHOLD:
                flows[a][b] = d
    for c, t in totals.items():
        if flows[c] or abs(t) >= PAIR_THRESHOLD:
            flows[c][c] = t
    return {k: v for k, v in flows.items() if v}


def main():
    os.makedirs(OUT, exist_ok=True)
    m49_to_iso2, names = load_iso()
    cents = load_centroids()
    stocks = load_stocks(m49_to_iso2)
    print(f"{len(stocks)} destination countries loaded")

    used = set()
    for t1, t2 in PERIODS:
        flows = build_period(stocks, t1, t2)
        used.update(flows.keys())
        path = os.path.join(OUT, f"flows_{t1}_{t2}.json")
        with open(path, "w", encoding="utf8") as f:
            json.dump(flows, f, separators=(",", ":"))
        print(f"{path}: {len(flows)} countries, {os.path.getsize(path)//1024} KB")

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
