"""
analysis_utils.py — Shared utilities for the four deep-dive analysis scripts.

Provides:
    - Constants (years, target countries, columns to keep)
    - load_ted_data() — load all TED CSVs, optionally filter to target countries
    - Output helpers for Markdown tables and console printing
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Project root  (these scripts live in src/data_processing/profiling/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "ted"
OUTPUT_DIR = PROJECT_ROOT / "doc" / "profiling" / "analysis"
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
YEARS: List[int] = list(range(2014, 2024))

# Target countries for the procurement-governance project.
# Maps ISO 2-letter codes to names.  CPI/WGI use ISO 3-letter codes:
#     DE → DEU, DK → DNK, RO → ROU, HU → HUN
TARGET_COUNTRIES: Dict[str, str] = {
    "DE": "Germany",
    "DK": "Denmark",
    "RO": "Romania",
    "HU": "Hungary",
}

# Columns relevant across all four deep-dive analyses.
# Keep these plus the key identity columns to minimise memory.
KEEP_COLUMNS: List[str] = [
    "ID_NOTICE_CAN",
    "ID_LOT",
    "ID_AWARD",
    "CORRECTIONS",
    "YEAR",
    "ISO_COUNTRY_CODE",
    "WIN_COUNTRY_CODE",
    "AWARD_VALUE_EURO",
    "VALUE_EURO",
    "NUMBER_OFFERS",
    "B_ACCELERATED",
    "B_AWARDED_TO_A_GROUP",
    "TOP_TYPE",
    "LOTS_NUMBER",
    "NUMBER_AWARDS",
]


def load_ted_data(
    years: Optional[List[int]] = None,
    filter_target_countries: bool = True,
    dtype: str = "numpy_nullable",
) -> pd.DataFrame:
    """Load and concatenate TED CSV files for the given years.

    Args:
        years: Which years to load (default: 2014–2023).
        filter_target_countries: If True, keep only DE/DK/RO/HU rows.
        dtype: pandas dtype backend (``"numpy_nullable"`` or ``None``).

    Returns:
        Combined DataFrame with ``KEEP_COLUMNS`` columns (if present).
    """
    if years is None:
        years = YEARS

    frames: List[pd.DataFrame] = []
    for year in years:
        fpath = DATA_DIR / f"ted_{year}.csv"
        if not fpath.exists():
            print(f"[WARN] File not found: {fpath} — skipping")
            continue

        df = pd.read_csv(
            fpath,
            dtype_backend=dtype,
            low_memory=False,
        )
        # Keep only the columns that exist in the file
        available = [c for c in KEEP_COLUMNS if c in df.columns]
        df = df[available]
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    if filter_target_countries:
        combined = combined[
            combined["ISO_COUNTRY_CODE"].isin(TARGET_COUNTRIES.keys())
        ]

    return combined


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def pct_of(part: float, whole: float, digits: int = 2) -> str:
    """Return a formatted percentage string, or ``"-"`` if whole is 0."""
    if whole == 0:
        return "-"
    return f"{(part / whole) * 100:.{digits}f}%"


def print_header(title: str) -> None:
    """Print a centred section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print(f"\n--- {title} ---")


# ---------------------------------------------------------------------------
# Quick initial peek (usable from any notebook / interactive session)
# ---------------------------------------------------------------------------

def peek(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Return the first *n* rows — convenience for interactive use."""
    return df.head(n)
