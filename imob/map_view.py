import json
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))

ACCENT = "#f7931a"
POSITIVE = "#22c55e"
NEGATIVE = "#ef4444"
TEXT_SECONDARY = "#a1a1a1"


@st.cache_data
def load_geometry(level):
    filename = "municipios_web.geojson" if level == "municipio" else "freguesias_web.geojson"
    with open(os.path.join(BASE, filename), encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_price_series(level):
    if level == "municipio":
        df = pd.read_csv(os.path.join(BASE, "blended_municipio_series.csv"))
        df["date"] = pd.to_datetime(df["period_date"])
    else:
        df = pd.read_csv(os.path.join(BASE, "ine_precos_m2_full.csv"))
        df = df[df["valor_eur_m2"].notna()].copy()
        df["date"] = pd.to_datetime(df["periodo"].str.extract(r"(\d)\D*Trimestre de (\d{4})").apply(
            lambda r: f"{r[1]}-{int(r[0]) * 3:02d}-01", axis=1
        )) + pd.offsets.MonthEnd(0)
        df["source"] = "venda"
        df = df.rename(columns={"valor_eur_m2": "valor_eur_m2"})
    nivel = "5" if level == "municipio" else "6"
    df = df[df["geo_nivel"].astype(str) == nivel]
    df["valor_eur_m2"] = pd.to_numeric(df["valor_eur_m2"], errors="coerce")
    return df.dropna(subset=["valor_eur_m2"])


@st.cache_data
def load_btc():
    btc = pd.read_csv(os.path.join(BASE, "..", "data", "btc_eur.csv"))
    btc["Date"] = pd.to_datetime(btc["Date"])
    btc["Price"] = pd.to_numeric(btc["Price"].astype(str).str.replace(",", ""), errors="coerce")
    return btc


def latest_prices(df):
    """Latest non-null value per geo_cod -- what the choropleth colors by."""
    idx = df.groupby("geo_cod")["date"].idxmax()
    return df.loc[idx, ["geo_cod", "geo_dsg", "valor_eur_m2", "date"]]


def earliest_available_date():
    """Earliest date across both geo levels -- used to widen the sidebar's date range
    so 'Tudo' unlocks each region's full history, not just the national series' start."""
    municipio = load_price_series("municipio")
    freguesia = load_price_series("freguesia")
    return min(municipio["date"].min(), freguesia["date"].min()).date()


def render():
    st.info(
        "O preço do m² varia muito entre regiões. Seleciona um município ou freguesia "
        "para ver a evolução local, em euros e em Bitcoin."
    )

    level_label = st.radio(
        "Nível geográfico:",
        ["Município", "Freguesia"],
        horizontal=True,
        help="Município tem histórico mais longo (até 15 anos). Freguesia é mais detalhado mas só desde 2019.",
    )
    level = "municipio" if level_label == "Município" else "freguesia"

    geo = load_geometry(level)
    prices = load_price_series(level)
    latest = latest_prices(prices)

    theme_base = st.get_option("theme.base") or "dark"
    is_dark = theme_base == "dark"
    map_text_color = st.get_option("theme.textColor") or ("#ededed" if is_dark else "#31333F")
    map_low_color = "#3a3a3a" if is_dark else "#e5e5e5"
    map_border_color = "rgba(255,255,255,0.16)" if is_dark else "rgba(0,0,0,0.16)"

    geo_id_key = "properties.geo_cod"
    fig_map = go.Figure(go.Choropleth(
        geojson=geo,
        locations=latest["geo_cod"],
        z=latest["valor_eur_m2"],
        featureidkey=geo_id_key,
        colorscale=[[0, map_low_color], [1, ACCENT]],
        marker_line_color=map_border_color,
        marker_line_width=0.5,
        colorbar=dict(title="€/m²", tickprefix="€", outlinewidth=0, tickfont=dict(color=map_text_color)),
        hovertemplate="<b>%{customdata}</b><br>€%{z:,.0f}/m²<extra></extra>",
        customdata=latest["geo_dsg"],
    ))
    fig_map.update_geos(
        visible=False,
        fitbounds="locations",
        scope="europe",
        bgcolor="rgba(0,0,0,0)",
        showland=False,
        showcountries=False,
        showcoastlines=False,
        showframe=False,
    )
    fig_map.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    map_event = st.plotly_chart(
        fig_map, use_container_width=True, on_select="rerun", selection_mode="points", key=f"map_{level}"
    )

    region_names = sorted(latest["geo_dsg"].unique())

    clicked_points = map_event.selection.points if map_event and map_event.selection else []
    if clicked_points:
        st.session_state[f"region_select_{level}"] = clicked_points[0]["properties"]["geo_dsg"]

    state_key = f"region_select_{level}"
    if state_key not in st.session_state or st.session_state[state_key] not in region_names:
        st.session_state[state_key] = "Lisboa" if "Lisboa" in region_names else region_names[0]

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
        key=state_key,
        help="Escreve para pesquisar ou escolhe na lista. Também podes clicar diretamente no mapa.",
    )

    region_df = prices[prices["geo_dsg"] == selected].sort_values("date")

    start_date = st.session_state.get("start_date")
    end_date = st.session_state.get("end_date")
    if start_date and end_date:
        region_df = region_df[
            (region_df["date"].dt.date >= start_date) & (region_df["date"].dt.date <= end_date)
        ]

    if region_df.empty:
        st.warning("Sem dados para esta região no período selecionado.")
        return

    btc = load_btc()
    region_df["year_month"] = region_df["date"].dt.to_period("M")
    btc = btc.copy()
    btc["year_month"] = btc["Date"].dt.to_period("M")
    btc_monthly = btc.sort_values("Date").groupby("year_month", as_index=False).last()
    region_df = region_df.merge(
        btc_monthly[["year_month", "Price"]].rename(columns={"Price": "btc_price"}), on="year_month", how="left"
    )
    region_df["valor_btc_m2"] = region_df["valor_eur_m2"] / region_df["btc_price"]
    region_df = region_df.dropna(subset=["valor_btc_m2"])

    if region_df.empty:
        st.warning("Sem dados de preço BTC alinhados com este período.")
        return

    first, latest_row = region_df.iloc[0], region_df.iloc[-1]
    eur_change = (latest_row["valor_eur_m2"] / first["valor_eur_m2"] - 1) * 100
    btc_change = (latest_row["valor_btc_m2"] / first["valor_btc_m2"] - 1) * 100

    if "source" in region_df.columns and region_df["source"].nunique() > 1:
        st.caption(
            "Este período combina duas fontes: avaliação bancária (até Q3 2019) e vendas efetivas (a partir de Q4 2019). "
            "São metodologias diferentes — a linha vertical no gráfico assinala a transição."
        )

    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"{selected} — EUR/m² (atual)", f"€{latest_row['valor_eur_m2']:,.0f}", f"{eur_change:+.1f}%", delta_color="inverse")
    with col2:
        st.metric(f"{selected} — BTC/m² (atual)", f"{latest_row['valor_btc_m2']:.6f} BTC", f"{btc_change:+.1f}%", delta_color="inverse")

    st.markdown("---")
    st.subheader("📈 Análise Comparativa")

    eur_abs = latest_row["valor_eur_m2"] - first["valor_eur_m2"]
    btc_abs = latest_row["valor_btc_m2"] - first["valor_btc_m2"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Variação EUR/m²",
                   f"{'+ ' if eur_abs >= 0 else '- '}€{abs(eur_abs):,.0f}",
                   f"{eur_change:.2f}%", delta_color="inverse")
    with col2:
        st.metric("Variação BTC/m²",
                   f"{'+ ' if btc_abs >= 0 else '- '}{abs(btc_abs):.6f} BTC",
                   f"{btc_change:.2f}%", delta_color="inverse")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=region_df["date"], y=region_df["valor_eur_m2"],
        name="Preço/m² [EUR]", mode="lines", line=dict(color=POSITIVE, width=2),
        hovertemplate="<b>%{x|%b %Y}</b><br>€%{y:,.0f}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=region_df["date"], y=region_df["valor_btc_m2"],
        name="Preço/m² [BTC]", mode="lines", line=dict(color=ACCENT, width=2),
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y:.6f} BTC<extra></extra>",
    ), secondary_y=True)

    if "source" in region_df.columns and region_df["source"].nunique() > 1:
        splice_date = region_df[region_df["source"] == "venda"]["date"].min()
        fig.add_vline(x=splice_date, line_dash="dot", line_color=TEXT_SECONDARY, opacity=0.5)

    fig.update_xaxes(title_text="Data")
    fig.update_yaxes(title_text="<b>Preço por m² (EUR)</b>", secondary_y=False,
                      title_font=dict(color=POSITIVE), gridcolor="rgba(34,197,94,0.15)")
    fig.update_yaxes(title_text="<b>Preço por m² (BTC)</b>", secondary_y=True,
                      type="log" if st.session_state.get("use_log_scale") else "linear",
                      title_font=dict(color=ACCENT), gridcolor="rgba(247,147,26,0.15)")
    fig.update_layout(
        hovermode="x unified", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    st.caption(
        "Dados: INE (Estatísticas de Preços da Habitação ao Nível Local e Inquérito à Avaliação Bancária na Habitação) "
        "· preço BTC/EUR via Kraken/Investing.com"
    )
