# Regional map feature — data, join, blend (done) + next steps

Goal: Portugal map where user selects a region and sees EUR/BTC price evolution for that region (m2-casas-PT.csv equivalent, but regional). User decided (2026-08-02): at least 10 years of history required; blend appraisal data pre-Q4-2019 with transaction sales data post-Q4-2019. Time-scope is now settled: no separate 20-year national-only fallback — 15 years of município-level blended history (for 145/306 municípios) is enough, not worth a third data source/methodology for 5 more years of national-only context.

## What's done

### 1. Sales price data — Q4 2019 onward (`ine_extractor.py` → `ine_precos_m2_full.csv`)
INE indicator **varcd 0012234** ("Valor mediano das vendas de alojamentos familiares... EUR/m2", Metodologia 2022) via the free JSON API.
- 24,128 rows, quarterly **Q4 2019 → Q1 2026** (26 quarters), Portugal / NUTS I-III / 308 municípios / 581 freguesias.
- Freguesia coverage: 397/581 have ≥1 non-empty quarter, 276/581 have all 26 quarters (rest suppressed — small/rural parishes below INE's disclosure threshold).
- This is **actual transaction data** (median sale price), the gold-standard metric, but only exists back to Q4 2019.

### 2. Bank appraisal data — 2011 to Q4 2019 (`ine_extractor.py` → `ine_avaliacao_bancaria_full.csv`) — DONE
INE indicator **varcd 0012248** ("Valor mediano de avaliação bancária EUR/m2", Município-2024 classification), monthly, **Jan 2011 → Jun 2026**, município-level (no freguesia — this series never goes finer than município).
- This is a **different metric** — bank mortgage-appraisal valuations, not actual sale prices. Tracks similarly but is not identical to the sales series; INE does not publish a spliced version itself.
- The old varcd for this series (`0010042`) is dead — stopped updating Dec 2023, still on "Município-2013" classification. `0012248` is the live replacement, found via dados.gov.pt's `xurl/indx/0012248/PT` redirect and confirmed directly against `pindicaMeta.jsp`.
- **Extraction was slow and bursty**: INE throttled this endpoint hard and unpredictably (alternating fast/slow windows, occasional 429/503/timeout/`jdbc` errors on their end) when pulling 186 months × 308 municípios. Took ~3 hours total despite chunking into 40-period batches and fully parallelizing every (geo_code, chunk) pair across a 12-worker pool. Final result: **63,640 rows, 25 of 1,735 time-chunks skipped (98.6% success)**. 185/308 municípios have ≥1 non-empty value (rest suppressed by INE or fell in the small number of skipped chunks — acceptable, not worth re-running for the last 1.4%).

### 3. Extractor script is now reusable
`ine_extractor.py` takes CLI args: `python ine_extractor.py [varcd] [dim3_code] [output_filename]`. Auto-chunks large time ranges (>40 periods) and parallelizes across geo codes and chunks. Default (no args) = the original sales-price pull.

### 4. Boundary geometries + join (`caop_join.py` → `caop_ine_join.csv`)
- Source: DGT CAOP2025 freguesias, OGC API Features at `https://ogcapi.dgterritorio.gov.pt/collections/freguesias`. **Mainland only** (3,049 parishes).
- Properties-only pull (`caop_freguesias_properties.json`, 1.8MB) used for the join — full-geometry pull was tested and abandoned (160MB+ unsimplified, still streaming when killed). Fetch geometry only for the ~565 matched freguesias, and simplify, when actually building map tiles.
- **Join key is (freguesia name, município name)**, not a shared code — INE's 9-digit codes and CAOP's 6-digit `dtmnfr` (DICOFRE) are unrelated schemes. Name matching resolves 519/581 directly.
- **2013 parish-merger handling**: CAOP2025 still stores ~50 pre-2013-merger parishes as separate polygons; INE reports the merged "União das freguesias de X e Y" unit. Script parses the union name and maps to N constituent CAOP polygons (to dissolve into one shape later). Resolves 46 more → **565/581 (97.2%) total**.
- Remaining 16 unmatched: 10 Funchal/Madeira parishes (absent from this mainland-only CAOP collection — need a different source if Madeira matters), 6 mainland name-format edge cases (parenthetical sub-parish naming mismatches, e.g. CAOP splits "Vila Frescainha" into separate (São Martinho)/(São Pedro) entries where INE has one merged name) — low priority given 97% coverage.

### 5. Blend logic (`blend_series.py` → `blended_municipio_series.csv`) — DONE
Splices the two series at Q4 2019 (2019-10-01): appraisal data for dates before, sales data from that date on. Every row carries a `source` column (`avaliacao_bancaria` | `venda`) — **any chart built on this must visually mark the Q4-2019 boundary as a methodology change**, not present it as one continuous unbroken metric, since the two series measure different things (bank valuation vs. actual sale price).
- Final result: 25,682 rows. **145 of 306 sales-covered municípios (47%) have the full blended 2011–2026 history** (~15 years); the rest have Q4-2019+ only (appraisal data was suppressed or missing for them).
- Validated at two splice points: Amares (appraisal ends 2019-06-30 at €685/m², sales picks up 2019-12-31 at €710/m²) and Porto (full 2011-01-31 → 2026-03-31 span, €1,927 Sept-2019 appraisal → €1,856 Dec-2019 sale). Clean handoffs, no overlap, values plausible and close at the boundary.
- Freguesia-level has **no pre-2020 leg** — the appraisal series never reaches that granularity. Hard data ceiling: parish-level history maxes out at ~6 years (Q4 2019+, 397 freguesias), município-level reaches ~15 years (2011+) for the 145 municípios with both legs.

### 6. Pipeline validated end-to-end (`preview_regional.py`)
Confirmed EUR→BTC join (`../data/btc_eur.csv`, monthly) works. Sample Lisboa/Porto/Évora, Q1 2020→Q4 2025: EUR/m² up 44–78%, same m² down 87–89% in BTC terms. **Note `btc_eur.csv` is monthly (day=01 always)**, not daily.

## Not done yet

1. **Actual polygon geometry fetch**, scoped to the ~565 matched freguesias only, plus dissolving ~46 multi-polygon union cases into single shapes, then simplify for web use.
2. **Madeira/Açores boundary source** — only needed if national (not just mainland) coverage matters. Not investigated.
3. **Fix the 6 remaining mainland CAOP name mismatches** — low priority, pattern understood (parenthetical sub-parish splitting).
4. **No map UI built.** Data + join + blend + validation are done; nothing rendered yet. This is the next real task — everything upstream of it (data, geo join, time-scope) is settled.

## Settled decisions (do not re-litigate without new information)

- **Time scope**: no 20-year national-only fallback. Município-level (~15yr for 145/306 municípios) + freguesia-level (~6yr for 397 parishes) blended data is the full scope. Decided 2026-08-02.
- **Blend methodology**: appraisal (bank valuation) pre-Q4-2019, transaction sales post-Q4-2019, spliced with a visible `source` marker per row. Decided 2026-08-02.

## Design note

Per `bitcoin-tools/CLAUDE.md`, any UI/visual work on this must follow `design-guidelines.md` before touching layout, color, or copy.
