"""
Extracts an INE housing-price indicator across all available geography levels
and time periods via the free JSON API.

Default (no args): varcd 0012234, median sale price EUR/m2 (Metodologia 2022),
Portugal -> NUTS -> municipio -> freguesia, Q4 2019 -> latest.

Usage: python ine_extractor.py [varcd] [dim3_code] [output_filename]
Example (bank appraisal series, municipio-level, 2011-present):
  python ine_extractor.py 0012248 T ine_avaliacao_bancaria_full.csv

Source: INE, json_indicador API (https://www.ine.pt/ine/json_indicador/)
"""
import json
import sys
import time
import urllib.request
import urllib.parse
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

VARCD = sys.argv[1] if len(sys.argv) > 1 else "0012234"
DIM3 = sys.argv[2] if len(sys.argv) > 2 else "H1"
OUT_FILENAME = sys.argv[3] if len(sys.argv) > 3 else "ine_precos_m2_full.csv"
BASE_META = "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp"
BASE_DATA = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKERS = 12


def fetch_json(url, retries=4):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise last_err


def get_meta():
    url = f"{BASE_META}?varcd={VARCD}&lang=PT"
    return fetch_json(url)[0]


def extract_dims(meta):
    time_codes = []
    geo_codes = []  # (cod, dsg, nivel)
    for entry in meta["Dimensoes"]["Categoria_Dim"]:
        for vals in entry.values():
            for v in vals:
                if v["dim_num"] == "1":
                    time_codes.append((v["categ_cod"], v["categ_dsg"]))
                elif v["dim_num"] == "2":
                    geo_codes.append((v["categ_cod"], v["categ_dsg"], v.get("categ_nivel", "?")))
    return time_codes, geo_codes


TIME_CHUNK_SIZE = 40  # keep Dim1 query strings short enough to avoid server-side timeouts


def chunk(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def fetch_data_batch(time_codes, geo_code, dim3=DIM3):
    dim1 = ",".join(c for c, _ in time_codes)
    params = {"op": "2", "varcd": VARCD, "Dim1": dim1, "Dim2": geo_code, "Dim3": dim3, "lang": "PT"}
    url = f"{BASE_DATA}?{urllib.parse.urlencode(params)}"
    result = fetch_json(url)[0]
    if "Sucesso" in result and "Falso" in result.get("Sucesso", {}):
        return None, result["Sucesso"]["Falso"][0]["Msg"]
    return result.get("Dados", {}), None


def worker(args):
    """Fetches one (geo_code, time_chunk) pair -- the unit of parallelism."""
    time_chunk, geo_cod, geo_dsg, nivel = args
    try:
        dados, err = fetch_data_batch(time_chunk, geo_cod)
    except Exception as e:
        return geo_cod, geo_dsg, nivel, None, str(e)
    if err:
        return geo_cod, geo_dsg, nivel, None, err
    return geo_cod, geo_dsg, nivel, dados, None


def main():
    print("Fetching metadata...", flush=True)
    meta = get_meta()
    time_codes, geo_codes = extract_dims(meta)
    print(f"Indicator: {meta['IndicadorNome']}", flush=True)
    print(f"Periods: {len(time_codes)} quarters, {time_codes[0][1]} -> {time_codes[-1][1]}", flush=True)

    by_nivel = {}
    for cod, dsg, nivel in geo_codes:
        by_nivel.setdefault(nivel, []).append((cod, dsg))
    for nivel, items in sorted(by_nivel.items()):
        print(f"  Geo nivel {nivel}: {len(items)} locations", flush=True)

    out_path = os.path.join(OUT_DIR, OUT_FILENAME)
    fieldnames = ["geo_cod", "geo_dsg", "geo_nivel", "periodo", "valor_eur_m2"]
    row_count = 0
    skipped_chunks = 0
    done = 0

    time_chunks = list(chunk(time_codes, TIME_CHUNK_SIZE))
    tasks = [
        (tc, cod, dsg, nivel)
        for cod, dsg, nivel in geo_codes
        for tc in time_chunks
    ]
    total = len(tasks)
    print(f"Total requests: {total} ({len(geo_codes)} geo codes x {len(time_chunks)} time chunks)", flush=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(worker, t) for t in tasks]
            for fut in as_completed(futures):
                geo_cod, geo_dsg, nivel, dados, err = fut.result()
                done += 1
                if done % 200 == 0:
                    print(f"  [{done}/{total}] ...", flush=True)
                if err:
                    print(f"    SKIP {geo_dsg} ({geo_cod}): {err}", flush=True)
                    skipped_chunks += 1
                    continue
                for period_label, entries in dados.items():
                    for e in entries:
                        val = e.get("valor")
                        writer.writerow({
                            "geo_cod": geo_cod,
                            "geo_dsg": geo_dsg,
                            "geo_nivel": nivel,
                            "periodo": period_label,
                            "valor_eur_m2": val if val not in (None, "") else "",
                        })
                        row_count += 1
                f.flush()

    print(f"\nWrote {row_count} rows to {out_path} ({skipped_chunks} time-chunks skipped)", flush=True)

    max_nivel = max(nivel for _, _, nivel in geo_codes)
    finest_count = sum(1 for _, _, nivel in geo_codes if nivel == max_nivel)
    print(f"Finest geo level attempted: nivel {max_nivel} ({finest_count} locations)", flush=True)


if __name__ == "__main__":
    main()
