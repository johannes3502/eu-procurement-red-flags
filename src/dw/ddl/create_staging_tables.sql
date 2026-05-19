-- ============================================================================
-- Challenge 3 — Staging Area DDL
-- Target: Exasol
-- Author: Johannes, OTH Regensburg
-- ============================================================================
-- These tables mirror the cleaned parquet files 1:1.
-- No constraints, no PKs, no FKs — staging is a raw dump area.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- stg_ted — 1:1 mirror of ted_clean.parquet (15 columns)
-- ----------------------------------------------------------------------------
-- All columns match config.TED_KEEP_COLUMNS exactly.
-- Types from config.EXASOL_TYPE_MAP.
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- stg_cpi — 1:1 mirror of cpi_clean.parquet (3 columns)
-- ----------------------------------------------------------------------------
-- CPI scores 0–100, 0% NULL, 40 rows (4 countries × 10 years).
-- ----------------------------------------------------------------------------
CREATE TABLE stg_cpi (
    country_iso3  CHAR(3),
    year          SMALLINT,
    cpi_score     SMALLINT
);

-- ----------------------------------------------------------------------------
-- stg_wgi — 1:1 mirror of wgi_clean.parquet (8 columns)
-- ----------------------------------------------------------------------------
-- WGI scores [-2.5, +2.5], 0% NULL, 40 rows.
-- ----------------------------------------------------------------------------
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
