import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date

import map_view
import dca_calc

st.set_page_config(
    page_title="Preço m² Portugal: EUR vs BTC",
    page_icon="🏠",
    layout="wide"
)


@st.cache_data
def load_national_data():
    base = os.path.dirname(os.path.abspath(__file__))

    btc = pd.read_csv(os.path.join(base, "..", "data", "btc_eur.csv"))
    btc["Date"] = pd.to_datetime(btc["Date"])
    btc["Price"] = pd.to_numeric(btc["Price"].astype(str).str.replace(",", ""), errors="coerce")

    imob = pd.read_csv(os.path.join(base, "m2-casas-PT.csv"))
    imob["Date"] = pd.to_datetime(imob["Mes"], format="%d-%m-%Y")

    df = btc.merge(imob[["Date", "Preco m2 [EUR]"]], on="Date", how="right")
    df = df[["Date", "Price", "Preco m2 [EUR]"]].copy()
    df["Preco m2 [BTC]"] = df["Preco m2 [EUR]"] / df["Price"]
    df = df.sort_values("Date", ascending=True).reset_index(drop=True)
    return df


def render_national():
    df = load_national_data()
    min_date = min(df["Date"].min().date(), map_view.earliest_available_date())
    max_date = df["Date"].max().date()

    if "start_date" not in st.session_state:
        st.session_state.start_date = max(min_date, date(max_date.year - 5, max_date.month, max_date.day))
    if "end_date" not in st.session_state:
        st.session_state.end_date = max_date

    st.sidebar.header("Controlos")

    month_options = pd.period_range(start=min_date, end=max_date, freq="M")

    def _closest_month(target_date):
        target_period = pd.Period(target_date, freq="M")
        return min(month_options, key=lambda p: abs((p - target_period).n))

    start_month, end_month = st.sidebar.select_slider(
        "Selecionar intervalo de datas:",
        options=month_options,
        value=(_closest_month(st.session_state.start_date), _closest_month(st.session_state.end_date)),
        format_func=lambda p: p.strftime("%b %Y"),
    )
    st.session_state.start_date = start_month.start_time.date()
    st.session_state.end_date = min(end_month.end_time.date(), max_date)

    use_log_scale = st.sidebar.checkbox("Escala logarítmica para BTC", value=False)
    st.session_state.use_log_scale = use_log_scale

    st.sidebar.markdown("### Atalhos")
    col1, col2 = st.sidebar.columns(2)
    if col1.button("1 Ano"):
        st.session_state.start_date = date(max_date.year - 1, max_date.month, max_date.day)
        st.session_state.end_date = max_date
        st.rerun()
    if col2.button("3 Anos"):
        st.session_state.start_date = date(max_date.year - 3, max_date.month, max_date.day)
        st.session_state.end_date = max_date
        st.rerun()
    col3, col4 = st.sidebar.columns(2)
    if col3.button("5 Anos"):
        st.session_state.start_date = date(max_date.year - 5, max_date.month, max_date.day)
        st.session_state.end_date = max_date
        st.rerun()
    if col4.button("Tudo"):
        st.session_state.start_date = min_date
        st.session_state.end_date = max_date
        st.rerun()

    filtered_df = df[
        (df["Date"].dt.date >= st.session_state.start_date) &
        (df["Date"].dt.date <= st.session_state.end_date)
    ]

    if filtered_df.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Estatísticas")
    st.sidebar.metric("Período selecionado", f"{len(filtered_df)} meses")
    st.sidebar.metric(
        "EUR/m² (média nacional)", f"€{filtered_df['Preco m2 [EUR]'].iloc[-1]:,.0f}",
        help="Média nacional — não muda ao selecionar uma região na aba \"Por região\".",
    )
    st.sidebar.metric(
        "BTC/m² (média nacional)", f"{filtered_df['Preco m2 [BTC]'].iloc[-1]:.6f} BTC",
        help="Média nacional — não muda ao selecionar uma região na aba \"Por região\".",
    )

    st.markdown("""
    <div style='background-color:#1a1a1a;padding:1.5rem;border-radius:0.5rem;margin-bottom:1.5rem;border-left:4px solid #f39c12;'>
        <p style='font-size:1.1rem;line-height:1.6;margin:0;'>
        Nos últimos anos, o aumento da oferta monetária tem contribuído para a inflação, fazendo com que os preços dos imóveis em Portugal aumentem constantemente.
        Os teus euros compram cada vez menos metros quadrados.
        A Bitcoin, com a sua oferta limitada a 21 milhões de unidades, surge como uma ferramenta de proteção do poder de compra.
        Como podes ver no gráfico abaixo, o mesmo metro quadrado que fica cada vez mais caro em euros, fica progressivamente mais barato quando medido em Bitcoin.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if len(filtered_df) > 1:
        first = filtered_df.iloc[0]
        latest = filtered_df.iloc[-1]
        eur_change = ((latest["Preco m2 [EUR]"] - first["Preco m2 [EUR]"]) / first["Preco m2 [EUR]"]) * 100
        price_word = "caro" if eur_change > 0 else "barato"
        color = "#e74c3c" if eur_change > 0 else "#2ecc71"
        st.markdown(f"""
        <div style='text-align:center;padding:1.5rem;margin-bottom:2rem;'>
            <p style='font-size:1.5rem;margin:0;'>
                <span style='color:white;'>No período selecionado, o imóvel está</span>
                <span style='color:{color};font-weight:bold;'> {abs(eur_change):.1f}% mais {price_word}</span><span style='color:white;'>.</span>
            </p>
            <p style='font-size:1.3rem;color:#bbb;margin-top:0.5rem;'>Quanto aumentou o teu salário?</p>
        </div>
        """, unsafe_allow_html=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=filtered_df["Date"],
        y=filtered_df["Preco m2 [EUR]"],
        name="Preço/m² [EUR]",
        mode="lines+markers",
        marker=dict(color="green", size=6),
        line=dict(color="green", width=2),
        hovertemplate="<b>Data:</b> %{x|%b %Y}<br><b>EUR:</b> €%{y:,.0f}<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=filtered_df["Date"],
        y=filtered_df["Preco m2 [BTC]"],
        name="Preço/m² [BTC]",
        mode="lines+markers",
        marker=dict(color="orange", size=6, symbol="square"),
        line=dict(color="orange", width=2),
        hovertemplate="<b>Data:</b> %{x|%b %Y}<br><b>BTC:</b> %{y:.6f}<extra></extra>"
    ), secondary_y=True)

    fig.update_xaxes(title_text="Data")
    fig.update_yaxes(title_text="<b>Preço por m² (EUR)</b>", secondary_y=False,
                     title_font=dict(color="green"), gridcolor="rgba(0,128,0,0.15)")
    fig.update_yaxes(title_text="<b>Preço por m² (BTC)</b>", secondary_y=True,
                     type="log" if use_log_scale else "linear",
                     title_font=dict(color="orange"), gridcolor="rgba(255,165,0,0.15)")
    fig.update_layout(
        hovermode="x unified", height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Análise Comparativa")

    if len(filtered_df) > 1:
        first = filtered_df.iloc[0]
        latest = filtered_df.iloc[-1]

        eur_abs = latest["Preco m2 [EUR]"] - first["Preco m2 [EUR]"]
        eur_pct = (eur_abs / first["Preco m2 [EUR]"]) * 100
        btc_abs = latest["Preco m2 [BTC]"] - first["Preco m2 [BTC]"]
        btc_pct = (btc_abs / first["Preco m2 [BTC]"]) * 100

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Variação EUR/m²",
                      f"{'+ ' if eur_abs >= 0 else '- '}€{abs(eur_abs):,.0f}",
                      f"{eur_pct:.2f}%", delta_color="inverse")
        with col2:
            st.metric("Variação BTC/m²",
                      f"{'+ ' if btc_abs >= 0 else '- '}{abs(btc_abs):.6f} BTC",
                      f"{btc_pct:.2f}%", delta_color="inverse")

    st.markdown("---")
    st.subheader("📊 Dados")
    with st.expander("Ver tabela de dados"):
        display_df = filtered_df[["Date", "Preco m2 [EUR]", "Preco m2 [BTC]"]].copy()
        display_df.columns = ["Data", "EUR/m²", "BTC/m²"]
        display_df["Data"] = display_df["Data"].dt.strftime("%b %Y")
        display_df["EUR/m²"] = display_df["EUR/m²"].apply(lambda x: f"€{x:,.0f}")
        display_df["BTC/m²"] = display_df["BTC/m²"].apply(lambda x: f"{x:.6f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("""
    <div style='text-align:center;color:gray;'>
    <small>Dados: preço do m² via <a href='https://www.idealista.pt/media/relatorios-preco-habitacao/venda/historico/' target='_blank' style='color:gray;'>idealista.pt</a>
    · preço BTC/EUR via <a href='https://www.coingecko.com' target='_blank' style='color:gray;'>CoinGecko</a></small>
    </div>
    """, unsafe_allow_html=True)


st.markdown(
    "<a href='https://bitcoinpt.barrosbuilds.com' style='font-size:0.9rem;color:#a1a1a1;text-decoration:none;'>"
    "&larr; bitcoinpt</a>",
    unsafe_allow_html=True,
)
st.title("🏠 Preço por m² em Portugal — EUR vs BTC")
st.markdown("---")

st.markdown("""
<style>
.stTabs [role="tablist"] {
    gap: 0;
    width: 100%;
}
.stTabs [role="tab"], .stTabs [data-baseweb="tab"] {
    flex: 1;
    height: 3.5rem;
    font-size: 1.15rem;
    font-weight: 600;
    justify-content: center;
}
.stTabs [role="tab"] p, .stTabs [data-baseweb="tab"] p {
    font-size: 1.15rem;
}
</style>
""", unsafe_allow_html=True)

tab_national, tab_map, tab_dca = st.tabs(["🇵🇹 Nacional", "🗺️ Por região", "🧮 Calculadora"])

with tab_national:
    render_national()

with tab_map:
    map_view.render()

with tab_dca:
    dca_calc.render()
