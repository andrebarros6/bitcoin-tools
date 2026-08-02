"""
Builds the join between INE freguesia geo codes (ine_precos_m2_full.csv, indicator
0012234) and DGT CAOP2025 freguesia boundary identifiers (dtmnfr, in
caop_freguesias_properties.json).

Why this is non-trivial:
- INE's 9-digit freguesia codes and CAOP's 6-digit `dtmnfr` (DICOFRE) codes use
  unrelated numbering schemes -- no code-level mapping exists.
- The reliable key is (freguesia name, municipio name), matched case/accent-insensitive.
- CAOP2025's `freguesias` collection is Continente-only and, for ~50 parishes created
  by the 2013 administrative merger (Lei 11/2012), still stores the PRE-merger polygons
  separately rather than one dissolved "Uniao das freguesias de X e Y" polygon. INE
  reports the merged (post-2013) unit. So those need dissolving: N CAOP polygons -> 1
  INE freguesia_geo_cod, identified by parsing the "Uniao das freguesias de ..." name.
- Acores/Madeira freguesias (e.g. Funchal's 10 parishes) have NO boundary in this CAOP
  collection at all -- it's mainland-only. A different source is needed for those.

Output: caop_ine_join.csv with columns geo_cod, geo_dsg, municipio, dtmnfr_codes
(semicolon-separated list -- usually 1, more than 1 means "dissolve these CAOP
polygons into one shape for this freguesia").
"""
import json
import csv
import re
import os
import unicodedata
import urllib.request

VARCD = "0012234"
BASE_META = "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp"
DIR = os.path.dirname(os.path.abspath(__file__))
CAOP_PROPS_PATH = os.path.join(DIR, "caop_freguesias_properties.json")
INE_CSV_PATH = os.path.join(DIR, "ine_precos_m2_full.csv")
OUT_PATH = os.path.join(DIR, "caop_ine_join.csv")
UNMATCHED_PATH = os.path.join(DIR, "caop_ine_join_unmatched.csv")


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.strip().lower())


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_ine_geo_dims():
    meta = fetch_json(f"{BASE_META}?varcd={VARCD}&lang=PT")[0]
    municipios, freguesias = {}, []
    for entry in meta["Dimensoes"]["Categoria_Dim"]:
        for vals in entry.values():
            for v in vals:
                if v["dim_num"] != "2":
                    continue
                if v.get("categ_nivel") == "5":
                    municipios[v["categ_cod"]] = v["categ_dsg"]
                elif v.get("categ_nivel") == "6":
                    freguesias.append((v["categ_cod"], v["categ_dsg"]))
    return municipios, freguesias


def parse_union_name(name):
    """'Uniao das freguesias de/da/do X, Y e Z' -> ['X', 'Y', 'Z']"""
    m = re.match(r"Uni[aã]o das freguesias d[aeo]s? (.+)", name)
    if not m:
        return None
    body = m.group(1)
    parts = re.split(r",\s*| e ", body)
    return [p.strip() for p in parts if p.strip()]


def main():
    print("Fetching INE geography dimensions...", flush=True)
    municipios, freguesias = get_ine_geo_dims()

    with open(CAOP_PROPS_PATH, encoding="utf-8") as f:
        caop = json.load(f)

    caop_index = {}
    caop_by_muni = {}
    for feat in caop["features"]:
        p = feat["properties"]
        key = (norm(p["freguesia"]), norm(p["municipio"]))
        caop_index[key] = p["dtmnfr"]
        caop_by_muni.setdefault(norm(p["municipio"]), {})[norm(p["freguesia"])] = p["dtmnfr"]

    with open(INE_CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    active_codes = set(r["geo_cod"] for r in rows if r["geo_nivel"] == "6")

    matched, unmatched = [], []
    for fcod, fname in freguesias:
        if fcod not in active_codes:
            continue
        mcod = fcod[:7]
        mname = municipios.get(mcod, "")
        key = (norm(fname), norm(mname))
        dtmnfr = caop_index.get(key)
        if dtmnfr:
            matched.append((fcod, fname, mname, [dtmnfr]))
            continue
        constituents = parse_union_name(fname)
        if constituents:
            muni_map = caop_by_muni.get(norm(mname), {})
            codes = [muni_map.get(norm(c)) for c in constituents]
            if all(codes):
                matched.append((fcod, fname, mname, codes))
                continue
        unmatched.append((fcod, fname, mname))

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["geo_cod", "geo_dsg", "municipio", "dtmnfr_codes"])
        for fcod, fname, mname, codes in matched:
            writer.writerow([fcod, fname, mname, ";".join(codes)])

    with open(UNMATCHED_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["geo_cod", "geo_dsg", "municipio", "reason"])
        for fcod, fname, mname in unmatched:
            reason = "acores_madeira_not_in_caop" if fcod[0] in ("2", "3") else "name_mismatch"
            writer.writerow([fcod, fname, mname, reason])

    print(f"Matched: {len(matched)} / {len(active_codes)}", flush=True)
    print(f"Unmatched: {len(unmatched)} -> {UNMATCHED_PATH}", flush=True)
    print(f"Join written to {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
