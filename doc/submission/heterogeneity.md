# Forms of Heterogeneity — TED ↔ CPI/WGI

**Project:** Red Flags Procurement Governance  
**Exercise:** Challenge 3 — Sheet 3, Exercise 1.4

---

## 1. Schema Heterogeneity (Structural)

| Aspect | TED | CPI | WGI |
|--------|-----|-----|-----|
| Source format | CSV (75 columns raw → 15 kept + 10 flags, auto-exports Parquet + CSV) | CSV (10 columns → 3 kept) | API (`wbgapi`, 8 columns kept) |
| Row count | ~1.78 Mio. (after dedup) | 40 (4 countries × 10 years) | 40 (4 countries × 10 years) |
| Granularity | Per award (`ID_AWARD`) | Per country-year | Per country-year |
| Key columns | `ID_AWARD`, `ISO_COUNTRY_CODE`, `YEAR` | `country_iso3`, `year`, `cpi_score` | `country_iso3`, `year`, 6× WGI |

> **Example:** TED delivers 1.78 million rows at award granularity, CPI/WGI each deliver 40 rows at country-year granularity. Joining requires SCD Type 2 on the country dimension — governance data is replicated across all awards of the same country-year combination.

---

## 2. Semantic Heterogeneity (Country Codes)

- **TED:** Uses ISO Alpha-2 codes directly in the source CSV:  
  `ISO_COUNTRY_CODE = 'DE'`, `'DK'`, `'RO'`, `'HU'`
- **CPI/WGI:** Uses ISO Alpha-3 codes:  
  `country_iso3 = 'DEU'`, `'DNK'`, `'ROU'`, `'HUN'`

> **Example:** Without mapping, `SELECT … WHERE country = 'DE'` would match TED rows but miss CPI/WGI rows. Resolution: [`lookup_countries.csv`](../../data/lookup/lookup_countries.csv) provides bidirectional mapping (alpha_2 ↔ alpha_3), applied during dimension building.

---

## 3. Temporal Heterogeneity

- **TED:** Column `YEAR` (SMALLINT, 2014–2023). Award date from `DT_AWARD` is available but not imported — only the year is used.
- **CPI/WGI:** Column `year` (SMALLINT, 2014–2023). Published annually; no sub-year resolution exists.

> **Example:** TED has multiple awards per country-year (e.g., 399,352 rows for 2021 alone), while CPI/WGI have exactly one row per country-year. For analysis, governance scores must be replicated across all TED rows of the same country-year via the SCD Type 2 country dimension.

---

## 4. Value Range Heterogeneity

- **TED measures:** `AWARD_VALUE_EURO` in Euro (0 to billions), `NUMBER_OFFERS` (0–999), Red Flag booleans
- **CPI:** `cpi_score` (SMALLINT, 0–100) — higher = less corruption
- **WGI:** 6 dimensions (DECIMAL(5,2), ~[-2.5, +2.5]) — higher = better governance

> **Example:** Aggregating `AVG(cpi_score)` and `AVG(F1)` in the same query requires awareness: `cpi_score` is a STOCK attribute (one value per country-year), while `F1` is a VPU measure computed per award. The SQL must handle these different aggregation types differently — CPI needs `AVG`, F1 needs `SUM(CAST(F1 AS INT)) / COUNT(*)`.

---

## Summary

| Heterogeneity Type | TED | CPI/WGI | Resolution |
|--------------------|-----|---------|------------|
| Schema | 15 columns, award granularity | 3–8 columns, country‑year granularity | SCD Type 2 dimension |
| Semantic (countries) | Alpha‑2 (`DE`) | Alpha‑3 (`DEU`) | `lookup_countries.csv` |
| Temporal | Year only, many rows/year | Year only, one row/year | JOIN via `dim_country` |
| Value range | EUR / counts / booleans | 0–100 / [-2.5, +2.5] | Separate aggregation strategies |
