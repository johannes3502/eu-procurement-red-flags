"""
Exasol connection test.

Prerequisites: Copy .env.template to .env and fill in your Exasol credentials.

Usage:
  python src/powerbi/test_connections.py
"""

import sys
import os
import ssl
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def _require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        print(f"[FAIL] Environment variable {key} is not set.")
        print("       Copy .env.template to .env and fill in your credentials.")
        sys.exit(1)
    return value


EXASOL_HOST = _require_env("EXASOL_HOST")
EXASOL_PORT = _require_env("EXASOL_PORT")
EXASOL_USER = _require_env("EXASOL_USER")
EXASOL_PASSWORD = _require_env("EXASOL_PASSWORD")
EXASOL_SCHEMA = _require_env("EXASOL_SCHEMA")

HOST_PORT = f"{EXASOL_HOST}:{EXASOL_PORT}"

print("=" * 60)
print("TEST 1: Native Exasol (pyexasol)")
print("=" * 60)

try:
    import pyexasol
    conn = pyexasol.connect(
        dsn=HOST_PORT,
        user=EXASOL_USER,
        password=EXASOL_PASSWORD,
        compression=True,
        encryption=True,
        websocket_sslopt={"cert_reqs": ssl.CERT_NONE},
    )
    conn.execute("SELECT 1")
    conn.close()
    print(f"  [OK] Connected to {HOST_PORT}")
except Exception as e:
    print(f"  [FAIL] {HOST_PORT}: {str(e)[:150]}")

print()
print("=" * 60)
print("TEST 2: List tables in schema")
print("=" * 60)

try:
    import pyexasol
    conn = pyexasol.connect(
        dsn=HOST_PORT,
        user=EXASOL_USER,
        password=EXASOL_PASSWORD,
        compression=True,
        encryption=True,
        websocket_sslopt={"cert_reqs": ssl.CERT_NONE},
    )
    rows = conn.execute(
        f"SELECT table_name FROM EXA_ALL_TABLES "
        f"WHERE table_schema = UPPER('{EXASOL_SCHEMA}') "
        f"ORDER BY table_name"
    ).fetchall()
    if rows:
        for (table_name,) in rows:
            count = conn.execute(f"SELECT COUNT(*) FROM {EXASOL_SCHEMA}.{table_name}").fetchone()[0]
            print(f"  {table_name:<25s} {count:>10,} rows")
    else:
        print("  (no tables found -- run setup_and_load first)")
    conn.close()
except Exception as e:
    print(f"  [FAIL] {str(e)[:150]}")

print()
print("=" * 60)
print("TEST 3: Red flag summary")
print("=" * 60)

try:
    import pyexasol
    conn = pyexasol.connect(
        dsn=HOST_PORT,
        user=EXASOL_USER,
        password=EXASOL_PASSWORD,
        compression=True,
        encryption=True,
        websocket_sslopt={"cert_reqs": ssl.CERT_NONE},
    )
    conn.execute(f"OPEN SCHEMA {EXASOL_SCHEMA}")
    rows = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN F1 THEN 1 ELSE 0 END) AS f1,
            SUM(CASE WHEN F2 THEN 1 ELSE 0 END) AS f2,
            SUM(CASE WHEN F3 THEN 1 ELSE 0 END) AS f3,
            SUM(CASE WHEN F5 THEN 1 ELSE 0 END) AS f5,
            SUM(CASE WHEN F6 THEN 1 ELSE 0 END) AS f6,
            SUM(CASE WHEN F7 THEN 1 ELSE 0 END) AS f7
        FROM fact_tender
    """).fetchone()
    total, f1, f2, f3, f5, f6, f7 = rows
    print(f"  Total tenders: {total:,}")
    if total:
        for name, count in [("F1 Single Bidder", f1), ("F2 Estimate/Award Discrepancy", f2),
                            ("F3 No Prior Call", f3), ("F5 Award to Group", f5),
                            ("F6 Elevated Price", f6), ("F7 Tax Haven W inner", f7)]:
            pct = (count or 0) / total * 100
            print(f"  {name:<30s} {count or 0:>8,} ({pct:5.1f}%)")
    conn.close()
except Exception as e:
    print(f"  [FAIL] {str(e)[:150]}")

print()
print("=" * 60)
print("DONE")
print("=" * 60)
