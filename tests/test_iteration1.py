"""Tests for Iteration 1: CSV/Excel upload and verdict table."""

import sys
import io
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import pytest

from pricing_engine import load_data, analyse_sku, run_scenarios, recommend


# ── Fixture: load both datasets ──────────────────────────────────────────────
@pytest.fixture
def default_data():
    return load_data()


@pytest.fixture
def portfolio_data():
    return pd.read_excel(Path(__file__).parent.parent / "data" / "full_portfolio.xlsx")


# ── Pricing engine tests ─────────────────────────────────────────────────────
class TestPricingEngine:
    def test_default_data_loads(self, default_data):
        assert len(default_data) == 20
        assert "sku_id" in default_data.columns

    def test_portfolio_data_loads(self, portfolio_data):
        assert len(portfolio_data) == 42
        assert set(portfolio_data["manufacturer"].unique()) == {
            "AB InBev", "Heineken", "Carlsberg", "Molson Coors"
        }

    def test_portfolio_has_required_columns(self, portfolio_data):
        required = [
            "sku_id", "manufacturer", "brand", "sku_name", "price_segment",
            "current_price_per_unit", "elasticity", "cannibalization_rate",
            "profit_pct_per_ml", "volume_2025_units", "unit_volume_ml",
            "competitor_sku_1", "competitor_sku_2",
        ]
        for col in required:
            assert col in portfolio_data.columns, f"Missing column: {col}"

    def test_analyse_sku_returns_valid_recommendation(self, portfolio_data):
        rec, scenarios = analyse_sku("ABI001", portfolio_data)
        assert rec["action"] in ("Increase Price", "Decrease Price", "Hold Price")
        assert "recommended_price" in rec
        assert "expected_profit_impact" in rec
        assert len(scenarios) == 5  # 5 price scenarios

    def test_all_portfolio_skus_analysable(self, portfolio_data):
        """Every SKU in the portfolio should produce a valid recommendation."""
        for sku_id in portfolio_data["sku_id"]:
            rec, scenarios = analyse_sku(sku_id, portfolio_data)
            assert rec["action"] in ("Increase Price", "Decrease Price", "Hold Price")
            assert len(scenarios) == 5

    def test_competitor_refs_valid(self, portfolio_data):
        """All competitor_sku references should point to existing SKUs."""
        all_ids = set(portfolio_data["sku_id"])
        for _, row in portfolio_data.iterrows():
            assert row["competitor_sku_1"] in all_ids, \
                f"{row['sku_id']} has invalid competitor_sku_1: {row['competitor_sku_1']}"
            assert row["competitor_sku_2"] in all_ids, \
                f"{row['sku_id']} has invalid competitor_sku_2: {row['competitor_sku_2']}"

    def test_no_duplicate_sku_ids(self, portfolio_data):
        assert portfolio_data["sku_id"].is_unique

    def test_price_segments_valid(self, portfolio_data):
        valid = {"Core", "Premium", "Value"}
        assert set(portfolio_data["price_segment"].unique()).issubset(valid)


# ── Upload parsing tests ─────────────────────────────────────────────────────
class TestUploadParsing:
    def _encode_csv(self, df):
        csv_str = df.to_csv(index=False)
        encoded = base64.b64encode(csv_str.encode("utf-8")).decode("utf-8")
        return f"data:text/csv;base64,{encoded}"

    def _encode_excel(self, df):
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{encoded}"

    def test_parse_csv_upload(self, portfolio_data):
        from app import parse_upload
        contents = self._encode_csv(portfolio_data)
        result_df, error = parse_upload(contents, "test.csv")
        assert error is None
        assert len(result_df) == 42

    def test_parse_excel_upload(self, portfolio_data):
        from app import parse_upload
        contents = self._encode_excel(portfolio_data)
        result_df, error = parse_upload(contents, "test.xlsx")
        assert error is None
        assert len(result_df) == 42

    def test_parse_rejects_missing_columns(self):
        from app import parse_upload
        bad_df = pd.DataFrame({"foo": [1], "bar": [2]})
        contents = self._encode_csv(bad_df)
        result_df, error = parse_upload(contents, "bad.csv")
        assert result_df is None
        assert "Missing columns" in error

    def test_parse_rejects_unsupported_format(self):
        from app import parse_upload
        encoded = base64.b64encode(b"hello").decode("utf-8")
        contents = f"data:text/plain;base64,{encoded}"
        result_df, error = parse_upload(contents, "test.txt")
        assert result_df is None
        assert "Unsupported" in error


# ── Overview / verdict table tests ───────────────────────────────────────────
class TestOverviewData:
    def test_build_overview_data(self, portfolio_data):
        from app import build_overview_data
        overview = build_overview_data(portfolio_data)
        assert len(overview) == 42
        assert "action" in overview.columns
        assert "profit_impact" in overview.columns
        assert "sku_name" in overview.columns

    def test_verdict_values(self, portfolio_data):
        from app import build_overview_data
        overview = build_overview_data(portfolio_data)
        valid_actions = {"Increase Price", "Decrease Price", "Hold Price"}
        assert set(overview["action"].unique()).issubset(valid_actions)
