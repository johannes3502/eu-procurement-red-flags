-- ============================================================================
-- Exercise 1 (Data Modelling) — Star Schema DDL
-- Target: Exasol
-- Author: Johannes, OTH Regensburg
-- ============================================================================
-- Order of creation:
--   1. dim_country        (SCD Type 2 with CPI/WGI governance scores)
--   2. dim_cpv            (CPV classification hierarchy)
--   3. dim_procedure_type (award procedure metadata)
--   4. fact_tender        (measures + flags, FK to all dimensions)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. dim_country — SCD Type 2 with governance scores
-- ----------------------------------------------------------------------------
-- Each row represents a country-year combination where CPI/WGI scores changed.
-- SCD logic: valid_from_year = year of the CPI/WGI data point,
-- valid_to_year = next year's valid_from_year - 1 (or 9999 for current).
-- ----------------------------------------------------------------------------
CREATE TABLE dim_country (
    country_key        INTEGER IDENTITY NOT NULL,
    country_code       CHAR(2)          NOT NULL,   -- ISO Alpha-2: DE, DK, RO, HU
    country_name       VARCHAR(100)     NOT NULL,
    -- Governance scores (STOCK attributes — point-in-time, year-specific; 0% NULL in source data)
    cpi_score          SMALLINT         NOT NULL,  -- 0–100
    control_of_corruption      DECIMAL(5,2) NOT NULL,
    government_effectiveness   DECIMAL(5,2) NOT NULL,
    political_stability        DECIMAL(5,2) NOT NULL,
    rule_of_law                DECIMAL(5,2) NOT NULL,
    regulatory_quality         DECIMAL(5,2) NOT NULL,
    voice_accountability       DECIMAL(5,2) NOT NULL,
    -- SCD Type 2 validity period
    valid_from_year    SMALLINT         NOT NULL,
    valid_to_year      SMALLINT         NOT NULL,   -- 9999 = currently valid
    --
    PRIMARY KEY (country_key)
);


-- ----------------------------------------------------------------------------
-- 2. dim_cpv — CPV classification hierarchy (denormalised)
-- ----------------------------------------------------------------------------
-- CPV codes are zero-padded to 8 digits. Hierarchy is extracted from the
-- string: division (2) → group (3) → class (4) → full code (8).
-- ----------------------------------------------------------------------------
CREATE TABLE dim_cpv (
    cpv_key        INTEGER IDENTITY NOT NULL,
    cpv_code       CHAR(8)          NOT NULL,   -- e.g. '03110000'
    cpv_division   VARCHAR(4),                  -- first 2 digits, e.g. '03'
    cpv_group      VARCHAR(4),                  -- first 3 digits, e.g. '031'
    cpv_class      VARCHAR(4),                  -- first 4 digits, e.g. '0311'
    --
    PRIMARY KEY (cpv_key)
);


-- ----------------------------------------------------------------------------
-- 3. dim_procedure_type — award procedure metadata
-- ----------------------------------------------------------------------------
-- Fixed, small mapping table (~10 rows).
-- transparency_level: 1 (least transparent) to 5 (most transparent).
-- ----------------------------------------------------------------------------
CREATE TABLE dim_procedure_type (
    procedure_key      INTEGER IDENTITY NOT NULL,
    procedure_code     VARCHAR(20)      NOT NULL,   -- e.g. 'OPE', 'NIC', 'AWP'
    procedure_name     VARCHAR(100),                -- e.g. 'Open Procedure'
    transparency_level SMALLINT,                    -- 1–5
    is_open            BOOLEAN,                     -- TRUE = competitive/open
    --
    PRIMARY KEY (procedure_key)
);


-- ----------------------------------------------------------------------------
-- 4. fact_tender — tender award fact table
-- ----------------------------------------------------------------------------
-- One row per award (ID_AWARD). No separate dim_time per exercise spec.
-- crisis_type is derived from year (see inline comment).
--
-- FK naming convention: foreign keys use the SAME column names as the
-- dimension primary keys they reference.
-- ----------------------------------------------------------------------------
CREATE TABLE fact_tender (
    award_id           VARCHAR(100)     NOT NULL,   -- natural key: ID_AWARD
    id_notice_can      VARCHAR(100),                -- degenerate dimension
    id_lot             VARCHAR(100),                -- degenerate dimension (NULL-prone)
    --
    -- Time attributes (embedded — no separate dim_time per exercise spec)
    year               SMALLINT         NOT NULL,
    -- crisis_type derived from year:
    --   2014-2019 -> 'keine Krise'
    --   2020-2021 -> 'COVID-19'
    --   2022-2023 -> 'Ukraine-Krieg'
    crisis_type        VARCHAR(50),
    --
    -- Foreign keys to dimension tables (names match dimension PKs)
    country_key        INTEGER,                     -- FK → dim_country.country_key (Auftraggeber-Land)
    winner_country_key INTEGER,                     -- FK → dim_country.country_key (Gewinner-Land, Role-Playing)
    cpv_key            INTEGER,                     -- FK → dim_cpv.cpv_key
    procedure_key      INTEGER,                     -- FK → dim_procedure_type.procedure_key
    --
    -- Measures (FLOW — additive)
    award_value_eur    DECIMAL(18,2),               -- genuine; sentinel (€10¹³) removed, no clipping
    value_eur          DECIMAL(18,2),               -- raw estimate (for F2 only)
    number_offers      SMALLINT,
    lots_number        INTEGER,
    number_awards      INTEGER,
    --
    -- Red Flags (BOOLEAN → VPU in analysis)
    F1                              BOOLEAN,        -- Single-Bidder
    F2                              BOOLEAN,        -- Estimate/Award Discrepancy > 10.0
    F3                              BOOLEAN,        -- No Prior Call / Direct Award
    F5                              BOOLEAN,        -- Award to Group (excl. 2014–2015)
    F6                              BOOLEAN,        -- Single-Bidder + High Value
    F7                              BOOLEAN,        -- Lot Fragmentation
    --
    -- Combination Flags
    comb_single_discrepancy         BOOLEAN,        -- F1 AND F2
    comb_single_non_open            BOOLEAN,        -- F1 AND (TOP_TYPE != 'OPE')
    comb_no_call_high_value         BOOLEAN,        -- F3 AND F6
    comb_frag_single                BOOLEAN,        -- F7 AND F1
    --
    PRIMARY KEY (award_id),
    FOREIGN KEY (country_key)        REFERENCES dim_country (country_key),
    FOREIGN KEY (winner_country_key) REFERENCES dim_country (country_key),
    FOREIGN KEY (cpv_key)            REFERENCES dim_cpv (cpv_key),
    FOREIGN KEY (procedure_key)      REFERENCES dim_procedure_type (procedure_key)
);
