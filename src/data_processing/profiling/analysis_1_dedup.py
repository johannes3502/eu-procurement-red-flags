"""
analysis_1_dedup.py — Fact granularity & deduplication strategy.

Key questions:
    1. Is ``ID_AWARD`` unique enough to serve as fact-table primary key?
    2. How does the ``(ID_NOTICE_CAN, ID_LOT)`` composite behave?
    3. How do duplicates relate to the ``CORRECTIONS`` column?
    4. ID_LOT NULL rate per year — what NULL semantics imply for dedup.
    5. Impact of different dedup strategies on row counts.

Output: console tables + ``analysis_1_dedup.csv`` summary.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Project root for imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.profiling.analysis_utils import (
    DATA_DIR,
    OUTPUT_DIR,
    YEARS,
    TARGET_COUNTRIES,
    KEEP_COLUMNS,
    load_ted_data,
    pct_of,
    print_header,
    print_subsection,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_big(n: int) -> str:
    """Format large integers with thousand separators."""
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run() -> None:
    """Execute all dedup analyses and print results."""
    print_header("Analysis 1: Fact Granularity & Deduplication Strategy")

    # ---- Load data --------------------------------------------------------
    # We need all columns for the dedup analysis (no country filter yet —
    # we compare global vs filtered later).
    print("Loading TED data (all countries, all years)...")
    df_all = load_ted_data(years=YEARS, filter_target_countries=False)
    print(f"  Total rows (all countries): {_fmt_big(len(df_all))}")

    # Also load with target-country filter
    df = load_ted_data(years=YEARS, filter_target_countries=True)
    print(f"  Total rows (target countries): {_fmt_big(len(df))}")

    # ---- 1. ID_AWARD as candidate primary key ----------------------------
    print_subsection("1. ID_AWARD uniqueness (target countries)")

    id_award_null = df["ID_AWARD"].isna().sum()
    id_award_dups = df.duplicated(subset=["ID_AWARD"], keep=False).sum()
    # How many ID_AWARD values appear >1 time
    id_award_counts = df["ID_AWARD"].value_counts()
    id_award_multi = (id_award_counts > 1).sum()
    id_award_max_dup = id_award_counts.max() if len(id_award_counts) > 0 else 0

    print(f"  Total rows:               {_fmt_big(len(df))}")
    print(f"  ID_AWARD is NULL:         {_fmt_big(id_award_null)}  ({pct_of(id_award_null, len(df))})")
    print(f"  Unique ID_AWARD values:   {_fmt_big(df['ID_AWARD'].nunique())}")
    print(f"  ID_AWARD values >1 row:   {_fmt_big(id_award_multi)}")
    print(f"  Rows in duplicate groups:  {_fmt_big(id_award_dups)}  ({pct_of(id_award_dups, len(df))})")
    print(f"  Max duplicate count:      {id_award_max_dup}")

    # ---- 2. (ID_NOTICE_CAN, ID_LOT) as candidate composite ---------------
    print_subsection("2. (ID_NOTICE_CAN, ID_LOT) uniqueness")

    id_lot_null = df["ID_LOT"].isna().sum()
    composite_null = df["ID_NOTICE_CAN"].isna() | df["ID_LOT"].isna()
    composite_dups = df.duplicated(
        subset=["ID_NOTICE_CAN", "ID_LOT"], keep=False,
    ).sum()

    print(f"  ID_LOT is NULL:             {_fmt_big(id_lot_null)}  ({pct_of(id_lot_null, len(df))})")
    print(f"  Either key NULL:            {_fmt_big(composite_null.sum())}  ({pct_of(composite_null.sum(), len(df))})")
    print(f"  Rows in duplicate groups:   {_fmt_big(composite_dups)}  ({pct_of(composite_dups, len(df))})")

    # ---- 3. ID_LOT NULL rate per year -----------------------------------
    print_subsection("3. ID_LOT NULL rate per year")

    for year in YEARS:
        dfy = df[df["YEAR"] == year]
        if len(dfy) == 0:
            continue
        nulls = dfy["ID_LOT"].isna().sum()
        print(f"  {year}: {_fmt_big(nulls)} of {_fmt_big(len(dfy))} NULL  ({pct_of(nulls, len(dfy))})")

    # ---- 4. Relationship between ID_AWARD and (ID_NOTICE_CAN, ID_LOT) ---
    print_subsection("4. ID_AWARD per (ID_NOTICE_CAN, ID_LOT)")

    # How many distinct ID_AWARD values exist per notice-lot combination
    awards_per_lot = (
        df.dropna(subset=["ID_NOTICE_CAN", "ID_LOT", "ID_AWARD"])
        .groupby(["ID_NOTICE_CAN", "ID_LOT"])["ID_AWARD"]
        .nunique()
    )
    multi_award_lots = (awards_per_lot > 1).sum()
    max_awards = awards_per_lot.max() if len(awards_per_lot) > 0 else 0
    print(f"  (ID_NOTICE_CAN, ID_LOT) combos:   {_fmt_big(len(awards_per_lot))}")
    print(f"  Combos with >1 ID_AWARD:           {_fmt_big(multi_award_lots)}  ({pct_of(multi_award_lots, len(awards_per_lot))})")
    print(f"  Max ID_AWARD per combo:            {max_awards}")

    # ---- 5. CORRECTIONS and duplicates -----------------------------------
    print_subsection("5. CORRECTIONS column vs duplicates")

    if "CORRECTIONS" in df.columns:
        corr_filled = df["CORRECTIONS"].notna().sum()
        corr_empty = df["CORRECTIONS"].isna().sum()
        print(f"  CORRECTIONS filled:  {_fmt_big(corr_filled)}  ({pct_of(corr_filled, len(df))})")
        print(f"  CORRECTIONS empty:   {_fmt_big(corr_empty)}  ({pct_of(corr_empty, len(df))})")

        # Duplicate rate among CORRECTIONS-filled vs CORRECTIONS-empty rows
        for label, mask in [("filled", df["CORRECTIONS"].notna()), ("empty", df["CORRECTIONS"].isna())]:
            sub = df[mask]
            dup_count = sub.duplicated(subset=["ID_AWARD"], keep=False).sum()
            print(f"  ID_AWARD dup rate (CORRECTIONS {label}): "
                  f"{_fmt_big(dup_count)} / {_fmt_big(len(sub))}  ({pct_of(dup_count, len(sub))})")

        # What share of duplicates are explained by CORRECTIONS?
        dup_mask = df.duplicated(subset=["ID_AWARD"], keep=False)
        dup_with_corr = (dup_mask & df["CORRECTIONS"].notna()).sum()
        dup_without_corr = (dup_mask & df["CORRECTIONS"].isna()).sum()
        print(f"  Duplicate rows with CORRECTIONS:    {_fmt_big(dup_with_corr)}")
        print(f"  Duplicate rows without CORRECTIONS: {_fmt_big(dup_without_corr)}")

    # ---- 6. Dedup impact summary -----------------------------------------
    print_subsection("6. Dedup strategy row-count impact")

    total = len(df)
    # Strategy A: keep first by ID_AWARD
    dedup_a = df.drop_duplicates(subset=["ID_AWARD"], keep="first")
    # Strategy B: keep last by ID_AWARD
    dedup_b = df.drop_duplicates(subset=["ID_AWARD"], keep="last")
    # Strategy C: when CORRECTIONS present, keep last; otherwise keep first
    if "CORRECTIONS" in df.columns:
        df_sorted = df.sort_values(["ID_AWARD", "CORRECTIONS"], na_position="first")
        dedup_c = df_sorted.drop_duplicates(subset=["ID_AWARD"], keep="last")
    else:
        dedup_c = dedup_a

    print(f"  Raw rows:                          {_fmt_big(total)}")
    print(f"  After drop_duplicates(ID_AWARD, first): {_fmt_big(len(dedup_a))}  (-{_fmt_big(total - len(dedup_a))})")
    print(f"  After drop_duplicates(ID_AWARD, last):  {_fmt_big(len(dedup_b))}  (-{_fmt_big(total - len(dedup_b))})")
    if "CORRECTIONS" in df.columns:
        print(f"  After CORRECTIONS-aware dedup:          {_fmt_big(len(dedup_c))}  (-{_fmt_big(total - len(dedup_c))})")

    # ---- 7. Country-filter impact on NULL rates -------------------------
    print_subsection("7. Country-filter impact on ID_LOT NULL rate")

    df_global = load_ted_data(years=YEARS, filter_target_countries=False)
    for year in YEARS:
        global_year = df_global[df_global["YEAR"] == year]
        target_year = df[df["YEAR"] == year]
        if len(global_year) == 0:
            continue
        global_null = global_year["ID_LOT"].isna().sum()
        target_null = target_year["ID_LOT"].isna().sum() if len(target_year) > 0 else 0
        print(f"  {year}: global {pct_of(global_null, len(global_year))}  |  "
              f"target {pct_of(target_null, len(target_year))}")

    # ---- Export summary CSV ----------------------------------------------
    summary_rows: List[Dict] = []
    for year in YEARS:
        dfy = df[df["YEAR"] == year]
        if len(dfy) == 0:
            continue
        id_lot_null_y = dfy["ID_LOT"].isna().sum()
        id_award_nunique_y = dfy["ID_AWARD"].nunique()
        id_award_dup_y = dfy.duplicated(subset=["ID_AWARD"], keep=False).sum()
        summary_rows.append({
            "year": year,
            "rows": len(dfy),
            "id_lot_null": id_lot_null_y,
            "id_lot_null_pct": round(id_lot_null_y / len(dfy) * 100, 2),
            "id_award_unique": id_award_nunique_y,
            "id_award_dup_rows": id_award_dup_y,
            "id_award_dup_pct": round(id_award_dup_y / len(dfy) * 100, 2),
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "analysis_1_dedup_summary.csv"
    pd.DataFrame(summary_rows).to_csv(out_path, index=False)
    print(f"\n  Summary exported to: {out_path}")


if __name__ == "__main__":
    run()
