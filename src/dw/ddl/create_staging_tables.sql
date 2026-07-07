-- IMPORTANT: Set your schema in DBeaver before running. The default schema is 'procurement_governance'.

CREATE TABLE stg_ted (
    ID_AWARD           VARCHAR(100),
    ID_NOTICE_CAN      VARCHAR(100),
    ID_LOT             VARCHAR(100),
    "YEAR"             SMALLINT,
    ISO_COUNTRY_CODE   CHAR(2),
    winner_country     CHAR(2),
    winner_country_raw VARCHAR(500),
    AWARD_VALUE_EURO   DECIMAL(18,2),
    VALUE_EURO         DECIMAL(18,2),
    NUMBER_OFFERS      SMALLINT,
    B_AWARDED_TO_A_GROUP CHAR(1),
    TOP_TYPE           VARCHAR(10),
    LOTS_NUMBER        INTEGER,
    NUMBER_AWARDS      INTEGER,
    cpv_code           CHAR(8),
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
    error_info          VARCHAR(2000)
);

CREATE TABLE stg_cpi (
    country_iso3  CHAR(3),
    "YEAR"        SMALLINT,
    cpi_score     SMALLINT,
    error_info    VARCHAR(2000)
);

CREATE TABLE stg_wgi (
    country_iso3            CHAR(3),
    "YEAR"                  SMALLINT,
    control_of_corruption   DECIMAL(5,2),
    government_effectiveness DECIMAL(5,2),
    political_stability     DECIMAL(5,2),
    rule_of_law             DECIMAL(5,2),
    regulatory_quality      DECIMAL(5,2),
    voice_accountability    DECIMAL(5,2),
    error_info              VARCHAR(2000)
);
