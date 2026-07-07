-- IMPORTANT: Set your schema in DBeaver before running. The default schema is 'procurement_governance'.

DELETE FROM fact_tender;
DELETE FROM dim_procedure_type;
DELETE FROM dim_cpv;
DELETE FROM dim_country;

INSERT INTO dim_procedure_type (procedure_code, procedure_name, transparency_level, is_open)
SELECT DISTINCT TOP_TYPE,
    CASE TOP_TYPE
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
        ELSE TOP_TYPE
    END,
    CASE TOP_TYPE
        WHEN 'OPE' THEN 5 WHEN 'RES' THEN 4 WHEN 'MIN' THEN 3 WHEN 'PAR' THEN 3
        WHEN 'NIC' THEN 2 WHEN 'NOC' THEN 3 WHEN 'AWP' THEN 1 WHEN 'VGB' THEN 2
        WHEN 'CAN' THEN 0 WHEN 'CON' THEN 2 WHEN 'OTH' THEN 1 WHEN 'SOC' THEN 2
        WHEN 'OUT' THEN 1 ELSE 1
    END,
    CASE WHEN TOP_TYPE IN ('OPE', 'RES', 'MIN', 'PAR') THEN TRUE ELSE FALSE END
FROM stg_ted
WHERE TOP_TYPE IS NOT NULL AND error_info IS NULL
  AND NOT EXISTS (SELECT 1 FROM dim_procedure_type d WHERE d.procedure_code = stg_ted.TOP_TYPE);

INSERT INTO dim_cpv (cpv_code, cpv_division, cpv_group, cpv_class)
SELECT DISTINCT cpv_code,
    SUBSTR(cpv_code, 1, 2),
    SUBSTR(cpv_code, 1, 3),
    SUBSTR(cpv_code, 1, 4)
FROM stg_ted
WHERE cpv_code IS NOT NULL
  AND error_info IS NULL
  AND NOT EXISTS (SELECT 1 FROM dim_cpv d WHERE d.cpv_code = stg_ted.cpv_code);

INSERT INTO dim_country (country_code, country_name, cpi_score, control_of_corruption, government_effectiveness, political_stability, rule_of_law, regulatory_quality, voice_accountability, valid_from_year, valid_to_year)
SELECT
    lkp.alpha_2, lkp.country_name,
    cpi.cpi_score,
    wgi.control_of_corruption, wgi.government_effectiveness,
    wgi.political_stability, wgi.rule_of_law,
    wgi.regulatory_quality, wgi.voice_accountability,
    cpi."YEAR",
    COALESCE(LEAD(cpi."YEAR") OVER (PARTITION BY lkp.alpha_2 ORDER BY cpi."YEAR") - 1, 9999)
FROM stg_cpi cpi
JOIN stg_wgi wgi ON cpi.country_iso3 = wgi.country_iso3 AND cpi."YEAR" = wgi."YEAR"
INNER JOIN (
    SELECT 'DEU' AS alpha_3, 'DE' AS alpha_2, 'Germany' AS country_name
    UNION ALL SELECT 'DNK', 'DK', 'Denmark'
    UNION ALL SELECT 'ROU', 'RO', 'Romania'
    UNION ALL SELECT 'HUN', 'HU', 'Hungary'
) lkp ON cpi.country_iso3 = lkp.alpha_3
WHERE cpi.error_info IS NULL AND wgi.error_info IS NULL
  AND NOT EXISTS (SELECT 1 FROM dim_country d WHERE d.country_code = lkp.alpha_2 AND d.valid_from_year = cpi."YEAR");

INSERT INTO fact_tender (award_id, id_notice_can, id_lot, "year", crisis_type, country_key, winner_country_key, cpv_key, procedure_key, award_value_eur, value_eur, number_offers, lots_number, number_awards, F1, F2, F3, F5, F6, F7, comb_single_discrepancy, comb_single_non_open, comb_no_call_high_value, comb_frag_single)
SELECT
    t.ID_AWARD, t.ID_NOTICE_CAN, t.ID_LOT, t."YEAR",
    CASE
        WHEN t."YEAR" BETWEEN 2014 AND 2019 THEN 'keine Krise'
        WHEN t."YEAR" BETWEEN 2020 AND 2021 THEN 'COVID-19'
        WHEN t."YEAR" BETWEEN 2022 AND 2023 THEN 'Ukraine-Krieg'
        ELSE 'keine Krise'
    END,
    c_authority.country_key, c_winner.country_key,
    cpv.cpv_key, proc.procedure_key,
    t.AWARD_VALUE_EURO, t.VALUE_EURO,
    t.NUMBER_OFFERS, t.LOTS_NUMBER, t.NUMBER_AWARDS,
    t.F1, t.F2, t.F3, t.F5, t.F6, t.F7,
    t.comb_single_discrepancy, t.comb_single_non_open,
    t.comb_no_call_high_value, t.comb_frag_single
FROM stg_ted t
LEFT JOIN dim_country c_authority ON t.ISO_COUNTRY_CODE = c_authority.country_code AND t."YEAR" BETWEEN c_authority.valid_from_year AND c_authority.valid_to_year
LEFT JOIN dim_country c_winner ON t.winner_country = c_winner.country_code AND t."YEAR" BETWEEN c_winner.valid_from_year AND c_winner.valid_to_year
LEFT JOIN dim_cpv cpv ON t.cpv_code = cpv.cpv_code
LEFT JOIN dim_procedure_type proc ON t.TOP_TYPE = proc.procedure_code
WHERE t.error_info IS NULL AND t.ID_AWARD IS NOT NULL;

SELECT 'dim_procedure_type' AS tbl, COUNT(*) AS cnt FROM dim_procedure_type
UNION ALL SELECT 'dim_cpv', COUNT(*) FROM dim_cpv
UNION ALL SELECT 'dim_country', COUNT(*) FROM dim_country
UNION ALL SELECT 'fact_tender', COUNT(*) FROM fact_tender;

SELECT country_code, valid_from_year, valid_to_year, cpi_score
FROM dim_country
ORDER BY country_code, valid_from_year;
