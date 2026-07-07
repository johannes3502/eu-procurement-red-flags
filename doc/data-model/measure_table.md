# Measure Table — Data Modelling

**Project:** Red Flags Procurement Governance — Star Schema  
**Author:** Johannes

---

## 1. Aggregation Type Classification

| Type | Meaning | Rule |
|------|---------|------|
| **FLOW** | Additive across all dimensions | `SUM(measure)` is meaningful across time, country, CPV, procedure |
| **STOCK** | Non-additive across time | Point-in-time value; aggregation requires `AVG` or `LAST`, never `SUM` across years |
| **VPU** | Value Per Unit (semi-additive) | Rate computed from counts; additive across all dimensions *except* where divisor changes |

---

## 2. Fact Table Measures (`fact_tender`)

All measures originate from the cleaned TED pipeline output ([`ted_clean.parquet`](../../data/processed/ted/)).

| Measure | Exasol Type | Range (post-cleaning) | Aggregation Type | Notes |
|---------|-------------|----------------------:|------------------|-------|
| `award_value_eur` | `DECIMAL(18,2)` | [0.00, >€1 Mrd] | **FLOW** | Sentinel (€10¹³) removed; genuine values unchanged (no clipping) |
| `value_eur` | `DECIMAL(18,2)` | [0.00, ~€10 M] | **FLOW** | Raw estimated value; used only for F2 computation |
| `number_offers` | `SMALLINT` | [0, 999] | **FLOW** | Count of bidders; 0 = failed procurement, 999 = capped |
| `lots_number` | `INTEGER` | [0, ~100+] | **FLOW** | Number of lots in the notice |
| `number_awards` | `INTEGER` | [0, ~100+] | **FLOW** | Number of awards in the notice |

### 2.1 Red Flag & Combination Measures (BOOLEAN → VPU)

Each flag is stored as `BOOLEAN` but analysed as a **VPU** measure:
- **Rate:** `SUM(CAST(flag AS INT)) / COUNT(*)` → fraction of tenders with that flag
- **Additivity:** Semi-additive: `COUNT` of flagged rows is additive, but the *rate* must be recomputed per group

| Flag | Name | Range | Aggregation Type | Computation Rule |
|------|------|-------|------------------|------------------|
| `F1` | Single-Bidder | {FALSE, TRUE} | **VPU** | `NUMBER_OFFERS == 1` |
| `F2` | Estimate/Award Discrepancy | {FALSE, TRUE} | **VPU** | `VALUE_EURO / AWARD_VALUE_EURO > 10.0` |
| `F3` | No Prior Call / Direct Award | {FALSE, TRUE} | **VPU** | `TOP_TYPE IN ('NIC', 'AWP')` |
| `F5` | Award to Group | {FALSE, TRUE} | **VPU** | `B_AWARDED_TO_A_GROUP == 'Y'` (excl. 2014–2015) |
| `F6` | Single-Bidder + High Value | {FALSE, TRUE} | **VPU** | `NUMBER_OFFERS == 1 AND AWARD_VALUE_EURO > per-year-p95` |
| `F7` | Lot Fragmentation | {FALSE, TRUE} | **VPU** | `NUMBER_AWARDS < LOTS_NUMBER * 0.5` |
| `comb_single_discrepancy` | Single-Bidder + Discrepancy | {FALSE, TRUE} | **VPU** | `F1 AND F2` |
| `comb_single_non_open` | Single-Bidder + Non-Open | {FALSE, TRUE} | **VPU** | `F1 AND (TOP_TYPE != 'OPE')` |
| `comb_no_call_high_value` | No Call + High Value | {FALSE, TRUE} | **VPU** | `F3 AND F6` |
| `comb_frag_single` | Fragmentation + Single | {FALSE, TRUE} | **VPU** | `F7 AND F1` |

> **Note:** `F4` (Accelerated Procedure) was dropped — 99.16 % NULL rate made it non-viable.

---

## 3. Dimension Attributes (for reference)

These are **not measures** but are numeric/quantifiable attributes that appear in dimension tables. They may be used in the exercise discussion.

| Attribute | Table | Type | Range | Aggregation Type | Notes |
|-----------|-------|------|------:|------------------|-------|
| `cpi_score` | `dim_country` | `SMALLINT` | [0, 100] | **STOCK** | Yearly CPI value; cannot be summed across years |
| `control_of_corruption` | `dim_country` | `DECIMAL(5,2)` | [-2.5, +2.5] | **STOCK** | WGI dimension — point-in-time |
| `government_effectiveness` | `dim_country` | `DECIMAL(5,2)` | [-2.5, +2.5] | **STOCK** | WGI dimension — point-in-time |
| `political_stability` | `dim_country` | `DECIMAL(5,2)` | [-2.5, +2.5] | **STOCK** | WGI dimension — point-in-time |
| `rule_of_law` | `dim_country` | `DECIMAL(5,2)` | [-2.5, +2.5] | **STOCK** | WGI dimension — point-in-time |
| `regulatory_quality` | `dim_country` | `DECIMAL(5,2)` | [-2.5, +2.5] | **STOCK** | WGI dimension — point-in-time |
| `voice_accountability` | `dim_country` | `DECIMAL(5,2)` | [-2.5, +2.5] | **STOCK** | WGI dimension — point-in-time |
| `valid_from_year` | `dim_country` | `SMALLINT` | [2014, 2023] | **STOCK** | SCD Type 2 start year |
| `valid_to_year` | `dim_country` | `SMALLINT` | [2014, 9999] | **STOCK** | SCD Type 2 end year (9999 = current) |
| `year` | `fact_tender` | `SMALLINT` | [2014, 2023] | — | Embedded in fact table per design spec |
| `transparency_level` | `dim_procedure_type` | `SMALLINT` | [0, 5] | **STOCK** | Fixed per procedure type |
| `is_open` | `dim_procedure_type` | `BOOLEAN` | {FALSE, TRUE} | — | Whether procedure is competitive/open |

---

## 4. Summary

| Aggregation Type | Count in Fact | Examples |
|------------------|:-------------:|----------|
| **FLOW** (additive) | 5 | `award_value_eur`, `value_eur`, `number_offers`, `lots_number`, `number_awards` |
| **VPU** (semi-additive) | 10 | F1–F3, F5–F7 (6) + 4 combinations |
| **STOCK** (non-additive) | 0 in fact (all in dims) | CPI/WGI scores, transparency levels |

*Document prepared 2026-05-17 .*
