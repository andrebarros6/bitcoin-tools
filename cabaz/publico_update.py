#!/usr/bin/env python3
"""
Weekly update from Publico's cabaz alimentar interactive.

Publico publishes the DECO PROteste weekly cabaz series inside the
SvelteKit bundle of its interactive page, as records shaped like:

    ano_2026:"2026-08-19",cabaz_2026:"253,5530159"

This is a better source than the Infogram embed used by
weekly_update.py: it carries an explicit ISO date per point (no
row-index date reconstruction to drift), it covers every year from 2022
in one payload, and it stays current when the Infogram chart stalls.

The bundle filename is content-hashed, so it is resolved from the page
rather than hardcoded.
"""

import csv
import re
from datetime import datetime
from pathlib import Path

import requests

PAGE_URL = (
    "https://www.publico.pt/interactivos/"
    "cabaz-alimentar-essencial-mais-caro-mais-barato/"
)
USER_AGENT = "Mozilla/5.0 (compatible; bitcoin-tools-bot/1.0)"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_CSV = SCRIPT_DIR / "infogram_data_with_btc.csv"
BTC_CSV_PATH = SCRIPT_DIR / ".." / "data" / "btc_eur.csv"

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

POINT_RE = re.compile(
    r'ano_(?P<year>\d{4}):"(?P<date>\d{4}-\d{2}-\d{2})",'
    r'cabaz_(?P=year):"(?P<price>[\d,]+)"'
)


def to_portuguese_date(d):
    return f"{d.day} de {MONTHS_PT[d.month - 1]} de {d.year}"


def fetch(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def find_bundle_url(page_html):
    match = re.search(r'_app/immutable/entry/_page\.svelte\.[a-z0-9]+\.js', page_html)
    if not match:
        raise RuntimeError("Could not find the interactive's page bundle")
    return PAGE_URL + match.group(0)


def extract_points(bundle_js):
    """Return sorted [(date, price)] parsed from the bundle records."""
    points = {}
    for match in POINT_RE.finditer(bundle_js):
        date = datetime.strptime(match.group("date"), "%Y-%m-%d")
        price = round(float(match.group("price").replace(",", ".")), 2)
        points[date] = price

    if not points:
        raise RuntimeError("No cabaz data points found — page structure may have changed")
    return sorted(points.items())


def load_btc_prices(csv_path):
    btc_data = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                btc_date = datetime.strptime(row["Date"].strip(), "%Y-%m-%d")
                btc_data.append((btc_date, float(str(row["Price"]).replace(",", ""))))
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
    print(f"Fetching {PAGE_URL} ...")
    bundle_url = find_bundle_url(fetch(PAGE_URL))
    print(f"Reading bundle {bundle_url.rsplit('/', 1)[-1]} ...")

    points = extract_points(fetch(bundle_url))
    print(f"Found {len(points)} weekly cabaz data points "
          f"({points[0][0].date()} to {points[-1][0].date()})")

    existing_dates = load_existing_dates(OUTPUT_CSV)
    new_points = [
        (date, price) for date, price in points
        if to_portuguese_date(date) not in existing_dates
    ]

    if not new_points:
        print("No new cabaz data. Nothing to do.")
        return

    print(f"{len(new_points)} new week(s) found, loading BTC prices ...")
    btc_data = load_btc_prices(BTC_CSV_PATH)
    print(f"Loaded {len(btc_data)} BTC/EUR price points")

    new_rows = []
    for date, food_price_eur in new_points:
        btc_price_eur = find_closest_btc_price(date, btc_data)
        date_str = to_portuguese_date(date)
        new_rows.append({
            "Date": date_str,
            "Price": food_price_eur,
            "BTC_Price_EUR": btc_price_eur,
            "Price_in_BTC": food_price_eur / btc_price_eur,
        })
        print(f"  {date_str}: cabaz EUR{food_price_eur:.2f}, "
              f"BTC EUR{btc_price_eur:.2f}, {food_price_eur / btc_price_eur:.8f} BTC")

    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Date", "Price", "BTC_Price_EUR", "Price_in_BTC"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"Appended {len(new_rows)} row(s) to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
