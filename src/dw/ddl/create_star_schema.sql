-- IMPORTANT: Set your schema in DBeaver before running. The default schema is 'procurement_governance'.

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

CREATE TABLE dim_cpv (
    cpv_key        INTEGER IDENTITY NOT NULL,
    cpv_code       CHAR(8)          NOT NULL,
    cpv_division   VARCHAR(4),
    cpv_group      VARCHAR(4),
    cpv_class      VARCHAR(4),
    PRIMARY KEY (cpv_key)
);

CREATE TABLE dim_procedure_type (
    procedure_key      INTEGER IDENTITY NOT NULL,
    procedure_code     VARCHAR(20)      NOT NULL,
    procedure_name     VARCHAR(100),
    transparency_level SMALLINT,
    is_open            BOOLEAN,
    PRIMARY KEY (procedure_key)
);

CREATE TABLE fact_tender (
    award_id           VARCHAR(100)     NOT NULL,
    id_notice_can      VARCHAR(100),
    id_lot             VARCHAR(100),
    "year"              SMALLINT         NOT NULL,
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
