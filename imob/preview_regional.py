"""
Sanity-check preview: EUR/m2 and BTC/m2 evolution for a few sample regions,
using the INE extract (ine_precos_m2_full.csv) and existing BTC/EUR series
(../data/btc_eur.csv). Not the final UI -- just validates the data is usable
before building the map.
"""
import csv
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))
INE_CSV = os.path.join(DIR, "ine_precos_m2_full.csv")
BTC_CSV = os.path.join(DIR, "..", "data", "btc_eur.csv")

QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}


def parse_periodo(periodo):
    # '4.º Trimestre de 2025' -> (2025, '12-31')
    m = re.match(r"(\d)\D*Trimestre de (\d{4})", periodo)
    if not m:
        return None
    q, year = m.group(1), m.group(2)
    return f"{year}-{QUARTER_END[q]}"


def load_btc():
    btc = {}
    with open(BTC_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            btc[row["Date"]] = float(row["Price"])
    return btc


def nearest_btc_price(btc, date_str):
    """btc_eur.csv is monthly (always day 01), so match on year-month."""
    year_month = date_str[:7]
    candidate = f"{year_month}-01"
    if candidate in btc:
        return btc[candidate]
    return None


def main():
    with open(INE_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    btc = load_btc()

    regions = ["Lisboa", "Porto", "Évora"]
    print(f"{'Region':<10} {'Quarter':<12} {'EUR/m2':>10} {'BTC/m2':>12} {'BTC EUR px':>12}")
    for region in regions:
        muni_rows = [r for r in rows if r["geo_nivel"] == "5" and r["geo_dsg"] == region and r["valor_eur_m2"]]
        muni_rows.sort(key=lambda r: r["periodo"])
        for r in [muni_rows[0], muni_rows[len(muni_rows) // 2], muni_rows[-1]]:
            date_str = parse_periodo(r["periodo"])
            eur_m2 = float(r["valor_eur_m2"])
            btc_px = nearest_btc_price(btc, date_str) if date_str else None
            btc_m2 = eur_m2 / btc_px if btc_px else None
            btc_m2_str = f"{btc_m2:.6f}" if btc_m2 else "n/a"
            btc_px_str = f"{btc_px:,.0f}" if btc_px else "n/a"
            print(f"{region:<10} {r['periodo']:<12} {eur_m2:>10,.0f} {btc_m2_str:>12} {btc_px_str:>12}")
        print()

    # % change EUR vs BTC-denominated, first to last quarter, per region
    print("Summary: change from first to last available quarter")
    print(f"{'Region':<10} {'EUR/m2 change':>16} {'BTC/m2 change':>16}")
    for region in regions:
        muni_rows = [r for r in rows if r["geo_nivel"] == "5" and r["geo_dsg"] == region and r["valor_eur_m2"]]
        muni_rows.sort(key=lambda r: r["periodo"])
        first, last = muni_rows[0], muni_rows[-1]
        eur_first, eur_last = float(first["valor_eur_m2"]), float(last["valor_eur_m2"])
        eur_pct = (eur_last / eur_first - 1) * 100

        btc_first_px = nearest_btc_price(btc, parse_periodo(first["periodo"]))
        btc_last_px = nearest_btc_price(btc, parse_periodo(last["periodo"]))
        btc_first_m2 = eur_first / btc_first_px
        btc_last_m2 = eur_last / btc_last_px
        btc_pct = (btc_last_m2 / btc_first_m2 - 1) * 100

        print(f"{region:<10} {eur_pct:>+15.1f}% {btc_pct:>+15.1f}%")


if __name__ == "__main__":
    main()
