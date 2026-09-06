# Salários — EUR vs BTC

O salário mínimo e o salário médio portugueses, medidos em euros e em satoshis.

## Dados

| Ficheiro | Série | Cobertura | Fonte |
|---|---|---|---|
| `salario_minimo.csv` | Retribuição Mínima Mensal Garantida | 2013–2026 | DGAEP / Pordata |
| `salario_medio.csv` | Remuneração bruta total mensal média | 2019–2025 | INE |
| `../data/btc_eur.csv` | BTC/EUR | 2013-10– | CoinGecko |

Duas notas sobre o `salario_medio.csv`:

- A série do INE só começa em 2019 — é quando passa a assentar nos registos da
  Segurança Social. Não há continuidade metodológica com anos anteriores.
- 2019 e 2022 são derivados das taxas de variação publicadas (−2,9% sobre 2020;
  −6,3% sobre 2023), porque o INE divulgou a variação e não o nível. A coluna
  `Fonte` marca essas duas linhas.

## Grão temporal

Os salários são anuais; o Bitcoin move-se todos os dias. O salário é mantido
constante dentro de cada ano (função em degrau) e só o preço do BTC varia
mês a mês. Interpolar o salário entre anos inventaria valores que nunca
existiram.

## Correr localmente

```
pip install -r requirements.txt
streamlit run app.py
```

## Atualização

Anual, não diária. `.github/workflows/check_salario.yml` abre uma issue em
janeiro/fevereiro se os CSVs ficarem para trás do ano corrente:

- **Salário mínimo** — fixado por decreto-lei em janeiro.
- **Salário médio** — o INE publica a média do ano anterior em fevereiro.
