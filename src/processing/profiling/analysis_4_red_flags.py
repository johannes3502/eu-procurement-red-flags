"""
analysis_4_red_flags.py — Red Flag definitions vs data availability.

Key questions:
    1. B_ACCELERATED non-NULL rate per year — is Flag 4 viable?
    2. B_AWARDED_TO_A_GROUP availability per year — Flag 5 status.
    3. NUMBER_OFFERS availability for Flag 1 and Flag 6.
    4. Flag 6 simulation: how many rows survive after clipping + offer filter?
    5. Flag 7 (lot fragmentation): NUMBER_AWARDS / LOTS_NUMBER analysis.
    6. Combined flag impact: how many rows survive each flag individually
       and in combination?

Output: console tables + ``analysis_4_red_flags_summary.csv``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.profiling.analysis_utils import (
    OUTPUT_DIR,
    YEARS,
    TARGET_COUNTRIES,
    load_ted_data,
    pct_of,
    print_header,
    print_subsection,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_big(n: int) -> str:
    return f"{n:,}"


def _bin_yn(series: pd.Series) -> Dict[str, int]:
    """Count Y / N / other values in a boolean-flag column."""
    counts = {"Y": 0, "N": 0, "other": 0, "NULL": 0}
    for v in series:
        if pd.isna(v):
            counts["NULL"] += 1
        elif v == "Y":
            counts["Y"] += 1
        elif v == "N":
            counts["N"] += 1
        else:
            counts["other"] += 1
    return counts


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def run() -> None:
    """Execute all red-flag analyses and print results."""
    print_header("Analysis 4: Red Flag Definitions vs Data Availability")

    # ---- Load data --------------------------------------------------------
    # Need additional columns beyond KEEP_COLUMNS for full red flag analysis
    extra_cols = ["LOTS_NUMBER", "NUMBER_AWARDS", "VALUE_EURO"]
    # We already have most from KEEP_COLUMNS in analysis_utils; load normally
    # but ensure we have everything
    print("Loading TED data (target countries)...")
    df = load_ted_data(years=YEARS, filter_target_countries=True)
    print(f"  Total rows: {_fmt_big(len(df))}")

    # ---- 0. Column availability check ------------------------------------
    print_subsection("0. Column availability")

    flag_cols = {
        "B_ACCELERATED": "Flag 4 (accelerated procedure)",
        "B_AWARDED_TO_A_GROUP": "Flag 5 (awarded to group)",
        "NUMBER_OFFERS": "Flags 1 & 6 (offers)",
        "AWARD_VALUE_EURO": "Flags 2 & 6 (award value)",
        "VALUE_EURO": "Flags 2 & 3 (estimate value)",
        "LOTS_NUMBER": "Flag 7 (lot fragmentation)",
        "NUMBER_AWARDS": "Flag 7 (lot fragmentation)",
    }
    for col, label in flag_cols.items():
        present = col in df.columns
        null_rate = df[col].isna().mean() * 100 if present else 100.0
        print(f"  {col:25s}  present={'YES' if present else 'NO'}  NULL={null_rate:.1f}%  ({label})")

    # ---- 1. B_ACCELERATED (Flag 4) ---------------------------------------
    print_subsection("1. B_ACCELERATED (Red Flag 4 — accelerated procedure)")

    if "B_ACCELERATED" in df.columns:
        for year in YEARS:
            dfy = df[df["YEAR"] == year]
            if len(dfy) == 0:
                continue
            counts = _bin_yn(dfy["B_ACCELERATED"])
            non_null = counts["Y"] + counts["N"] + counts["other"]
            print(f"  {year}: non-NULL={_fmt_big(non_null)} ({pct_of(non_null, len(dfy))})  "
                  f"Y={_fmt_big(counts['Y'])}  N={_fmt_big(counts['N'])}  "
                  f"NULL={_fmt_big(counts['NULL'])} ({pct_of(counts['NULL'], len(dfy))})")

        # Overall
        counts_all = _bin_yn(df["B_ACCELERATED"])
        print(f"\n  ALL YEARS: "
              f"Y={_fmt_big(counts_all['Y'])}  "
              f"N={_fmt_big(counts_all['N'])}  "
              f"NULL={_fmt_big(counts_all['NULL'])} "
              f"({pct_of(counts_all['NULL'], len(df))})")
        print(f"  VERDICT: Flag 4 data is "
              f"{'USABLE' if counts_all['NULL'] / len(df) < 0.50 else 'LARGELY MISSING (>50%)'} "
              f"— consider dropping this flag or treating NULL as 'N'.")
    else:
        print("  B_ACCELERATED column not found — Flag 4 NOT available.")

    # ---- 2. B_AWARDED_TO_A_GROUP (Flag 5) --------------------------------
    print_subsection("2. B_AWARDED_TO_A_GROUP (Red Flag 5 — group award)")

    if "B_AWARDED_TO_A_GROUP" in df.columns:
        for year in YEARS:
            dfy = df[df["YEAR"] == year]
            if len(dfy) == 0:
                continue
            counts = _bin_yn(dfy["B_AWARDED_TO_A_GROUP"])
            non_null = counts["Y"] + counts["N"] + counts["other"]
            print(f"  {year}: non-NULL={_fmt_big(non_null)} ({pct_of(non_null, len(dfy))})  "
                  f"Y={_fmt_big(counts['Y'])}  N={_fmt_big(counts['N'])}  "
                  f"NULL={_fmt_big(counts['NULL'])} ({pct_of(counts['NULL'], len(dfy))})")

        counts_all = _bin_yn(df["B_AWARDED_TO_A_GROUP"])
        print(f"\n  ALL YEARS: "
              f"Y={_fmt_big(counts_all['Y'])}  "
              f"N={_fmt_big(counts_all['N'])}  "
              f"NULL={_fmt_big(counts_all['NULL'])} "
              f"({pct_of(counts_all['NULL'], len(df))})")
        print(f"  VERDICT: Flag 5 data availability is "
              f"{'ADEQUATE' if counts_all['NULL'] / len(df) < 0.50 else 'POOR (>50% NULL)'}.")
    else:
        print("  B_AWARDED_TO_A_GROUP column not found — Flag 5 NOT available.")

    # ---- 3. NUMBER_OFFERS (Flags 1 & 6) ----------------------------------
    print_subsection("3. NUMBER_OFFERS (Red Flags 1 & 6 — offer count)")

    if "NUMBER_OFFERS" in df.columns:
        for year in YEARS:
            dfy = df[df["YEAR"] == year]
            if len(dfy) == 0:
                continue
            null_count = dfy["NUMBER_OFFERS"].isna().sum()
            non_null = len(dfy) - null_count
            print(f"  {year}: non-NULL={_fmt_big(non_null)} ({pct_of(non_null, len(dfy))})  "
                  f"NULL={_fmt_big(null_count)} ({pct_of(null_count, len(dfy))})")

        # Distribution of NUMBER_OFFERS
        offers = df["NUMBER_OFFERS"].dropna()
        if len(offers) > 0:
            print(f"\n  NUMBER_OFFERS distribution (non-NULL, n={_fmt_big(len(offers))}):")
            for threshold in [1, 2, 3, 5, 10]:
                above = (offers >= threshold).sum()
                print(f"    >= {threshold:2d}: {_fmt_big(above)}  ({pct_of(above, len(offers))})")

            # 0 offers (suspicious)
            zero_offers = (offers == 0).sum()
            print(f"    == 0:     {_fmt_big(zero_offers)}  ({pct_of(zero_offers, len(offers))})")
            print(f"    max:      {int(offers.max())}")
    else:
        print("  NUMBER_OFFERS column not found.")

    # ---- 4. Flag 6 simulation --------------------------------------------
    print_subsection("4. Flag 6 simulation (single bidder + high value)")

    if "NUMBER_OFFERS" in df.columns and "AWARD_VALUE_EURO" in df.columns:
        # Need both columns non-NULL
        flag6_base = df["NUMBER_OFFERS"].notna() & df["AWARD_VALUE_EURO"].notna()
        flag6_df = df[flag6_base].copy()
        print(f"  Rows with both NUMBER_OFFERS and AWARD_VALUE_EURO: "
              f"{_fmt_big(len(flag6_df))} ({pct_of(len(flag6_df), len(df))})")

        # Flag 6 condition: NUMBER_OFFERS == 1 AND AWARD_VALUE_EURO > p95
        # Compute p95 per year (or global — let's do per-year for accuracy)
        flag6_hits: List[int] = []
        for year in YEARS:
            dfy = flag6_df[flag6_df["YEAR"] == year]
            if len(dfy) < 100:
                continue
            p95 = np.percentile(dfy["AWARD_VALUE_EURO"].dropna(), 95)
            hits = (dfy["NUMBER_OFFERS"] <= 1) & (dfy["AWARD_VALUE_EURO"] > p95)
            flag6_hits.append(hits.sum())
            print(f"  {year}: p95=€{p95:,.0f}  "
                  f"single-bidder+high-value rows: {_fmt_big(hits.sum())} "
                  f"({pct_of(hits.sum(), len(dfy))})")

        total_flag6 = sum(flag6_hits)
        print(f"\n  Total Flag 6 rows (approx, per-year p95): {_fmt_big(total_flag6)}")

    # ---- 5. Flag 7 — Lot fragmentation ----------------------------------
    print_subsection("5. Flag 7 — Lot fragmentation (NUMBER_AWARDS / LOTS_NUMBER)")

    if "NUMBER_AWARDS" in df.columns and "LOTS_NUMBER" in df.columns:
        # Both present, compute ratio
        valid = df["NUMBER_AWARDS"].notna() & df["LOTS_NUMBER"].notna()
        valid_df = df[valid].copy()
        print(f"  Rows with both NUMBER_AWARDS and LOTS_NUMBER: "
              f"{_fmt_big(len(valid_df))} ({pct_of(len(valid_df), len(df))})")

        if len(valid_df) > 0:
            valid_df["lot_ratio"] = valid_df["NUMBER_AWARDS"] / valid_df["LOTS_NUMBER"].replace(0, np.nan)
            ratio = valid_df["lot_ratio"].dropna()

            print(f"\n  Lot ratio distribution (n={_fmt_big(len(ratio))}):")
            for pct in [5, 25, 50, 75, 95]:
                print(f"    p{pct}: {np.percentile(ratio, pct):.4f}")

            # High fragmentation: ratio < 0.5 (awards cover < half of lots)
            high_frag = (ratio < 0.5).sum()
            print(f"\n  Ratio < 0.5 (high fragmentation):  "
                  f"{_fmt_big(high_frag)}  ({pct_of(high_frag, len(ratio))})")
            print(f"  Ratio = 1.0 (no fragmentation):     "
                  f"{_fmt_big((ratio == 1.0).sum())}  ({pct_of((ratio == 1.0).sum(), len(ratio))})")
            print(f"  Ratio > 1.0 (more awards than lots): "
                  f"{_fmt_big((ratio > 1.0).sum())}  ({pct_of((ratio > 1.0).sum(), len(ratio))})")

        # Also check individual column NULL rates
        print(f"\n  LOTS_NUMBER NULL:    "
              f"{_fmt_big(df['LOTS_NUMBER'].isna().sum())} "
              f"({pct_of(df['LOTS_NUMBER'].isna().sum(), len(df))})")
        print(f"  NUMBER_AWARDS NULL:  "
              f"{_fmt_big(df['NUMBER_AWARDS'].isna().sum())} "
              f"({pct_of(df['NUMBER_AWARDS'].isna().sum(), len(df))})")
    else:
        missing = []
        if "NUMBER_AWARDS" not in df.columns:
            missing.append("NUMBER_AWARDS")
        if "LOTS_NUMBER" not in df.columns:
            missing.append("LOTS_NUMBER")
        print(f"  Cannot compute: missing columns {missing}")

    # ---- 6. Combined flag matrix -----------------------------------------
    print_subsection("6. Flags that survive data-availability filter")

    # Build a boolean matrix: row × flag, showing which flags can be
    # computed for each row (i.e., required columns are non-NULL).
    flags_available = pd.DataFrame(index=df.index)

    # Flag 1: single bidder — needs NUMBER_OFFERS
    flags_available["F1_single_bidder"] = df["NUMBER_OFFERS"].notna()

    # Flag 2: estimate vs award — needs VALUE_EURO + AWARD_VALUE_EURO
    flags_available["F2_discrepancy"] = (
        df["VALUE_EURO"].notna() & df["AWARD_VALUE_EURO"].notna()
    )

    # Flag 3: direct award — needs TOP_TYPE
    if "TOP_TYPE" in df.columns:
        flags_available["F3_direct_award"] = df["TOP_TYPE"].notna()
    else:
        flags_available["F3_direct_award"] = False

    # Flag 4: accelerated — needs B_ACCELERATED
    if "B_ACCELERATED" in df.columns:
        flags_available["F4_accelerated"] = df["B_ACCELERATED"].notna()
    else:
        flags_available["F4_accelerated"] = False

    # Flag 5: group award — needs B_AWARDED_TO_A_GROUP
    if "B_AWARDED_TO_A_GROUP" in df.columns:
        flags_available["F5_group"] = df["B_AWARDED_TO_A_GROUP"].notna()
    else:
        flags_available["F5_group"] = False

    # Flag 6: single bidder + high value — needs NUMBER_OFFERS + AWARD_VALUE_EURO
    flags_available["F6_single_high"] = (
        df["NUMBER_OFFERS"].notna() & df["AWARD_VALUE_EURO"].notna()
    )

    # Flag 7: lot fragmentation — needs NUMBER_AWARDS + LOTS_NUMBER
    if "NUMBER_AWARDS" in df.columns and "LOTS_NUMBER" in df.columns:
        flags_available["F7_fragmented"] = (
            df["NUMBER_AWARDS"].notna() & df["LOTS_NUMBER"].notna()
        )
    else:
        flags_available["F7_fragmented"] = False

    # Print matrix summary
    total = len(df)
    print(f"{'Flag':25s} {'Rows computable':>15s}  {'%':>7s}")
    print("-" * 55)
    for col in flags_available.columns:
        n = flags_available[col].sum()
        print(f"  {col:23s} {_fmt_big(n):>15s}  {pct_of(n, total):>7s}")

    # How many flags can be computed per row?
    n_flags = flags_available.sum(axis=1)
    print(f"\n  Flags computable per row:")
    for k in range(len(flags_available.columns) + 1):
        count = (n_flags == k).sum()
        if count > 0:
            print(f"    {k} flags: {_fmt_big(count)} rows  ({pct_of(count, total)})")

    # ---- 7. Per-year flag availability summary ---------------------------
    print_subsection("7. Yearly summary — flags computable")

    yearly_summary: List[Dict] = []
    for year in YEARS:
        dfy = df[df["YEAR"] == year]
        if len(dfy) == 0:
            continue
        row: Dict = {"year": year, "total_rows": len(dfy)}
        y_flags = flags_available.loc[dfy.index]

        for col in y_flags.columns:
            n = y_flags[col].sum()
            row[col] = n
            row[f"{col}_pct"] = round(n / len(dfy) * 100, 2)

        row["avg_flags"] = round(y_flags.sum(axis=1).mean(), 2)
        yearly_summary.append(row)

    yearly_df = pd.DataFrame(yearly_summary)
    print(yearly_df[["year", "total_rows", "avg_flags"]].to_string(index=False))

    # ---- Export -----------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "analysis_4_red_flags_summary.csv"
    yearly_df.to_csv(out_path, index=False)
    print(f"\n  Summary exported to: {out_path}")


if __name__ == "__main__":
    run()
