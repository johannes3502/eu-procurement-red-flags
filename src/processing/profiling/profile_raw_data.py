#!/usr/bin/env python3
"""
profile_raw_data.py — Automated profiling of all raw data sources (CPI, WGI, TED).

Scans ``data/raw/`` for CSV files, performs eight data-quality checks on each,
and writes one Markdown report per source into ``doc/profiling/``.

Usage::

    python src/data_processing/profile_raw_data.py

Dependencies: pandas, numpy (both in ``requirements.txt``).
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Project root setup  (allows ``from src.log import ...``)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.log import setup_logger

# ---------------------------------------------------------------------------
# Import generic profiling utilities
# ---------------------------------------------------------------------------
from src.processing.profiling.profiling_utils import (
    compute_basic_info,
    compute_dtype_report,
    compute_missing_values,
    compute_duplicates,
    compute_outliers,
    compute_value_ranges,
    compute_text_quality,
    generate_markdown,
)

# ---------------------------------------------------------------------------
# Column lists
# ---------------------------------------------------------------------------

CPI_NUMERIC: List[str] = [
    "score", "rank", "sources", "standardError", "lowerCi", "upperCi",
]
CPI_TEXT: List[str] = ["country", "iso3", "region"]
CPI_DUP_KEY: List[str] = ["iso3", "year"]

WGI_DIMS: List[str] = [
    "control_of_corruption",
    "government_effectiveness",
    "political_stability",
    "rule_of_law",
    "regulatory_quality",
    "voice_accountability",
]
WGI_DUP_KEY: List[str] = ["country_iso3", "year"]

TED_NUMERIC: List[str] = ["NUMBER_OFFERS", "AWARD_VALUE_EURO", "VALUE_EURO"]
TED_TEXT: List[str] = [
    "WIN_COUNTRY_CODE", "TOP_TYPE", "CPV",
    "B_ACCELERATED", "B_AWARDED_TO_A_GROUP",
]
TED_DUP_KEY: List[str] = ["ID_NOTICE_CAN", "ID_LOT"]


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------

def scan_raw_files(data_dir: Path) -> List[Tuple[str, Path, str]]:
    """Recursively find all ``*.csv`` files under *data_dir* and classify them.

    Classification is based on the parent directory name:
        ``cpi/``  → source type ``"cpi"``, label ``"CPI"``
        ``wgi/``  → source type ``"wgi"``, label ``"WGI"``
        ``ted/``  → source type ``"ted"``, label ``"TED {year}"``

    Returns:
        List of ``(source_type, file_path, label)`` tuples sorted by path.
    """
    found: List[Tuple[str, Path, str]] = []
    for csv_path in sorted(data_dir.glob("**/*.csv")):
        parent = csv_path.parent.name  # "cpi", "wgi", "ted"
        if parent == "cpi":
            found.append(("cpi", csv_path, "CPI"))
        elif parent == "wgi":
            found.append(("wgi", csv_path, "WGI"))
        elif parent == "ted":
            # Extract year from filename: e.g. "ted_2022.csv" → "2022"
            year_str = csv_path.stem.replace("ted_", "")
            found.append(("ted", csv_path, f"TED {year_str}"))
    return found


# ---------------------------------------------------------------------------
# Logical consistency (dataset-specific)
# ---------------------------------------------------------------------------

def _compute_logical_consistency(
    df: pd.DataFrame,
    dataset_type: str,
    logger: logging.Logger,
) -> Dict[str, Any]:
    """Apply dataset-specific logical consistency rules.

    Args:
        df: The raw DataFrame.
        dataset_type: One of ``"cpi"``, ``"wgi"``, ``"ted"``.
        logger: Logger for informational messages.

    Returns:
        Dictionary with ``rules_checked: list[str]`` and
        ``violations: dict[str, {...}]``.
    """
    rules_checked: List[str] = []
    violations: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # CPI rules
    # ------------------------------------------------------------------
    if dataset_type == "cpi":
        # Rule 1: lowerCi <= score <= upperCi  (only when CI is present)
        ci_cols = ["lowerCi", "score", "upperCi"]
        if all(c in df.columns for c in ci_cols):
            mask = df["lowerCi"].notna() & df["upperCi"].notna()
            viol = ((df["lowerCi"] > df["score"]) | (df["score"] > df["upperCi"]))
            count = int(viol.sum())
            rules_checked.append("lowerCi <= score <= upperCi")
            violations["ci_range"] = {
                "description": "lowerCi <= score <= upperCi",
                "violation_count": count,
                "pct_violations": round(count / mask.sum() * 100, 2) if mask.sum() > 0 else 0.0,
                "sample_violations": (
                    df[viol][["iso3", "year", "score", "lowerCi", "upperCi"]]
                    .head(3)
                    .to_dict(orient="records")
                    if count > 0
                    else []
                ),
            }

        # Rule 2: standardError >= 0
        if "standardError" in df.columns:
            neg = df["standardError"] < 0
            count = int(neg.sum())
            rules_checked.append("standardError >= 0")
            violations["neg_stderr"] = {
                "description": "standardError >= 0",
                "violation_count": count,
                "pct_violations": round(count / len(df) * 100, 2),
                "sample_violations": (
                    df[neg][["iso3", "year", "standardError"]]
                    .head(3)
                    .to_dict(orient="records")
                    if count > 0
                    else []
                ),
            }

    # ------------------------------------------------------------------
    # WGI rules
    # ------------------------------------------------------------------
    elif dataset_type == "wgi":
        for dim in WGI_DIMS:
            if dim not in df.columns:
                continue
            viol = (df[dim] < -3.0) | (df[dim] > 3.0)
            count = int(viol.sum())
            if count > 0:
                rules_checked.append(f"{dim} in [-3.0, 3.0]")
                violations[f"{dim}_range"] = {
                    "description": f"{dim} in [-3.0, 3.0]",
                    "violation_count": count,
                    "pct_violations": round(count / len(df) * 100, 2),
                    "sample_violations": (
                        df[viol][["country_iso3", "year", dim]]
                        .head(3)
                        .to_dict(orient="records")
                    ),
                }

    # ------------------------------------------------------------------
    # TED rules
    # ------------------------------------------------------------------
    elif dataset_type == "ted":
        # Rule 1: AWARD_VALUE_EURO >= 0
        if "AWARD_VALUE_EURO" in df.columns:
            neg = df["AWARD_VALUE_EURO"] < 0
            count = int(neg.sum())
            rules_checked.append("AWARD_VALUE_EURO >= 0")
            violations["neg_award"] = {
                "description": "AWARD_VALUE_EURO >= 0",
                "violation_count": count,
                "pct_violations": round(count / len(df) * 100, 4),
                "sample_violations": (
                    df[neg][["ID_NOTICE_CAN", "ID_LOT", "AWARD_VALUE_EURO"]]
                    .head(3)
                    .to_dict(orient="records")
                    if count > 0
                    else []
                ),
            }

        # Rule 2: VALUE_EURO <= AWARD_VALUE_EURO  (when both present)
        if "VALUE_EURO" in df.columns and "AWARD_VALUE_EURO" in df.columns:
            valid = df["VALUE_EURO"].notna() & df["AWARD_VALUE_EURO"].notna()
            viol = df["VALUE_EURO"] > df["AWARD_VALUE_EURO"]
            count = int(viol.sum())
            rules_checked.append("VALUE_EURO <= AWARD_VALUE_EURO")
            violations["value_vs_award"] = {
                "description": "VALUE_EURO <= AWARD_VALUE_EURO (estimate ≤ award)",
                "violation_count": count,
                "pct_violations": round(count / valid.sum() * 100, 2) if valid.sum() > 0 else 0.0,
                "sample_violations": (
                    df[viol][
                        ["ID_NOTICE_CAN", "ID_LOT", "VALUE_EURO", "AWARD_VALUE_EURO"]
                    ]
                    .head(3)
                    .to_dict(orient="records")
                    if count > 0
                    else []
                ),
            }

        # Rule 3: NUMBER_OFFERS >= 1  (0 is technically allowed but suspicious)
        if "NUMBER_OFFERS" in df.columns:
            zero = df["NUMBER_OFFERS"] == 0
            count = int(zero.sum())
            rules_checked.append("NUMBER_OFFERS >= 1")
            violations["zero_offers"] = {
                "description": "NUMBER_OFFERS >= 1 (0 offers = möglicherweise fehlerhaft)",
                "violation_count": count,
                "pct_violations": round(count / len(df) * 100, 2),
                "sample_violations": (
                    df[zero][
                        ["ID_NOTICE_CAN", "ID_LOT", "NUMBER_OFFERS", "AWARD_VALUE_EURO"]
                    ]
                    .head(3)
                    .to_dict(orient="records")
                    if count > 0
                    else []
                ),
            }

        # Rule 4: B_ACCELERATED distribution
        if "B_ACCELERATED" in df.columns and "TOP_TYPE" in df.columns:
            accel = df["B_ACCELERATED"] == "Y"
            count = int(accel.sum())
            rules_checked.append("B_ACCELERATED = Y (Verteilung)")
            # Sample: show TOP_TYPE distribution for accelerated rows
            sample_top_types = (
                df[accel]["TOP_TYPE"].value_counts().head(5).to_dict()
                if count > 0
                else {}
            )
            violations["accelerated"] = {
                "description": "B_ACCELERATED = Y nach TOP_TYPE",
                "violation_count": count,
                "pct_violations": round(count / len(df) * 100, 2),
                "sample_violations": (
                    [{"TOP_TYPE": k, "count": int(v)} for k, v in sample_top_types.items()]
                    if sample_top_types
                    else []
                ),
            }

    return {
        "rules_checked": rules_checked,
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# Dataset-specific profiling functions
# ---------------------------------------------------------------------------

def profile_cpi(df: pd.DataFrame, logger: logging.Logger) -> Dict[str, Any]:
    """Run all 8 profiling categories on CPI data.

    Args:
        df: CPI raw DataFrame.
        logger: Logger instance.

    Returns:
        Complete metrics dictionary.
    """
    logger.info("Profiling CPI-Daten (%d Zeilen)...", len(df))

    metrics: Dict[str, Any] = {}
    # basic_info is filled later in main() with file size; build stub here
    metrics["basic_info"] = {"rows": len(df), "columns": len(df.columns), "memory_mb": 0.0, "file_size_mb": 0.0}
    metrics["dtypes"] = compute_dtype_report(df)
    metrics["missing_values"] = compute_missing_values(df)
    metrics["duplicates"] = compute_duplicates(df, CPI_DUP_KEY)
    metrics["outliers"] = compute_outliers(df, CPI_NUMERIC)
    metrics["value_ranges"] = compute_value_ranges(df, CPI_NUMERIC)
    metrics["text_quality"] = compute_text_quality(df, CPI_TEXT)
    metrics["logical_consistency"] = _compute_logical_consistency(df, "cpi", logger)

    return metrics


def profile_wgi(df: pd.DataFrame, logger: logging.Logger) -> Dict[str, Any]:
    """Run all 8 profiling categories on WGI data.

    Args:
        df: WGI raw DataFrame.
        logger: Logger instance.

    Returns:
        Complete metrics dictionary.
    """
    logger.info("Profiling WGI-Daten (%d Zeilen)...", len(df))

    metrics: Dict[str, Any] = {}
    metrics["basic_info"] = {"rows": len(df), "columns": len(df.columns), "memory_mb": 0.0, "file_size_mb": 0.0}
    metrics["dtypes"] = compute_dtype_report(df)
    metrics["missing_values"] = compute_missing_values(df)
    metrics["duplicates"] = compute_duplicates(df, WGI_DUP_KEY)
    metrics["outliers"] = compute_outliers(df, WGI_DIMS)
    metrics["value_ranges"] = compute_value_ranges(df, WGI_DIMS)
    metrics["text_quality"] = compute_text_quality(df, ["country_iso3"])
    metrics["logical_consistency"] = _compute_logical_consistency(df, "wgi", logger)

    return metrics


def profile_ted(df: pd.DataFrame, year: int, logger: logging.Logger) -> Dict[str, Any]:
    """Run all 8 profiling categories on TED data for a single year.

    Args:
        df: TED raw DataFrame for one year.
        year: The year (used for reporting only).
        logger: Logger instance.

    Returns:
        Complete metrics dictionary.
    """
    logger.info("Profiling TED %d (%d Zeilen)...", year, len(df))

    metrics: Dict[str, Any] = {}
    metrics["basic_info"] = {"rows": len(df), "columns": len(df.columns), "memory_mb": 0.0, "file_size_mb": 0.0}
    metrics["dtypes"] = compute_dtype_report(df)
    metrics["missing_values"] = compute_missing_values(df)
    metrics["duplicates"] = compute_duplicates(df, TED_DUP_KEY)
    metrics["outliers"] = compute_outliers(df, TED_NUMERIC)
    metrics["value_ranges"] = compute_value_ranges(df, TED_NUMERIC)
    metrics["text_quality"] = compute_text_quality(df, TED_TEXT)
    metrics["logical_consistency"] = _compute_logical_consistency(df, "ted", logger)

    return metrics


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def main() -> None:
    """Main orchestrator: scan raw files, profile each, write Markdown reports."""
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")

    # -- Logger -----------------------------------------------------------
    logger = setup_logger(
        name=__name__,
        log_dir="logs",
        log_file="profiling.log",
    )

    logger.info("=" * 60)
    logger.info("Data Profiling started")
    logger.info("=" * 60)

    # -- Directories ------------------------------------------------------
    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "data" / "raw"
    output_dir = project_root / "doc" / "profiling"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Project root: %s", project_root)
    logger.info("Data directory: %s", data_dir)
    logger.info("Output directory: %s", output_dir)

    # -- Scan files -------------------------------------------------------
    files = scan_raw_files(data_dir)
    logger.info("CSV files found: %d", len(files))

    if not files:
        logger.warning("No CSV files found in %s!", data_dir)
        return

    # -- Process each file ------------------------------------------------
    for source_type, file_path, label in files:
        logger.info("=" * 50)
        logger.info("Processing %s ...", label)
        logger.info("File: %s", file_path)

        try:
            file_size_mb = file_path.stat().st_size / 1_000_000
            relative_path = file_path.relative_to(project_root)

            # Load CSV
            df = pd.read_csv(
                file_path,
                encoding="utf-8",
                low_memory=False,
                dtype_backend="numpy_nullable",
            )
            logger.info(
                "%s: %d rows, %d columns loaded (%.2f MB)",
                label, len(df), len(df.columns), file_size_mb,
            )

            # Route to the correct profiler
            if source_type == "cpi":
                metrics = profile_cpi(df, logger)
            elif source_type == "wgi":
                metrics = profile_wgi(df, logger)
            elif source_type == "ted":
                year = int(file_path.stem.replace("ted_", ""))
                metrics = profile_ted(df, year, logger)
            else:
                logger.warning("Unknown source type: %s -- skipping", source_type)
                continue

            # Overwrite basic_info with actual values (including file size)
            metrics["basic_info"] = compute_basic_info(df, file_size_mb)

            # Generate Markdown
            md_content = generate_markdown(
                metrics, label, relative_path, date_str,
            )

            # Determine output filename
            if source_type == "ted":
                year_part = f"_{file_path.stem.replace('ted_', '')}"
            else:
                year_part = ""
            out_name = f"profile_{source_type}{year_part}_{date_str}.md"
            out_path = output_dir / out_name

            # Write report
            out_path.write_text(md_content, encoding="utf-8")
            logger.info("Report written: %s", out_path)

        except Exception:
            logger.exception("Error processing %s", label)

    logger.info("=" * 60)
    logger.info("Data Profiling complete -- reports in %s", output_dir)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
