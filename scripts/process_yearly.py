"""Build YEARLY gross migration flow JSONs (1960->2020) from the UNU-CRIS
imputed bilateral migration dataset (Standaert & Rayp, 2022).

Input:  raw/unu/migration_imputed_RIKS_dec2021.csv (annual bilateral stocks)
Output: data/flows_<y>_<y+1>.json for y in 1960..2019, same format as the
        decade files: flows[A][B] = stock increase of B-born living in A over
        the year (clamped at 0); flows[A][A] = A's total net.

Country-name matching is shared with process_early.py.
"""
import csv
import json
import os
from collections import defaultdict

from process_early import NAME_FIXES, load_iso_names, resolve

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

Y0, Y1 = 1960, 2020  # inclusive stock years; transitions Y0->Y0+1 .. Y1-1->Y1
NYEARS = Y1 - Y0 + 1
PAIR_THRESHOLD = 50  # yearly flows are ~1/10 of decade ones


def load_stocks():
    by_name = load_iso_names()
    misses = set()
    cache = {}

    def r(name):
        if name not in cache:
            cache[name] = resolve(name, by_name, misses)
        return cache[name]

    # stocks[(dest, orig)] = [stock per year, index year-Y0]
    stocks = defaultdict(lambda: [0] * NYEARS)
    path = os.path.join(RAW, "unu", "migration_imputed_RIKS_dec2021.csv")
    with open(path, newline="", encoding="utf8", errors="replace") as f:
        for row in csv.DictReader(f):
            s = row["stock"]
            if not s:
                continue
            y = int(row["year"])
            if not (Y0 <= y <= Y1):
                continue
            orig = r(row["origin"])
            dest = r(row["destination"])
            if orig is None or dest is None or orig == dest:
                continue
            stocks[(dest, orig)][y - Y0] = int(float(s))
    if misses:
        print("unmatched names (skipped):", sorted(misses))
    return stocks


def main():
    with open(os.path.join(OUT, "countries.json"), encoding="utf8") as f:
        known = set(json.load(f))
    stocks = load_stocks()
    print(f"{len(stocks)} country pairs loaded")

    total_bytes = 0
    for y in range(Y0, Y1):
        i = y - Y0
        flows = defaultdict(dict)
        totals = defaultdict(int)
        for (a, b), vals in stocks.items():
            d = vals[i + 1] - vals[i]
            if d == 0:
                continue
            totals[a] += d
            totals[b] -= d
            if d >= PAIR_THRESHOLD and a in known and b in known:
                flows[a][b] = d
        for c, t in totals.items():
            if c in known and (flows[c] or abs(t) >= PAIR_THRESHOLD):
                flows[c][c] = t
        flows = {k: v for k, v in flows.items() if v}
        path = os.path.join(OUT, f"flows_{y}_{y + 1}.json")
        with open(path, "w", encoding="utf8") as f:
            json.dump(flows, f, separators=(",", ":"))
        total_bytes += os.path.getsize(path)
    print(f"wrote {Y1 - Y0} yearly files, {total_bytes // 1024} KB total")


if __name__ == "__main__":
    main()
