-- IMPORTANT: Set your schema in DBeaver before running. The default schema is 'procurement_governance'.

--
-- analytical_queries.sql
-- Seven Analytical Queries
--
-- Run AFTER merge_dimensions.sql

-- ===========================================================================
-- Q1: GROUPING SETS / ROLLUP
-- Red-Flag-Raten pro Land und Jahr mit ROLLUP
-- (Subtotals pro Land, Grand Total über alle Länder und Jahre)
-- ===========================================================================

-- Q1: ROLLUP über Land und Jahr — Single-Bidder-Rate (F1) und
-- Estimate/Award-Discrepancy-Rate (F2) mit aggregierten Subtotal-Ebenen
SELECT
    c.country_name,
    f."year",
    COUNT(*) AS tender_count,
    ROUND(100.0 * SUM(CAST(f.F1 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f1_single_bidder_pct,
    ROUND(100.0 * SUM(CAST(f.F2 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f2_discrepancy_pct,
    ROUND(100.0 * SUM(CAST(f.F3 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f3_no_prior_call_pct,
    GROUPING(c.country_name) AS grp_country,
    GROUPING(f."year")         AS grp_year
FROM fact_tender f
JOIN dim_country c ON f.country_key = c.country_key
GROUP BY ROLLUP(c.country_name, f."year")
ORDER BY
    GROUPING(c.country_name), c.country_name,
    GROUPING(f."year"), f."year";


-- ===========================================================================
-- Q2: Window Function (non-ranking)
-- Gleitender 3-Jahres-Durchschnitt der Single-Bidder-Rate pro Land
-- ===========================================================================

-- Q2: Window Function — 3-year moving average via AVG OVER (PARTITION BY ... ROWS)
-- Zeigt Trend der Single-Bidder-Rate, geglättet über 3 Jahre
WITH yearly_stats AS (
    SELECT
        f.country_key,
        f."year",
        COUNT(*) AS tender_count,
        SUM(CAST(f.F1 AS INT)) AS f1_flagged,
        ROUND(100.0 * SUM(CAST(f.F1 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f1_pct
    FROM fact_tender f
    WHERE f.F1 IS NOT NULL
    GROUP BY f.country_key, f."year"
)
SELECT
    c.country_name,
    y."year",
    y.tender_count,
    y.f1_pct AS single_bidder_pct,
    ROUND(AVG(y.f1_pct) OVER (
        PARTITION BY c.country_name
        ORDER BY y."year"
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS f1_pct_3yr_moving_avg
FROM yearly_stats y
JOIN dim_country c ON y.country_key = c.country_key
ORDER BY c.country_name, y."year";


-- ===========================================================================
-- Q3: Ranking Function
-- Top-15 CPV-Divisionen mit der höchsten Estimate/Award-Discrepancy-Rate (F2)
-- ===========================================================================

-- Q3: Ranking — Top 15 CPV divisions by F2 discrepancy rate
-- RANK() vergeben; CPV-Divisionen mit weniger als 50 Tenders werden ausgeschlossen
WITH cpv_f2_stats AS (
    SELECT
        cpv.cpv_division,
        COUNT(*) AS tender_count,
        SUM(CAST(f.F2 AS INT)) AS f2_flagged,
        ROUND(100.0 * SUM(CAST(f.F2 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f2_pct
    FROM fact_tender f
    JOIN dim_cpv cpv ON f.cpv_key = cpv.cpv_key
    WHERE f.F2 IS NOT NULL
    GROUP BY cpv.cpv_division
    HAVING COUNT(*) >= 50
)
SELECT
    RANK() OVER (ORDER BY f2_pct DESC) AS rank,
    cpv_division,
    tender_count,
    f2_flagged,
    f2_pct
FROM cpv_f2_stats
ORDER BY rank
LIMIT 15;


-- ===========================================================================
-- Q4: Statistical Function
-- Korrelation zwischen CPI-Score und Single-Bidder-Rate pro Land-Jahr
-- ===========================================================================

-- Q4: Statistical — CORR, STDDEV_POP zwischen CPI und F1-Rate
-- Untersucht: Hängt wahrgenommene Korruption mit der Single-Bidder-Quote zusammen?
WITH yearly_country AS (
    SELECT
        c.country_code,
        f."year",
        c.cpi_score,
        COUNT(*) AS tender_count,
        SUM(CAST(f.F1 AS INT)) AS f1_flagged,
        ROUND(100.0 * SUM(CAST(f.F1 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f1_pct
    FROM fact_tender f
    JOIN dim_country c ON f.country_key = c.country_key
        AND f."year" BETWEEN c.valid_from_year AND c.valid_to_year
    WHERE f.F1 IS NOT NULL
      AND c.cpi_score IS NOT NULL
    GROUP BY c.country_code, f."year", c.cpi_score
)
SELECT
    COUNT(*) AS data_points,
    ROUND(AVG(f1_pct), 2) AS avg_f1_pct,
    ROUND(STDDEV_POP(f1_pct), 2) AS stddev_f1_pct,
    ROUND(AVG(cpi_score), 2) AS avg_cpi_score,
    ROUND(STDDEV_POP(cpi_score), 2) AS stddev_cpi,
    ROUND(CORR(cpi_score, f1_pct), 4) AS correlation_cpi_vs_f1
FROM yearly_country;


-- ===========================================================================
-- Q5: Skyline Query
-- Länder-Skyline: Bevorzugt hohen CPI UND niedrige F3-No-Prior-Call-Rate
-- ===========================================================================

-- Q5: Skyline — Länder die in keiner Dimension von einem anderen Land dominiert werden
-- PREFERRING HIGH avg_cpi PLUS LOW f3_rate
WITH country_stats AS (
    SELECT
        c.country_name,
        ROUND(AVG(c.cpi_score), 2) AS avg_cpi,
        ROUND(100.0 * SUM(CAST(f.F3 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f3_rate,
        COUNT(*) AS tender_count
    FROM fact_tender f
    JOIN dim_country c ON f.country_key = c.country_key
        AND f."year" BETWEEN c.valid_from_year AND c.valid_to_year
    WHERE f.F3 IS NOT NULL
    GROUP BY c.country_name
)
SELECT *
FROM country_stats
PREFERRING HIGH avg_cpi PLUS LOW f3_rate;


-- ===========================================================================
-- Q6: Freie Abfrage — Krisenvergleich
-- F6 High-Value-Single-Bidder-Rate nach Krisentyp und Land
-- ===========================================================================

-- Q6: Vergleich der High-Value-Single-Bidder-Rate (F6) nach Krisentyp
-- Zeigt, wie sich COVID-19 und Ukraine-Krieg auf hochpreisige Einzelbieter-Vergaben auswirken
SELECT
    f.crisis_type,
    c.country_name,
    COUNT(*) AS tender_count,
    SUM(CAST(f.F6 AS INT)) AS f6_flagged,
    ROUND(100.0 * SUM(CAST(f.F6 AS INT)) / NULLIF(COUNT(*), 0), 4) AS f6_pct,
    ROUND(AVG(f.award_value_eur), 0) AS avg_award_eur
FROM fact_tender f
JOIN dim_country c ON f.country_key = c.country_key
WHERE f.F6 IS NOT NULL
GROUP BY f.crisis_type, c.country_name
ORDER BY f.crisis_type, c.country_name;


-- ===========================================================================
-- Q7: Freie Abfrage — Lot-Fragmentierung nach Verfahrenstyp
-- F7 Lot-Fragmentierungsrate pro Verfahrenstyp und Land
-- ===========================================================================

-- Q7: Lot-Fragmentierungsrate (F7) nach Verfahrenstyp, gruppiert nach Land
-- Untersucht: Korreliert die Fragmentierungsrate mit der Transparenz des Verfahrens?
SELECT
    p.procedure_name,
    p.transparency_level,
    c.country_name,
    COUNT(*) AS tender_count,
    SUM(CAST(f.F7 AS INT)) AS f7_flagged,
    ROUND(100.0 * SUM(CAST(f.F7 AS INT)) / NULLIF(COUNT(*), 0), 2) AS f7_pct
FROM fact_tender f
JOIN dim_procedure_type p ON f.procedure_key = p.procedure_key
JOIN dim_country c       ON f.country_key = c.country_key
WHERE f.F7 IS NOT NULL
GROUP BY p.procedure_name, p.transparency_level, c.country_name
ORDER BY c.country_name, f7_pct DESC;
