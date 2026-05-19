-- ============================================================================
-- Exercise 1 (Data Modelling) — Example INSERT Statements
-- Target: Exasol
-- Author: Johannes, OTH Regensburg
-- ============================================================================
-- Two example rows per table. Fact rows reference dimension keys inserted
-- above them. All flag values are semantically consistent.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Dimension: dim_country
-- ----------------------------------------------------------------------------

-- Row 1: Germany (2014–2019) — high governance scores
-- CPI = 80 (low corruption), WGI values all strongly positive
INSERT INTO dim_country (country_code, country_name, cpi_score,
    control_of_corruption, government_effectiveness, political_stability,
    rule_of_law, regulatory_quality, voice_accountability,
    valid_from_year, valid_to_year)
VALUES ('DE', 'Germany', 80,
    1.85, 1.72, 0.95, 1.63, 1.58, 1.42,
    2014, 2019);

-- Row 2: Romania (2014–2019) — lower governance scores
-- CPI = 44 (moderate corruption), WGI values mixed/negative
INSERT INTO dim_country (country_code, country_name, cpi_score,
    control_of_corruption, government_effectiveness, political_stability,
    rule_of_law, regulatory_quality, voice_accountability,
    valid_from_year, valid_to_year)
VALUES ('RO', 'Romania', 44,
    0.05, 0.12, 0.45, 0.38, 0.62, 0.40,
    2014, 2019);


-- ----------------------------------------------------------------------------
-- Dimension: dim_cpv
-- ----------------------------------------------------------------------------

-- Row 1: Agricultural, farming & related products
INSERT INTO dim_cpv (cpv_code, cpv_division, cpv_group, cpv_class)
VALUES ('03110000', '03', '031', '0311');

-- Row 2: Building construction work
INSERT INTO dim_cpv (cpv_code, cpv_division, cpv_group, cpv_class)
VALUES ('45210000', '45', '452', '4521');


-- ----------------------------------------------------------------------------
-- Dimension: dim_procedure_type
-- ----------------------------------------------------------------------------

-- Row 1: Open Procedure — most transparent, fully competitive
INSERT INTO dim_procedure_type (procedure_code, procedure_name, transparency_level, is_open)
VALUES ('OPE', 'Open Procedure', 5, TRUE);

-- Row 2: Negotiated without Prior Call — low transparency, non-competitive
INSERT INTO dim_procedure_type (procedure_code, procedure_name, transparency_level, is_open)
VALUES ('NIC', 'Negotiated without Prior Call', 2, FALSE);


-- ----------------------------------------------------------------------------
-- Fact Table: fact_tender
-- ----------------------------------------------------------------------------

-- Row 1: Open, competitive procedure — no suspicion whatsoever
-- Case: Germany 2019, 3 bidders, award_value = €500K, all flags FALSE
-- Procedure: OPE (key=1)
INSERT INTO fact_tender (
    award_id, id_notice_can, id_lot,
    year, crisis_type,
    country_key, winner_country_key, cpv_key, procedure_key,
    award_value_eur, value_eur, number_offers, lots_number, number_awards,
    F1, F2, F3, F5, F6, F7,
    comb_single_discrepancy, comb_single_non_open,
    comb_no_call_high_value, comb_frag_single
) VALUES (
    'AWARD-DE-2019-001', 'NOTICE-DE-2019-001', 'LOT-001',
    2019, 'keine Krise',
    1,    -- country_key = DE (2014–2019 row) — Auftraggeber
    1,    -- winner_country_key = DE — deutsches Unternehmen gewinnt (Role-Playing)
    1,    -- cpv_key = 03110000 (Agricultural products)
    1,    -- procedure_key = OPE (Open Procedure)
    500000.00, 450000.00, 3, 1, 1,
    FALSE, FALSE, FALSE, FALSE, FALSE, FALSE,
    FALSE, FALSE, FALSE, FALSE
);

-- Row 2: Direct award without prior call, single-bidder, high value
-- Case: Romania 2020 (COVID crisis), 1 bidder, award_value = €5M
-- F1=TRUE (single-bidder), F3=TRUE (NIC), F6=TRUE (single-bidder + above p95)
-- comb_single_non_open=TRUE, comb_no_call_high_value=TRUE
-- Procedure: NIC (key=2)
INSERT INTO fact_tender (
    award_id, id_notice_can, id_lot,
    year, crisis_type,
    country_key, winner_country_key, cpv_key, procedure_key,
    award_value_eur, value_eur, number_offers, lots_number, number_awards,
    F1, F2, F3, F5, F6, F7,
    comb_single_discrepancy, comb_single_non_open,
    comb_no_call_high_value, comb_frag_single
) VALUES (
    'AWARD-RO-2020-099', 'NOTICE-RO-2020-099', NULL,
    2020, 'COVID-19',
    2,    -- country_key = RO (Romania, 2014–2019 row) — Auftraggeber
    1,    -- winner_country_key = DE — deutsches Unternehmen gewinnt (Role-Playing)
    2,    -- cpv_key = 45210000 (Building construction work)
    2,    -- procedure_key = NIC (Negotiated without Prior Call)
    5000000.00, 6000000.00, 1, 1, 1,
    TRUE, FALSE, TRUE, FALSE, TRUE, FALSE,
    FALSE, TRUE, TRUE, FALSE
);
