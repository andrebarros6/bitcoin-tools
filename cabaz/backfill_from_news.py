#!/usr/bin/env python3
"""
One-off backfill: the Infogram embed stopped updating after 2026-06-10,
but DECO PROteste kept publishing the weekly cabaz alimentar figure via
press release (picked up by Observador, Jornal Economico, CNN Portugal,
etc.). This fills the resulting gap using those reported values, cross
-checked against each other's reported week-over-week deltas.

Source articles (all published within a day or two of the Wednesday
price date they report on):
  17 jun 2026: 257.68  (observador.pt/2026/06/17/...)
  24 jun 2026: 256.81  (jornaleconomico.sapo.pt "desce-87-centimos...25681")
  01 jul 2026: 253.63  (jornaleconomico.sapo.pt "valor-mais-baixo...25363",
                        cross-checked: 256.81 - 3.17 = 253.64 ~= 253.63)
  08 jul 2026: 256.71  (observador.pt/2026/07/08/...,
                        cross-checked: 253.63 + 3.08 = 256.71 exact)
  15 jul 2026: 256.46  (observador.pt/2026/07/15/...)
  22 jul 2026: 251.29  (dnoticias.pt 2026/7/22, sol.iol.pt "-5.17 euros")
  29 jul 2026: 253.47  (jornaleconomico.sapo.pt, folhanacional.pt,
                        cross-checked: 251.29 + 2.18 = 253.47 exact)
  05 aug 2026: 253.60  (dnoticias.pt 2026/8/5, observador.pt, cnnportugal.iol.pt)
"""

import csv
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_CSV = SCRIPT_DIR / "infogram_data_with_btc.csv"
BTC_CSV_PATH = SCRIPT_DIR / ".." / "data" / "btc_eur.csv"

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

NEWS_POINTS = [
    (datetime(2026, 6, 17), 257.68),
    (datetime(2026, 6, 24), 256.81),
    (datetime(2026, 7, 1), 253.63),
    (datetime(2026, 7, 8), 256.71),
    (datetime(2026, 7, 15), 256.46),
    (datetime(2026, 7, 22), 251.29),
    (datetime(2026, 7, 29), 253.47),
    (datetime(2026, 8, 5), 253.60),
]


def to_portuguese_date(d):
    return f"{d.day} de {MONTHS_PT[d.month - 1]} de {d.year}"


def load_btc_prices(csv_path):
    btc_data = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                btc_date = datetime.strptime(row["Date"].strip(), "%Y-%m-%d")
                btc_price = float(str(row["Price"]).replace(",", ""))
                btc_data.append((btc_date, btc_price))
            except (ValueError, KeyError):
                continue

    btc_data.sort()
    if not btc_data:
        raise RuntimeError("No BTC price data loaded")
    return btc_data


def find_closest_btc_price(target_date, btc_data):
    return min(btc_data, key=lambda entry: abs((target_date - entry[0]).days))[1]


def load_existing_dates(csv_path):
    if not csv_path.exists():
        return set()
    with open(csv_path, "r", encoding="utf-8") as f:
        return {row["Date"] for row in csv.DictReader(f)}


def main():
    existing_dates = load_existing_dates(OUTPUT_CSV)
    new_points = [
        (date, price) for date, price in NEWS_POINTS
        if to_portuguese_date(date) not in existing_dates
    ]

    if not new_points:
        print("Nothing new to backfill.")
        return

    print("Loading BTC/EUR prices ...")
    btc_data = load_btc_prices(BTC_CSV_PATH)
    print(f"Loaded {len(btc_data)} BTC/EUR price points")

    new_rows = []
    for date, food_price_eur in new_points:
        btc_price_eur = find_closest_btc_price(date, btc_data)
        price_in_btc = food_price_eur / btc_price_eur

        date_str = to_portuguese_date(date)
        new_rows.append({
            "Date": date_str,
            "Price": food_price_eur,
            "BTC_Price_EUR": btc_price_eur,
            "Price_in_BTC": price_in_btc,
        })
        print(f"  {date_str}: cabaz EUR{food_price_eur:.2f}, BTC EUR{btc_price_eur:.2f}, {price_in_btc:.8f} BTC")

    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["Date", "Price", "BTC_Price_EUR", "Price_in_BTC"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"Appended {len(new_rows)} row(s) to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
