"""
Summarizes what changed in blended_municipio_series.csv after a regional
data refresh -- run after blend_series.py, before committing, so it can
diff the new working-tree CSV against the last-committed version.

Finds the newest period_date added across municipios and reports the
biggest EUR/m2 movers for that period. Plain-text output, meant to be
read by a human (or fed to a LinkedIn-drafting step later) -- not JSON.

Usage: python summarize_regional_update.py
"""
import csv
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DIR = Path(__file__).resolve().parent
CSV_PATH = DIR / "blended_municipio_series.csv"


def load_current():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_previous():
    result = subprocess.run(
        ["git", "show", "HEAD:imob/blended_municipio_series.csv"],
        cwd=DIR.parent, capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    lines = result.stdout.splitlines()
    return list(csv.DictReader(lines))


def latest_period_by_geo(rows, nivel="5"):
    latest = {}
    for r in rows:
        if r["geo_nivel"] != nivel:
            continue
        cod = r["geo_cod"]
        if cod not in latest or r["period_date"] > latest[cod]["period_date"]:
            latest[cod] = r
    return latest


def main():
    current = load_current()
    previous = load_previous()

    cur_latest = latest_period_by_geo(current)
    prev_latest = latest_period_by_geo(previous)

    newest_period = max((r["period_date"] for r in cur_latest.values()), default=None)
    prev_newest_period = max((r["period_date"] for r in prev_latest.values()), default=None)

    print("Regional housing price data update")
    print("=" * 40)

    if newest_period == prev_newest_period:
        print("Newest period unchanged; underlying values may have been revised.")
    else:
        print(f"New period added: {newest_period} (previously: {prev_newest_period})")

    n_new_period = sum(1 for r in cur_latest.values() if r["period_date"] == newest_period)
    print(f"Municipios with data for {newest_period}: {n_new_period}")

    # Compare EUR/m2 movement for municipios present at both the new latest
    # period and their own previous latest period.
    movers = []
    for cod, cur_row in cur_latest.items():
        prev_row = prev_latest.get(cod)
        if not prev_row or not cur_row["valor_eur_m2"] or not prev_row["valor_eur_m2"]:
            continue
        if cur_row["period_date"] == prev_row["period_date"]:
            continue  # no new data point for this municipio
        cur_val = float(cur_row["valor_eur_m2"])
        prev_val = float(prev_row["valor_eur_m2"])
        pct = (cur_val - prev_val) / prev_val * 100
        movers.append((cod, cur_row["geo_dsg"], prev_val, cur_val, pct))

    movers.sort(key=lambda m: abs(m[4]), reverse=True)

    print(f"\nMunicipios with new data points this run: {len(movers)}")
    if movers:
        print("\nTop movers (EUR/m2, previous period -> newest period):")
        for cod, name, prev_val, cur_val, pct in movers[:10]:
            sign = "+" if pct >= 0 else ""
            print(f"  {name}: EUR{prev_val:,.0f} -> EUR{cur_val:,.0f} ({sign}{pct:.1f}%)")

    national_cur = cur_latest.get("PT")
    national_prev = prev_latest.get("PT")
    if national_cur and national_prev and national_cur["period_date"] != national_prev["period_date"]:
        nat_pct = (float(national_cur["valor_eur_m2"]) - float(national_prev["valor_eur_m2"])) / float(national_prev["valor_eur_m2"]) * 100
        print(f"\nNational (PT): EUR{float(national_prev['valor_eur_m2']):,.0f} -> EUR{float(national_cur['valor_eur_m2']):,.0f} ({nat_pct:+.1f}%)")


if __name__ == "__main__":
    main()
