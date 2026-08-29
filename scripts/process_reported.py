"""Build the country-specific 2024 year (flows_2024_2025.json) from OFFICIALLY
REPORTED statistics — only sources that publish BOTH directions:

- Eurostat (calendar 2024): migr_imm5prv (immigration by country of previous
  residence) + migr_emi3nxt (emigration by country of next residence) for
  ~30 European reporting countries. raw/eurostat_imm.json / eurostat_emi.json,
  fetched from the API with format=JSON&time=2024&age=TOTAL&sex=T.
- Australia (FY 2024-25): ABS Overseas Migration cubes 2 (arrivals) and 3
  (departures) by country of birth — raw/abs_2.xlsx / abs_3.xlsx, tables
  2.1 / 3.1. Country of birth is a proxy for origin/destination.

Output:
  data/flows_2024_2025.json   pair flows involving reporting countries only
  data/extended_years.json    {"2024_2025": [reporting ISO2s]} — the app only
                              offers the year when one of these is selected.
"""
import json
import os
from collections import defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data")
THRESHOLD = 50

EUROSTAT_GEO_FIX = {"EL": "GR", "UK": "GB"}

ABS_NAME_FIX = {
    "PNG": "Papua New Guinea", "Micronesia, F S": "Micronesia, Federated States of",
    "Marshall Is": "Marshall Islands", "N Mariana Is": "Northern Mariana Islands",
    "New Zealand": "New Zealand", "UK, C Is & IOM(f)": "United Kingdom of Great Britain and Northern Ireland",
    "UK, C Is & IOM": "United Kingdom of Great Britain and Northern Ireland",
    "Ireland": "Ireland", "South Africa": "South Africa",
    "Korea, South": "Korea, Republic of", "Korea, North": "Korea, Democratic People's Republic of",
    "USA(d)": "United States of America", "USA": "United States of America",
    "Viet Nam": "Viet Nam", "Vietnam": "Viet Nam",
    "Hong Kong": "Hong Kong", "Hong Kong (SAR of China)": "Hong Kong",
    "Macau (SAR of China)": "Macao", "Taiwan": "Taiwan, Province of China",
    "China(d)": "China", "China": "China", "Burma (Myanmar)": "Myanmar",
    "Laos": "Lao People's Democratic Republic", "Brunei": "Brunei Darussalam",
    "East Timor": "Timor-Leste", "Timor-Leste": "Timor-Leste",
    "Iran": "Iran, Islamic Republic of", "Syria": "Syrian Arab Republic",
    "Turkey": "Türkiye", "Russia": "Russian Federation",
    "Bolivia": "Bolivia, Plurinational State of",
    "Venezuela": "Venezuela, Bolivarian Republic of",
    "Congo, DR": "Congo, Democratic Republic of the", "Congo, Republic of": "Congo",
    "Cote d'Ivoire": "Côte d'Ivoire", "Ivory Coast": "Côte d'Ivoire",
    "Tanzania": "Tanzania, United Republic of", "Moldova": "Moldova, Republic of",
    "Macedonia": "North Macedonia", "North Macedonia": "North Macedonia",
    "Czechia": "Czechia", "Czech Republic": "Czechia",
    "Cape Verde": "Cabo Verde", "Swaziland": "Eswatini",
    "Palestine": "Palestine, State of", "Gaza Strip and West Bank": "Palestine, State of",
    "Antigua/Barbuda": "Antigua and Barbuda", "Bosnia/Herzegov": "Bosnia and Herzegovina",
    "Congo, Dem Rep": "Congo, Democratic Republic of the", "Congo, Rep": "Congo",
    "Cent Africa Rep": "Central African Republic", "Dominican Rep": "Dominican Republic",
    "Czech Rep": "Czechia", "St Vincent/Gren": "Saint Vincent and the Grenadines",
    "St Kitts/Nevis": "Saint Kitts and Nevis", "Trinidad/Tobago": "Trinidad and Tobago",
    "UAE": "United Arab Emirates", "Sth Eastern Europe, nfd": None, "Australia": None,
}


def load_iso_names():
    with open(os.path.join(RAW, "iso3166.json"), encoding="utf8") as f:
        entries = json.load(f)
    by_name = {e["name"].lower(): e["alpha-2"] for e in entries}
    by_name["kosovo"] = "XK"
    return by_name


def jsonstat_values(path):
    """Yield (geo, partner, value) picking the best agedef per cell."""
    with open(path, encoding="utf8") as f:
        d = json.load(f)
    dims = d["id"]
    sizes = d["size"]
    cats = {dim: list(d["dimension"][dim]["category"]["index"]) for dim in dims}
    strides = {}
    acc = 1
    for dim, size in zip(reversed(dims), reversed(sizes)):
        strides[dim] = acc
        acc *= size
    values = {int(k): v for k, v in d["value"].items()}
    gi, pi = dims.index("geo"), dims.index("partner")
    agedefs = cats.get("agedef", [None])
    best = {}
    for g_idx, geo in enumerate(cats["geo"]):
        for p_idx, partner in enumerate(cats["partner"]):
            for a_idx, _ in enumerate(agedefs):
                flat = g_idx * strides["geo"] + p_idx * strides["partner"]
                if "agedef" in strides:
                    flat += a_idx * strides["agedef"]
                v = values.get(flat)
                if v is not None:
                    key = (geo, partner)
                    best[key] = max(best.get(key, 0), int(v))
    return best


def map_code(code, known):
    code = EUROSTAT_GEO_FIX.get(code, code)
    return code if code in known else None


def load_abs(path, sheet, by_name, known):
    """{partner_iso2: value} from the FY2024-25 (last) column of an ABS table."""
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = next(r for r in rows if r and str(r[0]).startswith("SACC"))
    last_col = max(i for i, c in enumerate(header) if c is not None)
    assert str(header[last_col]).strip().startswith("2024-25"), header[last_col]
    out = {}
    misses = set()
    started = False
    for r in rows:
        if r is header:
            started = True
            continue
        if not started or not r or r[1] is None:
            continue
        name = str(r[1]).strip()
        base = name.split("(")[0].strip()
        fixed = ABS_NAME_FIX.get(name, ABS_NAME_FIX.get(base, base))
        if fixed is None or "nec" in name or "nfd" in name or "Not stated" in name or "Total" in name:
            continue
        iso2 = by_name.get(str(fixed).lower())
        if iso2 is None or iso2 not in known:
            misses.add(name)
            continue
        v = r[last_col]
        if v is None:
            continue
        try:
            out[iso2] = out.get(iso2, 0) + int(v)
        except (TypeError, ValueError):
            continue
    if misses:
        print(f"  {sheet}: unmatched (skipped): {sorted(misses)[:12]}{'...' if len(misses) > 12 else ''}")
    return out


def main():
    with open(os.path.join(OUT, "countries.json"), encoding="utf8") as f:
        known = set(json.load(f))
    by_name = load_iso_names()

    # flow[(A, B)] = migration B -> A
    flow = {}
    reporters = set()

    # Eurostat immigration: geo=destination, partner=previous residence.
    imm = jsonstat_values(os.path.join(RAW, "eurostat_imm.json"))
    for (geo, partner), v in imm.items():
        a, b = map_code(geo, known), map_code(partner, known)
        if a and b and a != b:
            reporters.add(a)
            flow[(a, b)] = v  # destination's own report wins
    # Eurostat emigration: geo=origin, partner=next residence; only fill
    # pairs the destination didn't report itself.
    emi = jsonstat_values(os.path.join(RAW, "eurostat_emi.json"))
    for (geo, partner), v in emi.items():
        a, b = map_code(partner, known), map_code(geo, known)  # flow b(geo) -> a(partner)
        if a and b and a != b:
            reporters.add(b)
            flow.setdefault((a, b), v)

    # Australia: arrivals of X-born -> flow X->AU; departures of X-born -> AU->X
    arr = load_abs(os.path.join(RAW, "abs_2.xlsx"), "Table 2.1", by_name, known)
    dep = load_abs(os.path.join(RAW, "abs_3.xlsx"), "Table 3.1", by_name, known)
    for x, v in arr.items():
        if x != "AU":
            flow.setdefault(("AU", x), v)
    for x, v in dep.items():
        if x != "AU":
            flow.setdefault((x, "AU"), v)
    reporters.add("AU")

    flows = defaultdict(dict)
    totals = defaultdict(int)
    for (a, b), v in flow.items():
        if v < THRESHOLD:
            continue
        flows[a][b] = v
        totals[a] += v
        totals[b] -= v
    for c in reporters:
        flows[c][c] = totals.get(c, 0)

    path = os.path.join(OUT, "flows_2024_2025.json")
    with open(path, "w", encoding="utf8") as f:
        json.dump(flows, f, separators=(",", ":"))
    print(f"{path}: {len(flows)} countries, {os.path.getsize(path)//1024} KB")

    ext = {"2024_2025": sorted(reporters)}
    with open(os.path.join(OUT, "extended_years.json"), "w", encoding="utf8") as f:
        json.dump(ext, f, separators=(",", ":"))
    print(f"extended_years.json: {len(reporters)} reporting countries: {sorted(reporters)}")


if __name__ == "__main__":
    main()
