"""Build 1990-2020 gross migration flow JSONs from Abel & Cohen's bilateral
flow estimates (https://doi.org/10.6084/m9.figshare.7731233, updated 2025).

Input (in raw/):
  abel_bilat_mig.csv  columns: year0, orig, dest (ISO3), six method estimates.
    We use da_pb_closed, the method recommended in Abel & Cohen (2019).

Output (in data/):
  flows_1990_2000.json, flows_2000_2010.json, flows_2010_2020.json
  flows[A][B] = estimated gross migration B->A over the decade (sum of the
  two five-year periods); flows[A][A] = A's net (gross in - gross out).

Unlike the stock-difference method (still used for 2020-2024 and pre-1990),
these are true flow estimates from demographic accounting, so emigration is
visible even where deaths shrink the migrant stock.
"""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

DECADES = {1990: (1990, 1995), 2000: (2000, 2005), 2010: (2010, 2015)}
PAIR_THRESHOLD = 100
METHOD = "da_pb_closed"


def load_iso3_to_iso2():
    with open(os.path.join(RAW, "iso3166.json"), encoding="utf8") as f:
        entries = json.load(f)
    m = {e["alpha-3"]: e["alpha-2"] for e in entries}
    m["XKX"] = "XK"
    # dissolved entities used in early periods, mapped to main successor
    m["SUD"] = "SD"  # Sudan incl. pre-2011 South Sudan
    m["SCG"] = "RS"  # Serbia and Montenegro
    return m


def main():
    iso3to2 = load_iso3_to_iso2()
    with open(os.path.join(OUT, "countries.json"), encoding="utf8") as f:
        known = set(json.load(f))

    # gross[decade][dest][orig] = summed flow orig->dest
    gross = {d: defaultdict(lambda: defaultdict(float)) for d in DECADES}
    unmatched = set()
    with open(os.path.join(RAW, "abel_bilat_mig.csv"), newline="", encoding="utf8") as f:
        for row in csv.DictReader(f):
            y = int(row["year0"])
            decade = 1990 if y < 2000 else 2000 if y < 2010 else 2010
            orig = iso3to2.get(row["orig"])
            dest = iso3to2.get(row["dest"])
            for iso3, iso2 in ((row["orig"], orig), (row["dest"], dest)):
                if iso2 is None:
                    unmatched.add(iso3)
            if orig is None or dest is None or orig == dest:
                continue
            if orig not in known or dest not in known:
                continue
            v = float(row[METHOD] or 0)
            if v > 0:
                gross[decade][dest][orig] += v
    if unmatched:
        print("unmatched ISO3 codes (skipped):", sorted(unmatched))

    for decade in DECADES:
        g = gross[decade]
        flows = defaultdict(dict)
        totals = defaultdict(float)
        for a in g:
            for b, v in g[a].items():
                totals[a] += v
                totals[b] -= v
                if v >= PAIR_THRESHOLD:
                    flows[a][b] = round(v)
        for c, t in totals.items():
            if flows[c] or abs(t) >= PAIR_THRESHOLD:
                flows[c][c] = round(t)
        flows = {k: v for k, v in flows.items() if v}
        path = os.path.join(OUT, f"flows_{decade}_{decade + 10}.json")
        with open(path, "w", encoding="utf8") as f:
            json.dump(flows, f, separators=(",", ":"))
        print(f"{path}: {len(flows)} countries, {os.path.getsize(path)//1024} KB")


if __name__ == "__main__":
    main()
