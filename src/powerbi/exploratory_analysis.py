"""
Exploratory Analysis — Red Flags Procurement Governance
Runs analytical queries against Exasol (via ODBC) to verify data plausibility
before building Power BI visualizations.

Prerequisites: Copy .env.template to .env and fill in your Exasol credentials.

Usage:  python src/powerbi/exploratory_analysis.py
"""

import sys
import os
from pathlib import Path
import textwrap

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def _require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        print(f"[FAIL]  Environment variable {key} is not set. Copy .env.template to .env and fill in your credentials.")
        sys.exit(1)
    return value


EXASOL_HOST = _require_env("EXASOL_HOST")
EXASOL_PORT = _require_env("EXASOL_PORT")
EXASOL_USER = _require_env("EXASOL_USER")
EXASOL_PASSWORD = _require_env("EXASOL_PASSWORD")
SCHEMA = _require_env("EXASOL_SCHEMA")

ODBC_CS = f"Driver={{Exasol Driver}};EXAHOST={EXASOL_HOST}:{EXASOL_PORT}/nocertcheck"

print("=" * 72)
print("EXPLORATORY ANALYSIS — Red Flags Procurement Governance")
print("=" * 72)
print()

try:
    import pyodbc
    conn = pyodbc.connect(ODBC_CS, uid=EXASOL_USER, pwd=EXASOL_PASSWORD, timeout=15)
    cur = conn.cursor()
    print(f"[OK]  Connected to Exasol via ODBC ({EXASOL_HOST})")
    print(f"      Schema: {SCHEMA}")
    print()
except Exception as e:
    msg = str(e).split("\n")[0][:150]
    print(f"[FAIL]  Connection error: {msg}")
    print()
    print(f">> Host: {EXASOL_HOST}:{EXASOL_PORT}")
    print(">> Is the Exasol instance reachable? Check VPN or network settings.")
    sys.exit(1)


def run_query(label: str, sql: str) -> list:
    print("-" * 72)
    print(label)
    print("-" * 72)
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    widths = {c: max(len(c), 10) for c in cols}
    for r in rows:
        for i, c in enumerate(cols):
            v = str(r[i]) if r[i] is not None else "NULL"
            widths[c] = max(widths[c], len(v))
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    if not rows:
        print("  (no rows)")
    else:
        for r in rows:
            vals = [str(r[i]).ljust(widths[cols[i]]) if r[i] is not None else "NULL".ljust(widths[cols[i]]) for i in range(len(cols))]
            print(" | ".join(vals))
    print()
    return rows


S = SCHEMA

run_query("Q1: Row counts per table", f"""
    SELECT 'fact_tender'       AS tabelle, COUNT(*) AS zeilen FROM {S}.fact_tender
    UNION ALL
    SELECT 'dim_country',      COUNT(*) FROM {S}.dim_country
    UNION ALL
    SELECT 'dim_cpv',          COUNT(*) FROM {S}.dim_cpv
    UNION ALL
    SELECT 'dim_procedure_type',COUNT(*) FROM {S}.dim_procedure_type
    ORDER BY tabelle
""")

run_query("Q2: Tenders per country + NULL check", f"""
    SELECT
        COALESCE(c.country_name, '*** NULL key ***') AS land,
        COUNT(*)      AS tenders,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_total
    FROM {S}.fact_tender f
    LEFT JOIN {S}.dim_country c ON f.country_key = c.country_key
    GROUP BY c.country_name
    ORDER BY tenders DESC
""")

run_query("Q3: Tenders per year (all countries)", f"""
    SELECT f."year", COUNT(*) AS tenders
    FROM {S}.fact_tender f
    GROUP BY f."year"
    ORDER BY f."year"
""")

run_query("Q4: Overall Red-Flag rates (global, all years)", f"""
    SELECT
        ROUND(100.0 * AVG(CASE WHEN F1 THEN 1 ELSE 0 END), 1) AS "f1_rate_%",
        ROUND(100.0 * AVG(CASE WHEN F2 THEN 1 ELSE 0 END), 1) AS "f2_rate_%",
        ROUND(100.0 * AVG(CASE WHEN F3 THEN 1 ELSE 0 END), 1) AS "f3_rate_%",
        ROUND(100.0 * AVG(CASE WHEN F5 THEN 1 ELSE 0 END), 1) AS "f5_rate_%",
        ROUND(100.0 * AVG(CASE WHEN F6 THEN 1 ELSE 0 END), 1) AS "f6_rate_%",
        ROUND(100.0 * AVG(CASE WHEN F7 THEN 1 ELSE 0 END), 1) AS "f7_rate_%",
        ROUND(100.0 * AVG(CASE WHEN F1 OR F2 OR F3 OR F5 OR F6 OR F7 THEN 1 ELSE 0 END), 1) AS "overall_%"
    FROM {S}.fact_tender
""")

run_query("Q5 ** Red-Flag rates per country (F1, F3, F6, Overall)", f"""
    SELECT
        c.country_name AS land,
        COUNT(*) AS tenders,
        ROUND(100.0 * AVG(CASE WHEN f.F1 THEN 1 ELSE 0 END), 1) AS "f1_%",
        ROUND(100.0 * AVG(CASE WHEN f.F3 THEN 1 ELSE 0 END), 1) AS "f3_%",
        ROUND(100.0 * AVG(CASE WHEN f.F6 THEN 1 ELSE 0 END), 1) AS "f6_%",
        ROUND(100.0 * AVG(CASE WHEN f.F1 OR f.F2 OR f.F3 OR f.F5 OR f.F6 OR f.F7 THEN 1 ELSE 0 END), 1) AS "overall_%"
    FROM {S}.fact_tender f
    JOIN {S}.dim_country c ON f.country_key = c.country_key
    GROUP BY c.country_name
    ORDER BY "overall_%" DESC
""")

run_query("Q6 ** Governance scores per country (CPI + WGI)", f"""
    SELECT
        country_name AS land,
        cpi_score AS cpi,
        control_of_corruption AS "corrupt_control",
        government_effectiveness AS "gov_eff",
        rule_of_law,
        political_stability AS "pol_stab",
        valid_from_year,
        valid_to_year
    FROM {S}.dim_country
    WHERE valid_to_year >= 2023
    ORDER BY cpi_score DESC
""")

run_query("Q7 ** CPI vs F1-Rate per country x year (correlation check)", f"""
    SELECT
        c.country_name AS land,
        f."year",
        ROUND(AVG(c.cpi_score), 1) AS cpi,
        ROUND(100.0 * AVG(CASE WHEN f.F1 THEN 1 ELSE 0 END), 1) AS "f1_rate_%",
        ROUND(100.0 * AVG(CASE WHEN f.F6 THEN 1 ELSE 0 END), 1) AS "f6_rate_%"
    FROM {S}.fact_tender f
    JOIN {S}.dim_country c ON f.country_key = c.country_key
    GROUP BY c.country_name, f."year"
    ORDER BY c.country_name, f."year"
""")

run_query("Q8 ** Crisis impact: F6-Rate per country x crisis_type", f"""
    SELECT
        c.country_name AS land,
        f.crisis_type AS krisenphase,
        COUNT(*) AS tenders,
        ROUND(100.0 * AVG(CASE WHEN f.F6 THEN 1 ELSE 0 END), 1) AS "f6_rate_%",
        ROUND(100.0 * AVG(CASE WHEN f.F1 OR f.F2 OR f.F3 OR f.F5 OR f.F6 OR f.F7 THEN 1 ELSE 0 END), 1) AS "overall_%"
    FROM {S}.fact_tender f
    JOIN {S}.dim_country c ON f.country_key = c.country_key
    GROUP BY c.country_name, f.crisis_type
    ORDER BY c.country_name, f.crisis_type
""")

run_query("Q9 ** Top 10 CPV divisions by tender volume", f"""
    SELECT
        d.cpv_division AS cpv_div,
        COUNT(*) AS tenders,
        ROUND(SUM(f.award_value_eur) / 1e9, 2) AS "wert_MrdEUR",
        ROUND(100.0 * AVG(CASE WHEN f.F1 OR f.F2 OR f.F3 OR f.F5 OR f.F6 OR f.F7 THEN 1 ELSE 0 END), 1) AS "overall_risiko_%",
        ROUND(100.0 * AVG(CASE WHEN f.F2 THEN 1 ELSE 0 END), 1) AS "f2_%"
    FROM {S}.fact_tender f
    JOIN {S}.dim_cpv d ON f.cpv_key = d.cpv_key
    GROUP BY d.cpv_division
    ORDER BY tenders DESC
    LIMIT 10
""")

run_query("Q10: Procedure type distribution", f"""
    SELECT
        p.procedure_name AS verfahrensart,
        COUNT(*) AS tenders,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_total,
        ROUND(100.0 * AVG(CASE WHEN f.F1 THEN 1 ELSE 0 END), 1) AS "f1_rate_%"
    FROM {S}.fact_tender f
    JOIN {S}.dim_procedure_type p ON f.procedure_key = p.procedure_key
    GROUP BY p.procedure_name
    ORDER BY tenders DESC
""")

run_query("Q11: Award value distribution (EUR)", f"""
    SELECT
        MIN(award_value_eur)       AS "min_EUR",
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY award_value_eur), 0) AS "q25",
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY award_value_eur), 0) AS "median",
        ROUND(AVG(award_value_eur), 0) AS "avg",
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY award_value_eur), 0) AS "q95",
        MAX(award_value_eur)       AS "max_EUR",
        COUNT(*) AS n
    FROM {S}.fact_tender
    WHERE award_value_eur IS NOT NULL
""")

run_query("Q12: Number of offers distribution", f"""
    SELECT
        number_offers,
        COUNT(*) AS tenders,
        ROUND(100.0 * AVG(CASE WHEN F1 THEN 1 ELSE 0 END), 1) AS "f1_rate_%"
    FROM {S}.fact_tender
    WHERE number_offers IS NOT NULL
    GROUP BY number_offers
    ORDER BY number_offers
""")

run_query("Q13: Tenders by winner country (cross-border check)", f"""
    SELECT
        w.country_name AS gewinner_land,
        COUNT(*) AS tenders,
        ROUND(100.0 * AVG(CASE WHEN f.F1 THEN 1 ELSE 0 END), 1) AS "f1_rate_%"
    FROM {S}.fact_tender f
    JOIN {S}.dim_country w ON f.winner_country_key = w.country_key
    GROUP BY w.country_name
    ORDER BY tenders DESC
""")

run_query("Q14: NULL rates on key columns", f"""
    SELECT
        'country_key'       AS spalte, ROUND(100.0 * COUNT(*) / MAX((SELECT COUNT(*) FROM {S}.fact_tender)), 1) AS pct_null FROM {S}.fact_tender WHERE country_key IS NULL
    UNION ALL
    SELECT 'winner_country_key',ROUND(100.0 * COUNT(*) / MAX((SELECT COUNT(*) FROM {S}.fact_tender)), 1) FROM {S}.fact_tender WHERE winner_country_key IS NULL
    UNION ALL
    SELECT 'cpv_key',          ROUND(100.0 * COUNT(*) / MAX((SELECT COUNT(*) FROM {S}.fact_tender)), 1) FROM {S}.fact_tender WHERE cpv_key IS NULL
    UNION ALL
    SELECT 'procedure_key',    ROUND(100.0 * COUNT(*) / MAX((SELECT COUNT(*) FROM {S}.fact_tender)), 1) FROM {S}.fact_tender WHERE procedure_key IS NULL
    UNION ALL
    SELECT 'award_value_eur',  ROUND(100.0 * COUNT(*) / MAX((SELECT COUNT(*) FROM {S}.fact_tender)), 1) FROM {S}.fact_tender WHERE award_value_eur IS NULL
    UNION ALL
    SELECT 'number_offers',    ROUND(100.0 * COUNT(*) / MAX((SELECT COUNT(*) FROM {S}.fact_tender)), 1) FROM {S}.fact_tender WHERE number_offers IS NULL
    ORDER BY pct_null DESC
""")


print("=" * 72)
print("ANALYSIS COMPLETE")
print("=" * 72)
print()

print("Key interpretation guide:")
print()
print("  Q5 (Red-Flag rates per country):")
print("    >> Do DE/DK have lower F1/F3/F6 rates than RO/HU?")
print("    >> Is the spread wide enough for a meaningful comparison?")
print()
print("  Q6 (Governance scores):")
print("    >> Do CPI scores vary meaningfully between countries?")
print("    >> DK should be ~88, DE ~79, HU ~42, RO ~46 (approx)")
print()
print("  Q7 (CPI vs F1 per year):")
print("    >> Does F1 Rate go UP when CPI goes DOWN? (negative correlation)")
print("    >> Any surprising years or outliers?")
print()
print("  Q8 (Crisis impact):")
print("    >> Does F6 rate spike during COVID (2020-21) and Ukraine (2022-23)?")
print("    >> Is the effect stronger in RO/HU than DE/DK?")
print()
print("  Q9 (Top CPV):")
print("    >> Which product categories dominate by value & risk?")
print("    >> Are there >10 divisions to make a meaningful treemap?")
print()

conn.close()
print("[DONE]")
