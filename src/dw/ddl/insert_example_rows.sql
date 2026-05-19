
INSERT INTO dim_country (country_code, country_name, cpi_score,
    control_of_corruption, government_effectiveness, political_stability,
    rule_of_law, regulatory_quality, voice_accountability,
    valid_from_year, valid_to_year)
VALUES ('DE', 'Germany', 80,
    1.85, 1.72, 0.95, 1.63, 1.58, 1.42,
    2014, 2019);

INSERT INTO dim_country (country_code, country_name, cpi_score,
    control_of_corruption, government_effectiveness, political_stability,
    rule_of_law, regulatory_quality, voice_accountability,
    valid_from_year, valid_to_year)
VALUES ('RO', 'Romania', 44,
    0.05, 0.12, 0.45, 0.38, 0.62, 0.40,
    2014, 2019);


INSERT INTO dim_cpv (cpv_code, cpv_division, cpv_group, cpv_class)
VALUES ('03110000', '03', '031', '0311');

INSERT INTO dim_cpv (cpv_code, cpv_division, cpv_group, cpv_class)
VALUES ('45210000', '45', '452', '4521');


INSERT INTO dim_procedure_type (procedure_code, procedure_name, transparency_level, is_open)
VALUES ('OPE', 'Open Procedure', 5, TRUE);

INSERT INTO dim_procedure_type (procedure_code, procedure_name, transparency_level, is_open)
VALUES ('NIC', 'Negotiated without Prior Call', 2, FALSE);


INSERT INTO fact_tender (
    award_id, id_notice_can, id_lot,
    "year", crisis_type,
    country_key, winner_country_key, cpv_key, procedure_key,
    award_value_eur, value_eur, number_offers, lots_number, number_awards,
    F1, F2, F3, F5, F6, F7,
    comb_single_discrepancy, comb_single_non_open,
    comb_no_call_high_value, comb_frag_single
) VALUES (
    'AWARD-DE-2019-001', 'NOTICE-DE-2019-001', 'LOT-001',
    2019, 'keine Krise',
    1,
    1,
    1,
    1,
    500000.00, 450000.00, 3, 1, 1,
    FALSE, FALSE, FALSE, FALSE, FALSE, FALSE,
    FALSE, FALSE, FALSE, FALSE
);

INSERT INTO fact_tender (
    award_id, id_notice_can, id_lot,
    "year", crisis_type,
    country_key, winner_country_key, cpv_key, procedure_key,
    award_value_eur, value_eur, number_offers, lots_number, number_awards,
    F1, F2, F3, F5, F6, F7,
    comb_single_discrepancy, comb_single_non_open,
    comb_no_call_high_value, comb_frag_single
) VALUES (
    'AWARD-RO-2020-099', 'NOTICE-RO-2020-099', NULL,
    2020, 'COVID-19',
    2,
    1,
    2,
    2,
    5000000.00, 6000000.00, 1, 1, 1,
    TRUE, FALSE, TRUE, FALSE, TRUE, FALSE,
    FALSE, TRUE, TRUE, FALSE
);
