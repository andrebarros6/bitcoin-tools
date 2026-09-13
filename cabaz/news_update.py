#!/usr/bin/env python3
"""
Fallback cabaz source: DECO PROteste's weekly figure as reported by ECO.

publico_update.py is the primary source, but Publico's interactive has
stalled for weeks at a time (Jun-Aug 2026, and again Aug-Sep 2026) while
DECO kept publishing on schedule. This fills those gaps from the press
coverage instead, so a stalled chart no longer freezes the series.

ECO runs WordPress, so its REST API gives dated JSON rather than HTML
that breaks on redesign. Each post is checked for a DECO mention and a
plausible basket total before it is trusted, and every extracted point
is cross-checked against the week-over-week delta stated in the article
where one is present.

Run after publico_update.py: existing dates are never overwritten, so
whichever source lands a week first wins and the other no-ops.
"""

import csv
import html
import re
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import requests

API = "https://eco.sapo.pt/wp-json/wp/v2/posts"
USER_AGENT = "Mozilla/5.0 (compatible; bitcoin-tools-bot/1.0)"

SCRIPT_DIR = Path(__file__).parent
OUTPUT_CSV = SCRIPT_DIR / "infogram_data_with_btc.csv"
BTC_CSV_PATH = SCRIPT_DIR / ".." / "data" / "btc_eur.csv"

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
MONTH_NUM = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}

# The basket has ranged 180-270 EUR since 2022. Anything outside this is a
# different figure that happens to sit near a "euros" (a yearly delta, a
# single product's price), not the weekly total.
MIN_PRICE, MAX_PRICE = 150.0, 400.0

# Tag-stripping can leave the unit split ("256,71 eur o s"), so match loosely.
PRICE_RE = re.compile(r"(\d{2,3},\d{1,2})\s*eur\s*o?\s*s?", re.I)
# "Entre 29 de julho e 5 de agosto, ..." names the week explicitly.
RANGE_RE = re.compile(r"entre\s+\d{1,2}\s+de\s+\w+\s+e\s+(\d{1,2})\s+de\s+(\w+)")
# "aumentou 52 centimos" / "desceu 0,94 euros" — the stated weekly delta.
DELTA_RE = re.compile(
    r"(aumentou|subiu|encareceu|desceu|baixou|recuou)\s+"
    r"(?:cerca\s+de\s+)?(\d{1,2},\d{1,2}|\d{1,2})\s*(c[eê]ntimos?|euros?)"
)
DOWN_WORDS = ("desceu", "baixou", "recuou")


def to_portuguese_date(d):
    return f"{d.day} de {MONTHS_PT[d.month - 1]} de {d.year}"


def strip_html(raw):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def deaccent(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()


def wednesday_of(d):
    """DECO publishes Wednesday; articles run same day or a day or two later."""
    return d - timedelta(days=(d.weekday() - 2) % 7)


def parse_delta(body_norm):
    """Signed week-over-week change in EUR, or None when not stated."""
    match = DELTA_RE.search(body_norm)
    if not match:
        return None
    verb, amount, unit = match.groups()
    value = float(amount.replace(",", "."))
    if unit.startswith("cent"):
        value /= 100
    return -value if verb in DOWN_WORDS else value


def extract_point(post):
    """Return (week_date, price, delta) for a weekly cabaz post, else None."""
    title = strip_html(post["title"]["rendered"])
    body = strip_html(post["content"]["rendered"])
    title_norm, body_norm = deaccent(title), deaccent(body)

    # Both guards matter: the title alone matches opinion and politics
    # pieces that mention the basket without reporting a new figure.
    if "cabaz" not in title_norm or "deco" not in body_norm:
        return None

    # Policy and election coverage ("IVA zero ... 642,9 milhoes de euros")
    # mentions DECO and a basket but reports no weekly total; the euro
    # figures in it are budget impacts that can land inside the price range.
    if "milho" in body_norm or "mil milho" in body_norm:
        return None
    # DECO's own weekly figure is always attributed as monitored by them.
    if not re.search(r"monitoriz|deco proteste", body_norm):
        return None
    # DECO also publishes a monthly round-up ("cai 1,1% em julho, face ao mes
    # anterior"). Its total is not that week's reading, so drop it rather than
    # attribute a month's figure to whichever Wednesday it was published near.
    if re.search(r"face ao mes anterior|em relacao ao mes anterior", body_norm):
        return None

    match = PRICE_RE.search(body) or PRICE_RE.search(title)
    if not match:
        return None
    price = float(match.group(1).replace(",", "."))
    if not MIN_PRICE <= price <= MAX_PRICE:
        return None

    published = datetime.strptime(post["date"][:10], "%Y-%m-%d")
    range_match = RANGE_RE.search(body_norm)
    if range_match:
        day, month = int(range_match.group(1)), MONTH_NUM.get(range_match.group(2))
        if month:
            # A December week reported in January belongs to the prior year.
            year = published.year - (1 if month == 12 and published.month == 1 else 0)
            return datetime(year, month, day), price, parse_delta(body_norm)

    return wednesday_of(published), price, parse_delta(body_norm)


def fetch_page(session, page, per_page, retries=4):
    """One page of results. ECO returns an intermittent 502, so retry."""
    params = {
        "search": "cabaz alimentar",
        "per_page": per_page,
        "page": page,
        "orderby": "date",
        "order": "desc",
        "_fields": "date,title,content",
    }
    last_error = None
    for attempt in range(retries):
        try:
            response = session.get(API, params=params, timeout=90)
            if response.status_code == 400:  # past the last page
                return None
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"ECO API failed after {retries} attempts: {last_error}")


def fetch_points(pages=2, per_page=100):
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    points = {}
    for page in range(1, pages + 1):
        posts = fetch_page(session, page, per_page)
        if posts is None:
            break
        if not posts:
            break

        for post in posts:
            found = extract_point(post)
            if found:
                date, price, delta = found
                # Same week reported twice: keep the earliest article, which
                # is the original report rather than a later follow-up.
                points.setdefault(date, (price, delta))

    return points


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


def load_existing(csv_path):
    if not csv_path.exists():
        return {}
    with open(csv_path, "r", encoding="utf-8") as f:
        return {row["Date"]: float(row["Price"]) for row in csv.DictReader(f)}


def main():
    print(f"Querying {API} ...")
    points = fetch_points()
    if not points:
        raise RuntimeError("No cabaz points extracted — the API or page shape changed")
    print(f"Extracted {len(points)} weekly point(s), "
          f"{min(points).date()} to {max(points).date()}")

    existing = load_existing(OUTPUT_CSV)

    # Report where the scrape disagrees with a row we already trust, rather
    # than silently ignoring it — that mismatch is how two bad values from
    # the old Infogram scraper went unnoticed for months.
    for date, (price, _) in sorted(points.items()):
        known = existing.get(to_portuguese_date(date))
        if known is not None and abs(known - price) > 0.02:
            print(f"  WARNING {date.date()}: CSV has {known:.2f}, "
                  f"news reports {price:.2f} — left unchanged, verify by hand")

    new_points = sorted(
        (d, p, delta) for d, (p, delta) in points.items()
        if to_portuguese_date(d) not in existing
    )
    if not new_points:
        print("No new cabaz data. Nothing to do.")
        return

    print(f"{len(new_points)} new week(s) found, loading BTC prices ...")
    btc_data = load_btc_prices(BTC_CSV_PATH)

    rows = []
    for date, price, delta in new_points:
        # Where the article states a delta and we hold the prior week, the
        # two must agree; a mismatch means the wrong number was picked up.
        previous = existing.get(to_portuguese_date(date - timedelta(days=7)))
        if delta is not None and previous is not None:
            expected = previous + delta
            if abs(expected - price) > 0.05:
                print(f"  SKIP {date.date()}: {price:.2f} fails delta check "
                      f"({previous:.2f} {delta:+.2f} = {expected:.2f})")
                continue

        btc_price = find_closest_btc_price(date, btc_data)
        date_str = to_portuguese_date(date)
        rows.append({
            "Date": date_str,
            "Price": f"{price:g}",
            "BTC_Price_EUR": btc_price,
            "Price_in_BTC": price / btc_price,
        })
        existing[date_str] = price
        print(f"  {date_str}: cabaz EUR{price:.2f}, BTC EUR{btc_price:.2f}")

    if not rows:
        print("Every candidate failed validation. Nothing written.")
        return

    file_exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="\n", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Date", "Price", "BTC_Price_EUR", "Price_in_BTC"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Appended {len(rows)} row(s) to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
