import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

PORTUGUESE_MONTHS = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

st.set_page_config(
    page_title="Cabaz Alimentar: EUR vs BTC",
    page_icon="🛒",
    layout="wide"
)


def parse_portuguese_date(date_str):
    parts = date_str.strip().split()
    day = int(parts[0])
    month_name = parts[2]
    year = int(parts[4])
    month = PORTUGUESE_MONTHS[month_name]
    return datetime(year, month, day)


@st.cache_data
def load_data():
    base = os.path.dirname(os.path.abspath(__file__))
    df = pd.read_csv(os.path.join(base, "infogram_data_with_btc.csv"))
    df['Date_parsed'] = df['Date'].apply(parse_portuguese_date)
    df = df.sort_values('Date_parsed')
    return df


def format_btc(value):
    return f"{value:.8f} BTC"


def format_eur(value):
    return f"€{value:.2f}"


def main():
    df = load_data()

    st.sidebar.header("Controlos")

    min_date = df['Date_parsed'].min().date()
    max_date = df['Date_parsed'].max().date()

    if 'start_date' not in st.session_state:
        st.session_state.start_date = min_date
    if 'end_date' not in st.session_state:
        st.session_state.end_date = max_date

    date_range = st.sidebar.date_input(
        "Selecionar intervalo de datas:",
        value=(st.session_state.start_date, st.session_state.end_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        st.session_state.start_date, st.session_state.end_date = date_range
        start_date, end_date = date_range
    else:
        start_date = st.session_state.start_date
        end_date = st.session_state.end_date

    log_scale_btc = st.sidebar.checkbox("Escala logarítmica para BTC", value=False)

    st.sidebar.markdown("### Atalhos")
    col1, col2 = st.sidebar.columns(2)

    today = max_date

    if col1.button("1 Ano"):
        st.session_state.start_date = today - timedelta(days=365)
        st.session_state.end_date = today
        st.rerun()

    if col2.button("2 Anos"):
        st.session_state.start_date = today - timedelta(days=365*2)
        st.session_state.end_date = today
        st.rerun()

    col3, col4 = st.sidebar.columns(2)

    if col3.button("3 Anos"):
        st.session_state.start_date = today - timedelta(days=365*3)
        st.session_state.end_date = today
        st.rerun()

    if col4.button("Tudo"):
        st.session_state.start_date = min_date
        st.session_state.end_date = max_date
        st.rerun()

    mask = (df['Date_parsed'].dt.date >= start_date) & (df['Date_parsed'].dt.date <= end_date)
    filtered_df = df[mask].copy()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Estatísticas")

    if len(filtered_df) > 0:
        period_days = (end_date - start_date).days
        period_months = round(period_days / 30)

        latest = filtered_df.iloc[-1]

        st.sidebar.metric("Período selecionado", f"{period_months} meses")
        st.sidebar.metric("Preço atual do cabaz alimentar em EUR", format_eur(latest['Price']))
        st.sidebar.metric("Preço atual do cabaz alimentar em BTC (atual)", format_btc(latest['Price_in_BTC']))

    st.title("🛒 Cabaz Alimentar em Portugal - EUR vs BTC")

    if len(filtered_df) == 0:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return

    st.info(
        "Nos últimos anos, o aumento da oferta monetária tem contribuído para a inflação, "
        "fazendo com que os preços dos produtos no supermercado aumentem constantemente.\n\n"
        "Isto significa que os teus euros compram cada vez menos produtos.\n\n"
        "A Bitcoin, com a sua oferta limitada a 21 milhões de unidades, surge como uma "
        "ferramenta de proteção do poder de compra.\n\n"
        "Como podes comprovar no gráfico abaixo, o mesmo cabaz alimentar que fica cada vez "
        "mais caro em euros, fica progressivamente mais barato quando medido em Bitcoin."
    )

    if len(filtered_df) > 1:
        first = filtered_df.iloc[0]
        latest = filtered_df.iloc[-1]
        eur_change = ((latest['Price'] - first['Price']) / first['Price']) * 100

        price_word = "caro" if eur_change > 0 else "barato"
        abs_change = abs(eur_change)

        st.markdown(
            f"<div style='text-align: center; padding: 1.5rem 0;'>"
            f"<p style='font-size: 1.5rem; margin: 0;'>No período selecionado, o cabaz alimentar "
            f"está <strong>{abs_change:.1f}% mais {price_word}</strong>.</p>"
            f"<p style='font-size: 1.3rem; opacity: 0.65; margin-top: 0.5rem;'>Quanto aumentou o teu salário?</p>"
            f"</div>",
            unsafe_allow_html=True
        )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=filtered_df['Date_parsed'],
        y=filtered_df['Price'],
        name='Cabaz [EUR]',
        line=dict(color='#22c55e', width=2),
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Preço: €%{y:.2f}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=filtered_df['Date_parsed'],
        y=filtered_df['Price_in_BTC'],
        name='Cabaz [BTC]',
        line=dict(color='#f7931a', width=2),
        yaxis='y2',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Preço: %{y:.8f} BTC<extra></extra>'
    ))

    fig.update_layout(
        xaxis=dict(title='Data'),
        yaxis=dict(
            title=dict(text='Preço do Cabaz [EUR]', font=dict(color='#22c55e')),
            tickfont=dict(color='#22c55e'),
            side='left'
        ),
        yaxis2=dict(
            title=dict(text='Preço do Cabaz [BTC]', font=dict(color='#f7931a')),
            tickfont=dict(color='#f7931a'),
            overlaying='y',
            side='right',
            type='log' if log_scale_btc else 'linear',
            showgrid=False
        ),
        hovermode='x unified',
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    st.markdown("---")
    st.subheader("📈 Análise Comparativa")

    if len(filtered_df) > 1:
        first = filtered_df.iloc[0]
        latest = filtered_df.iloc[-1]

        eur_absolute = latest['Price'] - first['Price']
        eur_percent = (eur_absolute / first['Price']) * 100
        eur_sign = "+ " if eur_absolute >= 0 else "- "

        btc_absolute = latest['Price_in_BTC'] - first['Price_in_BTC']
        btc_percent = (btc_absolute / first['Price_in_BTC']) * 100
        btc_sign = "+ " if btc_absolute >= 0 else "- "

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Variação EUR",
                f"{eur_sign}€{abs(eur_absolute):.2f}",
                f"{eur_percent:.2f}%",
                delta_color="inverse"
            )

        with col2:
            st.metric(
                "Variação BTC",
                f"{btc_sign}{abs(btc_absolute):.8f} BTC",
                f"{btc_percent:.2f}%",
                delta_color="inverse"
            )

    st.markdown("---")
    st.subheader("📊 Dados")
    with st.expander("Ver tabela de dados"):
        display_df = filtered_df[['Date_parsed', 'Price', 'Price_in_BTC']].copy()
        display_df.columns = ['Data', 'Preço Cabaz (EUR)', 'Preço Cabaz (BTC)']
        display_df['Data'] = display_df['Data'].dt.strftime('%Y-%m-%d')
        display_df['Preço Cabaz (EUR)'] = display_df['Preço Cabaz (EUR)'].apply(lambda x: f"€{x:.2f}")
        display_df['Preço Cabaz (BTC)'] = display_df['Preço Cabaz (BTC)'].apply(lambda x: f"{x:.8f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("Dados: BTC/EUR via CoinGecko e cabaz alimentar via DECO PROTESTE")


if __name__ == '__main__':
    main()
