"""
Pricing engine: rule-based price action recommendations for beer SKUs.

Logic:
  1. For each price scenario (% change), compute new volume using own-price elasticity:
       new_volume = current_volume * (1 + elasticity * price_pct_change)
  2. Compute cannibalization impact on sibling SKUs:
       cannibalized_volume = (current_volume - new_volume) * cannibalization_rate
       (positive = volume stolen from siblings when price rises and own volume falls)
  3. Compute baseline and new profit:
       profit = price * volume * unit_volume_ml * profit_pct_per_ml
  4. Net manufacturer profit impact accounts for both own SKU and cannibalized volume shift.
  5. Recommend the scenario with the highest net profit impact.
"""

import pandas as pd
import numpy as np
from pathlib import Path

SCENARIOS = [-0.10, -0.05, 0.00, +0.05, +0.10]
DATA_PATH = Path(__file__).parent.parent / "data" / "sample_skus.csv"


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def baseline_profit(row: pd.Series) -> float:
    """Total profit in £ for a SKU at current price and volume."""
    return (
        row["current_price_per_unit"]
        * row["volume_2025_units"]
        * row["unit_volume_ml"]
        * row["profit_pct_per_ml"]
    )


def run_scenarios(row: pd.Series) -> pd.DataFrame:
    """
    Evaluate all price scenarios for a single SKU row.
    Returns a DataFrame with one row per scenario.
    """
    records = []
    base_profit = baseline_profit(row)

    for pct in SCENARIOS:
        new_price = row["current_price_per_unit"] * (1 + pct)

        # Own-volume impact via elasticity
        volume_change_pct = row["elasticity"] * pct
        new_volume = row["volume_2025_units"] * (1 + volume_change_pct)
        new_volume = max(new_volume, 0)

        # Own-SKU profit
        own_profit = (
            new_price * new_volume * row["unit_volume_ml"] * row["profit_pct_per_ml"]
        )

        # Cannibalization: volume lost/gained by this SKU is partially absorbed by siblings.
        # When price rises, own volume drops → siblings gain that volume.
        # We assume the average sibling has the same profit% per mL and avg price as this SKU
        # (conservative simplification for iteration 0).
        volume_delta = new_volume - row["volume_2025_units"]  # negative if price up
        # Volume that shifts to/from siblings
        sibling_volume_shift = -volume_delta * row["cannibalization_rate"]
        # Profit from sibling shift (using same per-mL profit as proxy)
        sibling_profit_delta = (
            sibling_volume_shift
            * row["current_price_per_unit"]
            * row["unit_volume_ml"]
            * row["profit_pct_per_ml"]
        )

        net_profit = own_profit + sibling_profit_delta
        profit_impact = net_profit - base_profit
        profit_impact_pct = (profit_impact / base_profit * 100) if base_profit > 0 else 0

        records.append(
            {
                "scenario_pct": pct * 100,
                "new_price": round(new_price, 4),
                "new_volume": round(new_volume),
                "volume_change_pct": round(volume_change_pct * 100, 2),
                "own_profit": round(own_profit, 2),
                "sibling_profit_delta": round(sibling_profit_delta, 2),
                "net_profit": round(net_profit, 2),
                "profit_impact": round(profit_impact, 2),
                "profit_impact_pct": round(profit_impact_pct, 2),
                "baseline_profit": round(base_profit, 2),
            }
        )

    return pd.DataFrame(records)


def recommend(scenarios_df: pd.DataFrame) -> dict:
    """
    Pick the best scenario: highest net profit impact.
    If best scenario is 0% change, recommendation is Hold.
    """
    best_idx = scenarios_df["net_profit"].idxmax()
    best = scenarios_df.loc[best_idx]
    scenario_pct = best["scenario_pct"]

    if scenario_pct > 0:
        action = "Increase Price"
        color = "green"
    elif scenario_pct < 0:
        action = "Decrease Price"
        color = "red"
    else:
        action = "Hold Price"
        color = "gray"

    return {
        "action": action,
        "color": color,
        "recommended_scenario_pct": scenario_pct,
        "recommended_price": best["new_price"],
        "expected_profit_impact": best["profit_impact"],
        "expected_profit_impact_pct": best["profit_impact_pct"],
        "expected_volume_change_pct": best["volume_change_pct"],
    }


def analyse_sku(sku_id: str, df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Return (recommendation dict, scenarios DataFrame) for a given SKU ID."""
    row = df[df["sku_id"] == sku_id].iloc[0]
    scenarios = run_scenarios(row)
    rec = recommend(scenarios)
    return rec, scenarios


def simulate_portfolio(df: pd.DataFrame, price_changes: dict) -> pd.DataFrame:
    """
    Simulate portfolio-wide impact of custom price changes.

    Args:
        df: Full SKU DataFrame.
        price_changes: dict mapping sku_id -> price change percentage (e.g. {"ABI001": 5.0}).
                       SKUs not in the dict are treated as 0% change.

    Returns:
        DataFrame with one row per SKU showing baseline vs simulated metrics.
    """
    rows = []
    for _, sku in df.iterrows():
        sid = sku["sku_id"]
        pct = price_changes.get(sid, 0.0) / 100.0  # convert % to decimal

        base_prof = baseline_profit(sku)
        new_price = sku["current_price_per_unit"] * (1 + pct)

        # Own-volume impact
        volume_change_pct = sku["elasticity"] * pct
        new_volume = max(sku["volume_2025_units"] * (1 + volume_change_pct), 0)

        # Own-SKU profit
        own_profit = new_price * new_volume * sku["unit_volume_ml"] * sku["profit_pct_per_ml"]

        # Cannibalization
        volume_delta = new_volume - sku["volume_2025_units"]
        sibling_volume_shift = -volume_delta * sku["cannibalization_rate"]
        sibling_profit_delta = (
            sibling_volume_shift
            * sku["current_price_per_unit"]
            * sku["unit_volume_ml"]
            * sku["profit_pct_per_ml"]
        )

        net_profit = own_profit + sibling_profit_delta
        profit_impact = net_profit - base_prof

        rows.append({
            "sku_id": sid,
            "sku_name": sku["sku_name"],
            "manufacturer": sku["manufacturer"],
            "brand": sku["brand"],
            "segment": sku["price_segment"],
            "current_price": sku["current_price_per_unit"],
            "price_change_pct": pct * 100,
            "new_price": round(new_price, 4),
            "current_volume": sku["volume_2025_units"],
            "new_volume": round(new_volume),
            "volume_change_pct": round(volume_change_pct * 100, 2),
            "baseline_profit": round(base_prof, 2),
            "new_profit": round(net_profit, 2),
            "profit_impact": round(profit_impact, 2),
        })

    return pd.DataFrame(rows)
