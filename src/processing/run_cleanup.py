"""
run_cleanup.py — Orchestration script for all ETL cleanup pipelines.

Loads raw TED, CPI, and WGI data, applies dataset‑specific cleaning steps,
and exports the results as compressed Parquet files.

Usage:
    python -m src.data_processing.run_cleanup                         # full pipeline
    python -m src.data_processing.run_cleanup --years 2020 2021 2022
    python -m src.data_processing.run_cleanup --log-level DEBUG
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.processing import config
from src.processing import utils
from src.processing.cpi import clean as cpi_clean
from src.processing.ted import clean as ted_clean
from src.processing.wgi import clean as wgi_clean
from src.log.logger import setup_logger

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_TED_INPUT = config.DATA_DIR_RAW / "ted"
DEFAULT_CPI_INPUT = config.DATA_DIR_RAW / "cpi" / "cpi_raw.csv"
DEFAULT_WGI_INPUT = config.DATA_DIR_RAW / "wgi" / "wgi_raw.csv"
DEFAULT_OUTPUT_DIR = config.DATA_DIR_PROCESSED
TED_RAW_COLUMNS: List[str] = [
    "ID_AWARD", "ID_NOTICE_CAN", "ID_LOT", "YEAR",
    "ISO_COUNTRY_CODE", "WIN_COUNTRY_CODE",
    "AWARD_VALUE_EURO", "VALUE_EURO",
    "NUMBER_OFFERS", "B_AWARDED_TO_A_GROUP",
    "TOP_TYPE", "LOTS_NUMBER", "NUMBER_AWARDS",
    "CPV", "CORRECTIONS",
]


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def run_ted_pipeline(
    years: List[int],
    ted_input_dir: Path = DEFAULT_TED_INPUT,
) -> pd.DataFrame:
    """Execute the full TED cleaning pipeline.

    Steps in order:
        1. Load per‑year CSVs → concatenate
        2. clean_ted_filter_countries
        3. clean_ted_dedup
        4. clean_ted_remove_sentinels
        5. clean_ted_parse_winner
        6. clean_ted_normalize_cpv
        7. clean_ted_select_columns
        8. compute_red_flags

    Args:
        years: List of years to process.
        ted_input_dir: Directory containing ``ted_<year>.csv`` files.

    Returns:
        Fully processed, flag‑enriched DataFrame.
    """
    logger.info("=" * 60)
    logger.info("TED Pipeline — years: %s", years)
    logger.info("=" * 60)

    # Step 1: Load all years
    df = utils.load_ted_csvs(years, cols=TED_RAW_COLUMNS)
    stats: Dict[str, Any] = {"initial_rows": len(df)}

    # Step 2–8 — each step releases the old DataFrame immediately
    # to keep only one in-memory copy at a time
    _next = ted_clean.clean_ted_filter_countries(df)
    del df; gc.collect()
    df = _next
    stats["after_filter"] = len(df)

    _next = ted_clean.clean_ted_dedup(df)
    del df; gc.collect()
    df = _next
    stats["after_dedup"] = len(df)

    _next = ted_clean.clean_ted_remove_sentinels(df)
    del df; gc.collect()
    df = _next
    stats["after_sentinels"] = len(df)

    _next = ted_clean.clean_ted_parse_winner(df)
    del df; gc.collect()
    df = _next
    stats["after_parse_country"] = len(df)

    _next = ted_clean.clean_ted_normalize_cpv(df)
    del df; gc.collect()
    df = _next
    stats["after_normalize_cpv"] = len(df)

    _next = ted_clean.clean_ted_select_columns(df)
    del df; gc.collect()
    df = _next
    stats["after_select"] = len(df)

    _next = ted_clean.compute_red_flags(df)
    del df; gc.collect()
    df = _next
    stats["after_flags"] = len(df)
    stats["final_columns"] = list(df.columns)

    # Log flag frequencies
    for flag in ["F1", "F2", "F3", "F5", "F6", "F7"]:
        if flag in df.columns:
            stats[f"{flag}_count"] = int(df[flag].sum())
            stats[f"{flag}_pct"] = round(float(df[flag].mean()) * 100, 2)

    logger.info("-" * 60)
    logger.info("TED Pipeline complete — %d rows, %d columns", len(df), len(df.columns))
    logger.info("Summary: %s", json.dumps(stats, indent=2))
    logger.info("=" * 60)

    return df


def run_cpi_pipeline(cpi_input: Path) -> pd.DataFrame:
    """Execute the CPI cleaning pipeline.

    Args:
        cpi_input: Path to ``cpi_raw.csv``.

    Returns:
        Cleaned CPI DataFrame.
    """
    logger.info("=" * 60)
    logger.info("CPI Pipeline — input: %s", cpi_input)
    logger.info("=" * 60)

    df = pd.read_csv(cpi_input)
    logger.info("Loaded CPI raw: %d rows, %d columns", len(df), len(df.columns))

    df = cpi_clean.clean_cpi(df)

    logger.info("-" * 60)
    logger.info("CPI Pipeline complete — %d rows", len(df))
    logger.info("=" * 60)
    return df


def run_wgi_pipeline(wgi_input: Path) -> pd.DataFrame:
    """Execute the WGI cleaning pipeline.

    Args:
        wgi_input: Path to ``wgi_raw.csv``.

    Returns:
        Cleaned WGI DataFrame.
    """
    logger.info("=" * 60)
    logger.info("WGI Pipeline — input: %s", wgi_input)
    logger.info("=" * 60)

    df = pd.read_csv(wgi_input)
    logger.info("Loaded WGI raw: %d rows, %d columns", len(df), len(df.columns))

    df = wgi_clean.clean_wgi(df)

    logger.info("-" * 60)
    logger.info("WGI Pipeline complete — %d rows", len(df))
    logger.info("=" * 60)
    return df


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI arguments and run all three pipelines."""
    parser = argparse.ArgumentParser(
        description=(
            "ETL Cleanup Pipeline — prepare raw TED, CPI, and WGI data "
            "for the Data Warehouse."
        )
    )
    parser.add_argument(
        "--years",
        nargs="*",
        type=int,
        default=config.YEARS,
        help="Years to process (default: 2014 2015 ... 2023)",
    )
    parser.add_argument(
        "--ted-input-dir",
        type=Path,
        default=DEFAULT_TED_INPUT,
        help=f"Directory with ted_<year>.csv files (default: {DEFAULT_TED_INPUT})",
    )
    parser.add_argument(
        "--cpi-input",
        type=Path,
        default=DEFAULT_CPI_INPUT,
        help=f"CPI input path (default: {DEFAULT_CPI_INPUT})",
    )
    parser.add_argument(
        "--wgi-input",
        type=Path,
        default=DEFAULT_WGI_INPUT,
        help=f"WGI input path (default: {DEFAULT_WGI_INPUT})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for Parquet files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logger(
        name=__name__,
        log_dir=str(config.LOG_DIR),
        log_file="run_cleanup.log",
        console_level=getattr(logging, args.log_level.upper()),
    )

    # Create output directories (one per dataset)
    ted_output_dir = args.output_dir / "ted"
    cpi_output_dir = args.output_dir / "cpi"
    wgi_output_dir = args.output_dir / "wgi"
    for d in (ted_output_dir, cpi_output_dir, wgi_output_dir):
        d.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {}

    # ---- TED ----
    ted_output = ted_output_dir / "ted_clean.parquet"
    df_ted = run_ted_pipeline(
        years=args.years,
        ted_input_dir=args.ted_input_dir,
    )
    utils.export_parquet(df_ted, ted_output)
    summary["ted"] = {
        "rows": len(df_ted),
        "columns": len(df_ted.columns),
        "output": str(ted_output),
    }
    del df_ted; gc.collect()  # free TED before starting CPI

    # ---- CPI ----
    cpi_output = cpi_output_dir / "cpi_clean.parquet"
    df_cpi = run_cpi_pipeline(args.cpi_input)
    utils.export_parquet(df_cpi, cpi_output)
    summary["cpi"] = {
        "rows": len(df_cpi),
        "columns": len(df_cpi.columns),
        "output": str(cpi_output),
    }
    del df_cpi; gc.collect()  # free CPI before starting WGI

    # ---- WGI ----
    wgi_output = wgi_output_dir / "wgi_clean.parquet"
    df_wgi = run_wgi_pipeline(args.wgi_input)
    utils.export_parquet(df_wgi, wgi_output)
    summary["wgi"] = {
        "rows": len(df_wgi),
        "columns": len(df_wgi.columns),
        "output": str(wgi_output),
    }
    del df_wgi; gc.collect()  # free WGI after export

    # ---- Final summary ----
    logger.info("=" * 60)
    logger.info("ALL PIPELINES COMPLETE")
    logger.info("=" * 60)
    for dataset, info in summary.items():
        logger.info("  %-8s %s", dataset.upper(), json.dumps(info))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
