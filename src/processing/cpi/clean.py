"""
clean.py — CPI-specific cleaning functions.

All functions follow a pure-function pattern (DataFrame → DataFrame) with
no side effects.  Constants are imported from ``config.py``.
"""

from __future__ import annotations

import logging
from typing import Optional, Set

import pandas as pd

from src.processing import config

logger = logging.getLogger(__name__)

# ===================================================================
# CPI — Cleaning function
# ===================================================================


def clean_cpi(df: pd.DataFrame, target_alpha3: Optional[Set[str]] = None) -> pd.DataFrame:
    """Clean the raw CPI DataFrame.

    Steps:
        1. Filter rows to target Alpha-3 codes.
        2. Restrict to the years 2014–2023.
        3. Rename ``iso3`` → ``country_iso3``, ``score`` → ``cpi_score``.
        4. Keep only ``config.CPI_KEEP_COLUMNS``.

    Args:
        df: Raw CPI DataFrame with ```iso3```, ``year``, ```score``` columns.
        target_alpha3: Set of Alpha-3 codes to keep. Defaults to ``{"DEU", "DNK", "HUN", "ROU"}``.

    Returns:
        Cleaned CPI DataFrame.
    """
    if target_alpha3 is None:
        target_alpha3 = {"DEU", "DNK", "HUN", "ROU"}

    before = len(df)
    df = df[df["iso3"].isin(target_alpha3)].copy()
    df = df[df["year"].between(2014, 2023)]
    df = df.rename(columns={"iso3": "country_iso3", "score": "cpi_score"})
    df = df[config.CPI_KEEP_COLUMNS]
    after = len(df)
    logger.info("clean_cpi: %d -> %d rows (%.1f%% kept)", before, after,
                100.0 * after / before if before else 0.0)
    return df
