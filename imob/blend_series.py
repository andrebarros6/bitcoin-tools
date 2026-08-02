"""
Blends INE's two housing-price series into one longer municipio-level timeline:

- Pre Q4-2019: bank appraisal values (varcd 0012248, monthly, Jan 2011+,
  ine_avaliacao_bancaria_full.csv). Municipio-level only, no freguesia detail.
- Q4-2019 onward: actual sale transaction prices (varcd 0012234, quarterly,
  ine_precos_m2_full.csv). Goes down to freguesia level.

These are NOT the same metric -- appraisal is a bank's valuation for mortgage
purposes, sales is the median actual transaction price. They track similarly
but are not identical, and INE itself does not publish a spliced series. Every
row carries a `source` column (`avaliacao_bancaria` | `venda`) so any chart
built on this MUST visually mark the Q4-2019 boundary as a methodology change,
not present it as one continuous unbroken metric.

Freguesia-level has NO pre-2019 leg -- the appraisal series never goes that
fine. Only municipio and national/NUTS levels get the pre-2020 extension.

Output: blended_municipio_series.csv
Columns: geo_cod, geo_dsg, geo_nivel, period_date (YYYY-MM-DD, quarter-end for
both legs so they align), valor_eur_m2, source
"""
import csv
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))
SALES_CSV = os.path.join(DIR, "ine_precos_m2_full.csv")
APPRAISAL_CSV = os.path.join(DIR, "ine_avaliacao_bancaria_full.csv")
OUT_CSV = os.path.join(DIR, "blended_municipio_series.csv")

QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}
MONTH_NUM = {
    "Janeiro": "01", "Fevereiro": "02", "Março": "03", "Abril": "04",
    "Maio": "05", "Junho": "06", "Julho": "07", "Agosto": "08",
    "Setembro": "09", "Outubro": "10", "Novembro": "11", "Dezembro": "12",
}
MONTH_LAST_DAY = {
    "01": "31", "02": "28", "03": "31", "04": "30", "05": "31", "06": "30",
    "07": "31", "08": "31", "09": "30", "10": "31", "11": "30", "12": "31",
}

SPLICE_DATE = "2019-10-01"  # start of Q4 2019, where the sales series begins


def parse_quarter_periodo(periodo):
    # '4.º Trimestre de 2025' -> '2025-12-31'
    m = re.match(r"(\d)\D*Trimestre de (\d{4})", periodo)
    if not m:
        return None
    q, year = m.group(1), m.group(2)
    return f"{year}-{QUARTER_END[q]}"


def parse_month_periodo(periodo):
    # 'Janeiro de 2020' -> '2020-01-31'
    m = re.match(r"([A-Za-zçãéíóú]+) de (\d{4})", periodo)
    if not m:
        return None
    month_name, year = m.group(1), m.group(2)
    month_num = MONTH_NUM.get(month_name)
    if not month_num:
        return None
    return f"{year}-{month_num}-{MONTH_LAST_DAY[month_num]}"


def load_sales():
    with open(SALES_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r["geo_nivel"] not in ("1", "5", "6"):  # national + municipio + freguesia
            continue
        if not r["valor_eur_m2"]:
            continue
        date = parse_quarter_periodo(r["periodo"])
        if not date or date < SPLICE_DATE:
            continue
        out.append({
            "geo_cod": r["geo_cod"], "geo_dsg": r["geo_dsg"], "geo_nivel": r["geo_nivel"],
            "period_date": date, "valor_eur_m2": r["valor_eur_m2"], "source": "venda",
        })
    return out


def load_appraisal():
    with open(APPRAISAL_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r["geo_nivel"] not in ("1", "5"):  # national + municipio only -- no freguesia in this series
            continue
        if not r["valor_eur_m2"]:
            continue
        date = parse_month_periodo(r["periodo"])
        if not date or date >= SPLICE_DATE:
            continue
        out.append({
            "geo_cod": r["geo_cod"], "geo_dsg": r["geo_dsg"], "geo_nivel": r["geo_nivel"],
            "period_date": date, "valor_eur_m2": r["valor_eur_m2"], "source": "avaliacao_bancaria",
        })
    return out


def main():
    sales = load_sales()
    print(f"Sales-series rows (>= Q4 2019, national+municipio+freguesia): {len(sales)}")

    if not os.path.exists(APPRAISAL_CSV):
        print(f"WARNING: {APPRAISAL_CSV} not found yet -- writing sales-only output.")
        appraisal = []
    else:
        appraisal = load_appraisal()
    print(f"Appraisal-series rows (< Q4 2019, national+municipio): {len(appraisal)}")

    combined = appraisal + sales
    combined.sort(key=lambda r: (r["geo_nivel"], r["geo_dsg"], r["period_date"]))

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["geo_cod", "geo_dsg", "geo_nivel", "period_date", "valor_eur_m2", "source"])
        writer.writeheader()
        writer.writerows(combined)

    print(f"Wrote {len(combined)} rows to {OUT_CSV}")

    # Sanity: municipios present in both legs (full 2011-present coverage)
    muni_sales = {r["geo_cod"] for r in sales if r["geo_nivel"] == "5"}
    muni_appraisal = {r["geo_cod"] for r in appraisal if r["geo_nivel"] == "5"}
    both = muni_sales & muni_appraisal
    print(f"Municipios with BOTH legs (full 2011-present blended history): {len(both)} / {len(muni_sales)} sales-covered municipios")
    freguesia_only_sales = {r["geo_cod"] for r in sales if r["geo_nivel"] == "6"}
    print(f"Freguesias (sales-only, no pre-2020 leg exists): {len(freguesia_only_sales)}")


if __name__ == "__main__":
    main()
