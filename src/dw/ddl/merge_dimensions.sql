--
-- merge_dimensions.sql
-- Exercise Sheet 4, Exercise 2: MERGE Commands + Data Integration
-- Populates dim_procedure_type, dim_cpv, dim_country, fact_tender from staging.
--
-- Ausführen NACH data_quality_checks.sql im Schema JOHANNES_RAMSER.
--

OPEN SCHEMA JOHANNES_RAMSER;


-- ===========================================================================
-- Vorbereitung: Alte Beispiel-Zeilen löschen (falls vorhanden)
-- ===========================================================================

DELETE FROM fact_tender;
DELETE FROM dim_procedure_type;
DELETE FROM dim_cpv;
DELETE FROM dim_country;

COMMIT;


-- ===========================================================================
-- B.1: MERGE dim_procedure_type ← stg_ted
-- ===========================================================================

MERGE INTO dim_procedure_type d
USING (
    SELECT DISTINCT TOP_TYPE
    FROM stg_ted
    WHERE TOP_TYPE IS NOT NULL
      AND error_info IS NULL
) s
ON d.procedure_code = s.TOP_TYPE
WHEN NOT MATCHED THEN INSERT (
    procedure_code,
    procedure_name,
    transparency_level,
    is_open
) VALUES (
    s.TOP_TYPE,
    CASE s.TOP_TYPE
        WHEN 'OPE' THEN 'Open Procedure'
        WHEN 'RES' THEN 'Restricted Procedure'
        WHEN 'NIC' THEN 'Negotiated without Prior Call'
        WHEN 'AWP' THEN 'Award without Prior Publication'
        WHEN 'CAN' THEN 'Cancelled Procedure'
        WHEN 'OTH' THEN 'Other Procedure'
        WHEN 'MIN' THEN 'Mini Competition'
        WHEN 'VGB' THEN 'Voluntary Ex-Ante Transparency'
        WHEN 'NOC' THEN 'Negotiated with Prior Call'
        WHEN 'PAR' THEN 'Participation Request'
        WHEN 'CON' THEN 'Concession Award'
        WHEN 'SOC' THEN 'Social Services'
        WHEN 'OUT' THEN 'Outsourced'
        ELSE s.TOP_TYPE
    END,
    CASE s.TOP_TYPE
        WHEN 'OPE' THEN 5
        WHEN 'RES' THEN 4
        WHEN 'MIN' THEN 3
        WHEN 'PAR' THEN 3
        WHEN 'NIC' THEN 2
        WHEN 'NOC' THEN 3
        WHEN 'AWP' THEN 1
        WHEN 'VGB' THEN 2
        WHEN 'CAN' THEN 0
        WHEN 'CON' THEN 2
        WHEN 'OTH' THEN 1
        WHEN 'SOC' THEN 2
        WHEN 'OUT' THEN 1
        ELSE 1
    END,
    CASE WHEN s.TOP_TYPE IN ('OPE', 'RES', 'MIN', 'PAR') THEN TRUE ELSE FALSE END
);

SELECT 'dim_procedure_type' AS dim_table, COUNT(*) AS row_count
FROM dim_procedure_type;


-- ===========================================================================
-- B.2: MERGE dim_cpv ← stg_ted
-- ===========================================================================

MERGE INTO dim_cpv d
USING (
    SELECT DISTINCT
        cpv_code,
        SUBSTR(cpv_code, 1, 2) AS cpv_division,
        SUBSTR(cpv_code, 1, 3) AS cpv_group,
        SUBSTR(cpv_code, 1, 4) AS cpv_class
    FROM stg_ted
    WHERE cpv_code IS NOT NULL
      AND error_info IS NULL
) s
ON d.cpv_code = s.cpv_code
WHEN NOT MATCHED THEN INSERT (
    cpv_code,
    cpv_division,
    cpv_group,
    cpv_class
) VALUES (
    s.cpv_code,
    s.cpv_division,
    s.cpv_group,
    s.cpv_class
);

SELECT 'dim_cpv' AS dim_table, COUNT(*) AS row_count FROM dim_cpv;


-- ===========================================================================
-- B.3: dim_country (SCD Type 2) ← stg_cpi JOIN stg_wgi
--
-- SCD Type 2: Für jedes Land wird pro Jahr mit geänderten Governance-Scores
-- eine neue Zeile angelegt. valid_from_year = Jahr, valid_to_year = 9999.
-- Ältere Versionen erhalten valid_to_year = neues Jahr - 1.
-- ===========================================================================

-- Schritt 1: Neue Versionen einfügen (re-runsicher: prüft nur auf (country_code, valid_from_year))
INSERT INTO dim_country (
    country_code, country_name,
    cpi_score,
    control_of_corruption, government_effectiveness,
    political_stability, rule_of_law,
    regulatory_quality, voice_accountability,
    valid_from_year, valid_to_year
)
SELECT
    lkp.alpha_2 AS country_code,
    lkp.country_name,
    cpi.cpi_score,
    wgi.control_of_corruption,
    wgi.government_effectiveness,
    wgi.political_stability,
    wgi.rule_of_law,
    wgi.regulatory_quality,
    wgi.voice_accountability,
    cpi."YEAR" AS valid_from_year,
    9999 AS valid_to_year
FROM stg_cpi cpi
JOIN stg_wgi wgi
    ON cpi.country_iso3 = wgi.country_iso3
    AND cpi."YEAR" = wgi."YEAR"
CROSS JOIN (
    SELECT 'DEU' AS alpha_3, 'DE' AS alpha_2, 'Germany' AS country_name
    UNION ALL SELECT 'DNK', 'DK', 'Denmark'
    UNION ALL SELECT 'ROU', 'RO', 'Romania'
    UNION ALL SELECT 'HUN', 'HU', 'Hungary'
) lkp
ON cpi.country_iso3 = lkp.alpha_3
WHERE cpi.error_info IS NULL
  AND wgi.error_info IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM dim_country d
    WHERE d.country_code = lkp.alpha_2
      AND d.valid_from_year = cpi."YEAR"
  );

-- Schritt 2: valid_to_year älterer Versionen aktualisieren (SCD Type 2)
-- Exasol-kompatible Syntax: UPDATE mit korrelierter Subquery, kein UPDATE ... FROM.
-- Eine Version wird geschlossen auf das Jahr VOR der nächsthöheren Version.
UPDATE dim_country
SET valid_to_year = (
    SELECT MIN(d_next.valid_from_year) - 1
    FROM dim_country d_next
    WHERE d_next.country_code = dim_country.country_code
      AND d_next.valid_from_year > dim_country.valid_from_year
)
WHERE valid_to_year = 9999
  AND EXISTS (
    SELECT 1 FROM dim_country d_next
    WHERE d_next.country_code = dim_country.country_code
      AND d_next.valid_from_year > dim_country.valid_from_year
  );

COMMIT;

SELECT 'dim_country' AS dim_table, COUNT(*) AS row_count FROM dim_country;

-- Verifikation SCD Type 2: Jedes Land sollte mehrere Versionen haben
SELECT
    country_code,
    country_name,
    valid_from_year,
    valid_to_year,
    cpi_score
FROM dim_country
ORDER BY country_code, valid_from_year;


-- ===========================================================================
-- B.4: INSERT fact_tender ← stg_ted JOIN Dimensionen
--
-- Role-Playing: dim_country wird zweimal gejoint:
--   country_key       = Auftraggeber-Land (ISO_COUNTRY_CODE)
--   winner_country_key = Gewinner-Land    (winner_country)
-- ===========================================================================

INSERT INTO fact_tender (
    award_id,
    id_notice_can,
    id_lot,
    "year",
    crisis_type,
    country_key,
    winner_country_key,
    cpv_key,
    procedure_key,
    award_value_eur,
    value_eur,
    number_offers,
    lots_number,
    number_awards,
    F1, F2, F3, F5, F6, F7,
    comb_single_discrepancy,
    comb_single_non_open,
    comb_no_call_high_value,
    comb_frag_single
)
SELECT
    t.ID_AWARD,
    t.ID_NOTICE_CAN,
    t.ID_LOT,
    t."YEAR",
    CASE
        WHEN t."YEAR" BETWEEN 2014 AND 2019 THEN 'keine Krise'
        WHEN t."YEAR" BETWEEN 2020 AND 2021 THEN 'COVID-19'
        WHEN t."YEAR" BETWEEN 2022 AND 2023 THEN 'Ukraine-Krieg'
        ELSE 'keine Krise'
    END AS crisis_type,
    c_authority.country_key,
    c_winner.country_key,
    cpv.cpv_key,
    proc.procedure_key,
    t.AWARD_VALUE_EURO,
    t.VALUE_EURO,
    t.NUMBER_OFFERS,
    t.LOTS_NUMBER,
    t.NUMBER_AWARDS,
    t.F1, t.F2, t.F3, t.F5, t.F6, t.F7,
    t.comb_single_discrepancy,
    t.comb_single_non_open,
    t.comb_no_call_high_value,
    t.comb_frag_single
FROM stg_ted t
LEFT JOIN dim_country c_authority
    ON t.ISO_COUNTRY_CODE = c_authority.country_code
    AND t."YEAR" BETWEEN c_authority.valid_from_year AND c_authority.valid_to_year
LEFT JOIN dim_country c_winner
    ON t.winner_country = c_winner.country_code
    AND t."YEAR" BETWEEN c_winner.valid_from_year AND c_winner.valid_to_year
LEFT JOIN dim_cpv cpv
    ON t.cpv_code = cpv.cpv_code
LEFT JOIN dim_procedure_type proc
    ON t.TOP_TYPE = proc.procedure_code
WHERE t.error_info IS NULL;

COMMIT;

SELECT 'fact_tender' AS dim_table, COUNT(*) AS row_count FROM fact_tender;


-- ===========================================================================
-- B.5: Verifikation aller Tabellen
-- ===========================================================================

SELECT 'dim_procedure_type' AS table_name, COUNT(*) AS row_count
FROM dim_procedure_type
UNION ALL
SELECT 'dim_cpv', COUNT(*) FROM dim_cpv
UNION ALL
SELECT 'dim_country', COUNT(*) FROM dim_country
UNION ALL
SELECT 'fact_tender', COUNT(*) FROM fact_tender
UNION ALL
SELECT 'stg_ted (error-free)', COUNT(*) FROM stg_ted WHERE error_info IS NULL
UNION ALL
SELECT 'stg_ted (erroneous)', COUNT(*) FROM stg_ted WHERE error_info IS NOT NULL
ORDER BY table_name;

-- Sample Join: fact_tender mit allen Dimensionen (LIMIT 5)
SELECT
    f.award_id,
    f."year",
    f.crisis_type,
    c_auth.country_name AS auftraggeber,
    c_win.country_name AS gewinner,
    p.procedure_name,
    cpv.cpv_code,
    f.award_value_eur,
    f.F1, f.F3
FROM fact_tender f
LEFT JOIN dim_country c_auth  ON f.country_key = c_auth.country_key
LEFT JOIN dim_country c_win   ON f.winner_country_key = c_win.country_key
LEFT JOIN dim_procedure_type p ON f.procedure_key = p.procedure_key
LEFT JOIN dim_cpv cpv         ON f.cpv_key = cpv.cpv_key
LIMIT 5;
