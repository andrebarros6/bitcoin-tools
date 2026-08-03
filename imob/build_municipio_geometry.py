"""
Builds web-ready municipio boundary geometry for the map's default view.

Unlike freguesias, municipio-level has no 2013-merger dissolve step needed --
CAOP's 278 mainland municipios match INE's municipio names 1:1 directly.

Requires: caop_municipios_full.geojson already fetched (curl against
https://ogcapi.dgterritorio.gov.pt/collections/municipios/items?limit=300&f=json
-- ~200MB, ~90s, full CAOP precision, mainland only).
Requires INE municipio metadata (varcd 0012234's Dim2, nivel 5) fetched fresh
via pindicaMeta.jsp since we need geo_cod<->name pairs.

Requires Node.js + npx (mapshaper installed on demand).

Output: municipios_web.geojson -- one feature per INE municipio geo_cod,
properties: geo_cod, geo_dsg. Simplified for web rendering.
"""
import json
import os
import subprocess
import unicodedata
import urllib.request

VARCD = "0012234"
BASE_META = "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp"
DIR = os.path.dirname(os.path.abspath(__file__))
RAW_GEOJSON = os.path.join(DIR, "caop_municipios_full.geojson")
TAGGED_GEOJSON = os.path.join(DIR, "_tagged_municipios.geojson")
OUT_GEOJSON = os.path.join(DIR, "municipios_web.geojson")

SIMPLIFY_PCT = "5%"  # municipio shapes are simpler than freguesia unions, no dissolve needed


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.strip().lower()


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_ine_municipios():
    meta = fetch_json(f"{BASE_META}?varcd={VARCD}&lang=PT")[0]
    munis = {}
    for entry in meta["Dimensoes"]["Categoria_Dim"]:
        for vals in entry.values():
            for v in vals:
                if v["dim_num"] == "2" and v.get("categ_nivel") == "5":
                    munis[norm(v["categ_dsg"])] = {"geo_cod": v["categ_cod"], "geo_dsg": v["categ_dsg"]}
    return munis


def tag_features():
    ine_munis = get_ine_municipios()
    with open(RAW_GEOJSON, encoding="utf-8") as f:
        fc = json.load(f)

    tagged, missing = 0, []
    for feat in fc["features"]:
        name = feat["properties"]["municipio"]
        info = ine_munis.get(norm(name))
        if info:
            feat["properties"] = dict(info)
            tagged += 1
        else:
            missing.append(name)

    print(f"Tagged {tagged}/{len(fc['features'])} municipio features with INE geo_cod", flush=True)
    if missing:
        print(f"WARNING: unmatched CAOP municipios: {missing}", flush=True)

    with open(TAGGED_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)


def run_mapshaper():
    cmd = [
        "npx", "--yes", "mapshaper",
        "-i", TAGGED_GEOJSON,
        "-simplify", SIMPLIFY_PCT, "keep-shapes",
        "-o", OUT_GEOJSON, "format=geojson",
    ]
    print("Running:", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=DIR, capture_output=True, text=True, shell=True)
    print(result.stdout, flush=True)
    if result.returncode != 0:
        print(result.stderr, flush=True)
        raise RuntimeError("mapshaper failed")


def main():
    tag_features()
    run_mapshaper()
    os.remove(TAGGED_GEOJSON)

    with open(OUT_GEOJSON, encoding="utf-8") as f:
        fc = json.load(f)
    print(f"Final: {len(fc['features'])} simplified municipio shapes -> {OUT_GEOJSON}", flush=True)
    size = os.path.getsize(OUT_GEOJSON)
    print(f"File size: {size / 1024 / 1024:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
