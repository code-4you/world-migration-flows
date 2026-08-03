"""Build yearly flow JSONs 1990-2023 (and the 2020-2024 period file) from the
Gaskin & Abel deep-learning migration estimates.

Input:  raw/gaskin_mig_bilateral.csv from
        https://huggingface.co/datasets/ThGaskin/Migration_flows
        (Estimates/mig_bilateral.csv; "Deep learning four decades of human
        migration", arXiv:2506.22821; GPL-3.0)
        Columns: Origin ISO, Destination ISO (ISO3), Year, ..., mig_prev
        (flow by previous residence), ... Year 2024 rows exist but are empty.

Output: data/flows_<y>_<y+1>.json for y in 1990..2023 (overwrites the
        UNU-CRIS/Meta-derived files for those years) and
        data/flows_2020_2024.json (sum of years 2020-2023, replacing the
        UN stock-difference version). Same format as the other files.
"""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

Y0, Y1 = 1990, 2023  # inclusive years with data
YEAR_THRESHOLD = 50
PERIOD_THRESHOLD = 100


def load_iso3_to_iso2():
    with open(os.path.join(RAW, "iso3166.json"), encoding="utf8") as f:
        entries = json.load(f)
    m = {e["alpha-3"]: e["alpha-2"] for e in entries}
    m["XKX"] = "XK"
    return m


def write_flows(path, gross, threshold):
    flows = defaultdict(dict)
    totals = defaultdict(float)
    for a in gross:
        for b, v in gross[a].items():
            totals[a] += v
            totals[b] -= v
            if v >= threshold:
                flows[a][b] = round(v)
    for c, t in totals.items():
        if flows[c] or abs(t) >= threshold:
            flows[c][c] = round(t)
    flows = {k: v for k, v in flows.items() if v}
    with open(path, "w", encoding="utf8") as f:
        json.dump(flows, f, separators=(",", ":"))
    return len(flows), os.path.getsize(path)


def main():
    iso3to2 = load_iso3_to_iso2()
    with open(os.path.join(OUT, "countries.json"), encoding="utf8") as f:
        known = set(json.load(f))

    # gross[year][dest][orig] = flow orig->dest during that year
    gross = {y: defaultdict(lambda: defaultdict(float)) for y in range(Y0, Y1 + 1)}
    unmatched = set()
    with open(os.path.join(RAW, "gaskin_mig_bilateral.csv"), newline="", encoding="utf8") as f:
        for row in csv.DictReader(f):
            v = row["mig_prev"]
            if not v:
                continue
            y = int(row["Year"])
            if not (Y0 <= y <= Y1):
                continue
            orig = iso3to2.get(row["Origin ISO"])
            dest = iso3to2.get(row["Destination ISO"])
            for iso3, iso2 in ((row["Origin ISO"], orig), (row["Destination ISO"], dest)):
                if iso2 is None:
                    unmatched.add(iso3)
            if orig is None or dest is None or orig == dest:
                continue
            if orig not in known or dest not in known:
                continue
            fv = float(v)
            if fv > 0:
                gross[y][dest][orig] += fv
    if unmatched:
        print("unmatched ISO3 codes (skipped):", sorted(unmatched))

    total_bytes = 0
    for y in range(Y0, Y1 + 1):
        n, size = write_flows(os.path.join(OUT, f"flows_{y}_{y + 1}.json"), gross[y], YEAR_THRESHOLD)
        total_bytes += size
    print(f"wrote {Y1 - Y0 + 1} yearly files, {total_bytes // 1024} KB total")

    # 2020-2024 period = flows during 2020..2023
    period = defaultdict(lambda: defaultdict(float))
    for y in range(2020, 2024):
        for a in gross[y]:
            for b, v in gross[y][a].items():
                period[a][b] += v
    n, size = write_flows(os.path.join(OUT, "flows_2020_2024.json"), period, PERIOD_THRESHOLD)
    print(f"flows_2020_2024.json: {n} countries, {size // 1024} KB")


if __name__ == "__main__":
    main()
