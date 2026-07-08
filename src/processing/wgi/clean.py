"""
clean.py — WGI-specific cleaning functions.

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
# WGI — Cleaning function
# ===================================================================


def clean_wgi(df: pd.DataFrame, target_alpha3: Optional[Set[str]] = None) -> pd.DataFrame:
    """Clean the raw WGI DataFrame.

    Steps:
        1. Filter rows to target Alpha-3 codes.
        2. Restrict to the years 2014–2023.
        3. Keep only ``config.WGI_KEEP_COLUMNS``.
        4. Verify row count (expect 40 = 4 countries × 10 years).

    Args:
        df: Raw WGI DataFrame with ``country_iso3``, ``year``, and 6 governance columns.
        target_alpha3: Set of Alpha-3 codes to keep. Defaults to ``{"DEU", "DNK", "HUN", "ROU"}``.

    Returns:
        Cleaned WGI DataFrame.
    """
    if target_alpha3 is None:
        target_alpha3 = {"DEU", "DNK", "HUN", "ROU"}

    before = len(df)
    df = df[df["country_iso3"].isin(target_alpha3)].copy()
    df = df[df["year"].between(2014, 2023)]
    df = df[config.WGI_KEEP_COLUMNS]

    after = len(df)
    expected = 40  # 4 countries × 10 years
    if after != expected:
        logger.warning("clean_wgi: expected %d rows after filter, got %d", expected, after)
    logger.info("clean_wgi: %d -> %d rows (%.1f%% kept)", before, after,
                100.0 * after / before if before else 0.0)
    return df
