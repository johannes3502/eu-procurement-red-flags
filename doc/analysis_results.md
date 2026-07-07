# Analysis Results

**Project:** Red Flags Procurement Governance  
**Date:** 2026-06-18  
**Schema:** Exasol schema `procurement_governance`
**Data:** 1,783,795 clean TED tenders (2014–2023) × 4 countries × CPI/WGI governance scores

---

## Data Volume Summary

| Table | Rows | Description |
|-------|------|-------------|
| `dim_procedure_type` | 9 | Procedure types with transparency levels |
| `dim_cpv` | 6,470 | Distinct CPV codes with hierarchy |
| `dim_country` | 40 | SCD Type 2: 4 countries × 10 years |
| `fact_tender` | 1,783,795 | Clean tenders (762 failed procurements + 1 NULL ID excluded) |

---

## Q1 — ROLLUP: Red Flag Rates by Country and Year

**What:** Single-Bidder (F1), Estimate/Award Discrepancy (F2), and No-Prior-Call (F3) rates aggregated across three levels: per country-year, per country subtotal, and grand total.

**Key Findings:**

| Country | F1 (Single-Bidder) | F2 (Discrepancy) | F3 (No-Prior-Call) |
|---------|-------------------:|-----------------:|--------------------:|
| Denmark | 13.12% | 24.75% | 10.64% |
| Germany | 18.77% | 9.99% | 14.96% |
| Hungary | 32.16% | 37.93% | 8.10% |
| Romania | 16.98% | 51.21% | 0.70% |
| **Grand Total** | **18.36%** | **33.71%** | **6.95%** |

- **Hungary** has the highest single-bidder rate (32%), nearly double the EU average — consistent with its declining CPI (55 → 40).
- **Romania's** F2 rate (51%) is extreme. Over half of all Romanian tenders show the estimated value exceeding the award value by a factor >10. This suggests systematic overestimation or a different reporting practice.
- **Denmark's** F3 rate (10.64%) is surprising for a high-CPI country. Non-open procedures are not exclusively a corruption signal — they may reflect specialized procurement needs in a small economy.
- **Germany** is the "control group": mid-range CPI, mid-range red flag rates across all three indicators.

---

## Q2 — Window Function: 3-Year Moving Average of Single-Bidder Rate

**What:** `AVG OVER (PARTITION BY country ORDER BY year ROWS 2 PRECEDING)` smooths annual fluctuations to reveal long-term trends.

**Key Findings:**

| Country | Trend (2014 → 2023) | Moving Avg Change |
|---------|---------------------|:-----------------:|
| Denmark | 4.75% → 16.43% | ↗ +246% |
| Germany | 10.61% → 23.59% | ↗ +122% |
| Hungary | 33.03% → 32.42% | → stable |
| Romania | 18.00% → 13.44% | ↘ –25% |

- **Denmark** shows the steepest increase. The single-bidder rate more than tripled over 10 years. This could reflect increasing market concentration or a shift toward specialized procurement.
- **Germany** also trends upward, with a notable jump in 2022 (23.73%) — coinciding with the Ukraine war and energy crisis.
- **Hungary** is stable at a high level (~32%) — a structural issue, not a temporal one.
- **Romania** actually **declines** in single-bidder rate from 2014 to 2023, despite its low CPI. The massive increase in tender volume during COVID (156k → 190k tenders/year) dilutes the single-bidder rate. Raw flagged counts stay high, but the denominator grows faster.

---

## Q3 — RANK: Top 15 CPV Divisions by Discrepancy Rate (F2)

**What:** `RANK() OVER (ORDER BY f2_pct DESC)` identifies procurement categories most prone to inflated estimates. Divisions with <50 tenders excluded (noise filter).

**Top 5 CPV Divisions:**

| Rank | CPV Div | F2 Rate | Tenders | Likely Category |
|:----:|---------|--------:|--------:|-----------------|
| 1 | 15 | 61.72% | 69,642 | Construction materials |
| 2 | 33 | 50.11% | 736,282 | Medical equipment, pharmaceuticals |
| 3 | 03 | 48.80% | 6,567 | Agricultural products |
| 4 | 60 | 41.62% | 53,552 | Transport services |
| 5 | 18 | 39.48% | 11,623 | Clothing, footwear |

- **Division 15** (construction materials) tops the list with 62% discrepancy rate. Construction projects are notorious for cost overruns — the estimate may reflect a maximum budget rather than a realistic prediction.
- **Division 33** (medical/pharma) has the largest tender volume (736k) AND 50% F2 rate. COVID-19 procurement likely amplifies this — emergency purchases with inflated estimates.
- The full 6,470 CPV codes provide granular drill-down capability for procurement auditors.

---

## Q4 — Statistical: Correlation CPI vs. Single-Bidder Rate

**What:** `CORR(cpi_score, f1_pct)` + `STDDEV_POP()` across 40 country-year data points.

**Result:** **r = –0.6919** (strong negative correlation)

| Metric | Value |
|--------|-------|
| Data points | 40 |
| Avg F1 rate | 20.59% (σ = 8.36) |
| Avg CPI score | 65.18 (σ = 19.78) |
| Correlation | **–0.6919** |

**Interpretation:** Countries with lower perceived corruption (higher CPI) tend to have lower single-bidder rates. This confirms the project's central hypothesis — governance quality, as measured by CPI, is empirically linked to competitive procurement outcomes.

The relationship is not perfectly linear (r² = 0.48). Other factors — market size, sector composition, EU funding rules, cultural norms — contribute to the remaining variance. This is a descriptive correlation, not a causal claim.

---

## Q5 — Skyline: Non-Dominated Countries

**What:** `PREFERRING HIGH avg_cpi PLUS LOW f3_rate` finds countries not dominated by any other in BOTH dimensions simultaneously.

**Result:**

| Country | Avg CPI | F3 Rate | Tenders |
|---------|--------:|--------:|--------:|
| **Romania** | 45.45 | 0.70% | 927,906 |
| **Denmark** | 89.02 | 10.64% | 80,306 |

- **Romania** survives because no other country has simultaneously a higher CPI AND a lower F3 rate. Its F3 rate (0.7%) is the lowest by far, compensating for the low CPI.
- **Denmark** survives because of its high CPI (89), even though its F3 rate (10.6%) is moderate.
- **Germany** is dominated by Denmark (higher CPI, similar or lower F3).
- **Hungary** is dominated by Romania (lower F3 at similar CPI).

The skyline reveals two Pareto-optimal procurement regimes: "clean but moderately non-open" (DK) vs. "low CPI but extremely open" (RO). Romania's low F3 rate is a positive signal that complicates the simple "low CPI = bad procurement" narrative.

---

## Q6 — Crisis Comparison: High-Value Single-Bidder (F6) by Crisis Type

**What:** F6 rate (single-bidder + above-median award value) grouped by crisis period.

**Key Findings:**

| Country | Keine Krise | COVID-19 | Ukraine-Krieg | Crisis Effect |
|---------|:-----------:|:--------:|:-------------:|:-------------:|
| Denmark | 1.34% | 2.57% | 3.17% | ↗ +137% |
| Germany | 0.57% | 1.05% | 1.25% | ↗ +119% |
| Hungary | 1.94% | 2.57% | 1.94% | → spike then recovery |
| Romania | 0.59% | 0.38% | 0.44% | → stable |

- **Denmark** and **Germany** show clear crisis amplification: high-value single-bidder awards increase during COVID and further during the Ukraine war. Emergency procurement bypasses competitive processes.
- **Hungary's** F6 rate spiked during COVID but normalized during the Ukraine war, suggesting COVID-specific emergency measures.
- **Romania's** F6 rate is consistently low and stable across crises — its tenders are numerous but individually small (avg award EUR 245k–387k), so the high-value threshold (per-year p95) captures fewer cases.

---

## Q7 — Lot Fragmentation (F7) by Procedure Type

**What:** F7 rate (awards covering <50% of lots) by procedure type and country.

**Key Findings:**

| Country | Most Fragmented Procedure | F7 Rate | Tendency |
|---------|--------------------------|--------:|----------|
| Denmark | Negotiated w/o Call (NIC) | 0.47% | Low overall |
| Germany | Negotiated w/o Call (NIC) | 0.49% | NIC leads |
| Hungary | Open Procedure | 0.05% | Near-zero |
| Romania | Open Procedure | 0.10% | Near-zero |

- **Fragmentation is generally rare** (0–0.5% across all procedures). The F7 flag fires for only ~3,300 of 1.78M tenders.
- **Germany** and **Denmark** show measurable fragmentation in non-open procedures (NIC, AWP). This is consistent with the interpretation that lot splitting is a strategy to tailor tenders to specific bidders — and non-open procedures provide the cover.
- **Hungary** and **Romania** have negligible fragmentation — their procurement structures may be less complex (fewer multi-lot contracts).
- The relationship between `transparency_level` and F7 rate is weak — high-transparency procedures (level 5) still show fragmentation in DE/DK.

---

## Summary: What We Learned

1. **Governance quality matters.** CPI correlates negatively with single-bidder rates (r = –0.69). Countries perceived as less corrupt tend to have more competitive procurement.

2. **Crises amplify risks.** Single-bidder high-value awards increase 2–2.5× during COVID and the Ukraine war in Denmark and Germany. Emergency procurement bypasses standard competitive safeguards.

3. **Romania is a paradox.** Lowest CPI (45) but also lowest F3 rate (0.7%) and declining F1 rate. High tender volume dilutes flag rates; low award values keep F6 under threshold. The raw number of flagged tenders is still substantial.

4. **Hungary shows structural issues.** Highest and most stable single-bidder rate (32%) across all 10 years. This is not a crisis effect but a persistent pattern consistent with its declining CPI trajectory.

5. **Denmark is not immune.** Despite the highest CPI (89), Denmark's single-bidder rate tripled in 10 years. High governance quality does not guarantee competitive procurement — market structure and specialization matter too.

6. **Lot fragmentation is marginal.** F7 affects <0.5% of tenders. Where it exists (DE, DK), it concentrates in non-open procedures. This metric may be more useful for targeted audits than broad analysis.

7. **CPV Division 15 (construction) and 33 (medical)** are hotspots for estimate/award discrepancy (F2 > 50%). These sectors deserve focused compliance review.

---

*Analysis executed on Exasol via DBeaver, 2026-06-18. All SQL queries in `src/dw/ddl/analytical_queries.sql`.*
