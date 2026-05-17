# profiling_utils.py — Generic Data Profiling Utilities
#
# This module provides reusable helper functions for data profiling:
#   - Basic information (rows, columns, memory)
#   - Data type report per column
#   - Missing value analysis
#   - Duplicate detection
#   - IQR-based outlier detection
#   - Value ranges and categorical distributions
#   - Text quality indicators
#   - Markdown report generation
#
# All functions are standalone (no logging, no path logic) and accept /
# return plain dicts for maximum reusability.

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Basic Information
# ---------------------------------------------------------------------------

def compute_basic_info(df: pd.DataFrame, file_size_mb: float) -> Dict[str, Any]:
    """Return basic table statistics (rows, columns, memory usage, file size).

    Args:
        df: Input DataFrame.
        file_size_mb: Size of the source file in megabytes.

    Returns:
        Dictionary with keys:
            rows (int), columns (int),
            memory_mb (float), file_size_mb (float).
    """
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "memory_mb": float(round(df.memory_usage(deep=True).sum() / 1_000_000, 2)),
        "file_size_mb": round(file_size_mb, 2),
    }


# ---------------------------------------------------------------------------
# 2. Data Type Report
# ---------------------------------------------------------------------------

def compute_dtype_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Report the dtype, unique count, and sample values for every column.

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary mapping column name to:
            {"dtype": str, "unique_values": int, "sample_values": list}.
    """
    report: Dict[str, Any] = {}
    for col in df.columns:
        series = df[col]
        sample = series.dropna().head(5).tolist()
        report[col] = {
            "dtype": str(series.dtype),
            "unique_values": int(series.nunique()),
            "sample_values": sample[:5],
        }
    return report


# ---------------------------------------------------------------------------
# 3. Missing Values
# ---------------------------------------------------------------------------

def compute_missing_values(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute global and per-column missing-value statistics.

    Handles empty DataFrames gracefully (returns all zeros).

    Args:
        df: Input DataFrame.

    Returns:
        Dictionary with:
            total_cells (int), total_missing (int), pct_missing (float),
            per_column (dict) — only columns with missing > 0.
    """
    total_cells = df.size
    if total_cells == 0:
        return {
            "total_cells": 0,
            "total_missing": 0,
            "pct_missing": 0.0,
            "per_column": {},
        }

    total_missing = int(df.isnull().sum().sum())
    per_column: Dict[str, Any] = {}
    for col in df.columns:
        missing = int(df[col].isnull().sum())
        if missing > 0:
            per_column[col] = {
                "missing": missing,
                "pct": round(missing / len(df) * 100, 2),
            }

    return {
        "total_cells": total_cells,
        "total_missing": total_missing,
        "pct_missing": round(total_missing / total_cells * 100, 2),
        "per_column": per_column,
    }


# ---------------------------------------------------------------------------
# 4. Duplicates
# ---------------------------------------------------------------------------

def compute_duplicates(df: pd.DataFrame, key_cols: List[str]) -> Dict[str, Any]:
    """Detect duplicate rows based on the given key columns.

    If key columns are missing from the DataFrame, only the available ones
    are used.  Returns an error dict when no key column exists at all.

    Args:
        df: Input DataFrame.
        key_cols: Column name(s) that should form a unique key.

    Returns:
        Dictionary with:
            total_rows (int), duplicate_rows (int), pct_duplicates (float),
            key_columns (list[str]), sample_duplicates (list[dict]).
    """
    # Filter to columns that actually exist
    existing = [c for c in key_cols if c in df.columns]
    if not existing:
        return {
            "error": "Keine der angegebenen Schlüsselspalten im DataFrame vorhanden.",
        }

    dups = df.duplicated(subset=existing, keep=False)
    dup_count = int(dups.sum())

    sample: List[dict] = []
    if dup_count > 0:
        dup_df = df[dups].sort_values(by=existing)
        sample = dup_df.head(5).to_dict(orient="records")

    return {
        "total_rows": len(df),
        "duplicate_rows": dup_count,
        "pct_duplicates": round(dup_count / len(df) * 100, 4) if len(df) > 0 else 0.0,
        "key_columns": existing,
        "sample_duplicates": sample,
    }


# ---------------------------------------------------------------------------
# 5. Outliers (IQR method)
# ---------------------------------------------------------------------------

def compute_outliers(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
    """Detect outliers using the IQR (1.5 × IQR) method.

    Columns with fewer than 10 non-NaN values are skipped.  Values are
    coerced to numeric first (non-convertible → NaN, then dropped).

    Args:
        df: Input DataFrame.
        numeric_cols: Column names to analyse.

    Returns:
        Dictionary ``{"per_column": {col: {...}}}`` where each value contains:
            outlier_count (int), pct_outliers (float),
            lower_bound (float), upper_bound (float),
            min_actual (float), max_actual (float),
            suggested_clip_99pct (float | None).
    """
    result: Dict[str, Any] = {}

    for col in numeric_cols:
        if col not in df.columns:
            continue

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 10:
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers = series[(series < lower) | (series > upper)]
        outlier_count = len(outliers)

        # 99th percentile as suggested clip threshold (only if positive values exist)
        has_positive = bool((series > 0).any())
        clip_val: float | None = (
            round(float(series.quantile(0.99)), 2) if has_positive else None
        )

        result[col] = {
            "outlier_count": int(outlier_count),
            "pct_outliers": round(outlier_count / len(series) * 100, 2),
            "lower_bound": round(lower, 2) if not math.isnan(lower) and not math.isinf(lower) else None,
            "upper_bound": round(upper, 2) if not math.isnan(upper) and not math.isinf(upper) else None,
            "min_actual": round(float(series.min()), 2),
            "max_actual": round(float(series.max()), 2),
            "suggested_clip_99pct": clip_val,
        }

    return {"per_column": result}


# ---------------------------------------------------------------------------
# 6. Value Ranges  (numerical + categorical)
# ---------------------------------------------------------------------------

def compute_value_ranges(
    df: pd.DataFrame,
    numeric_cols: List[str],
    categorical_threshold: int = 50,
) -> Dict[str, Any]:
    """Compute descriptive statistics for numeric columns and Top-10 for
    categorical (``object``) columns with few unique values.

    Args:
        df: Input DataFrame.
        numeric_cols: Numeric columns to describe.
        categorical_threshold: Max unique values for a column to be treated
            as categorical (default 50).

    Returns:
        Dictionary with keys ``numerical`` (dict) and ``categorical`` (dict).
    """
    # ── Numerical ──────────────────────────────────────────────────────
    numerical: Dict[str, Any] = {}
    for col in numeric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) == 0:
            continue

        numerical[col] = {
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
            "mean": round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "std": round(float(series.std()), 2),
            "q1": round(float(series.quantile(0.25)), 2),
            "q3": round(float(series.quantile(0.75)), 2),
            "unique_values": int(series.nunique()),
            "negative_count": int((series < 0).sum()),
        }

    # ── Categorical (object columns with low cardinality) ──────────────
    categorical: Dict[str, Any] = {}
    for col in df.select_dtypes(include=["object"]).columns:
        unique_count = int(df[col].nunique())
        if unique_count > categorical_threshold:
            continue

        value_counts = df[col].value_counts().head(10)
        top_values: List[Dict[str, Any]] = []
        for value, count in value_counts.items():
            top_values.append({
                "value": str(value),
                "count": int(count),
                "pct": round(count / len(df) * 100, 2),
            })

        categorical[col] = {
            "unique_values": unique_count,
            "top_values": top_values,
        }

    return {"numerical": numerical, "categorical": categorical}


# ---------------------------------------------------------------------------
# 7. Text Quality
# ---------------------------------------------------------------------------

def compute_text_quality(df: pd.DataFrame, text_cols: List[str]) -> Dict[str, Any]:
    """Analyse text quality for the given columns.

    Checks for empty strings, whitespace-only strings, and common null-like
    literal strings ("null", "na", "nan", "none", "n/a", case-insensitive).
    Also reports min / max / average string lengths.

    Handles columns that are entirely null (pd.NA) gracefully — length
    statistics default to 0 / 0.0 in that case.

    Args:
        df: Input DataFrame.
        text_cols: Column names to analyse (must exist or are silently skipped).

    Returns:
        Dictionary ``{"per_column": {col: {...}}}``.
    """
    NULL_LITERALS = {"null", "na", "nan", "none", "n/a"}

    result: Dict[str, Any] = {}

    for col in text_cols:
        if col not in df.columns:
            continue

        series = df[col].astype(str)
        lengths = series.str.len()

        empty = int((series == "").sum())
        whitespace = int(series.str.match(r"^\s+$").fillna(False).sum())
        null_str = int(series.str.lower().isin(NULL_LITERALS).sum())

        # Drop NA values before computing statistics —
        #   Integer-valued `.str.len()` can still produce pd.NA when the
        #   underlying column uses StringDtype (numpy_nullable backend) and
        #   all values are null.  Calling int()/float() on pd.NA raises
        #   ValueError: cannot convert float NaN to integer.
        valid_lengths = lengths.dropna()
        has_values = len(valid_lengths) > 0

        result[col] = {
            "empty_strings": empty,
            "whitespace_only": whitespace,
            "null_strings": null_str,
            "avg_length": round(float(valid_lengths.mean()), 2) if has_values else 0.0,
            "min_length": int(valid_lengths.min()) if has_values else 0,
            "max_length": int(valid_lengths.max()) if has_values else 0,
        }

    return {"per_column": result}


# ---------------------------------------------------------------------------
# 8. Markdown Report Generation
# ---------------------------------------------------------------------------

def _fmt_val(val: Any, fmt: str = ".2f") -> str:
    """Format a value for display; return ``"—"`` for None."""
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:{fmt}}"
    return str(val)


def generate_markdown(
    metrics: Dict[str, Any],
    source_name: str,
    file_path: Path,
    timestamp: str,
) -> str:
    """Render the profiling metrics as a full Markdown report.

    The report contains 8 sections:
        1. Basic Information
        2. Datentypen (Data Types)
        3. Fehlende Werte (Missing Values)
        4. Duplikate (Duplicates)
        5. Ausreisser (Outliers via IQR)
        6. Wertebereiche & Verteilungen (Value Ranges)
        7. Textqualität (Text Quality)
        8. Logische Konsistenz (Logical Consistency)

    Args:
        metrics: The profiling metrics dict (produced by the compute_* helpers
            and the dataset-specific logic).
        source_name: Human-readable label (e.g. "CPI", "TED 2022").
        file_path: Relative path to the source file (for display).
        timestamp: Date string, e.g. "2026-05-16".

    Returns:
        Markdown source as a single string.
    """
    lines: List[str] = []

    # === HEADER ==========================================================
    lines.append(f"# Profiling Report: {source_name}")
    lines.append("")
    lines.append(f"**Datei:** `{file_path}`  ")
    lines.append(f"**Erstellt:** {timestamp}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    bi = metrics.get("basic_info", {})

    # === 1. BASIC INFORMATION ============================================
    lines.append("## 1. Basic Information")
    lines.append("")
    lines.append("| Metrik | Wert |")
    lines.append("|--------|------|")
    _append_row(lines, "Zeilen", f"{bi.get('rows', 0):,}")
    _append_row(lines, "Spalten", str(bi.get("columns", 0)))
    _append_row(lines, "Speicher (RAM)", f"{bi.get('memory_mb', 0):.2f} MB")
    _append_row(lines, "Dateigrösse", f"{bi.get('file_size_mb', 0):.2f} MB")
    lines.append("")

    # === 2. DATATYPES ====================================================
    lines.append("## 2. Datentypen")
    lines.append("")
    lines.append("| Spalte | Typ | Einzigartige Werte | Beispielwerte |")
    lines.append("|--------|-----|-------------------|---------------|")
    dtypes = metrics.get("dtypes", {})
    if dtypes:
        for col, info in dtypes.items():
            samples = ", ".join(str(v)[:25] for v in info.get("sample_values", [])[:3])
            lines.append(
                f"| {col} | {info['dtype']} | "
                f"{info['unique_values']:,} | {samples} |"
            )
    else:
        lines.append("| — | — | — | — |")
    lines.append("")

    # === 3. MISSING VALUES ===============================================
    lines.append("## 3. Fehlende Werte")
    lines.append("")
    mv = metrics.get("missing_values", {})
    lines.append(f"- **Gesamtzellen:** {mv.get('total_cells', 0):,}")
    lines.append(f"- **Fehlende Zellen:** {mv.get('total_missing', 0):,}")
    lines.append(f"- **Fehlwerten-Rate:** {mv.get('pct_missing', 0):.2f}%")
    lines.append("")
    per_col = mv.get("per_column", {})
    if per_col:
        lines.append("| Spalte | Fehlend | Anteil |")
        lines.append("|--------|---------|--------|")
        for col, info in sorted(per_col.items(), key=lambda x: x[1]["missing"], reverse=True):
            lines.append(f"| {col} | {info['missing']:,} | {info['pct']:.2f}% |")
    lines.append("")

    # === 4. DUPLICATES ===================================================
    lines.append("## 4. Duplikate")
    lines.append("")
    dup = metrics.get("duplicates", {})
    if "error" in dup:
        lines.append(f"⚠️ {dup['error']}")
    else:
        key_str = ", ".join(dup.get("key_columns", []))
        lines.append(f"- **Prüfschlüssel:** `{key_str}`")
        lines.append(
            f"- **Duplikate:** {dup.get('duplicate_rows', 0):,} "
            f"({dup.get('pct_duplicates', 0):.4f}%)"
        )
    lines.append("")

    # === 5. OUTLIERS (IQR) ===============================================
    lines.append("## 5. Ausreisser (IQR)")
    lines.append("")
    ol = metrics.get("outliers", {}).get("per_column", {})
    if ol:
        lines.append(
            "| Spalte | #Ausreisser | Anteil | Untergrenze | Obergrenze | "
            "Min (Ist) | Max (Ist) | 99% Clip |"
        )
        lines.append(
            "|--------|------------|--------|-------------|-------------|"
            "-----------|-----------|----------|"
        )
        for col, info in ol.items():
            lines.append(
                f"| {col} | {info['outlier_count']:,} | "
                f"{info['pct_outliers']:.2f}% | "
                f"{_fmt_val(info.get('lower_bound'))} | "
                f"{_fmt_val(info.get('upper_bound'))} | "
                f"{info['min_actual']:.2f} | "
                f"{info['max_actual']:.2f} | "
                f"{_fmt_val(info.get('suggested_clip_99pct'))} |"
            )
    else:
        lines.append("Keine numerischen Spalten für Ausreisser-Analyse.")
    lines.append("")

    # === 6. VALUE RANGES =================================================
    lines.append("## 6. Wertebereiche & Verteilungen")
    lines.append("")
    vr = metrics.get("value_ranges", {})
    num = vr.get("numerical", {})
    cat = vr.get("categorical", {})

    if num:
        lines.append("### Numerische Spalten")
        lines.append("")
        lines.append("| Spalte | Min | Max | Mean | Median | Std | Negative |")
        lines.append("|--------|-----|-----|------|--------|-----|----------|")
        for col, info in num.items():
            lines.append(
                f"| {col} | {info['min']} | {info['max']} | "
                f"{info['mean']} | {info['median']} | "
                f"{info['std']} | {info.get('negative_count', 0):,} |"
            )

    if cat:
        lines.append("")
        lines.append("### Kategoriale Spalten (Top 10)")
        lines.append("")
        for col, info in cat.items():
            lines.append(f"**{col}** ({info['unique_values']} unique)")
            lines.append("")
            lines.append("| Wert | Count | Anteil |")
            lines.append("|------|-------|--------|")
            for top in info.get("top_values", []):
                lines.append(
                    f"| {top['value'][:45]} | {top['count']:,} | "
                    f"{top['pct']:.2f}% |"
                )
            lines.append("")
    lines.append("")

    # === 7. TEXT QUALITY =================================================
    lines.append("## 7. Textqualität")
    lines.append("")
    tq = metrics.get("text_quality", {}).get("per_column", {})
    if tq:
        lines.append(
            "| Spalte | Leerstrings | Whitespace | Null-Strings | "
            "Ø Länge | Min | Max |"
        )
        lines.append(
            "|--------|------------|------------|-------------|"
            "---------|-----|-----|"
        )
        for col, info in tq.items():
            lines.append(
                f"| {col} | {info['empty_strings']:,} | "
                f"{info['whitespace_only']:,} | "
                f"{info['null_strings']:,} | "
                f"{info['avg_length']:.2f} | "
                f"{info['min_length']} | {info['max_length']} |"
            )
    else:
        lines.append("Keine Text-Spalten analysiert.")
    lines.append("")

    # === 8. LOGICAL CONSISTENCY ==========================================
    lines.append("## 8. Logische Konsistenz")
    lines.append("")
    lc = metrics.get("logical_consistency", {})
    rules = lc.get("rules_checked", [])
    violations = lc.get("violations", {})

    if rules:
        lines.append("**Geprüfte Regeln:**")
        for r in rules:
            lines.append(f"- {r}")
        lines.append("")

    if violations:
        lines.append("| Regel | Verstösse | Anteil | Beispiele |")
        lines.append("|-------|-----------|--------|-----------|")
        for rule_name, info in violations.items():
            samples = info.get("sample_violations", [])
            sample_str = (
                ", ".join(str(s)[:60] for s in samples[:2])
                if samples
                else "—"
            )
            lines.append(
                f"| {info.get('description', rule_name)[:55]} | "
                f"{info['violation_count']:,} | "
                f"{info['pct_violations']:.2f}% | "
                f"`{sample_str}` |"
            )
    else:
        lines.append("Keine Verstösse gefunden.")
    lines.append("")

    # === FOOTER ==========================================================
    lines.append("---")
    lines.append(
        f"*Report automatisch generiert von `profile_raw_data.py` "
        f"am {timestamp}*"
    )

    return "\n".join(lines)


def _append_row(lines: List[str], label: str, value: str) -> None:
    """Append a single table row (label | value)."""
    lines.append(f"| {label} | {value} |")
