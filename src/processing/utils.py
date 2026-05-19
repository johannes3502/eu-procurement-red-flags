"""
utils.py — Shared helper functions for the ETL pipeline.

Dataset‑agnostic utilities: logging, country‑lookup loading, TED CSV loading,
percentile computation, Parquet export, and pipeline‑step logging.

All constants are imported from ``config.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from src.processing import config

# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a module‑level logger (no handler setup — that's the caller's job).

    Args:
        name: Typically ``__name__``.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Country lookup helpers
# ---------------------------------------------------------------------------


def load_target_countries() -> Dict[str, str]:
    """Read ``lookup_countries.csv`` and return target countries as ``{alpha_2: country_name}``.

    Returns:
        Dict mapping Alpha‑2 → country name for rows where ``is_target == True``.
        Falls back to hardcoded defaults if the file is missing.
    """
    try:
        lookup = pd.read_csv(config.LOOKUP_PATH)
        mask = lookup["is_target"] == True  # noqa: E712
        result: Dict[str, str] = dict(
            zip(lookup.loc[mask, "alpha_2"], lookup.loc[mask, "country_name"])
        )
        return result
    except FileNotFoundError:
        logger = logging.getLogger(__name__)
        logger.warning(
            "lookup_countries.csv not found at %s — falling back to hardcoded defaults",
            config.LOOKUP_PATH,
        )
        return {"DE": "Germany", "DK": "Denmark", "RO": "Romania", "HU": "Hungary"}


def load_target_alpha2_set() -> Set[str]:
    """Convenience wrapper — returns the set of target Alpha‑2 codes.

    Returns:
        ``{"DE", "DK", "RO", "HU"}`` (or whatever ``lookup_countries.csv`` defines).
    """
    return set(load_target_countries().keys())


# ---------------------------------------------------------------------------
# TED data loading
# ---------------------------------------------------------------------------


def load_ted_csvs(years: List[int], cols: Optional[List[str]] = None) -> pd.DataFrame:
    """Load per‑year TED CSV files, keep only the specified columns, concatenate.

    Files are expected at ``{config.DATA_DIR_RAW}/ted/ted_{year}.csv``.

    Args:
        years: List of years to load.
        cols: If provided, only these columns are kept (reduces memory).

    Returns:
        Concatenated DataFrame.

    Raises:
        FileNotFoundError: If NO CSV files were found for the given years.
    """
    frames: List[pd.DataFrame] = []
    data_dir = config.DATA_DIR_RAW / "ted"
    for year in years:
        fpath = data_dir / f"ted_{year}.csv"
        if not fpath.exists():
            logging.getLogger(__name__).warning(
                "File not found: %s — skipping year %d", fpath, year
            )
            continue
        usecols: Optional[List[str]] = None
        if cols is not None:
            # Only keep columns that actually exist in the CSV
            available = pd.read_csv(fpath, nrows=0).columns.tolist()
            usecols = [c for c in cols if c in available]
        df = pd.read_csv(fpath, usecols=usecols, low_memory=False)
        logging.getLogger(__name__).info(
            "Loaded %s: %d rows, %d columns", fpath.name, len(df), len(df.columns)
        )
        frames.append(df)

    if not frames:
        raise FileNotFoundError(
            f"No TED CSV files found in {data_dir} for years {years}"
        )

    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Percentile computation
# ---------------------------------------------------------------------------


def compute_p95_per_year(df: pd.DataFrame, col: str = "AWARD_VALUE_EURO") -> Dict[int, float]:
    """Compute the 95th percentile of a numeric column per year.

    Args:
        df: DataFrame with a ``YEAR`` column and *col*.
        col: Column name to compute percentile over (default ``AWARD_VALUE_EURO``).

    Returns:
        Dict mapping year → p95 value.
    """
    p95_dict: Dict[int, float] = {}
    for year, group in df.groupby("YEAR"):
        vals = group[col].dropna()
        if len(vals) == 0:
            logging.getLogger(__name__).warning(
                "Year %d has no non‑NULL values in '%s' — p95 set to 0", year, col
            )
            p95_dict[int(year)] = 0.0
        else:
            p95_dict[int(year)] = float(vals.quantile(config.P95_PERCENTILE))
    return p95_dict


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame as a compressed Parquet file.

    Creates parent directories if they don't exist.

    Args:
        df: DataFrame to export.
        path: Destination path (should end in ``.parquet``).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logging.getLogger(__name__).info("Exported %d rows to %s", len(df), path)


# ---------------------------------------------------------------------------
# Pipeline-step logging
# ---------------------------------------------------------------------------


def log_pipeline_step(
    logger: logging.Logger,
    step_name: str,
    before: int,
    after: int,
) -> Dict[str, Any]:
    """Log a single pipeline step with row‑count change and return a stats dict.

    Args:
        logger: Logger instance.
        step_name: Human‑readable step name.
        before: Row count before the step.
        after: Row count after the step.

    Returns:
        Dict with ``step``, ``before``, ``after``, ``delta``.
    """
    delta = after - before
    pct = 100.0 * abs(delta) / before if before else 0.0
    direction = "removed" if delta < 0 else "added" if delta > 0 else "unchanged"
    logger.info(
        "%-30s %d → %d  (%s %d, %.1f%%)",
        step_name,
        before,
        after,
        direction,
        abs(delta),
        pct,
    )
    return {
        "step": step_name,
        "before": before,
        "after": after,
        "delta": delta,
    }
