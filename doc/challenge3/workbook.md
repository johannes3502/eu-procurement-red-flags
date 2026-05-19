# Challenge 3: Data Modelling and Importing the Data

**Name:** Johannes, OTH Regensburg

---

## Title

Mehrdimensionale Analyse von Auffälligkeiten in EU-Vergabedaten (TED)
mit externen Governance‑Scores (CPI/WGI) – Ein Data‑Warehouse‑Ansatz

---

## Staging Area: Tables

*`CREATE TABLE` commands for the staging area — 1:1 mirrors of the cleaned parquet files. (Exercise Sheet 3, Exercise 1.3)*

```sql
-- ============================================================================
-- stg_ted — 1:1 mirror of ted_clean.parquet (15 columns)
-- ============================================================================
CREATE TABLE stg_ted (
    ID_AWARD           VARCHAR(100),
    ID_NOTICE_CAN      VARCHAR(100),
    ID_LOT             VARCHAR(100),
    YEAR               SMALLINT,
    ISO_COUNTRY_CODE   CHAR(2),
    winner_country     CHAR(2),
    winner_country_raw VARCHAR(100),
    AWARD_VALUE_EURO   DECIMAL(18,2),
    VALUE_EURO         DECIMAL(18,2),
    NUMBER_OFFERS      SMALLINT,
    B_AWARDED_TO_A_GROUP CHAR(1),
    TOP_TYPE           VARCHAR(10),
    LOTS_NUMBER        INTEGER,
    NUMBER_AWARDS      INTEGER,
    cpv_code           CHAR(8)
);
```

```sql
-- ============================================================================
-- stg_cpi — 1:1 mirror of cpi_clean.parquet (3 columns)
-- ============================================================================
CREATE TABLE stg_cpi (
    country_iso3  CHAR(3),
    year          SMALLINT,
    cpi_score     SMALLINT
);
```

```sql
-- ============================================================================
-- stg_wgi — 1:1 mirror of wgi_clean.parquet (8 columns)
-- ============================================================================
CREATE TABLE stg_wgi (
    country_iso3            CHAR(3),
    year                    SMALLINT,
    control_of_corruption   DECIMAL(5,2),
    government_effectiveness DECIMAL(5,2),
    political_stability     DECIMAL(5,2),
    rule_of_law             DECIMAL(5,2),
    regulatory_quality      DECIMAL(5,2),
    voice_accountability    DECIMAL(5,2)
);
```

---

## Forms of Heterogeneity

*Which forms of heterogeneity exist between TED and CPI/WGI? (Exercise Sheet 3, Exercise 1.4)*

### 1. Schema Heterogeneity (Structural)

| Aspect | TED | CPI | WGI |
|--------|-----|-----|-----|
| Source format | CSV (75 columns raw → 15 kept) | CSV (10 columns → 3 kept) | API (`wbgapi`, 8 columns kept) |
| Row count | ~1.78 Mio. (after dedup) | 40 (4 countries × 10 years) | 40 (4 countries × 10 years) |
| Granularity | Per award (`ID_AWARD`) | Per country-year | Per country-year |
| Key columns | `ID_AWARD`, `ISO_COUNTRY_CODE`, `YEAR` | `country_iso3`, `year`, `cpi_score` | `country_iso3`, `year`, 6× WGI |

> **Example:** TED delivers 1.78 million rows at award granularity, CPI/WGI each deliver 40 rows at country-year granularity. Joining requires SCD Type 2 on the country dimension — governance data is replicated across all awards of the same country-year combination.

---

### 2. Semantic Heterogeneity (Country Codes)

- **TED:** Uses ISO Alpha-2 codes directly in the source CSV: `ISO_COUNTRY_CODE = 'DE'`, `'DK'`, `'RO'`, `'HU'`
- **CPI/WGI:** Uses ISO Alpha-3 codes: `country_iso3 = 'DEU'`, `'DNK'`, `'ROU'`, `'HUN'`

> **Example:** Without mapping, `SELECT … WHERE country = 'DE'` would match TED rows but miss CPI/WGI rows. Resolution: `lookup_countries.csv` provides bidirectional mapping (alpha_2 ↔ alpha_3), applied during dimension building.

---

### 3. Temporal Heterogeneity

- **TED:** Column `YEAR` (SMALLINT, 2014–2023). Award date from `DT_AWARD` is available but not imported — only the year is used.
- **CPI/WGI:** Column `year` (SMALLINT, 2014–2023). Published annually; no sub-year resolution exists.

> **Example:** TED has multiple awards per country-year (e.g., 399,352 rows for 2021 alone), while CPI/WGI have exactly one row per country-year. For analysis, governance scores must be replicated across all TED rows of the same country-year via the SCD Type 2 country dimension.

---

### 4. Value Range Heterogeneity

- **TED measures:** `AWARD_VALUE_EURO` in Euro (0 to billions), `NUMBER_OFFERS` (0–999), Red Flag booleans
- **CPI:** `cpi_score` (SMALLINT, 0–100) — higher = less corruption
- **WGI:** 6 dimensions (DECIMAL(5,2), ~[-2.5, +2.5]) — higher = better governance

> **Example:** Aggregating `AVG(cpi_score)` and `AVG(F1)` in the same query requires awareness: `cpi_score` is a STOCK attribute (one value per country-year), while `F1` is a VPU measure computed per award. The SQL must handle these different aggregation types differently — CPI needs `AVG`, F1 needs `SUM(CAST(F1 AS INT)) / COUNT(*)`.

---

### Summary

| Heterogeneity Type | TED | CPI/WGI | Resolution |
|--------------------|-----|---------|------------|
| Schema | 15 columns, award granularity | 3–8 columns, country‑year granularity | SCD Type 2 dimension |
| Semantic (countries) | Alpha‑2 (`DE`) | Alpha‑3 (`DEU`) | `lookup_countries.csv` |
| Temporal | Year only, many rows/year | Year only, one row/year | JOIN via `dim_country` |
| Value range | EUR / counts / booleans | 0–100 / [-2.5, +2.5] | Separate aggregation strategies |

---

## Star / Snowflake Schema

*The DDL of the final star schema — with `winner_country` as Role-Playing FK. (Exercise Sheet 3, Exercise 1.6)*

### Fact table: `fact_tender`

```sql
CREATE TABLE fact_tender (
    award_id           VARCHAR(100)     NOT NULL,
    id_notice_can      VARCHAR(100),
    id_lot             VARCHAR(100),
    year               SMALLINT         NOT NULL,
    crisis_type        VARCHAR(50),
    country_key        INTEGER,
    winner_country_key INTEGER,
    cpv_key            INTEGER,
    procedure_key      INTEGER,
    award_value_eur    DECIMAL(18,2),
    value_eur          DECIMAL(18,2),
    number_offers      SMALLINT,
    lots_number        INTEGER,
    number_awards      INTEGER,
    F1                              BOOLEAN,
    F2                              BOOLEAN,
    F3                              BOOLEAN,
    F5                              BOOLEAN,
    F6                              BOOLEAN,
    F7                              BOOLEAN,
    comb_single_discrepancy         BOOLEAN,
    comb_single_non_open            BOOLEAN,
    comb_no_call_high_value         BOOLEAN,
    comb_frag_single                BOOLEAN,
    PRIMARY KEY (award_id),
    FOREIGN KEY (country_key)        REFERENCES dim_country (country_key),
    FOREIGN KEY (winner_country_key) REFERENCES dim_country (country_key),
    FOREIGN KEY (cpv_key)            REFERENCES dim_cpv (cpv_key),
    FOREIGN KEY (procedure_key)      REFERENCES dim_procedure_type (procedure_key)
);
```

- **One row per `ID_AWARD`** (CORRECTIONS-aware dedup). `ID_NOTICE_CAN` and `ID_LOT` as degenerate dimensions.
- **Role-Playing:** `dim_country` referenced twice — `country_key` (Auftraggeber-Land = `ISO_COUNTRY_CODE`), `winner_country_key` (Gewinner-Land = parsed `WIN_COUNTRY_CODE`).
- **Red Flags:** 6 single flags (F1–F3, F5–F7) + 4 combinations. F4 dropped (99.16% NULL).
- **AWARD_VALUE_EURO:** Sentinel removal (€10T → NaN) only — no percentile clipping.

### Dimension tables

```sql
-- dim_country — SCD Type 2 with governance scores
CREATE TABLE dim_country (
    country_key        INTEGER IDENTITY NOT NULL,
    country_code       CHAR(2)          NOT NULL,
    country_name       VARCHAR(100)     NOT NULL,
    cpi_score          SMALLINT         NOT NULL,
    control_of_corruption      DECIMAL(5,2) NOT NULL,
    government_effectiveness   DECIMAL(5,2) NOT NULL,
    political_stability        DECIMAL(5,2) NOT NULL,
    rule_of_law                DECIMAL(5,2) NOT NULL,
    regulatory_quality         DECIMAL(5,2) NOT NULL,
    voice_accountability       DECIMAL(5,2) NOT NULL,
    valid_from_year    SMALLINT         NOT NULL,
    valid_to_year      SMALLINT         NOT NULL,
    PRIMARY KEY (country_key)
);
```

```sql
-- dim_cpv — CPV classification hierarchy (denormalised)
CREATE TABLE dim_cpv (
    cpv_key        INTEGER IDENTITY NOT NULL,
    cpv_code       CHAR(8)          NOT NULL,
    cpv_division   VARCHAR(4),
    cpv_group      VARCHAR(4),
    cpv_class      VARCHAR(4),
    PRIMARY KEY (cpv_key)
);
```

```sql
-- dim_procedure_type — award procedure metadata
CREATE TABLE dim_procedure_type (
    procedure_key      INTEGER IDENTITY NOT NULL,
    procedure_code     VARCHAR(20)      NOT NULL,
    procedure_name     VARCHAR(100),
    transparency_level SMALLINT,
    is_open            BOOLEAN,
    PRIMARY KEY (procedure_key)
);
```

---

## IMPORT

*`IMPORT` commands to load data from cleaned CSV files into staging tables. (Exercise Sheet 3, Exercise 2.1)*

**Prerequisite:** One-time CSV export from parquet (Python):
```python
import pandas as pd
pd.read_parquet('data/processed/ted/ted_clean.parquet').to_csv('data/processed/ted/ted_clean.csv', index=False)
pd.read_parquet('data/processed/cpi/cpi_clean.parquet').to_csv('data/processed/cpi/cpi_clean.csv', index=False)
pd.read_parquet('data/processed/wgi/wgi_clean.parquet').to_csv('data/processed/wgi/wgi_clean.csv', index=False)
```

```sql
-- IMPORT stg_ted — ~1.78M rows, ~28 MB CSV
IMPORT INTO stg_ted
FROM LOCAL CSV FILE 'data/processed/ted/ted_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1;

-- IMPORT stg_cpi — 40 rows
IMPORT INTO stg_cpi
FROM LOCAL CSV FILE 'data/processed/cpi/cpi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1;

-- IMPORT stg_wgi — 40 rows
IMPORT INTO stg_wgi
FROM LOCAL CSV FILE 'data/processed/wgi/wgi_clean.csv'
ENCODING = 'UTF-8'
ROW SEPARATOR = 'LF'
COLUMN SEPARATOR = ','
COLUMN DELIMITER = '"'
SKIP = 1;
```

---

## Numbers

* Number of rows in your biggest table: **1,784,558**
* Size (KB, MB, or GB) of your biggest table: **29,103 KB (28.42 MB)**
* Name of that biggest table: **fact_tender**
* Total size of your schema: **29,113 KB (28.43 MB)**

*(Measured from `ted_clean.parquet` + `cpi_clean.parquet` + `wgi_clean.parquet` on disk.)*

---

## ME/R Model

![ME/R Model](../exercise1/mer_model.png)
