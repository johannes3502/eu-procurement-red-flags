#!/usr/bin/env python3
"""
download_data.py — Automated data acquisition orchestrator.

Coordinates downloads for TED, CPI, and WGI datasets.
Each dataset module independently handles HTTP, extraction, and file storage.

Usage:
    python src/download_data.py                   # download all (skip existing)
    python src/download_data.py --force           # re-download all
    python src/download_data.py --dataset ted     # only TED
    python src/download_data.py --dataset wgi --force  # force re-download WGI only
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path (so imports work from any CWD)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Logging setup (basicConfig — sufficient for a CLI orchestrator)
# ---------------------------------------------------------------------------
# Ensure logs directory exists (relative to project root)
Path(_PROJECT_ROOT / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            str(_PROJECT_ROOT / "logs" / "download_data.log"), encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("download_data")

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from src.acquisition.ted.download import download_ted
from src.acquisition.cpi.download import download_cpi
from src.acquisition.wgi.download import download_wgi

# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------
DATASETS: dict[str, dict] = {
    "ted": {"func": download_ted, "label": "TED"},
    "cpi": {"func": download_cpi, "label": "CPI"},
    "wgi": {"func": download_wgi, "label": "WGI"},
}

# Expected output paths (for size reporting)
ROOT = _PROJECT_ROOT
EXPECTED_PATHS: dict[str, Path] = {
    "ted": ROOT / "data" / "raw" / "ted",                     # directory with multiple CSVs
    "cpi": ROOT / "data" / "raw" / "cpi" / "cpi_raw.csv",
    "wgi": ROOT / "data" / "raw" / "wgi" / "wgi_raw.csv",
}


def _get_file_size_mb(path: Path) -> str:
    """Return a human-readable size string for a path (file or directory)."""
    try:
        if path.is_file():
            size = path.stat().st_size / (1024 * 1024)
            return f"{size:.2f} MB"
        elif path.is_dir():
            total = sum(f.stat().st_size for f in path.glob("*.csv"))
            return f"{total / (1024 * 1024):.2f} MB"
    except OSError:
        pass
    return "?"


def _get_file_name(path: Path) -> str:
    """Return a short file name for display (relative to data/raw)."""
    try:
        raw = ROOT / "data" / "raw"
        return str(path.relative_to(raw))
    except (ValueError, OSError):
        return path.name


def _print_summary(results: list[dict]) -> None:
    """Print a human-readable summary table of all downloads."""
    print("\n" + "=" * 72)
    print("  DOWNLOAD SUMMARY — Red Flags Procurement Governance")
    print("=" * 72)
    for r in results:
        marker = "OK" if r["status"] == "OK" else "FAIL"
        print(
            f"  {marker} [{r['dataset']:>4s}] "
            f"{r['file']:<30s} {r['size']:>10s}"
        )
        if r["note"]:
            print(f"         ({r['note']})")
    print("=" * 72)

    ok_count = sum(1 for r in results if r["status"] == "OK")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    skip_count = sum(1 for r in results if r["status"] == "SKIPPED")
    print(
        f"  TOTAL: {len(results)}  |  "
        f"OK: {ok_count}  |  SKIPPED: {skip_count}  |  FAILED: {fail_count}"
    )
    print("=" * 72 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download raw data for the Red Flags Procurement Governance project.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download all files even if they already exist.",
    )
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()),
        help="Download only a specific dataset (default: all).",
    )
    args = parser.parse_args()

    logger.info("=== download_data.py started (force=%s) ===", args.force)
    t_start = time.monotonic()

    # Determine which datasets to process
    selected = (
        {args.dataset: DATASETS[args.dataset]}
        if args.dataset
        else DATASETS
    )

    results: list[dict] = []

    for key, info in selected.items():
        label = info["label"]
        logger.info("--- Processing: %s ---", label)

        try:
            success = info["func"](force=args.force)
        except Exception as exc:
            logger.error("%s raised an exception: %s", label, exc)
            success = False

        # Build result entry
        expected = EXPECTED_PATHS.get(key)
        size_str = _get_file_size_mb(expected) if expected else "?"
        file_str = _get_file_name(expected) if expected else key

        if success and expected and expected.exists():
            results.append({
                "dataset": label,
                "file": file_str,
                "size": size_str,
                "status": "OK",
                "note": "",
            })
        elif success and expected and not expected.exists():
            results.append({
                "dataset": label,
                "file": file_str,
                "size": size_str,
                "status": "OK",
                "note": "function returned True, but output not found",
            })
        elif success:
            results.append({
                "dataset": label,
                "file": file_str,
                "size": size_str,
                "status": "OK",
                "note": "",
            })
        else:
            results.append({
                "dataset": label,
                "file": file_str,
                "size": size_str,
                "status": "FAIL",
                "note": "download failed (see log)",
            })

    elapsed = time.monotonic() - t_start
    logger.info("=== download_data.py finished in %.1f s ===", elapsed)

    _print_summary(results)

    # Exit code: 0 if all OK, 1 if any failed
    any_fail = any(r["status"] == "FAIL" for r in results)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
