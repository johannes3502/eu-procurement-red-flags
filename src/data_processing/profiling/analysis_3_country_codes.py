"""
analysis_3_country_codes.py — Multi-value WIN_COUNTRY_CODE parsing.

Key questions:
    1. NULL rate and simple vs multi-value breakdown.
    2. ``---`` separator prevalence; check for alternative separators.
    3. Position distribution of target country codes within multi-values.
    4. Impact of "first valid Alpha-2 code only" rule vs strict ``IN`` filter.
    5. Year-by-year and country-by-country patterns.

Output: console tables + ``analysis_3_country_codes_summary.csv``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_processing.profiling.analysis_utils import (
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

def _valid_alpha2(code: str) -> bool:
    """Check whether *code* looks like a real Alpha-2 country code."""
    if not isinstance(code, str):
        return False
    return len(code) == 2 and code.isalpha() and code == code.upper()


def _split_codes(raw: str) -> List[str]:
    """Split WIN_COUNTRY_CODE on ``---`` and strip whitespace."""
    if not isinstance(raw, str):
        return []
    return [c.strip() for c in raw.split("---")]


def _first_valid_alpha2(codes: List[str]) -> str:
    """Return the first code that looks like an Alpha-2 code, or empty."""
    for c in codes:
        if _valid_alpha2(c):
            return c
    return ""


def _fmt_big(n: int) -> str:
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def run() -> None:
    """Execute all WIN_COUNTRY_CODE analyses and print results."""
    print_header("Analysis 3: Multi-Value WIN_COUNTRY_CODE Parsing")

    # ---- Load data --------------------------------------------------------
    print("Loading TED data (target countries)...")
    df = load_ted_data(years=YEARS, filter_target_countries=True)
    print(f"  Total rows: {_fmt_big(len(df))}")

    # ---- 1. NULL rate -----------------------------------------------------
    print_subsection("1. WIN_COUNTRY_CODE NULL rate")

    null_mask = df["WIN_COUNTRY_CODE"].isna()
    filled_mask = df["WIN_COUNTRY_CODE"].notna()
    print(f"  NULL:           {_fmt_big(null_mask.sum())}  ({pct_of(null_mask.sum(), len(df))})")
    print(f"  Non-NULL:       {_fmt_big(filled_mask.sum())}  ({pct_of(filled_mask.sum(), len(df))})")

    # ---- 2. Simple vs multi-value ----------------------------------------
    print_subsection("2. Simple (2-char) vs multi-value breakdown")

    wcc = df.loc[filled_mask, "WIN_COUNTRY_CODE"].astype(str)
    simple_mask = wcc.str.match(r"^[A-Z]{2}$")           # exactly 2 uppercase letters
    multi_mask = wcc.str.contains("---")                  # contains separator
    other_mask = ~simple_mask & ~multi_mask               # neither

    print(f"  Simple 2-char (e.g. 'DE'):    {_fmt_big(simple_mask.sum())}  ({pct_of(simple_mask.sum(), len(wcc))})")
    print(f"  Multi-value (--- separated):  {_fmt_big(multi_mask.sum())}  ({pct_of(multi_mask.sum(), len(wcc))})")
    print(f"  Other (unexpected format):   {_fmt_big(other_mask.sum())}  ({pct_of(other_mask.sum(), len(wcc))})")

    # Show examples of "other"
    if other_mask.sum() > 0:
        other_vals = wcc[other_mask].value_counts().head(10)
        print(f"\n  Top-10 unexpected formats:")
        for val, cnt in other_vals.items():
            print(f"    '{val}' — {cnt} rows")

    # ---- 3. Multi-value analysis -----------------------------------------
    print_subsection("3. Multi-value code analysis")

    if multi_mask.sum() > 0:
        multi_vals = wcc[multi_mask]
        # Split and collect all individual codes
        all_codes: List[str] = []
        segment_counts: List[int] = []
        for raw in multi_vals:
            parts = _split_codes(raw)
            segment_counts.append(len(parts))
            all_codes.extend(parts)

        print(f"  Multi-value rows:       {_fmt_big(len(multi_vals))}")
        print(f"  Total segments:          {_fmt_big(len(all_codes))}")
        print(f"  Avg segments / row:      {sum(segment_counts) / len(segment_counts):.2f}")
        print(f"  Max segments in one row:  {max(segment_counts)}")

        # Segment-count distribution
        seg_series = pd.Series(segment_counts)
        print(f"\n  Segment count distribution:")
        for n_seg in sorted(seg_series.unique()):
            count = (seg_series == n_seg).sum()
            print(f"    {n_seg} segments: {_fmt_big(count)} rows  ({pct_of(count, len(seg_series))})")

        # Are all segments valid Alpha-2?
        valid_seg = sum(1 for c in all_codes if _valid_alpha2(c))
        invalid_seg = len(all_codes) - valid_seg
        print(f"\n  Valid Alpha-2 segments:   {_fmt_big(valid_seg)}  ({pct_of(valid_seg, len(all_codes))})")
        print(f"  Invalid segments:         {_fmt_big(invalid_seg)}  ({pct_of(invalid_seg, len(all_codes))})")

        # Show invalid segment examples
        if invalid_seg > 0:
            invalid_set = set(c for c in all_codes if not _valid_alpha2(c))
            print(f"  Unique invalid segments:  {len(invalid_set)}")
            print(f"  Examples: {sorted(invalid_set)[:15]}")

    # ---- 4. Target-country position analysis -----------------------------
    print_subsection("4. Position of target countries in multi-value codes")

    target_set = set(TARGET_COUNTRIES.keys())  # {"DE", "DK", "RO", "HU"}

    # For multi-value rows, find where target countries appear
    position_stats: Dict[str, List[int]] = {c: [] for c in target_set}
    rows_with_target: Set[int] = set()

    if multi_mask.sum() > 0:
        for idx in multi_vals.index:
            parts = _split_codes(multi_vals.loc[idx])
            found_any = False
            for pos, code in enumerate(parts):
                if code in target_set:
                    position_stats[code].append(pos + 1)  # 1-indexed
                    found_any = True
            if found_any:
                rows_with_target.add(idx)

        print(f"  Multi-value rows containing >=1 target country: "
              f"{_fmt_big(len(rows_with_target))} "
              f"({pct_of(len(rows_with_target), len(multi_vals))})")

        for code in sorted(target_set):
            positions = position_stats[code]
            if not positions:
                print(f"  {code} ({TARGET_COUNTRIES[code]}): never appears in multi-value fields")
                continue
            pos_series = pd.Series(positions)
            print(f"  {code} ({TARGET_COUNTRIES[code]}): "
                  f"appears {len(positions)}×,  "
                  f"median pos={pos_series.median():.1f},  "
                  f"p90 pos={pos_series.quantile(0.9):.0f},  "
                  f"pos=1 in {pct_of((pos_series == 1).sum(), len(positions))} of cases")

    # ---- 5. "First valid" rule impact ------------------------------------
    print_subsection("5. Filter rule impact: first valid vs strict IN")

    # Rule A: Take first valid Alpha-2 code
    all_codes_extracted = df.loc[filled_mask, "WIN_COUNTRY_CODE"].apply(
        lambda x: _first_valid_alpha2(_split_codes(x))
    )
    match_first = all_codes_extracted.isin(target_set)
    print(f"  Rule 'first valid Alpha-2': "
          f"{_fmt_big(match_first.sum())} of {_fmt_big(len(all_codes_extracted))} "
          f"match target  ({pct_of(match_first.sum(), len(all_codes_extracted))})")

    # Rule B: All segments must be target country codes (strict)
    def _all_target(raw: str) -> bool:
        parts = _split_codes(raw)
        if not parts:
            return False
        return all(p in target_set for p in parts)

    match_strict = df.loc[filled_mask, "WIN_COUNTRY_CODE"].apply(_all_target)
    print(f"  Rule 'all segments target': "
          f"{_fmt_big(match_strict.sum())} of {_fmt_big(len(all_codes_extracted))} "
          f"match  ({pct_of(match_strict.sum(), len(all_codes_extracted))})")

    # Rule C: At least one segment is a target code
    def _any_target(raw: str) -> bool:
        parts = _split_codes(raw)
        return any(p in target_set for p in parts)

    match_any = df.loc[filled_mask, "WIN_COUNTRY_CODE"].apply(_any_target)
    print(f"  Rule 'any segment target': "
          f"{_fmt_big(match_any.sum())} of {_fmt_big(len(all_codes_extracted))} "
          f"match  ({pct_of(match_any.sum(), len(all_codes_extracted))})")

    # ---- 6. Non-target codes ---------------------------------------------
    print_subsection("6. Non-target Alpha-2 codes in WIN_COUNTRY_CODE")

    # Collect all non-target Alpha-2 codes (both simple and from multi-value)
    non_target_counts: Dict[str, int] = {}
    for raw in wcc:
        parts = _split_codes(raw)
        for code in parts:
            if _valid_alpha2(code) and code not in target_set:
                non_target_counts[code] = non_target_counts.get(code, 0) + 1

    top_non_target = sorted(non_target_counts.items(), key=lambda x: -x[1])[:15]
    print(f"  Unique non-target codes seen: {len(non_target_counts)}")
    print(f"  Top-15 non-target codes:")
    for code, cnt in top_non_target:
        print(f"    {code}: {_fmt_big(cnt)}")

    # ---- 7. Per-year breakdown --------------------------------------------
    print_subsection("7. Per-year WIN_COUNTRY_CODE availability")

    yearly_summary: List[Dict] = []
    for year in YEARS:
        dfy = df[df["YEAR"] == year]
        if len(dfy) == 0:
            continue
        null_y = dfy["WIN_COUNTRY_CODE"].isna().sum()
        filled_y = len(dfy) - null_y
        wcc_y = dfy.loc[dfy["WIN_COUNTRY_CODE"].notna(), "WIN_COUNTRY_CODE"].astype(str)
        multi_y = wcc_y.str.contains("---").sum()
        simple_y = wcc_y.str.match(r"^[A-Z]{2}$").sum()

        print(f"  {year}: rows={_fmt_big(len(dfy))}  "
              f"NULL={pct_of(null_y, len(dfy))}  "
              f"simple={_fmt_big(simple_y)}  "
              f"multi={_fmt_big(multi_y)}")

        yearly_summary.append({
            "year": year,
            "total_rows": len(dfy),
            "null_count": null_y,
            "null_pct": round(null_y / len(dfy) * 100, 2),
            "simple_count": simple_y,
            "multi_count": multi_y,
        })

    # ---- Export -----------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "analysis_3_country_codes_summary.csv"
    pd.DataFrame(yearly_summary).to_csv(out_path, index=False)
    print(f"\n  Summary exported to: {out_path}")


if __name__ == "__main__":
    run()
