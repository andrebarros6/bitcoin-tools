"""
Builds the final web-ready freguesia boundary file:
1. Tags each raw CAOP feature (caop_geometry_matched.geojson) with its INE
   geo_cod (from caop_ine_join.csv), so post-2013-merger union parishes that
   map to multiple CAOP polygons share the same geo_cod.
2. Shells out to mapshaper (via npx) to dissolve by geo_cod -- collapses the
   ~46 multi-polygon union cases into one shape each -- then simplifies for
   web use.

Requires Node.js + npx (mapshaper installed on demand via npx --yes).

Output: freguesias_web.geojson -- one feature per INE freguesia geo_cod,
properties: geo_cod, geo_dsg, municipio. Simplified for web rendering.
"""
import json
import csv
import os
import subprocess

DIR = os.path.dirname(os.path.abspath(__file__))
JOIN_CSV = os.path.join(DIR, "caop_ine_join.csv")
RAW_GEOJSON = os.path.join(DIR, "caop_geometry_matched.geojson")
TAGGED_GEOJSON = os.path.join(DIR, "_tagged_for_dissolve.geojson")
DISSOLVED_GEOJSON = os.path.join(DIR, "_dissolved.geojson")
OUT_GEOJSON = os.path.join(DIR, "freguesias_web.geojson")

SIMPLIFY_PCT = "8%"  # visual-vector-retain percentage; tune after visual check


def load_dtmnfr_to_ine():
    mapping = {}
    with open(JOIN_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for code in row["dtmnfr_codes"].split(";"):
                mapping[code.strip()] = {
                    "geo_cod": row["geo_cod"],
                    "geo_dsg": row["geo_dsg"],
                    "municipio": row["municipio"],
                }
    return mapping


def tag_features():
    mapping = load_dtmnfr_to_ine()
    with open(RAW_GEOJSON, encoding="utf-8") as f:
        fc = json.load(f)

    tagged = 0
    for feat in fc["features"]:
        dtmnfr = feat["properties"]["dtmnfr"]
        info = mapping.get(dtmnfr)
        if info:
            feat["properties"] = dict(info)
            tagged += 1

    print(f"Tagged {tagged}/{len(fc['features'])} features with INE geo_cod", flush=True)
    with open(TAGGED_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)


def run_mapshaper():
    # Dissolve by geo_cod (merges multi-polygon unions), then simplify.
    cmd = [
        "npx", "--yes", "mapshaper",
        "-i", TAGGED_GEOJSON,
        "-dissolve2", "geo_cod", "copy-fields=geo_dsg,municipio",
        "-simplify", SIMPLIFY_PCT, "keep-shapes",
        "-o", DISSOLVED_GEOJSON, "format=geojson",
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
    os.replace(DISSOLVED_GEOJSON, OUT_GEOJSON)
    os.remove(TAGGED_GEOJSON)

    with open(OUT_GEOJSON, encoding="utf-8") as f:
        fc = json.load(f)
    print(f"Final: {len(fc['features'])} dissolved+simplified freguesia shapes -> {OUT_GEOJSON}", flush=True)
    size = os.path.getsize(OUT_GEOJSON)
    print(f"File size: {size / 1024 / 1024:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
