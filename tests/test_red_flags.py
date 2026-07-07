"""Unit tests for red flag computation logic (src/processing/ted/clean.py).

Tests isolated flag logic without database or file I/O dependencies."""

import pandas as pd
import pytest
from src.processing.ted.clean import compute_red_flags


class TestRedFlagF1SingleBidder:
    def test_single_bidder_true(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 1
        result = compute_red_flags(df)
        assert result["F1"].all()

    def test_single_bidder_false_multiple_offers(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 3
        result = compute_red_flags(df)
        assert not result["F1"].any()

    def test_single_bidder_false_zero_offers(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 0
        result = compute_red_flags(df)
        assert not result["F1"].any()

    def test_single_bidder_handles_null(self, sample_base_df):
        df = sample_base_df.copy()
        df.loc[0, "NUMBER_OFFERS"] = None
        result = compute_red_flags(df)
        assert not result.loc[0, "F1"]


class TestRedFlagF2ValueDiscrepancy:
    def test_f2_true_ratio_exceeds_10(self, sample_base_df):
        df = sample_base_df.copy()
        df["AWARD_VALUE_EURO"] = 1000
        df["VALUE_EURO"] = 15000
        result = compute_red_flags(df)
        assert result["F2"].all()

    def test_f2_false_ratio_below_10(self, sample_base_df):
        df = sample_base_df.copy()
        df["AWARD_VALUE_EURO"] = 10000
        df["VALUE_EURO"] = 50000
        result = compute_red_flags(df)
        assert not result["F2"].any()

    def test_f2_false_exact_ratio_10(self, sample_base_df):
        df = sample_base_df.copy()
        df["AWARD_VALUE_EURO"] = 1000
        df["VALUE_EURO"] = 10000
        result = compute_red_flags(df)
        assert not result["F2"].any()

    def test_f2_handles_zero_award_value(self, sample_base_df):
        df = sample_base_df.copy()
        df["AWARD_VALUE_EURO"] = 0
        df["VALUE_EURO"] = 5000
        result = compute_red_flags(df)
        assert not result["F2"].any()

    def test_f2_handles_null_award_value(self, sample_base_df):
        df = sample_base_df.copy()
        df.loc[0, "AWARD_VALUE_EURO"] = None
        df.loc[0, "VALUE_EURO"] = 10000
        result = compute_red_flags(df)
        assert not result.loc[0, "F2"]

    def test_f2_handles_null_value(self, sample_base_df):
        df = sample_base_df.copy()
        df.loc[0, "VALUE_EURO"] = None
        result = compute_red_flags(df)
        assert not result.loc[0, "F2"]


class TestRedFlagF3NoPriorCall:
    def test_f3_true_nic(self, sample_base_df):
        df = sample_base_df.copy()
        df["TOP_TYPE"] = "NIC"
        result = compute_red_flags(df)
        assert result["F3"].all()

    def test_f3_true_awp(self, sample_base_df):
        df = sample_base_df.copy()
        df["TOP_TYPE"] = "AWP"
        result = compute_red_flags(df)
        assert result["F3"].all()

    def test_f3_false_open(self, sample_base_df):
        df = sample_base_df.copy()
        df["TOP_TYPE"] = "OPE"
        result = compute_red_flags(df)
        assert not result["F3"].any()

    def test_f3_false_negotiated(self, sample_base_df):
        df = sample_base_df.copy()
        df["TOP_TYPE"] = "NEG"
        result = compute_red_flags(df)
        assert not result["F3"].any()

    def test_f3_handles_null(self, sample_base_df):
        df = sample_base_df.copy()
        df.loc[0, "TOP_TYPE"] = None
        result = compute_red_flags(df)
        assert not result.loc[0, "F3"]


class TestRedFlagF5AwardToGroup:
    def test_f5_true_group_award(self, sample_base_df):
        df = sample_base_df.copy()
        df["YEAR"] = 2022
        df["B_AWARDED_TO_A_GROUP"] = "Y"
        result = compute_red_flags(df)
        assert result["F5"].all()

    def test_f5_false_not_group(self, sample_base_df):
        df = sample_base_df.copy()
        df["YEAR"] = 2022
        df["B_AWARDED_TO_A_GROUP"] = "N"
        result = compute_red_flags(df)
        assert not result["F5"].any()

    def test_f5_false_excluded_years(self, sample_base_df):
        df = sample_base_df.copy()
        df["YEAR"] = 2014
        df["B_AWARDED_TO_A_GROUP"] = "Y"
        result = compute_red_flags(df)
        assert not result["F5"].any()


class TestRedFlagF6HighValueSingleBidder:
    def test_f6_true_above_p95_single_bidder(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 1
        df["AWARD_VALUE_EURO"] = [10_000_000, 100, 100, 100, 100, 100]
        df["YEAR"] = 2022
        result = compute_red_flags(df)
        assert result.loc[0, "F6"]

    def test_f6_false_above_p95_multiple_bidders(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 3
        df["AWARD_VALUE_EURO"] = [10_000_000, 100, 100, 100, 100, 100]
        df["YEAR"] = 2022
        result = compute_red_flags(df)
        assert not result.loc[0, "F6"]

    def test_f6_false_below_p95_single_bidder(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 1
        df["AWARD_VALUE_EURO"] = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        df["YEAR"] = 2022
        result = compute_red_flags(df)
        assert not result["F6"].any()


class TestRedFlagF7LotFragmentation:
    def test_f7_true_awards_less_than_half_lots(self, sample_base_df):
        df = sample_base_df.copy()
        df["LOTS_NUMBER"] = 10
        df["NUMBER_AWARDS"] = 4
        result = compute_red_flags(df)
        assert result["F7"].all()

    def test_f7_false_awards_more_than_half_lots(self, sample_base_df):
        df = sample_base_df.copy()
        df["LOTS_NUMBER"] = 10
        df["NUMBER_AWARDS"] = 6
        result = compute_red_flags(df)
        assert not result["F7"].any()

    def test_f7_false_single_lot(self, sample_base_df):
        df = sample_base_df.copy()
        df["LOTS_NUMBER"] = 1
        df["NUMBER_AWARDS"] = 1
        result = compute_red_flags(df)
        assert not result["F7"].any()


class TestCompoundFlags:
    def test_comb_single_discrepancy(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 1
        df["AWARD_VALUE_EURO"] = 100
        df["VALUE_EURO"] = 2000
        result = compute_red_flags(df)
        assert (result["comb_single_discrepancy"] == (result["F1"] & result["F2"])).all()

    def test_comb_single_non_open_false_for_open(self, sample_base_df):
        df = sample_base_df.copy()
        df["NUMBER_OFFERS"] = 1
        df["TOP_TYPE"] = "OPE"
        result = compute_red_flags(df)
        assert not result["comb_single_non_open"].any()

    def test_comb_no_call_high_value(self, sample_base_df):
        df = sample_base_df.copy()
        df["TOP_TYPE"] = "NIC"
        df["NUMBER_OFFERS"] = 1
        df["AWARD_VALUE_EURO"] = [10_000_000, 100, 100, 100, 100, 100]
        df["VALUE_EURO"] = [10_000, 100, 100, 100, 100, 100]
        result = compute_red_flags(df)
        assert result.loc[0, "comb_no_call_high_value"]


class TestRedFlagColumnPresence:
    def test_all_expected_columns_present(self, sample_base_df):
        result = compute_red_flags(sample_base_df)
        expected = ["F1", "F2", "F3", "F5", "F6", "F7",
                     "comb_single_discrepancy", "comb_single_non_open",
                     "comb_no_call_high_value", "comb_frag_single"]
        for col in expected:
            assert col in result.columns, f"Missing column: {col}"

    def test_input_columns_preserved(self, sample_base_df):
        result = compute_red_flags(sample_base_df)
        for col in sample_base_df.columns:
            assert col in result.columns, f"Input column lost: {col}"

    def test_no_f4_column(self, sample_base_df):
        result = compute_red_flags(sample_base_df)
        assert "F4" not in result.columns
