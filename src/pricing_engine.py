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


# ══════════════════════════════════════════════════════════════════════════════
# Iteration 5 — analytics helpers
# ══════════════════════════════════════════════════════════════════════════════

def generate_cross_elasticity_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build an N×N synthetic cross-elasticity matrix from own-price elasticity,
    cannibalization rate, segment, manufacturer, and competitor links.
    """
    skus = df["sku_id"].tolist()
    n = len(skus)
    matrix = np.zeros((n, n))

    # Build lookup helpers
    idx = {s: i for i, s in enumerate(skus)}
    mfr = df.set_index("sku_id")["manufacturer"].to_dict()
    seg = df.set_index("sku_id")["price_segment"].to_dict()
    elas = df.set_index("sku_id")["elasticity"].to_dict()
    cann = df.set_index("sku_id")["cannibalization_rate"].to_dict()
    comp1 = df.set_index("sku_id")["competitor_sku_1"].to_dict()
    comp2 = df.set_index("sku_id")["competitor_sku_2"].to_dict()

    competitor_pairs = set()
    for s in skus:
        for c in (comp1.get(s), comp2.get(s)):
            if c and c in idx:
                competitor_pairs.add((s, c))
                competitor_pairs.add((c, s))

    for i, a in enumerate(skus):
        for j, b in enumerate(skus):
            if i == j:
                continue

            same_mfr = mfr[a] == mfr[b]
            same_seg = seg[a] == seg[b]

            if same_mfr and same_seg:
                val = cann[a] * 0.5
            elif same_mfr:
                val = cann[a] * 0.2
            elif same_seg:
                val = abs(elas[a]) * 0.05
            else:
                val = 0.015

            # Competitor bonus
            if (a, b) in competitor_pairs:
                val *= 1.5

            matrix[i][j] = np.clip(val, 0.0, 0.3)

    return pd.DataFrame(matrix, index=skus, columns=skus)


def compute_cannibalization_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Per-SKU cannibalization breakdown: cannibalised volume, safe volume, severity."""
    out = df[["sku_id", "sku_name", "manufacturer", "brand"]].copy()
    out["segment"] = df["price_segment"]
    out["cannibalization_rate"] = df["cannibalization_rate"]
    out["cannibalised_volume"] = (df["volume_2025_units"] * df["cannibalization_rate"]).round().astype(int)
    out["safe_volume"] = (df["volume_2025_units"] - out["cannibalised_volume"]).astype(int)
    out["total_volume"] = df["volume_2025_units"]
    out["severity"] = pd.cut(
        df["cannibalization_rate"],
        bins=[-np.inf, 0.08, 0.12, np.inf],
        labels=["Low", "Moderate", "High"],
    )
    return out.reset_index(drop=True)


def generate_executive_insights(df: pd.DataFrame, overview_data: pd.DataFrame) -> dict:
    """Auto-generate numbered insights and actionable recommendations."""

    manufacturers = sorted(df["manufacturer"].unique())
    total_skus = len(df)

    # ── Market structure ──
    mfr_skus = df.groupby("manufacturer").size().to_dict()
    mfr_vol = df.groupby("manufacturer")["volume_2025_units"].sum().to_dict()
    total_vol = sum(mfr_vol.values())
    mfr_share = {m: round(v / total_vol * 100, 1) for m, v in mfr_vol.items()}
    market_leader = max(mfr_share, key=mfr_share.get)

    market_structure = {
        "total_skus": total_skus,
        "manufacturers": manufacturers,
        "sku_counts": mfr_skus,
        "volume_shares": mfr_share,
        "market_leader": market_leader,
        "segments": sorted(df["price_segment"].unique()),
    }

    # ── Elasticity risks ──
    highly_elastic = df[df["elasticity"] < -2.0].sort_values("elasticity")
    elastic = df[(df["elasticity"] >= -2.0) & (df["elasticity"] < -1.5)]
    inelastic = df[df["elasticity"] >= -1.5]

    elasticity_insights = []
    for _, sku in highly_elastic.head(5).iterrows():
        elasticity_insights.append(
            f"{sku['sku_name']} has high price sensitivity (elasticity {sku['elasticity']:.2f}). "
            f"A 5% price increase would reduce volume by {abs(sku['elasticity'] * 5):.1f}%."
        )
    if not elasticity_insights:
        elasticity_insights.append("No SKUs show extreme price sensitivity (all elasticities > -2.0).")

    elasticity_risks = {
        "highly_elastic_count": len(highly_elastic),
        "elastic_count": len(elastic),
        "inelastic_count": len(inelastic),
        "insights": elasticity_insights,
    }

    # ── Cannibalization threats ──
    cann_df = compute_cannibalization_risk(df)
    high_risk = cann_df[cann_df["severity"] == "High"]
    threats_by_mfr = {}
    for m in manufacturers:
        mfr_high = high_risk[high_risk["manufacturer"] == m]
        if not mfr_high.empty:
            names = mfr_high["sku_name"].tolist()
            total_at_risk = mfr_high["cannibalised_volume"].sum()
            threats_by_mfr[m] = {
                "skus": names,
                "volume_at_risk": total_at_risk,
            }

    cannibalization_threats = {
        "high_risk_count": len(high_risk),
        "moderate_count": len(cann_df[cann_df["severity"] == "Moderate"]),
        "low_count": len(cann_df[cann_df["severity"] == "Low"]),
        "by_manufacturer": threats_by_mfr,
    }

    # ── Recommendations ──
    recommendations = []

    # Price decreases for highly elastic value SKUs
    elastic_value = highly_elastic[highly_elastic["price_segment"] == "Value"]
    for _, sku in elastic_value.head(2).iterrows():
        recommendations.append({
            "direction": "↓",
            "sku": sku["sku_name"],
            "rationale": f"High elasticity ({sku['elasticity']:.2f}) in Value segment — "
                         f"a price cut would drive significant volume gains.",
        })

    # Price increases for inelastic premium SKUs
    inelastic_prem = inelastic[inelastic["price_segment"] == "Premium"]
    for _, sku in inelastic_prem.head(2).iterrows():
        recommendations.append({
            "direction": "↑",
            "sku": sku["sku_name"],
            "rationale": f"Low sensitivity ({sku['elasticity']:.2f}) in Premium segment — "
                         f"price increase would boost profit with limited volume loss.",
        })

    # Hold for moderate elasticity, high cannibalization
    mod_high_cann = df[(df["elasticity"].between(-2.0, -1.5)) & (df["cannibalization_rate"] >= 0.10)]
    for _, sku in mod_high_cann.head(1).iterrows():
        recommendations.append({
            "direction": "→",
            "sku": sku["sku_name"],
            "rationale": f"Moderate sensitivity ({sku['elasticity']:.2f}) but high cannibalization "
                         f"({sku['cannibalization_rate']:.0%}) — hold price to avoid sibling erosion.",
        })

    # Ensure at least 3 recommendations
    if len(recommendations) < 3:
        for _, sku in overview_data.head(3 - len(recommendations)).iterrows():
            action = sku.get("action", "Hold Price")
            arrow = "↑" if "Increase" in action else "↓" if "Decrease" in action else "→"
            recommendations.append({
                "direction": arrow,
                "sku": sku["sku_name"],
                "rationale": f"Optimal action based on elasticity/cannibalization trade-off.",
            })

    return {
        "market_structure": market_structure,
        "elasticity_risks": elasticity_risks,
        "cannibalization_threats": cannibalization_threats,
        "recommendations": recommendations[:5],
    }
