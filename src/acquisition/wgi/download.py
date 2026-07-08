"""
WGI download module — uses wbgapi (World Bank API wrapper).

Downloads Worldwide Governance Indicators for specified countries and years.
Six governance dimensions are fetched in a single API call.
The raw MultiIndex DataFrame is reshaped into a flat, CSV-ready format.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import wbgapi as wb
from wbgapi import APIResponseError

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------

# Korrekte Series-Codes für WGI (mit .EST)
WGI_INDICATOR_CODES = [
    'GOV_WGI_CC.EST',   # Control of Corruption
    'GOV_WGI_GE.EST',   # Government Effectiveness
    'GOV_WGI_PV.EST',   # Political Stability
    'GOV_WGI_RL.EST',   # Rule of Law
    'GOV_WGI_RQ.EST',   # Regulatory Quality
    'GOV_WGI_VA.EST',   # Voice and Accountability
]

# Lesbare Namen in gleicher Reihenfolge
READABLE_NAMES = [
    'control_of_corruption',
    'government_effectiveness',
    'political_stability',
    'rule_of_law',
    'regulatory_quality',
    'voice_accountability',
]

# Mapping für späteres Umbenennen
INDICATOR_MAP = dict(zip(WGI_INDICATOR_CODES, READABLE_NAMES))

# Weltbank Datenbank-ID für WGI
WGI_DB_ID = 3

# Rate Limiting (Sekunden zwischen Calls)
WGI_API_DELAY = 0.3

# Project root, resolved from this module (src/data_aquisition/wgi/download.py):
#   4 × .parent → project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Output
WGI_DIR = _PROJECT_ROOT / "data" / "raw" / "wgi"
WGI_FILENAME = "wgi_raw.csv"

DEFAULT_COUNTRIES = ["DEU", "DNK", "HUN", "ROU"]


def download_wgi(
    force: bool = False,
    countries: Optional[list[str]] = None,
    years: Optional[range] = None,
) -> bool:
    """
    Download WGI data using wbgapi and save as a flat CSV.

    Fetches all six governance indicators in a single API call (db=3).
    The raw MultiIndex DataFrame is reshaped (stack + pivot) into a flat
    format with readable column names.

    Parameters
    ----------
    force : bool
        Re-download even if the file exists.
    countries : list[str] or None
        ISO Alpha-3 country codes. Defaults to ['DEU', 'DNK', 'HUN', 'ROU'].
    years : range or None
        Year range. Defaults to range(2014, 2024) → 2014–2023.

    Returns
    -------
    bool
        True on success (or file already exists). False on any error.
    """
    if countries is None:
        countries = DEFAULT_COUNTRIES
    if years is None:
        years = range(2014, 2024)

    dest_dir = WGI_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / WGI_FILENAME

    if dest.exists() and not force:
        logger.info("WGI already exists -- skipped (%s)", dest)
        return True

    logger.info(
        "Fetching WGI data (db=%s) for %d countries, years %d-%d …",
        WGI_DB_ID, len(countries), years.start, years.stop - 1,
    )

    try:
        # 1. Rohdaten abrufen (MultiIndex mit Jahren als Spalten)
        df_raw = wb.data.DataFrame(
            WGI_INDICATOR_CODES,
            economy=countries,
            time=years,
            db=WGI_DB_ID,
            labels=False,
            numericTimeKeys=True,
        )
        time.sleep(WGI_API_DELAY)
    except APIResponseError as exc:
        logger.error("WGI API call failed: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error during WGI download: %s", exc)
        return False

    if df_raw is None or df_raw.empty:
        logger.warning("WGI returned empty DataFrame — API may be unavailable")
        return False

    # 2. Reshaping: MultiIndex → flach
    df_stacked = df_raw.stack().reset_index()
    df_stacked.columns = ['country_iso3', 'indicator', 'year', 'value']

    df_wide = df_stacked.pivot_table(
        index=['country_iso3', 'year'],
        columns='indicator',
        values='value',
    ).reset_index()

    # 3. Spalten lesbar umbenennen
    df_wide.rename(columns=INDICATOR_MAP, inplace=True)

    # 4. Sicherstellen, dass alle sechs Spalten existieren
    for col in READABLE_NAMES:
        if col not in df_wide.columns:
            df_wide[col] = pd.NA

    # 5. Sortieren
    df_wide.sort_values(['country_iso3', 'year'], inplace=True)

    # 6. Auf die exakt gewünschten Jahre filtern
    year_list = list(years)
    df_wide = df_wide[df_wide["year"].isin(year_list)]

    # 7. Speichern
    df_wide.to_csv(dest, index=False, encoding="utf-8")
    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info(
        "WGI saved -- %.2f MB, %d rows -> %s",
        size_mb, len(df_wide), dest,
    )
    return True
