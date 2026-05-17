"""
config.py — Central constants for the ETL pipeline.

Single source of truth for all parameters used by utils.py, the per-dataset
clean modules (ted/clean.py, cpi/clean.py, wgi/clean.py), and
run_cleanup.py.  No functions, no logic.
"""

from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR_RAW: Path = PROJECT_ROOT / "data" / "raw"
DATA_DIR_PROCESSED: Path = PROJECT_ROOT / "data" / "processed"
LOOKUP_PATH: Path = PROJECT_ROOT / "data" / "lookup" / "lookup_countries.csv"
LOG_DIR: Path = PROJECT_ROOT / "logs"

# ---------------------------------------------------------------------------
# Years
# ---------------------------------------------------------------------------
YEARS: List[int] = list(range(2014, 2024))  # 2014–2023

# ---------------------------------------------------------------------------
# Columns after TED cleaning  (15 columns — F4 (B_ACCELERATED) is dropped)
# ---------------------------------------------------------------------------
TED_KEEP_COLUMNS: List[str] = [
    "ID_AWARD",
    "ID_NOTICE_CAN",
    "ID_LOT",
    "YEAR",
    "ISO_COUNTRY_CODE",
    "winner_country",
    "winner_country_raw",
    "AWARD_VALUE_EURO",
    "VALUE_EURO",
    "NUMBER_OFFERS",
    "B_AWARDED_TO_A_GROUP",
    "TOP_TYPE",
    "LOTS_NUMBER",
    "NUMBER_AWARDS",
    "cpv_code",
]

# ---------------------------------------------------------------------------
# Monetary thresholds
# ---------------------------------------------------------------------------
SENTINEL_THRESHOLD: float = 1_000_000_000_000        # €10T
CLIP_PERCENTILE: int = 95                              # per‑year percentile for F6 consistency
F2_DISCREPANCY_RATIO: float = 10.0                     # VALUE_EURO / AWARD_VALUE_EURO > 10.0
P95_PERCENTILE: float = 0.95

# ---------------------------------------------------------------------------
# F5: years with insufficient data
# ---------------------------------------------------------------------------
F5_EXCLUDE_YEARS: List[int] = [2014, 2015]

# ---------------------------------------------------------------------------
# Exasol type mappings  (for DDL / documentation)
# ---------------------------------------------------------------------------
EXASOL_TYPE_MAP: Dict[str, str] = {
    "ID_AWARD": "VARCHAR(100)",
    "ID_NOTICE_CAN": "VARCHAR(100)",
    "ID_LOT": "VARCHAR(100)",
    "YEAR": "SMALLINT",
    "ISO_COUNTRY_CODE": "CHAR(2)",
    "winner_country": "CHAR(2)",
    "winner_country_raw": "VARCHAR(100)",
    "AWARD_VALUE_EURO": "DECIMAL(18,2)",
    "VALUE_EURO": "DECIMAL(18,2)",
    "NUMBER_OFFERS": "SMALLINT",
    "B_AWARDED_TO_A_GROUP": "CHAR(1)",
    "TOP_TYPE": "VARCHAR(10)",
    "LOTS_NUMBER": "INTEGER",
    "NUMBER_AWARDS": "INTEGER",
    "cpv_code": "CHAR(8)",
    # Flags
    "F1": "BOOLEAN",
    "F2": "BOOLEAN",
    "F3": "BOOLEAN",
    "F5": "BOOLEAN",
    "F6": "BOOLEAN",
    "F7": "BOOLEAN",
    "comb_single_discrepancy": "BOOLEAN",
    "comb_single_non_open": "BOOLEAN",
    "comb_no_call_high_value": "BOOLEAN",
    "comb_frag_single": "BOOLEAN",
}

# ---------------------------------------------------------------------------
# CPI columns
# ---------------------------------------------------------------------------
CPI_KEEP_COLUMNS: List[str] = ["country_iso3", "year", "cpi_score"]

# ---------------------------------------------------------------------------
# WGI columns
# ---------------------------------------------------------------------------
WGI_KEEP_COLUMNS: List[str] = [
    "country_iso3",
    "year",
    "control_of_corruption",
    "government_effectiveness",
    "political_stability",
    "rule_of_law",
    "regulatory_quality",
    "voice_accountability",
]
