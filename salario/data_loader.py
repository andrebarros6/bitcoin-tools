"""Salary series and BTC price loading, merged onto a monthly grain.

The salary series are annual: the salario minimo is legislated once a year and
INE publishes the salario medio as an annual average. BTC moves daily, so the
salary is held flat across each year (a step function) and only the BTC leg
moves within the year. Interpolating the salary between years would invent
values that never existed.
"""
import os

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
SATS_PER_BTC = 100_000_000

SERIES = {
    "minimo": {
        "file": "salario_minimo.csv",
        "label": "Salário mínimo",
        "source": "DGAEP / Pordata",
    },
    "medio": {
        "file": "salario_medio.csv",
        "label": "Salário médio",
        "source": "INE — remuneração bruta total mensal média",
    },
}


def load_btc_monthly():
    """BTC/EUR resampled to month-end. The CSV is monthly early on and daily
    more recently, so resampling normalises both halves to one point a month."""
    btc = pd.read_csv(os.path.join(BASE, "..", "data", "btc_eur.csv"))
    btc["Date"] = pd.to_datetime(btc["Date"])
    btc["Price"] = pd.to_numeric(
        btc["Price"].astype(str).str.replace(",", ""), errors="coerce"
    )
    btc = btc.dropna(subset=["Price"])
    monthly = btc.set_index("Date")["Price"].resample("ME").last().dropna()
    return monthly.rename("BTC_EUR")


def load_salary(series_key):
    cfg = SERIES[series_key]
    df = pd.read_csv(os.path.join(BASE, cfg["file"]))
    df["Ano"] = df["Ano"].astype(int)
    df["Valor_EUR"] = pd.to_numeric(df["Valor_EUR"], errors="coerce")
    return df.dropna(subset=["Valor_EUR"]).sort_values("Ano").reset_index(drop=True)


def build_series(series_key):
    """Monthly frame: salary in EUR (stepped by year), BTC price, salary in BTC/sats."""
    salary = load_salary(series_key)
    btc = load_btc_monthly()

    df = btc.to_frame().reset_index()
    df["Ano"] = df["Date"].dt.year
    df = df.merge(salary[["Ano", "Valor_EUR"]], on="Ano", how="inner")

    df["Salario_BTC"] = df["Valor_EUR"] / df["BTC_EUR"]
    df["Salario_SATS"] = df["Salario_BTC"] * SATS_PER_BTC
    return df.sort_values("Date").reset_index(drop=True)


def format_sats(value):
    return f"{value:,.0f} sats".replace(",", " ")


def format_eur(value):
    return f"{value:,.0f} €".replace(",", " ")
