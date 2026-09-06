import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import data_loader as dl

st.set_page_config(
    page_title="Salários em Portugal: EUR vs BTC",
    page_icon="💶",
    layout="wide",
)

ACCENT = "#f7931a"
NEUTRAL = "#a1a1a1"


@st.cache_data
def get_series(series_key):
    return dl.build_series(series_key)


def pct_change(first, last):
    return ((last - first) / first) * 100


def render_headline(filtered, label):
    first, last = filtered.iloc[0], filtered.iloc[-1]
    eur_chg = pct_change(first["Valor_EUR"], last["Valor_EUR"])
    sats_chg = pct_change(first["Salario_SATS"], last["Salario_SATS"])

    c1, c2, c3 = st.columns(3)
    c1.metric(
        f"{label} (EUR)",
        dl.format_eur(last["Valor_EUR"]),
        f"{eur_chg:+.1f}% no período",
    )
    c2.metric(
        f"{label} (sats)",
        dl.format_sats(last["Salario_SATS"]),
        f"{sats_chg:+.1f}% no período",
    )
    c3.metric(
        "Preço do Bitcoin",
        dl.format_eur(last["BTC_EUR"]),
        f"{pct_change(first['BTC_EUR'], last['BTC_EUR']):+.1f}% no período",
    )


def render_chart(filtered, label, log_scale):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=filtered["Date"],
            y=filtered["Valor_EUR"],
            name=f"{label} (EUR)",
            line=dict(color=NEUTRAL, width=2, shape="hv"),
            hovertemplate="%{x|%b %Y}<br>%{y:,.0f} €<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=filtered["Date"],
            y=filtered["Salario_SATS"],
            name=f"{label} (sats)",
            line=dict(color=ACCENT, width=2),
            hovertemplate="%{x|%b %Y}<br>%{y:,.0f} sats<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="EUR", secondary_y=False)
    fig.update_yaxes(
        title_text="sats",
        secondary_y=True,
        type="log" if log_scale else "linear",
    )
    fig.update_layout(
        height=520,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(t=40, b=40, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_hours(filtered, label):
    """A month's salary is ~22 working days; the hourly figure makes the
    number small enough to feel concrete."""
    last = filtered.iloc[-1]
    hourly_sats = last["Salario_SATS"] / (22 * 8)
    hourly_eur = last["Valor_EUR"] / (22 * 8)
    st.markdown(
        f"Ao valor de hoje, uma hora de trabalho ao {label.lower()} vale "
        f"**{dl.format_sats(hourly_sats)}** — {dl.format_eur(hourly_eur)}."
    )


def main():
    st.title("💶 Salários em Portugal — EUR vs BTC")
    st.markdown("---")

    st.sidebar.header("Controlos")
    series_key = st.sidebar.radio(
        "Série",
        options=list(dl.SERIES.keys()),
        format_func=lambda k: dl.SERIES[k]["label"],
    )
    cfg = dl.SERIES[series_key]
    label = cfg["label"]

    df = get_series(series_key)
    if df.empty:
        st.warning("Sem dados disponíveis para esta série.")
        st.stop()

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    month_options = pd.period_range(start=min_date, end=max_date, freq="M")
    start_month, end_month = st.sidebar.select_slider(
        "Selecionar intervalo de datas:",
        options=month_options,
        value=(month_options[0], month_options[-1]),
        format_func=lambda p: p.strftime("%b %Y"),
    )

    log_scale = st.sidebar.checkbox("Escala logarítmica para sats", value=True)

    filtered = df[
        (df["Date"].dt.to_period("M") >= start_month)
        & (df["Date"].dt.to_period("M") <= end_month)
    ]

    if len(filtered) < 2:
        st.warning("Seleciona um intervalo com pelo menos dois meses.")
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Fonte")
    st.sidebar.caption(cfg["source"])
    st.sidebar.caption("BTC/EUR: CoinGecko")

    st.info(
        "O salário sobe todos os anos em euros. Medido em Bitcoin, a mesma "
        "remuneração compra uma fração cada vez menor — o gráfico mostra as "
        "duas leituras lado a lado. A linha em euros é um degrau porque o "
        "salário é fixado uma vez por ano."
    )

    render_headline(filtered, label)
    render_chart(filtered, label, log_scale)
    render_hours(filtered, label)

    with st.expander("Ver dados"):
        table = filtered[["Date", "Valor_EUR", "BTC_EUR", "Salario_SATS"]].copy()
        table["Date"] = table["Date"].dt.strftime("%Y-%m")
        table.columns = ["Mês", "Salário (EUR)", "BTC (EUR)", "Salário (sats)"]
        st.dataframe(table.iloc[::-1], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
