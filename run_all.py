#!/usr/bin/env python3
"""
run_all.py — Single entry point for the full pipeline.

Usage:
    python run_all.py                    # full pipeline
    python run_all.py --years 2022 2023  # limit TED to specific years
    python run_all.py --skip-download    # skip download, start from cleanup
    python run_all.py --skip-tests       # skip pytest
"""

from __future__ import annotations

import argparse
import gc
import logging
import os
import ssl
import sys
import time
from pathlib import Path
from typing import Any

# Set before any project imports to suppress individual logger handlers
os.environ["RUN_ALL"] = "1"

import pandas as pd
import pyexasol
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                import os; os.environ[key.strip()] = val.strip()

# ---------------------------------------------------------------------------
# Logging — suppress all module output, only show run_all messages
# ---------------------------------------------------------------------------
# Root logger: CRITICAL to silence all sub-modules
logging.basicConfig(level=logging.CRITICAL, format="%(message)s", stream=sys.stdout)

logger = logging.getLogger("run_all")
logger.setLevel(logging.INFO)
logger.propagate = False
_h = logging.StreamHandler(sys.stdout)
_h.setFormatter(logging.Formatter("%(message)s"))
logger.handlers.clear()
logger.addHandler(_h)

SEP = "=" * 64
SEP2 = "-" * 64


def phase_header(phase: int, title: str) -> None:
    print(f"\n{SEP}")
    print(f"  PHASE {phase}: {title}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Phase 1: Download
# ---------------------------------------------------------------------------

def phase_download(years: list[int] | None = None) -> bool:
    """Download TED, CPI, WGI raw data."""
    phase_header(1, "Download Raw Data")

    from src.acquisition.ted.download import download_ted, TED_URLS
    from src.acquisition.cpi.download import download_cpi
    from src.acquisition.wgi.download import download_wgi

    all_ok = True

    # TED
    if years is None:
        years = sorted(TED_URLS.keys())
    print(f"  Downloading TED CSV ({len(years)} years: {years[0]}–{years[-1]})")
    with tqdm(total=len(years), desc="  TED", unit="year", ncols=80, colour="green") as pbar:
        session = _create_ted_session()
        from src.acquisition.ted.download import TED_DIR, _download_and_extract_zip, TED_URLS
        TED_DIR.mkdir(parents=True, exist_ok=True)
        for year in years:
            url = TED_URLS.get(year)
            if url is None:
                pbar.update(1)
                continue
            ok = _download_and_extract_zip(session, year, url, TED_DIR, force=False)
            if not ok:
                all_ok = False
                tqdm.write(f"  [FAIL] TED {year} download failed")
            pbar.update(1)

    print(f"  TED complete — {len(years)} files in data/raw/ted/")

    # CPI
    print("  Downloading CPI...")
    ok = download_cpi(force=False)
    status = "OK" if ok else "FAIL"
    print(f"  CPI: {status}")
    all_ok = all_ok and ok

    # WGI
    print("  Downloading WGI...")
    ok = download_wgi(force=False)
    status = "OK" if ok else "FAIL"
    print(f"  WGI: {status}")
    all_ok = all_ok and ok

    return all_ok


def _create_ted_session():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import requests
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], allowed_methods={"GET"})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


# ---------------------------------------------------------------------------
# Phase 2: Cleanup
# ---------------------------------------------------------------------------

def phase_cleanup(years: list[int] | None = None) -> bool:
    """Clean raw data, compute red flags, export Parquet."""
    phase_header(2, "Clean & Process Data")

    from src.processing import config, utils
    from src.processing.run_cleanup import run_ted_pipeline, run_cpi_pipeline, run_wgi_pipeline

    if years is None:
        years = list(config.YEARS)
    output_dir = config.DATA_DIR_PROCESSED

    # TED
    print(f"  Processing TED ({len(years)} years)...")
    t0 = time.time()
    df_ted = run_ted_pipeline(years=years)
    ted_time = time.time() - t0
    ted_output = output_dir / "ted" / "ted_clean.parquet"
    ted_output.parent.mkdir(parents=True, exist_ok=True)
    utils.export_parquet(df_ted, ted_output)
    flag_counts = {f: int(df_ted[f].sum()) for f in ["F1", "F2", "F3", "F5", "F6", "F7"] if f in df_ted.columns}
    overall = int((df_ted[["F1", "F2", "F3", "F5", "F6", "F7"]].sum(axis=1) > 0).sum())
    print(f"  TED: {len(df_ted):,} rows, {len(df_ted.columns)} cols in {ted_time:.0f}s")
    print(f"  Red flags: {overall:,} tenders with >=1 flag ({overall/len(df_ted)*100:.1f}%)")
    del df_ted; gc.collect()

    # CPI
    print("  Processing CPI...")
    df_cpi = run_cpi_pipeline(config.DATA_DIR_RAW / "cpi" / "cpi_raw.csv")
    cpi_output = output_dir / "cpi" / "cpi_clean.parquet"
    cpi_output.parent.mkdir(parents=True, exist_ok=True)
    utils.export_parquet(df_cpi, cpi_output)
    print(f"  CPI: {len(df_cpi):,} rows")
    del df_cpi; gc.collect()

    # WGI
    print("  Processing WGI...")
    df_wgi = run_wgi_pipeline(config.DATA_DIR_RAW / "wgi" / "wgi_raw.csv")
    wgi_output = output_dir / "wgi" / "wgi_clean.parquet"
    wgi_output.parent.mkdir(parents=True, exist_ok=True)
    utils.export_parquet(df_wgi, wgi_output)
    print(f"  WGI: {len(df_wgi):,} rows")
    del df_wgi; gc.collect()

    print(f"\n  Export: {output_dir}/ted/ted_clean.parquet")
    print(f"          {output_dir}/cpi/cpi_clean.parquet")
    print(f"          {output_dir}/wgi/wgi_clean.parquet")
    return True


# ---------------------------------------------------------------------------
# Phase 3: Exasol Setup & Load
# ---------------------------------------------------------------------------

def phase_setup_load() -> bool:
    """Create schema, load staging, merge dimensions into star schema."""
    phase_header(3, "Exasol Setup & Data Load")

    import os
    from src.dw.setup_and_load import (
        get_connection, load_env, ddl_create_all,
        load_parquet_files, merge_dimensions,
    )

    load_env()

    print("  Connecting to Exasol...")
    conn, schema = get_connection()
    print(f"  Connected: {os.environ['EXASOL_HOST']}:{os.environ['EXASOL_PORT']}")
    print(f"  Schema: {schema}")

    # DDL
    print("\n  Creating tables...")
    ok = ddl_create_all(conn, schema)
    if not ok:
        print("  [FAIL] DDL creation failed")
        return False
    print("  [OK]  7 tables created (3 staging + 4 star schema)")

    # Load parquet
    print("\n  Loading parquet into staging tables...")
    ok = load_parquet_files(conn)
    if not ok:
        print("  [FAIL] Parquet load failed")
        return False

    # Merge dimensions
    print("\n  Merging dimensions + populating fact table...")
    ok = merge_dimensions(conn)
    if not ok:
        print("  [FAIL] Merge dimensions failed")
        return False

    # Final counts
    print(f"\n{SEP2}")
    print(f"  {'Table':<25s} {'Rows':>12s}")
    print(f"  {'-'*37}")
    for table in ["stg_cpi", "stg_wgi", "stg_ted", "dim_country", "dim_cpv", "dim_procedure_type", "fact_tender"]:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:<25s} {count:>12,}")
        except Exception:
            print(f"  {table:<25s} {'ERROR':>12}")

    conn.close()
    print(f"  {'-'*37}")
    return True


# ---------------------------------------------------------------------------
# Phase 4: Tests
# ---------------------------------------------------------------------------

def phase_tests() -> bool:
    """Run pytest test suite."""
    phase_header(4, "Run Unit Tests")

    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    # Print filtered output — just summary lines
    for line in result.stdout.split("\n"):
        if "PASSED" in line or "FAILED" in line or "ERROR" in line or "passed" in line or "failed" in line:
            print(f"  {line.strip()}")
    if result.returncode != 0:
        print(f"\n  [FAIL] {result.returncode} test failures")
        # Print failures
        for line in result.stdout.split("\n"):
            if line.strip().startswith("FAILED") or line.strip().startswith("ERROR"):
                print(f"  {line.strip()}")
        return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full pipeline — EU Procurement Red Flags")
    parser.add_argument("--years", type=int, nargs="+", help="TED years to process (default: 2014-2023)")
    parser.add_argument("--skip-download", action="store_true", help="Skip Phase 1 (download)")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip Phase 2 (cleanup)")
    parser.add_argument("--skip-load", action="store_true", help="Skip Phase 3 (Exasol load)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip Phase 4 (tests)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    years = args.years if args.years else None

    print(f"\n{'=' * 64}")
    print(f"  EU PROCUREMENT RED FLAGS — Full Pipeline")
    print(f"  {'=' * 64}")
    if years:
        print(f"  Years: {years}")
    print()

    t_start = time.time()
    phases_run = 0
    phases_ok = 0

    if not args.skip_download:
        phases_run += 1
        if phase_download(years):
            phases_ok += 1
            print(f"\n  [OK] Phase 1 complete")
        else:
            print(f"\n  [WARN] Phase 1 completed with errors")

    if not args.skip_cleanup:
        phases_run += 1
        if phase_cleanup(years):
            phases_ok += 1
            print(f"\n  [OK] Phase 2 complete")
        else:
            print(f"\n  [FAIL] Phase 2 failed")

    if not args.skip_load:
        phases_run += 1
        if phase_setup_load():
            phases_ok += 1
            print(f"\n  [OK] Phase 3 complete")
        else:
            print(f"\n  [FAIL] Phase 3 failed")

    if not args.skip_tests:
        phases_run += 1
        if phase_tests():
            phases_ok += 1
            print(f"\n  [OK] Phase 4 complete")
        else:
            print(f"\n  [FAIL] Phase 4 failed")

    elapsed = time.time() - t_start
    print(f"\n{'=' * 64}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Phases: {phases_ok}/{phases_run} OK  |  Time: {elapsed:.0f}s")
    print(f"{'=' * 64}\n")

    if phases_ok < phases_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
