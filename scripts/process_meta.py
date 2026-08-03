"""Build yearly gross migration flow JSONs for 2019-2022 from Meta's
"International Migration Flows" dataset (Chi et al., PNAS 2025).

Input:  raw/meta_migration.csv (country_from, country_to ISO2,
        migration_month YYYY-MM, num_migrants) - monthly bilateral flow
        estimates for 181 countries, 2019-2022, from privacy-protected
        Facebook data weighted to population level.
        https://data.humdata.org/dataset/international-migration-flows

Output: data/flows_<y>_<y+1>.json for y in 2019..2022 (calendar-year sums;
        the id convention matches the stock-difference yearly files, so
        calendar 2019 -> flows_2019_2020.json). NOTE: overwrites the
        UNU-CRIS-derived 2019_2020 file with measured data.
"""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

YEARS = (2019, 2020, 2021, 2022)
PAIR_THRESHOLD = 50  # same as the other yearly files


def main():
    with open(os.path.join(OUT, "countries.json"), encoding="utf8") as f:
        known = set(json.load(f))

    # gross[year][dest][orig] = summed migrants orig->dest that calendar year
    gross = {y: defaultdict(lambda: defaultdict(int)) for y in YEARS}
    skipped = set()
    with open(os.path.join(RAW, "meta_migration.csv"), newline="", encoding="utf8") as f:
        for row in csv.DictReader(f):
            y = int(row["migration_month"][:4])
            a, b = row["country_to"], row["country_from"]
            if a not in known or b not in known:
                skipped.update(c for c in (a, b) if c not in known)
                continue
            if a == b:
                continue
            gross[y][a][b] += int(row["num_migrants"])
    if skipped:
        print("codes not in countries.json (skipped):", sorted(skipped))

    for y in YEARS:
        g = gross[y]
        flows = defaultdict(dict)
        totals = defaultdict(int)
        for a in g:
            for b, v in g[a].items():
                totals[a] += v
                totals[b] -= v
                if v >= PAIR_THRESHOLD:
                    flows[a][b] = v
        for c, t in totals.items():
            if flows[c] or abs(t) >= PAIR_THRESHOLD:
                flows[c][c] = t
        flows = {k: v for k, v in flows.items() if v}
        path = os.path.join(OUT, f"flows_{y}_{y + 1}.json")
        with open(path, "w", encoding="utf8") as f:
            json.dump(flows, f, separators=(",", ":"))
        print(f"{path}: {len(flows)} countries, {os.path.getsize(path)//1024} KB")


if __name__ == "__main__":
    main()
