#!/usr/bin/env python3
"""
One-off rebuild: reconstruct the full weekly cabaz alimentar history from
the Infogram chart matrix (all years, all rows) instead of relying on the
old fragile per-point date-text extraction, then re-merge with BTC/EUR
prices. Overwrites infogram_data_with_btc.csv from scratch.

Row index within a year's column = week number (chart is weekly, starting
on the first Wednesday of the year). Verified against 2022 data, where
the existing recorded dates line up exactly with this row-index math.
"""

import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests

INFOGRAM_URL = "https://infogram.com/cabaz-alimentar-desde-2022-adl-1hmr6g8oqqrwz2n"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_CSV = SCRIPT_DIR / "infogram_data_with_btc.csv"
BTC_CSV_PATH = SCRIPT_DIR / ".." / "data" / "btc_eur.csv"

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def to_portuguese_date(d):
    return f"{d.day} de {MONTHS_PT[d.month - 1]} de {d.year}"


def first_wednesday(year):
    d = datetime(year, 1, 1)
    while d.weekday() != 2:
        d += timedelta(days=1)
    return d


def fetch_infogram_data(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"

    match = re.search(
        r"window\.infographicData\s*=\s*({.*?});?\s*(?:</script>|$)",
        response.text,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not find window.infographicData in the page")

    return json.loads(match.group(1))


def find_chart_data(infogram_data):
    entities = (
        infogram_data.get("elements", {})
        .get("content", {})
        .get("content", {})
        .get("entities", {})
    )
    for entity in entities.values():
        chart_data = entity.get("props", {}).get("chartData")
        if chart_data:
            return chart_data
    raise RuntimeError("No chart data found on the page")


def extract_all_points(chart_data):
    """Return sorted list of (date, price) reconstructed from row index."""
    rows = chart_data["data"][0]
    header_row, data_rows = rows[0], rows[1:]

    years = [
        cell["value"] if isinstance(cell, dict) else cell for cell in header_row
    ]

    points = []
    for col_idx, year in enumerate(years):
        if year is None:
            continue
        year = int(year)
        week0 = first_wednesday(year)

        for row_idx, row in enumerate(data_rows):
            cell = row[col_idx] if col_idx < len(row) else None
            if cell is None:
                continue
            value = cell["value"] if isinstance(cell, dict) else cell
            if value is None:
                continue

            cleaned = re.sub(r"[€\s]", "", str(value)).replace(",", ".")
            try:
                price = float(cleaned)
            except ValueError:
                continue

            date = week0 + timedelta(weeks=row_idx)
            points.append((date, price))

    points.sort()
    return points


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


def main():
    print(f"Fetching {INFOGRAM_URL} ...")
    infogram_data = fetch_infogram_data(INFOGRAM_URL)
    chart_data = find_chart_data(infogram_data)

    points = extract_all_points(chart_data)
    print(f"Reconstructed {len(points)} weekly cabaz data points")

    print("Loading BTC/EUR prices ...")
    btc_data = load_btc_prices(BTC_CSV_PATH)
    print(f"Loaded {len(btc_data)} BTC/EUR price points")

    rows = []
    for date, food_price_eur in points:
        btc_price_eur = find_closest_btc_price(date, btc_data)
        price_in_btc = food_price_eur / btc_price_eur
        rows.append({
            "Date": to_portuguese_date(date),
            "Price": food_price_eur,
            "BTC_Price_EUR": btc_price_eur,
            "Price_in_BTC": price_in_btc,
        })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["Date", "Price", "BTC_Price_EUR", "Price_in_BTC"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
