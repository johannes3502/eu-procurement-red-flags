"""
analysis_2_monetary.py — Extreme monetary values & clipping threshold.

Key questions:
    1. AWARD_VALUE_EURO distribution per year — percentiles (90/95/99/99.9).
    2. Identify extreme outlier clusters (> 10¹⁰, > 10¹¹, > 10¹² EUR).
    3. VALUE_EURO vs AWARD_VALUE_EURO — which is more reliable?
    4. Recommend clipping threshold with row-impact quantification.
    5. Distribution comparison (should AWARD_VALUE_EURO be authoritative?).

Output: console tables + ``analysis_2_monetary_summary.csv``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.profiling.analysis_utils import (
    OUTPUT_DIR,
    YEARS,
    load_ted_data,
    pct_of,
    print_header,
    print_subsection,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Scientific notation thresholds (EUR)
B_10  = 10_000_000_000      # 10^10
B_100 = 100_000_000_000     # 10^11
T_1   = 1_000_000_000_000   # 10^12

# Candidate clipping percentiles
CLIP_PERCENTILES = [95, 99, 99.5, 99.9]


def _fmt_val(val: float) -> str:
    """Format monetary value in human-readable form."""
    if pd.isna(val):
        return "NULL"
    abs_val = abs(val)
    if abs_val >= T_1:
        return f"€{val / T_1:.2f} T"
    if abs_val >= B_100:
        return f"€{val / B_100:.2f} B"
    if abs_val >= 1_000_000:
        return f"€{val / 1_000_000:.2f} M"
    return f"€{val:,.0f}"


def _fmt_big(n: int) -> str:
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run() -> None:
    """Execute all monetary analyses and print results."""
    print_header("Analysis 2: Extreme Monetary Values & Clipping Threshold")

    # ---- Load data --------------------------------------------------------
    print("Loading TED data (target countries)...")
    df = load_ted_data(years=YEARS, filter_target_countries=True)
    print(f"  Total rows: {_fmt_big(len(df))}")

    # ---- 1. Distribution per year ----------------------------------------
    print_subsection("1. AWARD_VALUE_EURO percentiles per year")

    percentiles = [0, 25, 50, 75, 90, 95, 99, 99.5, 99.9, 100]
    for year in YEARS:
        dfy = df[df["YEAR"] == year]
        vals = dfy["AWARD_VALUE_EURO"].dropna()
        if len(vals) == 0:
            print(f"  {year}: no non-NULL AWARD_VALUE_EURO rows")
            continue
        pct_vals = np.percentile(vals, percentiles)
        print(f"  {year} (n={_fmt_big(len(vals))}): "
              f"p50={_fmt_val(pct_vals[2])}  "
              f"p90={_fmt_val(pct_vals[5])}  "
              f"p95={_fmt_val(pct_vals[6])}  "
              f"p99={_fmt_val(pct_vals[7])}  "
              f"p99.9={_fmt_val(pct_vals[8])}  "
              f"max={_fmt_val(pct_vals[9])}")

    # ---- 2. Extreme outlier clusters -------------------------------------
    print_subsection("2. Extreme outlier clusters (AWARD_VALUE_EURO)")

    award = df["AWARD_VALUE_EURO"].dropna()
    extreme = {
        "> 10 B EUR  (10^10)": (award > B_10).sum(),
        "> 100 B EUR (10^11)": (award > B_100).sum(),
        "> 1 T EUR   (10^12)": (award > T_1).sum(),
        "== 0": (award == 0).sum(),
        "< 0": (award < 0).sum(),
        "NULL": df["AWARD_VALUE_EURO"].isna().sum(),
    }
    for label, count in extreme.items():
        print(f"  {label:25s}: {_fmt_big(count)}  ({pct_of(count, len(df))})")

    # Show extreme samples
    print("\n  Top-10 AWARD_VALUE_EURO values:")
    top10 = award.nlargest(10)
    for i, v in top10.items():
        row = df.loc[i]
        print(f"    {_fmt_val(v)}  |  ID_AWARD={row['ID_AWARD']}  "
              f"|  YEAR={row['YEAR']}  |  ISO={row['ISO_COUNTRY_CODE']}")

    # ---- 3. AWARD_VALUE_EURO vs VALUE_EURO ------------------------------
    print_subsection("3. AWARD_VALUE_EURO vs VALUE_EURO comparison")

    both_mask = df["AWARD_VALUE_EURO"].notna() & df["VALUE_EURO"].notna()
    award_only = df["AWARD_VALUE_EURO"].notna() & df["VALUE_EURO"].isna()
    value_only = df["AWARD_VALUE_EURO"].isna() & df["VALUE_EURO"].notna()
    both_null = df["AWARD_VALUE_EURO"].isna() & df["VALUE_EURO"].isna()

    n_both = int(both_mask.sum())
    print(f"  Both present:       {_fmt_big(n_both)}  ({pct_of(n_both, len(df))})")
    print(f"  AWARD only:          {_fmt_big(int(award_only.sum()))}  ({pct_of(int(award_only.sum()), len(df))})")
    print(f"  VALUE only:          {_fmt_big(int(value_only.sum()))}  ({pct_of(int(value_only.sum()), len(df))})")
    print(f"  Both NULL:           {_fmt_big(int(both_null.sum()))}  ({pct_of(int(both_null.sum()), len(df))})")

    if n_both > 0:
        # VALUE > AWARD violation
        viol = df["VALUE_EURO"] > df["AWARD_VALUE_EURO"]
        viol_mask = viol & both_mask
        viol_count = int(viol_mask.sum())
        print(f"\n  VALUE_EURO > AWARD_VALUE_EURO: "
              f"{_fmt_big(viol_count)}  ({pct_of(viol_count, n_both)})")

        # Ratio statistics (AWARD / VALUE where both > 0)
        pos = both_mask & (df["VALUE_EURO"] > 0) & (df["AWARD_VALUE_EURO"] > 0)
        ratio = df.loc[pos, "AWARD_VALUE_EURO"] / df.loc[pos, "VALUE_EURO"]
        print(f"  AWARD / VALUE ratio (both > 0, n={_fmt_big(len(ratio))}):")
        for pct in [5, 25, 50, 75, 95]:
            print(f"    p{pct}: {np.percentile(ratio, pct):.4f}")

    # ---- 4. Clipping threshold recommendation ----------------------------
    print_subsection("4. Clipping threshold impact (AWARD_VALUE_EURO)")

    n_award = award.notna().sum() if hasattr(award, 'notna') else 0
    # Recompute properly
    non_null = df["AWARD_VALUE_EURO"].notna()
    award_non_null = df.loc[non_null, "AWARD_VALUE_EURO"]

    for pct in CLIP_PERCENTILES:
        threshold = np.percentile(award_non_null, pct)
        clipped_count = (award_non_null > threshold).sum()
        print(f"  p{pct:5.1f} threshold = {_fmt_val(threshold):>12s}  |  "
              f"clips {_fmt_big(clipped_count)} rows  "
              f"({pct_of(clipped_count, non_null.sum())})")

    # Also try fixed thresholds
    print("\n  Fixed thresholds:")
    for threshold in [10_000_000, 25_000_000, 50_000_000, 100_000_000]:
        clipped_count = (award_non_null > threshold).sum()
        print(f"  €{threshold:>12,}  |  clips {_fmt_big(clipped_count)} rows  "
              f"({pct_of(clipped_count, non_null.sum())})")

    # ---- 5. Per-year clipping impact -------------------------------------
    print_subsection("5. Clipping impact per year (p99 threshold)")

    yearly_summary: List[Dict] = []
    for year in YEARS:
        dfy = df[df["YEAR"] == year]
        vals_y = dfy["AWARD_VALUE_EURO"].dropna()
        if len(vals_y) == 0:
            continue
        p99 = np.percentile(vals_y, 99)
        p999 = np.percentile(vals_y, 99.9)
        max_val = vals_y.max()
        clipped_99 = (vals_y > p99).sum()
        clipped_999 = (vals_y > p999).sum()
        print(f"  {year}: p99={_fmt_val(p99)}  (clips {clipped_99})  |  "
              f"p99.9={_fmt_val(p999)}  (clips {clipped_999})  |  "
              f"max={_fmt_val(max_val)}")

        yearly_summary.append({
            "year": year,
            "non_null_count": len(vals_y),
            "p90": np.percentile(vals_y, 90),
            "p95": np.percentile(vals_y, 95),
            "p99": p99,
            "p99_5": np.percentile(vals_y, 99.5),
            "p99_9": p999,
            "max": max_val,
            "rows_above_p99": clipped_99,
            "rows_above_p99_9": clipped_999,
        })

    # ---- 6. VALUE_EURO outlier analysis ----------------------------------
    print_subsection("6. VALUE_EURO distribution (for comparison)")

    val_non_null = df["VALUE_EURO"].dropna()
    if len(val_non_null) > 0:
        for pct in CLIP_PERCENTILES:
            threshold = np.percentile(val_non_null, pct)
            print(f"  p{pct:5.1f} threshold = {_fmt_val(threshold)}")
        print(f"  VALUE_EURO max = {_fmt_val(val_non_null.max())}")

    # ---- Export -----------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "analysis_2_monetary_summary.csv"
    pd.DataFrame(yearly_summary).to_csv(out_path, index=False)
    print(f"\n  Summary exported to: {out_path}")


if __name__ == "__main__":
    run()
