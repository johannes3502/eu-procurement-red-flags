"""
Connection test helper for Power BI <-> Exasol.

Prerequisites: Copy .env.template to .env and fill in your Exasol credentials.

Usage: (from venv)
  python src/powerbi/test_connections.py

Tests ODBC and native Exasol connections,
prints working connection strings for Power BI.
"""

import sys
import os
import ssl
from pathlib import Path


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
EXASOL_SCHEMA = _require_env("EXASOL_SCHEMA")

HOST_PORT = f"{EXASOL_HOST}:{EXASOL_PORT}"
ODBC_CS = f"Driver={{Exasol Driver}};EXAHOST={HOST_PORT}/nocertcheck"


print("=" * 60)
print("TEST 1: ODBC (Power BI -> ODBC)")
print("=" * 60)

try:
    import pyodbc
    conn = pyodbc.connect(ODBC_CS, uid=EXASOL_USER, pwd=EXASOL_PASSWORD, timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    row = cur.fetchone()
    conn.close()
    print(f"  [OK] {ODBC_CS}")
except Exception as e:
    msg = str(e).split("\n")[0][:120]
    print(f"  [FAIL] {msg}")

print()
print("--- Power BI ODBC connection string (copy-paste): ---")
print()
print(ODBC_CS)
print()
print("  In Power BI:")
print("  1. Get Data -> Other -> ODBC")
print("  2. Select 'Connection string'")
print("  3. Paste the string above")
print("  4. OK -> Select 'Database' on the left")
print(f"  5. User: {EXASOL_USER}")
print("  6. Choose DirectQuery or Import")
print()


print("=" * 60)
print("TEST 2: Native Exasol (Power BI - Exasol Connector)")
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
    cur = conn.execute("SELECT 1")
    row = cur.fetchone()
    conn.close()
    print(f"  [OK] {HOST_PORT}")
except Exception as e:
    print(f"  [FAIL] {HOST_PORT} : {str(e)[:150]}")

print()
print("--- Power BI Exasol Connector Server field: ---")
print()
print(f"  {HOST_PORT}/nocertcheck")
print()


print("=" * 60)
print("TEST 3: List tables")
print("=" * 60)

try:
    import pyodbc
    conn = pyodbc.connect(ODBC_CS, uid=EXASOL_USER, pwd=EXASOL_PASSWORD, timeout=10)
    cur = conn.cursor()
    cur.execute(f"SELECT table_name FROM cat WHERE table_schema = '{EXASOL_SCHEMA}' AND table_type = 'TABLE' ORDER BY table_name")
    for row in cur.fetchall():
        print(f"  {row.table_name}")
    conn.close()
except Exception as e:
    print(f"  [FAIL] {str(e)[:150]}")

print()
print("=" * 60)
print("DONE - working connection strings are above.")
print("=" * 60)
