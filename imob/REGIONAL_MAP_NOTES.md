# Regional map feature — data scoping (done) + next steps

Goal: Portugal map where user selects a region and sees EUR/BTC price evolution for that region (m2-casas-PT.csv equivalent, but regional).

## What's done

- `ine_extractor.py` pulls INE indicator **varcd 0012234** ("Valor mediano das vendas de alojamentos familiares... EUR/m2", Metodologia 2022) via the free JSON API (`pindicaMeta.jsp` / `pindica.jsp`), no scraping needed.
- Output: `ine_precos_m2_full.csv` — 24,128 rows, quarterly **Q4 2019 → Q1 2026** (26 quarters), across Portugal / NUTS I-III / 308 municípios / 581 freguesias.
- Freguesia coverage: 397/581 have ≥1 non-empty quarter, 276/581 have all 26 quarters (rest suppressed by INE's statistical secrecy rule for low transaction counts — mostly small/rural parishes).
- Script is idempotent and reusable — swap `VARCD` to pull related series already identified:
  - `0014696` — median rent EUR/m2 (new contracts), Q1 2020–Q1 2026, also freguesia-level
  - `0014363` — number of sale transactions, same geography/time as the price series
- Rate limit: INE throttles concurrent requests. Current script uses 12 threads with retry/backoff; only 3/931 calls were dropped on the last run. Don't go much higher on concurrency.

## Not done yet — blockers before the map UI can be built

1. **Boundary geometries.** Need DGT's CAOP GeoJSON for freguesia polygons: `https://ogcapi.dgterritorio.gov.pt/collections/freguesias` (also mirrored as a lighter simplified GeoJSON via "Aldeias Portuguesas", ~25.7MB). Not yet fetched or inspected.
2. **The join.** INE's `geo_cod` in the CSV (e.g. `112030201` for a freguesia) needs to be matched against whatever code CAOP uses for the same polygon. Likely DICOFRE-based (2 district + 2 município + 2 freguesia digits) but this hasn't been verified — CAOP may use a different code scheme (esp. post-2013 parish-merger codes, which INE's NUTS-2024 codes should already reflect but CAOP might not use identical strings). Check this first before building anything — a silent mismatched join would quietly drop most of the map.
3. **No preview/sanity chart built yet.** Before investing in the full interactive map, worth plotting 3-4 regions (e.g. Lisboa, Porto, a rural município) in EUR and BTC-denominated terms using the existing `bitcoin-tools/data/btc_eur.csv`, same pattern as `app_imob.py`'s BTC merge logic.
4. **Time-scope decision deferred.** User wants to revisit how far back to go (6 years available via this source vs the 20-year national-only series). Not decided.

## Design note

Per `bitcoin-tools/CLAUDE.md`, any UI/visual work on this must follow `design-guidelines.md` before touching layout, color, or copy.
