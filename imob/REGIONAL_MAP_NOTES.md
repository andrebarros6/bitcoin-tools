# Regional map feature — data scoping + join (done) + next steps

Goal: Portugal map where user selects a region and sees EUR/BTC price evolution for that region (m2-casas-PT.csv equivalent, but regional).

## What's done

### 1. Price data (`ine_extractor.py` → `ine_precos_m2_full.csv`)
Pulls INE indicator **varcd 0012234** ("Valor mediano das vendas de alojamentos familiares... EUR/m2", Metodologia 2022) via the free JSON API (`pindicaMeta.jsp` / `pindica.jsp`), no scraping needed.
- 24,128 rows, quarterly **Q4 2019 → Q1 2026** (26 quarters), across Portugal / NUTS I-III / 308 municípios / 581 freguesias.
- Freguesia coverage: 397/581 have ≥1 non-empty quarter, 276/581 have all 26 quarters (rest suppressed by INE's statistical secrecy rule for low transaction counts — mostly small/rural parishes).
- Rate limit: INE throttles concurrent requests. Script uses 12 threads with retry/backoff; only 3/931 calls were dropped on the last run.
- Reusable for related series (swap `VARCD`): `0014696` (median rent EUR/m2, freguesia-level, Q1 2020–Q1 2026), `0014363` (number of sale transactions, same geography/time).

### 2. Boundary geometries + join (`caop_join.py` → `caop_ine_join.csv`)
- Source: DGT's CAOP2025 freguesias collection, OGC API Features at `https://ogcapi.dgterritorio.gov.pt/collections/freguesias`. **Mainland Portugal only** (3,049 parishes) — confirmed no Açores/Madeira coverage in this collection.
- Properties-only pull (no geometry) saved as `caop_freguesias_properties.json` (1.8MB, 3049 records) — fast, used for the join. Full-geometry pull was tested and abandoned: unsimplified CAOP polygons are huge (160MB+ and still streaming when killed) — need to fetch + simplify geometry only for the ~565 freguesias that actually have INE data, not all 3049, when building the real map.
- **The join key is (freguesia name, município name), not a shared code.** INE's 9-digit codes and CAOP's 6-digit `dtmnfr` (DICOFRE) are unrelated numbering schemes. Name matching (accent/case-insensitive) resolves 519/581 directly.
- **2013 parish-merger gap, confirmed and handled**: CAOP2025 still stores ~50 pre-2013-merger parishes as separate unmerged polygons (e.g. Custóias, Leça do Balio, Guifões each standalone in Matosinhos), while INE reports the merged "União das freguesias de X e Y" unit. `caop_join.py` parses the union name and maps it to N constituent CAOP polygons, which need to be dissolved into one shape at map-build time. This resolves 46 more (565/581 total, 97.2%).
- **Remaining 16 unmatched** (see `caop_ine_join_unmatched.csv`): 10 are Funchal/Madeira parishes — genuinely absent from this CAOP collection, need a different geometry source (SNIG or a Madeira-specific dataset) if Madeira coverage matters. 6 are mainland name-format mismatches (parenthetical variants like "Vila Frescainha (São Martinho e São Pedro)" vs CAOP's separate "Vila Frescainha (São Martinho)"/"(São Pedro)" entries) — fixable with a slightly smarter parser but low priority given 97% is already achieved.

### 3. Data validated (`preview_regional.py`)
Confirmed the full pipeline (INE price → BTC/EUR join via `../data/btc_eur.csv`, monthly) works end to end. Sample Lisboa/Porto/Évora, Q1 2020 → Q4 2025: EUR/m² up 44–78%, same m² in BTC terms down 87–89%. Directionally consistent with the existing national-level app. **`btc_eur.csv` is monthly (day=01 always), not daily** — matching logic must account for this, don't assume daily granularity.

## Not done yet

1. **Actual polygon geometry fetch**, scoped to the ~565 matched freguesias only (not all 3049), plus dissolving the ~46 multi-polygon union cases into single shapes. Then simplify for web use (full CAOP precision is far too heavy — the abandoned full pull was 160MB+ for partial data).
2. **Madeira/Açores boundary source** — needed only if national (not just mainland) coverage is required. Not investigated yet.
3. **Fix the 6 remaining mainland name mismatches** — low priority, pattern is understood (parenthetical sub-parish splitting), just needs a better parser.
4. **No map UI built.** Data + join + validation are done; nothing rendered yet.
5. **Time-scope decision still deferred to the user.** 6 years available via this INE source (Q4 2019–Q1 2026) vs. the ~20-year national-only series from other sources (Confidencial Imobiliário, Banco de Portugal). Needs a decision before committing to a final UI design (e.g. does the map need a longer national-only fallback view for pre-2020 history?).

## Design note

Per `bitcoin-tools/CLAUDE.md`, any UI/visual work on this must follow `design-guidelines.md` before touching layout, color, or copy.
