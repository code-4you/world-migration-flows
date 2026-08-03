"""Build pre-1990 net migration flow JSONs from the UNU-CRIS imputed
bilateral migration dataset (Standaert & Rayp, 2022).

Input (in raw/unu/):
  migration_imputed_RIKS_dec2021.csv
    columns: iso_or, origin, iso_des, destination, year, stock, flow, ...
    Annual imputed bilateral migrant stocks 1960-2020, Correlates of War
    style country codes; we match countries by NAME against ISO 3166.

Output (in data/):
  flows_1960_1970.json, flows_1970_1980.json, flows_1980_1990.json
  in the same format as process.py, using the same stock-difference method.

Countries are matched by name to keep centroids/labels consistent with the
UN-based periods; unmatched entities are reported and skipped.
"""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")

YEARS = [1960, 1970, 1980, 1990]
PERIODS = [(1960, 1970), (1970, 1980), (1980, 1990)]
PAIR_THRESHOLD = 100

# dataset name -> ISO name where simple matching fails (None = dissolved
# entity with no single ISO successor; skipped)
NAME_FIXES = {
    "Bahamas; The": "Bahamas",
    "Bolivia": "Bolivia, Plurinational State of",
    "Bonaire; Sint Eustatius and Saba": "Bonaire, Sint Eustatius and Saba",
    "Cape Verde": "Cabo Verde",
    "Central African Rep.": "Central African Republic",
    "Congo; Dem. Rep.": "Congo, Democratic Republic of the",
    "Congo; Rep.": "Congo",
    "Curacao": "Curaçao",
    "Czech Rep.": "Czechia",
    "Czech Republic": "Czechia",
    "Dominican Rep.": "Dominican Republic",
    "East and West Pakistan": "Pakistan",
    "East Timor": "Timor-Leste",
    "Egypt; Arab Rep.": "Egypt",
    "Gambia; The": "Gambia",
    "Hong Kong; SAR China": "Hong Kong",
    "Iran; Islamic Rep.": "Iran, Islamic Republic of",
    "Ivory Coast": "Côte d'Ivoire",
    "Korea; Dem. People's Rep.": "Korea, Democratic People's Republic of",
    "Korea; Rep.": "Korea, Republic of",
    "Kyrgyz Rep.": "Kyrgyzstan",
    "Lao People's Dem. Rep.": "Lao People's Democratic Republic",
    "Macao SAR; China": "Macao",
    "Macedonia": "North Macedonia",
    "Micronesia; Fed. Sts.": "Micronesia, Federated States of",
    "Moldova": "Moldova, Republic of",
    "Netherlands; The": "Netherlands, Kingdom of the",
    "Reunion": "Réunion",
    "Russia": "Russian Federation",
    "Sahrawi Arab Dem. Rep.": "Western Sahara",
    "Slovak Rep.": "Slovakia",
    "St. Helena": "Saint Helena, Ascension and Tristan da Cunha",
    "St. Kitts and Nevis": "Saint Kitts and Nevis",
    "St. Lucia": "Saint Lucia",
    "St. Pierre and Miquelon": "Saint Pierre and Miquelon",
    "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "Swaziland": "Eswatini",
    "Syrian Arab Rep.": "Syrian Arab Republic",
    "Taiwan": "Taiwan, Province of China",
    "Tanzania": "Tanzania, United Republic of",
    "Turkey": "Türkiye",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "United States": "United States of America",
    "Venezuela": "Venezuela, Bolivarian Republic of",
    "Vietnam": "Viet Nam",
    "Vietnam; Dem. Rep.": "Viet Nam",
    "West Bank and Gaza": "Palestine, State of",
    "Yemen Arab Rep.": "Yemen",
    "Yemen; Rep.": "Yemen",
    "Pitcairn Islands": "Pitcairn",
    "Kosovo": "Kosovo",
    "British Virgin Islands": "Virgin Islands (British)",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Falkland Islands": "Falkland Islands (Malvinas)",
    "Serbia-Montenegro": None,
    "USSR Soviet Union": None,
    "Netherlands Antilles": None,
    "Yugoslavia": None,
    "Czechoslovakia": None,
}


def load_iso_names():
    with open(os.path.join(RAW, "iso3166.json"), encoding="utf8") as f:
        entries = json.load(f)
    by_name = {e["name"].lower(): e["alpha-2"] for e in entries}
    by_name["kosovo"] = "XK"
    return by_name


def resolve(name, by_name, misses):
    fixed = NAME_FIXES.get(name, name)
    if fixed is None:
        return None
    iso2 = by_name.get(fixed.lower())
    if iso2 is None:
        misses.add(name)
    return iso2


def load_stocks(by_name):
    """stocks[dest][orig] = {year: stock}"""
    stocks = defaultdict(lambda: defaultdict(dict))
    misses = set()
    want = set(YEARS)
    path = os.path.join(RAW, "unu", "migration_imputed_RIKS_dec2021.csv")
    with open(path, newline="", encoding="utf8", errors="replace") as f:
        for row in csv.DictReader(f):
            year = int(row["year"])
            if year not in want:
                continue
            stock = row["stock"]
            if not stock:
                continue
            orig = resolve(row["origin"], by_name, misses)
            dest = resolve(row["destination"], by_name, misses)
            if orig is None or dest is None or orig == dest:
                continue
            stocks[dest][orig][year] = int(float(stock))
    if misses:
        print("unmatched names (skipped):", sorted(misses))
    return stocks


def build_period(stocks, t1, t2):
    """Same gross-flow format as process.py: flows[A][B] = stock increase of
    B-born living in A (clamped at 0); flows[A][A] = total net."""
    flows = defaultdict(dict)
    totals = defaultdict(int)
    for a in stocks:
        for b in stocks[a]:
            sa = stocks[a][b]  # b-born living in a
            d = sa.get(t2, 0) - sa.get(t1, 0)
            totals[a] += d
            totals[b] -= d
            if d >= PAIR_THRESHOLD:
                flows[a][b] = d
    for c, t in totals.items():
        if flows[c] or abs(t) >= PAIR_THRESHOLD:
            flows[c][c] = t
    return {k: v for k, v in flows.items() if v}


def main():
    by_name = load_iso_names()
    stocks = load_stocks(by_name)
    print(f"{len(stocks)} destination countries loaded")
    with open(os.path.join(OUT, "countries.json"), encoding="utf8") as f:
        known = set(json.load(f))
    for t1, t2 in PERIODS:
        flows = build_period(stocks, t1, t2)
        dropped = [c for c in flows if c not in known]
        if dropped:
            print(f"{t1}-{t2}: dropping countries without centroid: {dropped}")
            flows = {
                a: {b: v for b, v in row.items() if b in known}
                for a, row in flows.items()
                if a in known
            }
            flows = {a: row for a, row in flows.items() if row}
        path = os.path.join(OUT, f"flows_{t1}_{t2}.json")
        with open(path, "w", encoding="utf8") as f:
            json.dump(flows, f, separators=(",", ":"))
        print(f"{path}: {len(flows)} countries, {os.path.getsize(path)//1024} KB")


if __name__ == "__main__":
    main()
