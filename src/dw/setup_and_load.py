"""
setup_and_load.py — Complete Exasol setup and data load.

One script to rule them all:
    1. Connect to Exasol (credentials from .env)
    2. Create all tables (staging + star schema)
    3. Load cleaned parquet files (CPI, WGI, TED)
    4. Insert example rows (2 per table)
    5. Verify row counts and show sample join
    6. Print final summary

Usage:
    python src/dw/setup_and_load.py                # Full pipeline
    python src/dw/setup_and_load.py --ddl-only     # Only DDL
    python src/dw/setup_and_load.py --load-only    # Only data load
    python src/dw/setup_and_load.py --verify       # Only verification
"""

import argparse
import os
import ssl
import sys
import time
import pandas as pd
import pyexasol
from pathlib import Path

from src.log.logger import setup_logger
logger = setup_logger(
    name=__name__,
    log_dir="logs",
    log_file="setup_and_load.log",
    console_level=20,
    file_level=10,
)


# ============================================================================
# Connection
# ============================================================================

def find_project_root():
    """Search upward for the project root (where .env resides)."""
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".env").exists() or (parent / ".env.template").exists():
            return parent
        if parent.parent == parent:
            break
    return path.parents[2]


def load_env():
    """Load .env file into os.environ."""
    project_root = find_project_root()
    env_path = project_root / ".env"
    if not env_path.exists():
        logger.warning(".env not found at %s — create it from .env.template", env_path)
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()
    logger.info("Loaded .env from %s", env_path)


def get_connection(schema=None):
    """Connect to Exasol using .env or environment variables."""
    host_raw = os.environ["EXASOL_HOST"].strip()
    port = int(os.environ.get("EXASOL_PORT", "8563"))
    user = os.environ["EXASOL_USER"]
    password = os.environ["EXASOL_PASSWORD"]
    schema = schema or os.environ.get("EXASOL_SCHEMA", "procurement_governance")

    # Strip DBeaver-style /nocertcheck suffix — handled via sslopt
    host = host_raw.split("/")[0].strip()

    logger.info("Connecting to %s:%s (schema: %s) — using websocket_sslopt for self-signed certs",
                host, port, schema)

    conn = pyexasol.connect(
        dsn=f"{host}:{port}",
        user=user,
        password=password,
        compression=True,
        encryption=True,
        websocket_sslopt={"cert_reqs": ssl.CERT_NONE},
    )
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    conn.execute(f"OPEN SCHEMA {schema}")
    return conn, schema


# ============================================================================
# SQL file execution — robust version without sqlparse dependency
# ============================================================================

def execute_sql_file(conn, filepath):
    """Execute a .sql file, statement by statement.

    Splits on ';'. Auto-drops tables before CREATE TABLE to handle re-runs.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error("SQL file not found: %s", filepath)
        return False

    raw_sql = filepath.read_text(encoding="utf-8")

    # Remove all single-line comments first
    lines = [l for l in raw_sql.split("\n") if not l.strip().startswith("--")]
    raw_sql = "\n".join(lines)

    raw_statements = raw_sql.split(";")

    executed = 0
    for i, raw_stmt in enumerate(raw_statements, 1):
        stmt = raw_stmt.strip()
        if not stmt:
            continue

        if stmt.upper().startswith("CREATE TABLE"):
            parts = stmt.split()
            if len(parts) >= 3:
                table_name = parts[2].strip('"')
                try:
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                except Exception as drop_err:
                    logger.warning("Could not drop %s: %s", table_name, drop_err)

        try:
            conn.execute(stmt)
            executed += 1
            logger.debug("Statement %d executed (%.60s...)", i, stmt[:60])
        except Exception as e:
            logger.error("Statement %d failed: %s", i, e)
            logger.error("SQL: %.200s", stmt)
            conn.rollback()
            return False

    conn.commit()
    logger.info("Executed %d SQL statements from %s", executed, filepath.name)
    return True


# ============================================================================
# Phase 1: DDL
# ============================================================================

def _drop_all_tables_fk_safe(conn):
    """Drop all 7 tables in reverse FK dependency order.

    Facts before dims so FK constraints don't block DROP.
    """
    drop_order = [
        "fact_tender",           # references dim_country, dim_cpv, dim_procedure_type
        "dim_procedure_type",    # referenced by fact_tender
        "dim_cpv",               # referenced by fact_tender
        "dim_country",           # referenced by fact_tender (twice, role-playing)
        "stg_ted",               # no FKs on staging tables
        "stg_cpi",
        "stg_wgi",
    ]
    logger.info("Dropping existing tables in FK-safe order...")
    for name in drop_order:
        try:
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        except pyexasol.ExaQueryError as e:
            logger.warning("Could not drop %s: %s", name, e)
    conn.commit()


def ddl_create_all(conn, schema):
    """Create schema (if needed) and all tables."""
    ddl_dir = Path(__file__).resolve().parent / "ddl"

    logger.info("=" * 60)
    logger.info("PHASE 1: Creating tables in schema '%s'", schema)
    logger.info("=" * 60)

    # Open existing schema or create + open
    try:
        conn.execute(f"OPEN SCHEMA {schema}")
        logger.info("Schema '%s' opened", schema)
    except Exception:
        conn.execute(f"CREATE SCHEMA {schema}")
        conn.execute(f"OPEN SCHEMA {schema}")
        logger.info("Schema '%s' created and opened", schema)

    # Drop all tables in reverse FK order before re-creating
    _drop_all_tables_fk_safe(conn)

    # Staging tables
    staging_file = ddl_dir / "create_staging_tables.sql"
    logger.info("Executing %s...", staging_file.name)
    if not execute_sql_file(conn, staging_file):
        logger.error("Staging DDL failed")
        return False

    # Star schema tables
    star_file = ddl_dir / "create_star_schema.sql"
    logger.info("Executing %s...", star_file.name)
    if not execute_sql_file(conn, star_file):
        logger.error("Star schema DDL failed")
        return False

    # Verify all 7 tables exist
    all_tables = [
        "stg_ted", "stg_cpi", "stg_wgi",
        "dim_country", "dim_cpv", "dim_procedure_type", "fact_tender",
    ]
    missing = []
    for table in all_tables:
        try:
            conn.execute(f"SELECT 1 FROM {table} WHERE 1=0")
            logger.debug("Table %s exists", table)
        except Exception:
            logger.error("Table %s does NOT exist!", table)
            missing.append(table)

    if missing:
        logger.error("%d / %d tables missing: %s", len(missing), len(all_tables), ", ".join(missing))
        return False

    logger.info("All %d tables created and verified", len(all_tables))
    return True


# ============================================================================
# Phase 2: Parquet loading
# ============================================================================

def load_parquet_files(conn):
    """Load cleaned parquet files into staging tables via put_dataframe."""
    base = Path("data/processed")
    tables = [
        ("stg_cpi", base / "cpi" / "cpi_clean.parquet"),
        ("stg_wgi", base / "wgi" / "wgi_clean.parquet"),
        ("stg_ted", base / "ted" / "ted_clean.parquet"),
    ]

    logger.info("=" * 60)
    logger.info("PHASE 2: Loading data from parquet files")
    logger.info("=" * 60)

    all_ok = True
    for table_name, parquet_path in tables:
        if not parquet_path.exists():
            logger.error("Parquet not found: %s", parquet_path)
            all_ok = False
            continue

        size_mb = parquet_path.stat().st_size / (1024 * 1024)
        logger.info("%s (%s MB) -> %s", parquet_path.name, f"{size_mb:.2f}", table_name)

        t0 = time.time()
        df = pd.read_parquet(parquet_path)
        t1 = time.time()
        rows = len(df)
        cols = len(df.columns)
        logger.info("Read: %s rows x %s cols in %.1fs", f"{rows:,}", cols, t1 - t0)

        if "error_info" not in df.columns and "ERROR_INFO" not in [c.upper() for c in df.columns]:
            df["error_info"] = None

        conn.execute(f"TRUNCATE TABLE {table_name}")

        t0 = time.time()
        conn.import_from_pandas(df, table_name)
        t1 = time.time()
        rate = rows / (t1 - t0) if (t1 - t0) > 0 else 0
        logger.info("Loaded %s rows in %.1fs (%s rows/s)", f"{rows:,}", t1 - t0, f"{rate:,.0f}")

        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        status = "OK" if count == rows else "MISMATCH"
        logger.info("%s: %s rows in table (expected %s)", status, f"{count:,}", f"{rows:,}")

        if count != rows:
            all_ok = False

    return all_ok


# ============================================================================
# Phase 3: Example rows
# ============================================================================

def insert_example_rows(conn):
    """Insert 2 example rows per table (clean + insert)."""
    ddl_dir = Path(__file__).resolve().parent / "ddl"

    logger.info("=" * 60)
    logger.info("PHASE 3: Inserting example rows")
    logger.info("=" * 60)

    # Clean in reverse FK order: facts first, then dims
    for table in ["fact_tender", "dim_procedure_type", "dim_cpv", "dim_country"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    logger.info("Cleaned dimension + fact tables")

    insert_file = ddl_dir / "insert_example_rows.sql"
    logger.info("Executing %s...", insert_file.name)
    if not execute_sql_file(conn, insert_file):
        logger.error("Example INSERTs failed")
        return False

    for table in ["dim_country", "dim_cpv", "dim_procedure_type", "fact_tender"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info("  %s: %s rows", table, f"{count}")

    return True


# ============================================================================
# Phase 4: Verification
# ============================================================================

def verify_and_report(conn):
    """Print all table row counts and a sample join."""
    tables = [
        "stg_cpi", "stg_wgi", "stg_ted",
        "dim_country", "dim_cpv", "dim_procedure_type", "fact_tender",
    ]

    logger.info("=" * 60)
    logger.info("PHASE 4: Final Verification Report")
    logger.info("=" * 60)
    logger.info("%-25s %10s", "TABLE", "ROWS")
    logger.info("-" * 35)

    counts = {}
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            counts[t] = count
            logger.info("  %-25s %10s", t, f"{count:,}")
        except Exception:
            logger.error("  %-25s %10s", t, "ERROR")

    # Sample join — Exasol uses LIMIT, not TOP
    logger.info("Sample Join: fact_tender -> dimensions (LIMIT 5)")
    logger.info("-" * 60)
    try:
        rows = conn.execute("""
            SELECT
                f.award_id,
                f."year",
                c.country_name AS auftraggeber,
                w.country_name AS gewinner,
                p.procedure_name,
                f.award_value_eur,
                f.F1, f.F3
            FROM fact_tender f
            JOIN dim_country c  ON f.country_key = c.country_key
            JOIN dim_country w  ON f.winner_country_key = w.country_key
            JOIN dim_procedure_type p ON f.procedure_key = p.procedure_key
            LIMIT 5
        """).fetchall()

        for row in rows:
            val = float(row[5]) if row[5] is not None else 0
            logger.info("  %s | %s | %s->%s | %s | EUR%s | F1=%s F3=%s",
                        row[0], row[1], row[2], row[3], row[4],
                        f"{val:,.0f}", row[6], row[7])
    except Exception as e:
        logger.warning("Join query failed (OK if fact_tender is empty): %s", e)

    # Workbook numbers
    logger.info("Summary")
    logger.info("-" * 50)
    if "stg_ted" in counts:
        logger.info("  Number of rows in biggest table:  %s", f"{counts['stg_ted']:,}")
        ted_path = Path("data/processed/ted/ted_clean.parquet")
        if ted_path.exists():
            size_kb = ted_path.stat().st_size / 1024
            logger.info("  Size of biggest table:            %s KB (%s MB)",
                        f"{size_kb:,.0f}", f"{size_kb/1024:.2f}")
    logger.info("  Name of biggest table:            fact_tender")
    total_kb = 0
    for sub in ["ted", "cpi", "wgi"]:
        p = Path(f"data/processed/{sub}/{sub}_clean.parquet")
        if p.exists():
            total_kb += p.stat().st_size / 1024
    logger.info("  Total size of schema:             %s KB (%s MB)",
                f"{total_kb:,.0f}", f"{total_kb/1024:.2f}")

    return True


# ============================================================================
# Main orchestrator
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Complete Exasol setup and data load")
    parser.add_argument("--ddl-only", action="store_true", help="Only create tables")
    parser.add_argument("--load-only", action="store_true", help="Only load parquet data")
    parser.add_argument("--verify", action="store_true", help="Only verify existing data")
    parser.add_argument("--schema", help="Schema name (default from .env or procurement_governance)")
    return parser.parse_args()


def main():
    args = parse_args()
    load_env()

    for key in ["EXASOL_HOST", "EXASOL_USER", "EXASOL_PASSWORD"]:
        if key not in os.environ or not os.environ[key]:
            logger.error("%s not set in .env or environment", key)
            logger.error("Create .env from .env.template and fill in your credentials")
            sys.exit(1)

    conn, schema = get_connection(schema=args.schema)
    logger.info("Schema: %s", schema)

    do_ddl = args.ddl_only or (not args.load_only and not args.verify)
    do_load = args.load_only or (not args.ddl_only and not args.verify)
    do_verify = args.verify or (not args.ddl_only and not args.load_only)

    phase_ok = True
    if do_ddl:
        phase_ok = ddl_create_all(conn, schema)
    if do_load and phase_ok:
        phase_ok = load_parquet_files(conn)
    if (do_ddl or do_load) and phase_ok:
        if not insert_example_rows(conn):
            logger.warning("Example INSERTs had issues")
    if do_verify:
        verify_and_report(conn)

    logger.info("=" * 60)
    if phase_ok:
        logger.info("ALL PHASES COMPLETED SUCCESSFULLY")
    else:
        logger.warning("Some phases had issues — check log above")
    logger.info("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
