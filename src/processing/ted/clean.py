"""
clean.py — TED-specific cleaning functions.

All functions follow a pure-function pattern (DataFrame → DataFrame) with
no side effects.  Constants are imported from ``config.py``, shared helpers
from ``utils.py``.

Functions are prefixed ``clean_ted_*`` to avoid name collisions with
CPI/WGI cleaning functions in sibling modules.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.processing import config
from src.processing import utils

logger = logging.getLogger(__name__)


# ===================================================================
# TED — Cleaning functions
# ===================================================================


def clean_ted_filter_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict the DataFrame to the 4 target countries (DE, DK, RO, HU).

    Uses ``utils.load_target_alpha2_set()`` which reads ``lookup_countries.csv``.

    Args:
        df: Raw TED DataFrame with ``ISO_COUNTRY_CODE`` column.

    Returns:
        Filtered DataFrame (rows with non‑target or NULL country removed).
    """
    before = len(df)
    target = utils.load_target_alpha2_set()
    mask = df["ISO_COUNTRY_CODE"].isin(target)
    df = df[mask].copy()
    after = len(df)
    logger.info(
        "clean_ted_filter_countries: %d → %d rows (%.1f%% kept)",
        before,
        after,
        100.0 * after / before if before else 0.0,
    )
    return df


def clean_ted_dedup(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate on ``ID_AWARD`` with a CORRECTIONS-aware strategy.

    Sort by ``(ID_AWARD, CORRECTIONS)`` with ``NA`` first, then keep the last
    row per ``ID_AWARD``.  Drops the ``CORRECTIONS`` column afterwards.

    Args:
        df: DataFrame with ``ID_AWARD`` and optionally ``CORRECTIONS``.

    Returns:
        Deduplicated DataFrame (no ``CORRECTIONS`` column).
    """
    before = len(df)

    if "CORRECTIONS" not in df.columns:
        logger.warning(
            "CORRECTIONS column missing — falling back to simple "
            "drop_duplicates(keep='first')"
        )
        df = df.drop_duplicates(subset=["ID_AWARD"], keep="first").copy()
    else:
        df = df.sort_values(["ID_AWARD", "CORRECTIONS"], na_position="first")
        df = df.drop_duplicates(subset=["ID_AWARD"], keep="last")
        df = df.drop(columns=["CORRECTIONS"])

    after = len(df)
    logger.info(
        "clean_ted_dedup: %d → %d rows (%.1f%% removed)",
        before,
        after,
        100.0 * (before - after) / before if before else 0.0,
    )

    if "YEAR" in df.columns:
        for year, grp in df.groupby("YEAR"):
            logger.debug("  Year %s: %d rows after dedup", year, len(grp))

    return df


def clean_ted_remove_sentinels(
    df: pd.DataFrame,
    sentinel_threshold: float = config.SENTINEL_THRESHOLD,
) -> pd.DataFrame:
    """Remove sentinel (placeholder) values from ``AWARD_VALUE_EURO``.

    Sentinel values are set to NaN — genuine award amounts, even extreme ones,
    are kept as-is.  This function does NOT apply percentile clipping; real
    values are not modified.

    Args:
        df: DataFrame with ``AWARD_VALUE_EURO``.
        sentinel_threshold: Threshold for sentinel removal (default €1T; the
            actual sentinel value is exactly €10T — 62 rows, all DE 2016–2017).

    Returns:
        DataFrame with sentinel values set to NaN.
    """
    sentinel_mask = df["AWARD_VALUE_EURO"] >= sentinel_threshold
    n_sentinels = sentinel_mask.sum()
    if n_sentinels > 0:
        logger.warning(
            "Removing %d sentinel rows (AWARD_VALUE_EURO >= €%sT)",
            n_sentinels,
            int(sentinel_threshold // 1_000_000_000_000),
        )
        df = df.copy()
        df.loc[sentinel_mask, "AWARD_VALUE_EURO"] = np.nan
        logger.info(
            "clean_ted_remove_sentinels: %d sentinel values removed — "
            "genuine amounts left unchanged",
            n_sentinels,
        )
    else:
        logger.info(
            "clean_ted_remove_sentinels: no sentinel values found"
        )

    return df


def clean_ted_parse_winner(df: pd.DataFrame) -> pd.DataFrame:
    """Parse multi-value ``WIN_COUNTRY_CODE`` using the "any segment match" rule.

    Splits on ``---``, returns the first target-country Alpha-2 code found.

    Args:
        df: DataFrame with ``WIN_COUNTRY_CODE`` column.

    Returns:
        DataFrame with:
            - ``winner_country_raw`` — original ``WIN_COUNTRY_CODE``
            - ``winner_country`` — parsed Alpha-2 code (or None)
        ``WIN_COUNTRY_CODE`` is dropped.
    """
    if "WIN_COUNTRY_CODE" not in df.columns:
        logger.warning("WIN_COUNTRY_CODE not found — skipping parse_winner_country")
        return df

    target = utils.load_target_alpha2_set()

    def _extract_winner(raw: object) -> Optional[str]:
        """Return first target-country Alpha-2 found, or None."""
        if pd.isna(raw):
            return None
        segments = str(raw).split("---")
        for segment in segments:
            code = segment.strip()
            if code in target:
                return code
        return None  # has codes, but none are target countries

    df = df.copy()
    df["winner_country_raw"] = df["WIN_COUNTRY_CODE"]
    df["winner_country"] = df["WIN_COUNTRY_CODE"].apply(_extract_winner)
    df = df.drop(columns=["WIN_COUNTRY_CODE"])

    parsed_count = df["winner_country"].notna().sum()
    total = len(df)
    logger.info(
        "clean_ted_parse_winner: %d / %d rows parsed (%.1f%%)",
        parsed_count,
        total,
        100.0 * parsed_count / total if total else 0.0,
    )
    return df


def clean_ted_normalize_cpv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize CPV codes to exactly 8 digits, rename to ``cpv_code``.

    Handles two sources of CPV representation in raw TED:
    - ``int64`` years (most years): ``3110000`` → ``'03110000'``
    - ``float64`` years (2014, 2016, 2017 — NaN forces float dtype):
      ``3110000.0`` → ``'3110000'`` → ``'03110000'``

    Drops rows where CPV is NULL (cannot normalise).

    Args:
        df: DataFrame with ``CPV`` column.

    Returns:
        DataFrame with ``cpv_code`` (8-char zero-padded string).
        Original ``CPV`` column is dropped.
    """
    if "CPV" not in df.columns:
        logger.warning("CPV column not found — skipping normalize_cpv")
        return df

    before = len(df)
    df = df.copy()
    df = df.dropna(subset=["CPV"])
    after = len(df)
    if before != after:
        logger.info("clean_ted_normalize_cpv: dropped %d rows with NULL CPV", before - after)

    # Step 1: convert to string — int64 → "3110000", float64 → "3110000.0"
    raw_str = df["CPV"].astype(str)

    # Step 2: count how many had float-representation (informational)
    float_count = raw_str.str.contains(r"\.", regex=True).sum()
    if float_count > 0:
        logger.info(
            "clean_ted_normalize_cpv: %d CPVs had float representation (.0) — stripping decimals",
            float_count,
        )

    # Step 3: strip trailing ".0" from float years, then zero-pad to 8 digits
    df["cpv_code"] = raw_str.str.replace(r"\.0+$", "", regex=True).str.zfill(8)
    df = df.drop(columns=["CPV"])

    # Sanity check: all codes should now be exactly 8 chars
    invalid = df[df["cpv_code"].str.len() != 8]
    if len(invalid) > 0:
        logger.warning(
            "clean_ted_normalize_cpv: %d codes still not 8 digits after fix "
            "(sample: %s)",
            len(invalid),
            invalid["cpv_code"].unique()[:10].tolist(),
        )

    logger.info(
        "clean_ted_normalize_cpv: %d rows with valid cpv_code (%d had float repr)",
        len(df),
        float_count,
    )
    return df


def clean_ted_select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns needed in the fact table.

    The column list is defined in ``config.TED_KEEP_COLUMNS`` (15 columns).

    Args:
        df: DataFrame after all cleaning steps.

    Returns:
        Narrow DataFrame with exactly the columns that exist (missing ones skipped).
    """
    available = [c for c in config.TED_KEEP_COLUMNS if c in df.columns]
    missing = [c for c in config.TED_KEEP_COLUMNS if c not in df.columns]
    if missing:
        logger.warning(
            "clean_ted_select_columns: %d expected columns missing: %s",
            len(missing),
            missing,
        )

    df = df[available].copy()
    logger.info(
        "clean_ted_select_columns: %d columns kept (expecting %d)",
        len(available),
        len(config.TED_KEEP_COLUMNS),
    )
    return df


# ===================================================================
# TED — Red Flag computation
# ===================================================================


def compute_red_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Red Flags F1–F7 (F4 dropped) and compound combinations.

    Flags computed (per Section 4.2.1 of the Data Preparation Plan):

        F1  — Single-Bidder:                  NUMBER_OFFERS == 1
        F2  — Estimate/Award Discrepancy:     VALUE_EURO / AWARD_VALUE_EURO > 10.0
        F3  — No Prior Call:                  TOP_TYPE IN ('NIC', 'AWP')
        F5  — Award to Group:                 B_AWARDED_TO_A_GROUP == 'Y'  (2014-2015: hard False)
        F6  — Single-Bidder + High Value:     F1 AND AWARD_VALUE_EURO > per-year-p95
        F7  — Lot Fragmentation:              NUMBER_AWARDS < LOTS_NUMBER * 0.5

    Compound combinations (per Section 4.2.2):

        comb_single_discrepancy  = F1 AND F2
        comb_single_non_open     = F1 AND (TOP_TYPE != 'OPE')
        comb_no_call_high_value  = F3 AND F6
        comb_frag_single         = F7 AND F1

    ``F4 is DROPPED`` (99.16 % NULL) — column not created.

    Args:
        df: Cleaned DataFrame with at least ``YEAR``, ``AWARD_VALUE_EURO``,
            ``VALUE_EURO``, ``NUMBER_OFFERS``, ``TOP_TYPE``,
            ``B_AWARDED_TO_A_GROUP``, ``LOTS_NUMBER``, ``NUMBER_AWARDS``.

    Returns:
        DataFrame with 6 new flag columns (F1, F2, F3, F5, F6, F7)
        and 4 new compound columns.
    """
    df = df.copy()

    # ---- Precompute per-year p95 for F6 (uses already-cleaned AWARD_VALUE_EURO) ----
    p95_map = utils.compute_p95_per_year(df, col="AWARD_VALUE_EURO")

    # ---- F1: Single-Bidder ----
    df["F1"] = df["NUMBER_OFFERS"].fillna(0).astype(int) == 1

    # ---- F2: Estimate/Award Discrepancy ----
    a_notna = df["AWARD_VALUE_EURO"].notna() & (df["AWARD_VALUE_EURO"] != 0)
    v_notna = df["VALUE_EURO"].notna()
    ratio = np.where(
        a_notna & v_notna,
        df["VALUE_EURO"].fillna(0) / df["AWARD_VALUE_EURO"],
        0.0,
    )
    df["F2"] = ratio > config.F2_DISCREPANCY_RATIO

    # ---- F3: No Prior Call ----
    df["F3"] = df["TOP_TYPE"].fillna("").isin(["NIC", "AWP"])

    # ---- F4: DROPPED (not created) ----

    # ---- F5: Award to Group ----
    is_early = df["YEAR"].isin(config.F5_EXCLUDE_YEARS)
    df["F5"] = False
    if is_early.any():
        logger.info(
            "F5: %d rows in %s set to False (insufficient data coverage)",
            is_early.sum(),
            config.F5_EXCLUDE_YEARS,
        )
    later = ~is_early
    if later.any():
        df.loc[later, "F5"] = df.loc[later, "B_AWARDED_TO_A_GROUP"].fillna("N") == "Y"

    # ---- F6: Single-Bidder + High Value ----
    df["_p95"] = df["YEAR"].map(p95_map)
    df["F6"] = df["F1"] & (df["AWARD_VALUE_EURO"].fillna(0) > df["_p95"])
    df = df.drop(columns=["_p95"])

    # ---- F7: Lot Fragmentation ----
    n_aw = df["NUMBER_AWARDS"].fillna(999_999).astype(float)
    n_lo = df["LOTS_NUMBER"].fillna(0).astype(float)
    df["F7"] = n_aw < n_lo * 0.5

    # ---- Compound combinations ----
    df["comb_single_discrepancy"] = df["F1"] & df["F2"]
    df["comb_single_non_open"] = df["F1"] & (df["TOP_TYPE"].fillna("") != "OPE")
    df["comb_no_call_high_value"] = df["F3"] & df["F6"]
    df["comb_frag_single"] = df["F7"] & df["F1"]

    # ---- Log summary ----
    total = len(df)
    for flag in ["F1", "F2", "F3", "F5", "F6", "F7"]:
        flagged = df[flag].sum()
        logger.info(
            "compute_red_flags: %-6s = %d / %d (%.1f%%)",
            flag,
            flagged,
            total,
            100.0 * flagged / total if total else 0.0,
        )

    for combo in [
        "comb_single_discrepancy",
        "comb_single_non_open",
        "comb_no_call_high_value",
        "comb_frag_single",
    ]:
        flagged = df[combo].sum()
        logger.info(
            "compute_red_flags: %-25s = %d / %d (%.1f%%)",
            combo,
            flagged,
            total,
            100.0 * flagged / total if total else 0.0,
        )

    return df
