"""Build YEARLY gross migration flow JSONs (1960->1990) from the UNU-CRIS
imputed bilateral migration dataset (Standaert & Rayp, 2022).

Input:  raw/unu/migration_imputed_RIKS_dec2021.csv (annual bilateral stocks)
Output: data/flows_<y>_<y+1>.json for y in 1960..1989, same format as the
        decade files: flows[A][B] = stock increase of B-born living in A over
        the year (clamped at 0); flows[A][A] = A's total net.

Years from 1990 on come from process_gaskin.py instead — do not extend Y1
past 1990 or this script will overwrite those better files.
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

Y0, Y1 = 1960, 1990  # inclusive stock years; transitions Y0->Y0+1 .. Y1-1->Y1
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

    # stocks[(dest, orig)] = [stock per year or None, index year-Y0].
    # Values are ADDED so entities that map to one ISO code merge (e.g.
    # "Vietnam; Dem. Rep." pre-1970 + unified "Vietnam" from 1980).
    stocks = defaultdict(lambda: [None] * NYEARS)
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
            i = y - Y0
            vals = stocks[(dest, orig)]
            vals[i] = (vals[i] or 0) + int(float(s))
    if misses:
        print("unmatched names (skipped):", sorted(misses))

    # Interior gaps (e.g. Vietnam 1971-1979, absent between its two entities)
    # are linearly interpolated so a decade of migration isn't dumped into the
    # single year where data resumes; leading/trailing gaps are held flat so
    # no flows are invented outside the observed range.
    for vals in stocks.values():
        known = [i for i, v in enumerate(vals) if v is not None]
        if not known:
            continue
        first, last = known[0], known[-1]
        for i in range(first):
            vals[i] = vals[first]
        for i in range(last + 1, NYEARS):
            vals[i] = vals[last]
        for a, b in zip(known, known[1:]):
            if b - a > 1:
                for i in range(a + 1, b):
                    vals[i] = vals[a] + (vals[b] - vals[a]) * (i - a) / (b - a)
        for i, v in enumerate(vals):
            vals[i] = int(v)
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
