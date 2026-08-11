import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import map_view

ACCENT = "#f7931a"
POSITIVE = "#22c55e"
TEXT_SECONDARY = "#a1a1a1"


def _earliest_region_date(prices, geo_dsg):
    return prices[prices["geo_dsg"] == geo_dsg]["date"].min().date()


def render():
    st.info(
        "Se tivesses investido um valor fixo em Bitcoin todos os meses, em vez de o "
        "guardares em euros, a quantos m² isso equivaleria hoje? Compara as duas estratégias."
    )

    level_label = st.radio(
        "Nível geográfico:",
        ["Município", "Freguesia"],
        horizontal=True,
        key="dca_level",
        help="Município tem histórico mais longo (até 15 anos). Freguesia é mais detalhado mas só desde 2019.",
    )
    level = "municipio" if level_label == "Município" else "freguesia"

    prices = map_view.load_price_series(level)
    region_names = sorted(prices["geo_dsg"].unique())
    default_idx = region_names.index("Lisboa") if "Lisboa" in region_names else 0

    st.markdown("""
    <style>
    div[data-testid="stSelectbox"] label[data-testid="stWidgetLabel"] {
        justify-content: flex-start;
        gap: 0.25rem;
    }
    div[data-testid="stSelectbox"] label[data-testid="stWidgetLabel"] > div {
        flex: 0 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)
    selected = st.selectbox(
        f"Selecionar {level_label.lower()}:",
        region_names,
        index=default_idx,
        key="dca_region",
        help="Escreve para pesquisar ou escolhe na lista.",
    )

    btc = map_view.load_btc()
    region_df = prices[prices["geo_dsg"] == selected].sort_values("date")

    btc_min_date = btc["Date"].min().date()
    region_min_date = region_df["date"].min().date()
    min_start = max(btc_min_date, region_min_date)
    max_start = region_df["date"].max().date()

    sidebar_start = st.session_state.get("start_date")
    sidebar_end = st.session_state.get("end_date")
    default_start = max(min_start, sidebar_start) if sidebar_start else min_start
    default_start = min(default_start, max_start)
    sim_end = min(max_start, sidebar_end) if sidebar_end else max_start

    col1, col2 = st.columns(2)
    with col1:
        monthly_amount = st.number_input(
            "Valor investido por mês (€):", min_value=10, max_value=10000, value=100, step=10,
        )
    with col2:
        start_date = st.date_input(
            "Investir desde:", value=default_start, min_value=min_start, max_value=max_start,
            help="Segue o intervalo de datas da barra lateral por defeito — ajusta aqui se quiseres um período diferente.",
        )

    months = pd.period_range(start=start_date, end=sim_end, freq="M")
    if len(months) < 2:
        st.warning("Escolhe uma data de início mais antiga para simular pelo menos 2 meses.")
        return

    btc_monthly = btc.copy()
    btc_monthly["year_month"] = btc_monthly["Date"].dt.to_period("M")
    btc_monthly = btc_monthly.sort_values("Date").groupby("year_month", as_index=False).last()
    btc_by_month = btc_monthly.set_index("year_month")["Price"]

    region_monthly = region_df.copy()
    region_monthly["year_month"] = region_monthly["date"].dt.to_period("M")
    region_monthly = region_monthly.sort_values("date").groupby("year_month", as_index=False).last()
    price_by_month = region_monthly.set_index("year_month")["valor_eur_m2"]

    sim_months = [m for m in months if m in btc_by_month.index]
    if len(sim_months) < 2:
        st.warning("Sem dados de preço BTC suficientes para este período.")
        return

    total_btc = 0.0
    total_saved = 0.0
    timeline = []
    for m in sim_months:
        btc_price = btc_by_month[m]
        total_btc += monthly_amount / btc_price
        total_saved += monthly_amount
        timeline.append({"year_month": m, "total_btc": total_btc, "total_saved": total_saved})

    timeline_df = pd.DataFrame(timeline)
    timeline_df = timeline_df.merge(
        price_by_month.rename("valor_eur_m2"), left_on="year_month", right_index=True, how="left"
    ).ffill()
    timeline_df = timeline_df.merge(
        btc_by_month.rename("btc_price"), left_on="year_month", right_index=True, how="left"
    )
    timeline_df["btc_value_eur"] = timeline_df["total_btc"] * timeline_df["btc_price"]
    timeline_df["m2_btc_route"] = timeline_df["btc_value_eur"] / timeline_df["valor_eur_m2"]
    timeline_df["m2_cash_route"] = timeline_df["total_saved"] / timeline_df["valor_eur_m2"]
    timeline_df["date"] = timeline_df["year_month"].dt.to_timestamp(how="end")

    latest = timeline_df.iloc[-1]
    n_months = len(sim_months)
    multiplier = latest["m2_btc_route"] / latest["m2_cash_route"] if latest["m2_cash_route"] > 0 else float("nan")

    st.markdown(
        f"<div style='text-align:center;padding:1.5rem 0 1rem;'>"
        f"<p style='font-size:1.5rem;margin:0;'>Em {n_months} meses, investir "
        f"€{monthly_amount:,.0f}/mês em Bitcoin em vez de poupar em euros teria comprado "
        f"<span style='color:{ACCENT};font-weight:bold;'>{multiplier:.1f}x mais m²</span> "
        f"em {selected}.</p>"
        f"</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            f"{selected} — m² via Bitcoin",
            f"{latest['m2_btc_route']:.1f} m²",
            f"€{latest['btc_value_eur']:,.0f} acumulados",
        )
    with col2:
        st.metric(
            f"{selected} — m² via poupança em euros",
            f"{latest['m2_cash_route']:.1f} m²",
            f"€{latest['total_saved']:,.0f} guardados",
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timeline_df["date"], y=timeline_df["m2_btc_route"],
        name="m² via Bitcoin", mode="lines", line=dict(color=ACCENT, width=2),
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y:.1f} m²<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=timeline_df["date"], y=timeline_df["m2_cash_route"],
        name="m² via poupança em euros", mode="lines", line=dict(color=POSITIVE, width=2),
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y:.1f} m²<extra></extra>",
    ))
    fig.update_xaxes(title_text="Data")
    fig.update_yaxes(title_text="<b>m² equivalentes</b>")
    fig.update_layout(
        hovermode="x unified", height=460,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    st.caption(
        "Simulação: compra mensal de Bitcoin ao preço de fecho do mês, sem taxas. "
        "Não é aconselhamento financeiro — resultados passados não garantem resultados futuros."
    )
