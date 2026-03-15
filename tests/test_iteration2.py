"""Tests for Iteration 2: Scenario Simulator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import pytest

from pricing_engine import load_data, simulate_portfolio


@pytest.fixture
def portfolio_data():
    return pd.read_excel(Path(__file__).parent.parent / "data" / "full_portfolio.xlsx")


@pytest.fixture
def default_data():
    return load_data()


class TestSimulatePortfolio:
    def test_no_changes_zero_impact(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {})
        assert len(result) == 42
        assert (result["profit_impact"] == 0).all()

    def test_single_sku_change(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {"ABI001": 5.0})
        changed = result[result["sku_id"] == "ABI001"].iloc[0]
        assert changed["price_change_pct"] == 5.0
        assert changed["new_price"] > changed["current_price"]
        assert changed["profit_impact"] != 0

    def test_unchanged_skus_zero_impact(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {"ABI001": 10.0})
        unchanged = result[result["sku_id"] != "ABI001"]
        assert (unchanged["profit_impact"] == 0).all()

    def test_negative_price_change(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {"ABI001": -10.0})
        changed = result[result["sku_id"] == "ABI001"].iloc[0]
        assert changed["new_price"] < changed["current_price"]
        assert changed["new_volume"] > changed["current_volume"]  # lower price -> more volume

    def test_positive_price_change_reduces_volume(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {"ABI001": 10.0})
        changed = result[result["sku_id"] == "ABI001"].iloc[0]
        assert changed["new_volume"] < changed["current_volume"]

    def test_multi_sku_changes(self, portfolio_data):
        changes = {"ABI001": -10.0, "HEI001": 5.0, "MC001": -5.0}
        result = simulate_portfolio(portfolio_data, changes)
        assert len(result) == 42
        for sku_id, pct in changes.items():
            row = result[result["sku_id"] == sku_id].iloc[0]
            assert row["price_change_pct"] == pct

    def test_result_columns(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {"ABI001": 5.0})
        expected_cols = [
            "sku_id", "sku_name", "manufacturer", "brand", "segment",
            "current_price", "price_change_pct", "new_price",
            "current_volume", "new_volume", "volume_change_pct",
            "baseline_profit", "new_profit", "profit_impact",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_works_with_default_data(self, default_data):
        result = simulate_portfolio(default_data, {"SKU001": -5.0})
        assert len(result) == 20
        changed = result[result["sku_id"] == "SKU001"].iloc[0]
        assert changed["price_change_pct"] == -5.0

    def test_zero_change_is_noop(self, portfolio_data):
        result = simulate_portfolio(portfolio_data, {"ABI001": 0.0})
        row = result[result["sku_id"] == "ABI001"].iloc[0]
        assert row["profit_impact"] == 0
