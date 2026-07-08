"""Shared test fixtures for the eu-procurement-red-flags test suite."""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_base_df():
    """Minimal clean DataFrame with all columns required by compute_red_flags."""
    return pd.DataFrame(
        {
            "YEAR": [2022, 2022, 2022, 2022, 2022, 2022],
            "AWARD_VALUE_EURO": [100_000, 200_000, 50_000, 300_000, 0, 80_000],
            "VALUE_EURO": [150_000, 200_000, 500_000, 300_000, 100_000, 80_000],
            "NUMBER_OFFERS": [1, 3, 2, 1, 5, 0],
            "TOP_TYPE": ["OPE", "NEG", "NIC", "OPE", "AWP", "OPE"],
            "B_AWARDED_TO_A_GROUP": ["N", "Y", "N", "N", "N", "Y"],
            "LOTS_NUMBER": [1, 3, 5, 2, 10, 1],
            "NUMBER_AWARDS": [1, 2, 5, 1, 2, 1],
        }
    )


@pytest.fixture
def sample_ted_df():
    """Realistic TED-like DataFrame for integration tests."""
    return pd.DataFrame(
        {
            "ID_AWARD": ["A1", "A2", "A3", "A4", "A5"],
            "YEAR": [2022, 2022, 2022, 2022, 2022],
            "ISO_COUNTRY_CODE": ["DE", "DK", "RO", "HU", "DE"],
            "AWARD_VALUE_EURO": [50000.0, 120000.0, 30000.0, 80000.0, 200000.0],
            "VALUE_EURO": [60000.0, 120000.0, 300000.0, 80000.0, 250000.0],
            "NUMBER_OFFERS": [2, 1, 1, 3, 2],
            "TOP_TYPE": ["OPE", "OPE", "NIC", "NEG", "OPE"],
            "B_AWARDED_TO_A_GROUP": ["N", "N", "N", "Y", "N"],
            "LOTS_NUMBER": [1, 2, 1, 3, 5],
            "NUMBER_AWARDS": [1, 1, 1, 2, 4],
            "B_ACCELERATED": ["N", "N", "N", "N", "N"],
            "winner_country": ["DE", "DK", "RO", "HU", "DE"],
            "winner_country_raw": ["DE", "DK", "RO", "HU", "DE"],
            "cpv_code": ["45000000", "33100000", "15000000", "03000000", "45000000"],
        }
    )
