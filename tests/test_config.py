"""Tests for configuration constants (src/processing/config.py)."""

import pytest
from src.processing import config


class TestConfigPaths:
    def test_project_root_exists(self):
        assert config.PROJECT_ROOT.exists()

    def test_lookup_path_exists(self):
        assert config.LOOKUP_PATH.exists()

    def test_data_dirs_defined(self):
        assert config.DATA_DIR_RAW is not None
        assert config.DATA_DIR_PROCESSED is not None


class TestConfigYears:
    def test_years_range(self):
        assert config.YEARS == list(range(2014, 2024))

    def test_years_length(self):
        assert len(config.YEARS) == 10


class TestConfigThresholds:
    def test_sentinel_threshold(self):
        assert config.SENTINEL_THRESHOLD == 1_000_000_000_000

    def test_f2_ratio(self):
        assert config.F2_DISCREPANCY_RATIO == 10.0

    def test_p95_percentile(self):
        assert 0 < config.P95_PERCENTILE < 1


class TestConfigTEDColumns:
    def test_keep_columns_not_empty(self):
        assert len(config.TED_KEEP_COLUMNS) > 0

    def test_key_columns_present(self):
        cols = config.TED_KEEP_COLUMNS
        assert "ID_AWARD" in cols
        assert "YEAR" in cols
        assert "ISO_COUNTRY_CODE" in cols
        assert "AWARD_VALUE_EURO" in cols


class TestConfigF5ExcludeYears:
    def test_exclude_years(self):
        assert 2014 in config.F5_EXCLUDE_YEARS
        assert 2015 in config.F5_EXCLUDE_YEARS


class TestConfigExasolTypeMap:
    def test_type_map_not_empty(self):
        assert len(config.EXASOL_TYPE_MAP) > 20

    def test_key_columns_have_types(self):
        assert "ID_AWARD" in config.EXASOL_TYPE_MAP
        assert "YEAR" in config.EXASOL_TYPE_MAP
        assert "F1" in config.EXASOL_TYPE_MAP
