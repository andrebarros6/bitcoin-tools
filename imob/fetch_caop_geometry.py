"""
Fetches full-resolution CAOP2025 freguesia geometry, paginated, and keeps only
the ~565 polygons matched in caop_ine_join.csv (INE freguesias with price data).

Why not filter server-side: the OGC API's per-property filter (?dtmnfr=X) takes
~20s per single feature regardless of payload size (looks like an unindexed
scan), and does not support comma-separated multi-value filters. A single
100-feature unfiltered page takes ~50s and 14MB (full CAOP precision, no
simplify param available). With 565 of 3049 features needed (~18.5%, spread
nationwide), paginating through everything and discarding non-matches
client-side is more reliable than 565 sequential ~20s filtered calls.

Output: caop_geometry_matched.geojson -- FeatureCollection with ONLY the
dtmnfr codes present in caop_ine_join.csv. Still full CAOP precision (not yet
simplified for web use -- that's a separate follow-up pass once a mapping
library/tolerance is chosen).
"""
import json
import csv
import os
import time
import urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
JOIN_CSV = os.path.join(DIR, "caop_ine_join.csv")
OUT_PATH = os.path.join(DIR, "caop_geometry_matched.geojson")
BASE_URL = "https://ogcapi.dgterritorio.gov.pt/collections/freguesias/items"
PAGE_SIZE = 200


def fetch_json(url, retries=4, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err


def load_wanted_codes():
    wanted = set()
    with open(JOIN_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for code in row["dtmnfr_codes"].split(";"):
                wanted.add(code.strip())
    return wanted


def main():
    wanted = load_wanted_codes()
    print(f"Looking for {len(wanted)} distinct CAOP dtmnfr codes", flush=True)

    matched = {}
    offset = 0
    total = None

    while total is None or offset < total:
        url = f"{BASE_URL}?limit={PAGE_SIZE}&offset={offset}&f=json"
        data = fetch_json(url)
        total = data["numberMatched"]
        for feat in data["features"]:
            dtmnfr = feat["properties"]["dtmnfr"]
            if dtmnfr in wanted:
                matched[dtmnfr] = feat
        offset += PAGE_SIZE
        print(f"  [{min(offset, total)}/{total}] pages fetched, {len(matched)}/{len(wanted)} matched so far", flush=True)
        if len(matched) == len(wanted):
            print("  All wanted codes found, stopping early.", flush=True)
            break

    missing = wanted - set(matched.keys())
    if missing:
        print(f"WARNING: {len(missing)} dtmnfr codes not found in CAOP: {sorted(missing)}", flush=True)

    fc = {"type": "FeatureCollection", "features": list(matched.values())}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)

    print(f"Wrote {len(matched)} features to {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
