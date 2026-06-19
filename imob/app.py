import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date

st.set_page_config(
    page_title="Preço m² Portugal: EUR vs BTC",
    page_icon="🏠",
    layout="wide"
)

@st.cache_data
def load_data():
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

df = load_data()
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

# Session state for date range (needed for shortcut buttons to work)
if "start_date" not in st.session_state:
    st.session_state.start_date = min_date
if "end_date" not in st.session_state:
    st.session_state.end_date = max_date

st.title("🏠 Preço por m² em Portugal — EUR vs BTC")
st.markdown("---")

# Sidebar
st.sidebar.header("Controlos")

date_range = st.sidebar.date_input(
    "Selecionar intervalo de datas:",
    value=(st.session_state.start_date, st.session_state.end_date),
    min_value=min_date,
    max_value=max_date,
)
if len(date_range) == 2:
    st.session_state.start_date, st.session_state.end_date = date_range

use_log_scale = st.sidebar.checkbox("Escala logarítmica para BTC", value=False)

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

# Filter
filtered_df = df[
    (df["Date"].dt.date >= st.session_state.start_date) &
    (df["Date"].dt.date <= st.session_state.end_date)
]

if filtered_df.empty:
    st.warning("Nenhum dado disponível para o período selecionado.")
    st.stop()

# Sidebar stats
st.sidebar.markdown("---")
st.sidebar.markdown("### Estatísticas")
st.sidebar.metric("Período selecionado", f"{len(filtered_df)} meses")
st.sidebar.metric("EUR/m² (atual)", f"€{filtered_df['Preco m2 [EUR]'].iloc[-1]:,.0f}")
st.sidebar.metric("BTC/m² (atual)", f"{filtered_df['Preco m2 [BTC]'].iloc[-1]:.6f} BTC")

# Explanatory text
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

# Impact statement
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

# Chart
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

# Comparative analysis
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

# Data table
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
