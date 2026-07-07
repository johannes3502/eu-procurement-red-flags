# Snowflake Schema Variant — Data Modelling

**Project:** Red Flags Procurement Governance  
**Author:** Johannes

---

## 1. Snowflake Normalisation Strategies

### 1a. CPV Hierarchy Normalisation (Primary Variant)

The denormalised `dim_cpv` in the star schema contains division, group, class, and full code in a single table. A snowflake variant normalises this hierarchy into separate tables — one per CPV level:

```text
dim_cpv_division   ──<  dim_cpv_group   ──<  dim_cpv_class   ──<  dim_cpv_code
     division_id    │      group_id       │      class_id       │      code_id
     division_name  │      division_fk    │      group_fk       │      class_fk
     division_desc  │      group_name     │      class_name     │      cpv_code
                    │      group_desc     │      class_desc     │
```

**How it works:**
- `dim_cpv_division` stores the 2‑digit division (e.g., `'03'`) with its description once.
- `dim_cpv_group` stores the 3‑digit group (e.g., `'031'`), references its division, and is itself referenced by `dim_cpv_class`.
- `dim_cpv_class` stores the 4‑digit class (e.g., `'0311'`), references its group.
- `dim_cpv_code` stores the full 8‑digit code (e.g., `'03110000'`), references its class.
- `fact_tender` references `dim_cpv_code.code_id` instead of the denormalised `dim_cpv`.

**Impact on queries:**
- **Before (star):** `SELECT ... FROM fact_tender f JOIN dim_cpv c ON f.cpv_key = c.cpv_key`
- **After (snowflake):** `SELECT ... FROM fact_tender f JOIN dim_cpv_code c ON f.cpv_code_key = c.code_id JOIN dim_cpv_class cl ON c.class_fk = cl.class_id JOIN dim_cpv_group g ON cl.group_fk = g.group_id JOIN dim_cpv_division d ON g.division_fk = d.division_id`

### 1b. Governance Outrigger (Alternative Normalisation)

CPI and WGI scores are embedded directly in `dim_country` in the star schema (SCD Type 2). A snowflake alternative extracts these into a separate governance dimension:

```
dim_country:          country_key, country_code, country_name, fk_governance_key
dim_governance:       governance_key, country_iso3, year,
                      cpi_score, wgi_* (6×)
```

**How it works:**
- `dim_country` contains only stable country attributes (code, name).
- `dim_governance` stores one row per country‑year with all governance scores.
- `dim_country.fk_governance_key` references the appropriate governance version.

**Note:** The SCD Type 2 in the star schema already handles governance changes by versioning the country row. The outrigger is an alternative approach that separates concerns but adds a JOIN for every governance query.

---

## 2. Star Schema vs. Snowflake Schema — Comparison

| Criterion | Star Schema | Snowflake Schema |
|-----------|-------------|------------------|
| **Query Performance** | ✅ Fewer JOINs → faster analytical aggregations | ❌ 2–4 additional JOINs per query; noticeable on 1.78M‑row fact table |
| **Storage Efficiency** | ❌ Division/group/class names repeated per CPV code (~5K rows × few hundred bytes = ~1 MB) | ✅ Each hierarchy level stored once — negligible gain on a ~300 MB database |
| **Maintainability** | ✅ Single `dim_cpv` table; ETL is a simple `df["cpv_code"].drop_duplicates()` | ❌ Four tables; inserting a new CPV code requires resolving/linking all hierarchy levels |
| **Business User Friendliness** | ✅ Analysts and non‑technical users see all CPV attributes in one place | ❌ Users must navigate multiple tables to see the full hierarchy |
| **CPV Hierarchy Stability** | ✅ CPV codes change very slowly (years between revisions) → low denormalisation cost | ✅ In theory, updating a division name touches one row — but in practice this almost never happens |
| **ETL Complexity** | ✅ Low — single pandas expression | ❌ Medium — need to track new/updated divisions, groups, classes and build cross‑references |
| **Governance Queries** | ✅ CPI/WGI joined via `dim_country` in one hop | ❌ Outrigger adds another JOIN; composite key `(country, year)` needed |

---

## 3. Decision

**✅ Star Schema is the better choice for this project.**

### Reasons

1. **Performance dominates the use case.** Analytical queries aggregate 1.78 M tender rows across years, countries, and CPV groups. Each additional JOIN in a snowflake multiplies the query execution cost. The 4‑level CPV snowflake would require 2–4 extra JOINs per query.

2. **Storage savings are irrelevant.** ~5,000 distinct CPV codes occupy roughly 1 MB even fully denormalised. In a ~300 MB database, this is below the noise floor.

3. **CPV hierarchy is extremely stable.** The CPV nomenclature changes every few years at most. The risk of update anomalies in the denormalised `dim_cpv` is near‑zero.

4. **ETL simplicity matters for a student project.** The star ETL is a one‑line pandas deduplication (`df["cpv_code"].drop_duplicates()`). The snowflake would require iterative lookup‑and‑link across four tables.

### When Would Snowflake Be Better?

- If the CPV hierarchy were large (millions of codes) or changed daily.
- If the database were extremely storage‑constrained.
- If queries primarily used one hierarchy level (e.g., only divisions) and never needed the full code.

None of these conditions apply to this project.

---

*Document prepared 2026-05-17 .*
