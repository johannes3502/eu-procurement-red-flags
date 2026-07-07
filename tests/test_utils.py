"""Tests for utility functions (src/processing/utils.py)."""

import pandas as pd
import pytest
from pathlib import Path
from src.processing import utils
from src.processing import config


class TestTargetCountries:
    def test_load_target_countries_returns_dict(self):
        result = utils.load_target_countries()
        assert isinstance(result, dict)

    def test_target_countries_has_four(self):
        result = utils.load_target_countries()
        assert len(result) == 4

    def test_target_countries_keys(self):
        result = utils.load_target_countries()
        assert set(result.keys()) == {"DE", "DK", "RO", "HU"}

    def test_load_target_alpha2_set(self):
        result = utils.load_target_alpha2_set()
        assert result == {"DE", "DK", "RO", "HU"}


class TestP95Computation:
    def test_p95_basic(self, sample_ted_df):
        result = utils.compute_p95_per_year(sample_ted_df, col="AWARD_VALUE_EURO")
        assert isinstance(result, dict)
        assert 2022 in result
        assert result[2022] > 0

    def test_p95_returns_float_values(self, sample_ted_df):
        result = utils.compute_p95_per_year(sample_ted_df, col="AWARD_VALUE_EURO")
        for v in result.values():
            assert isinstance(v, float)

    def test_p95_empty_group(self):
        df = pd.DataFrame({"YEAR": [2022, 2022], "AWARD_VALUE_EURO": [None, None]})
        result = utils.compute_p95_per_year(df, col="AWARD_VALUE_EURO")
        assert result[2022] == 0.0


class TestCountryLookupCSV:
    def test_csv_readable(self):
        lookup = pd.read_csv(config.LOOKUP_PATH)
        assert len(lookup) > 0
        assert "alpha_2" in lookup.columns
        assert "country_name" in lookup.columns
        assert "is_target" in lookup.columns
