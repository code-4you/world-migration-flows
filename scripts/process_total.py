"""Build data/flows_1960_2024.json: the whole-map "All decades" view, summing
the seven decade files (UNU-CRIS 1960-1990, Abel & Cohen 1990-2020,
Gaskin & Abel 2020-2024). Run after the other process scripts."""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
PERIODS = ["1960_1970", "1970_1980", "1980_1990", "1990_2000",
           "2000_2010", "2010_2020", "2020_2024"]

pair = defaultdict(float)
tot = defaultdict(float)
for p in PERIODS:
    with open(os.path.join(OUT, f"flows_{p}.json"), encoding="utf8") as f:
        data = json.load(f)
    for a, row in data.items():
        for b, v in row.items():
            if a == b:
                tot[a] += v
            else:
                pair[(a, b)] += v

flows = defaultdict(dict)
for (a, b), v in pair.items():
    flows[a][b] = round(v)
for c, t in tot.items():
    if flows[c] or abs(t) >= 100:
        flows[c][c] = round(t)

path = os.path.join(OUT, "flows_1960_2024.json")
with open(path, "w", encoding="utf8") as f:
    json.dump(flows, f, separators=(",", ":"))
print(f"{path}: {len(flows)} countries, {os.path.getsize(path)//1024} KB")
