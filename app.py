import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, html, dcc, dash_table, Input, Output, callback, no_update
import dash_bootstrap_components as dbc

from pricing_engine import load_data, analyse_sku, baseline_profit, SCENARIOS

# ── Data ──────────────────────────────────────────────────────────────────────
df = load_data()

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Beer SKU Price Recommender",
    suppress_callback_exceptions=True,
)

# ── Precompute all-SKU recommendations for overview ─────────────────────────
def build_overview_data():
    rows = []
    for _, sku in df.iterrows():
        rec, scenarios = analyse_sku(sku["sku_id"], df)
        revenue = sku["current_price_per_unit"] * sku["volume_2025_units"]
        volume_change_pct = rec["expected_volume_change_pct"]
        projected_volume = sku["volume_2025_units"] * (1 + volume_change_pct / 100)
        projected_revenue = rec["recommended_price"] * projected_volume
        rows.append({
            "sku_id": sku["sku_id"],
            "manufacturer": sku["manufacturer"],
            "brand": sku["brand"],
            "sku_name": sku["sku_name"],
            "segment": sku["price_segment"],
            "current_price": sku["current_price_per_unit"],
            "volume": sku["volume_2025_units"],
            "elasticity": sku["elasticity"],
            "action": rec["action"],
            "recommended_price": rec["recommended_price"],
            "scenario_pct": rec["recommended_scenario_pct"],
            "profit_impact": rec["expected_profit_impact"],
            "profit_impact_pct": rec["expected_profit_impact_pct"],
            "baseline_profit": scenarios.iloc[0]["baseline_profit"],
            "revenue": revenue,
            "projected_volume": projected_volume,
            "projected_revenue": projected_revenue,
            "volume_change_pct": volume_change_pct,
        })
    return pd.DataFrame(rows)

overview_df = build_overview_data()

# ── Sidebar ──────────────────────────────────────────────────────────────────
sidebar = html.Div(
    [
        html.H4("Price Recommender", className="mb-3"),
        html.Hr(),
        dbc.Label("View"),
        dbc.Select(
            id="view-select",
            options=[
                {"label": "All Manufacturers", "value": "overview"},
                {"label": "SKU Detail", "value": "detail"},
            ],
            value="overview",
        ),
        html.Div(
            id="sku-filters",
            children=[
                dbc.Label("Manufacturer", className="mt-3"),
                dbc.Select(
                    id="manufacturer-select",
                    options=[{"label": m, "value": m} for m in sorted(df["manufacturer"].unique())],
                    value=sorted(df["manufacturer"].unique())[0],
                ),
                dbc.Label("Brand", className="mt-3"),
                dbc.Select(id="brand-select"),
                dbc.Label("Price Segment", className="mt-3"),
                dbc.Select(id="segment-select"),
                dbc.Label("SKU", className="mt-3"),
                dbc.Select(id="sku-select"),
            ],
        ),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16%",
        "padding": "2rem 1rem",
        "backgroundColor": "#f8f9fa",
        "overflowY": "auto",
    },
)

# ── Main content area ────────────────────────────────────────────────────────
content = html.Div(
    id="main-content",
    style={"marginLeft": "18%", "padding": "2rem"},
)

app.layout = html.Div([sidebar, content])


# ── Show/hide SKU filters based on view ─────────────────────────────────────
@callback(
    Output("sku-filters", "style"),
    Input("view-select", "value"),
)
def toggle_filters(view):
    if view == "overview":
        return {"display": "none"}
    return {"display": "block"}


# ── Route to correct view ───────────────────────────────────────────────────
@callback(
    Output("main-content", "children"),
    Input("view-select", "value"),
    Input("sku-select", "value"),
)
def render_view(view, sku_id):
    if view == "overview":
        return build_overview_layout()
    return build_detail_layout(sku_id)


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW VIEW — All Manufacturers
# ══════════════════════════════════════════════════════════════════════════════

def build_overview_layout():
    manufacturers = sorted(overview_df["manufacturer"].unique())

    # Summary KPIs across all SKUs
    total_skus = len(overview_df)
    increase_count = (overview_df["action"] == "Increase Price").sum()
    decrease_count = (overview_df["action"] == "Decrease Price").sum()
    hold_count = (overview_df["action"] == "Hold Price").sum()
    total_profit_impact = overview_df["profit_impact"].sum()

    summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Total SKUs", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(str(total_skus), className="mb-0"),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Increase Price", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(str(increase_count), className="mb-0", style={"color": "#155724"}),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Decrease Price", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(str(decrease_count), className="mb-0", style={"color": "#721c24"}),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Hold Price", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(str(hold_count), className="mb-0", style={"color": "#383d41"}),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Total Profit Impact", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(f"\u00a3{total_profit_impact:+,.0f}", className="mb-0"),
        ]), className="text-center"), width=True),
    ], className="mb-4")

    # Profit impact by manufacturer bar chart
    mfr_impact = overview_df.groupby("manufacturer")["profit_impact"].sum().reset_index()
    mfr_impact = mfr_impact.sort_values("profit_impact", ascending=True)
    fig_mfr = go.Figure(go.Bar(
        x=mfr_impact["profit_impact"],
        y=mfr_impact["manufacturer"],
        orientation="h",
        marker_color=["#2ecc71" if v >= 0 else "#e74c3c" for v in mfr_impact["profit_impact"]],
        text=[f"\u00a3{v:+,.0f}" for v in mfr_impact["profit_impact"]],
        textposition="outside",
    ))
    fig_mfr.update_layout(
        title="Total Recommended Profit Impact by Manufacturer",
        xaxis_title="Profit Impact (\u00a3)",
        plot_bgcolor="white",
        xaxis=dict(gridcolor="#eeeeee"),
        height=300,
        margin=dict(t=40, l=150),
    )
    fig_mfr.add_vline(x=0, line_dash="dash", line_color="gray")

    # Action distribution by manufacturer — stacked bar
    action_counts = overview_df.groupby(["manufacturer", "action"]).size().reset_index(name="count")
    action_color_map = {
        "Increase Price": "#2ecc71",
        "Decrease Price": "#e74c3c",
        "Hold Price": "#95a5a6",
    }
    fig_actions = go.Figure()
    for action in ["Decrease Price", "Hold Price", "Increase Price"]:
        subset = action_counts[action_counts["action"] == action]
        fig_actions.add_trace(go.Bar(
            x=subset["manufacturer"],
            y=subset["count"],
            name=action,
            marker_color=action_color_map[action],
        ))
    fig_actions.update_layout(
        barmode="stack",
        title="Recommended Actions by Manufacturer",
        yaxis_title="Number of SKUs",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"),
        height=300,
        margin=dict(t=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # ── Market share: before vs after price actions ────────────────────────
    mfr_vol_current = overview_df.groupby("manufacturer")["volume"].sum()
    mfr_vol_projected = overview_df.groupby("manufacturer")["projected_volume"].sum()
    mfr_rev_current = overview_df.groupby("manufacturer")["revenue"].sum()
    mfr_rev_projected = overview_df.groupby("manufacturer")["projected_revenue"].sum()

    # Volume share % (before and after)
    total_vol_current = mfr_vol_current.sum()
    total_vol_projected = mfr_vol_projected.sum()
    vol_share_current = (mfr_vol_current / total_vol_current * 100).round(1)
    vol_share_projected = (mfr_vol_projected / total_vol_projected * 100).round(1)
    vol_share_delta = (vol_share_projected - vol_share_current).round(2)

    mfr_colors = dict(zip(
        sorted(overview_df["manufacturer"].unique()),
        px.colors.qualitative.Set2,
    ))

    from plotly.subplots import make_subplots
    fig_vol_share = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["Current Volume Share", "Projected Volume Share"],
    )
    mfr_order = sorted(overview_df["manufacturer"].unique())
    pie_colors = [mfr_colors[m] for m in mfr_order]
    fig_vol_share.add_trace(go.Pie(
        labels=mfr_order,
        values=[mfr_vol_current[m] for m in mfr_order],
        hole=0.45,
        marker_colors=pie_colors,
        textinfo="label+percent",
        textposition="outside",
    ), row=1, col=1)
    fig_vol_share.add_trace(go.Pie(
        labels=mfr_order,
        values=[mfr_vol_projected[m] for m in mfr_order],
        hole=0.45,
        marker_colors=pie_colors,
        textinfo="label+percent",
        textposition="outside",
    ), row=1, col=2)
    fig_vol_share.update_layout(
        title="Volume Market Share: Before vs After Price Actions",
        height=380,
        margin=dict(t=60, b=20),
        showlegend=False,
    )

    # Revenue share % (before and after)
    total_rev_current = mfr_rev_current.sum()
    total_rev_projected = mfr_rev_projected.sum()
    rev_share_current = (mfr_rev_current / total_rev_current * 100).round(1)
    rev_share_projected = (mfr_rev_projected / total_rev_projected * 100).round(1)
    rev_share_delta = (rev_share_projected - rev_share_current).round(2)

    fig_rev_share = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["Current Revenue Share", "Projected Revenue Share"],
    )
    fig_rev_share.add_trace(go.Pie(
        labels=mfr_order,
        values=[mfr_rev_current[m] for m in mfr_order],
        hole=0.45,
        marker_colors=pie_colors,
        textinfo="label+percent",
        textposition="outside",
    ), row=1, col=1)
    fig_rev_share.add_trace(go.Pie(
        labels=mfr_order,
        values=[mfr_rev_projected[m] for m in mfr_order],
        hole=0.45,
        marker_colors=pie_colors,
        textinfo="label+percent",
        textposition="outside",
    ), row=1, col=2)
    fig_rev_share.update_layout(
        title="Revenue Market Share: Before vs After Price Actions",
        height=380,
        margin=dict(t=60, b=20),
        showlegend=False,
    )

    # Market share shift summary bar — shows the pp change per manufacturer
    fig_share_shift = go.Figure()
    fig_share_shift.add_trace(go.Bar(
        x=mfr_order,
        y=[vol_share_delta[m] for m in mfr_order],
        name="Volume Share \u0394",
        marker_color="#3498db",
        text=[f"{vol_share_delta[m]:+.2f}pp" for m in mfr_order],
        textposition="outside",
    ))
    fig_share_shift.add_trace(go.Bar(
        x=mfr_order,
        y=[rev_share_delta[m] for m in mfr_order],
        name="Revenue Share \u0394",
        marker_color="#e67e22",
        text=[f"{rev_share_delta[m]:+.2f}pp" for m in mfr_order],
        textposition="outside",
    ))
    fig_share_shift.update_layout(
        title="Market Share Shift After Price Actions (percentage points)",
        yaxis_title="Change (pp)",
        barmode="group",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"),
        height=350,
        margin=dict(t=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_share_shift.add_hline(y=0, line_dash="dash", line_color="gray")

    # Per-SKU profit impact waterfall (sorted by impact)
    sku_sorted = overview_df.sort_values("profit_impact", ascending=True)
    fig_waterfall = go.Figure(go.Bar(
        x=sku_sorted["profit_impact"],
        y=sku_sorted["sku_name"],
        orientation="h",
        marker_color=[
            "#2ecc71" if a == "Increase Price"
            else "#e74c3c" if a == "Decrease Price"
            else "#95a5a6"
            for a in sku_sorted["action"]
        ],
        text=[f"\u00a3{v:+,.0f}" for v in sku_sorted["profit_impact"]],
        textposition="outside",
    ))
    fig_waterfall.update_layout(
        title="Profit Impact by SKU (All Manufacturers)",
        xaxis_title="Profit Impact (\u00a3)",
        plot_bgcolor="white",
        xaxis=dict(gridcolor="#eeeeee"),
        height=max(400, len(sku_sorted) * 28),
        margin=dict(t=40, l=220),
    )
    fig_waterfall.add_vline(x=0, line_dash="dash", line_color="gray")

    # Per-manufacturer sections
    manufacturer_sections = []
    for mfr in manufacturers:
        mfr_skus = overview_df[overview_df["manufacturer"] == mfr]
        table_data = []
        for _, row in mfr_skus.iterrows():
            table_data.append({
                "SKU": row["sku_name"],
                "Brand": row["brand"],
                "Segment": row["segment"],
                "Current Price": f"\u00a3{row['current_price']:.2f}",
                "Volume 2025": f"{row['volume']:,.0f}",
                "Elasticity": f"{row['elasticity']:.2f}",
                "Action": row["action"],
                "New Price": f"\u00a3{row['recommended_price']:.2f}",
                "Change": f"{row['scenario_pct']:+.0f}%",
                "Profit Impact": f"\u00a3{row['profit_impact']:+,.0f}",
                "Impact %": f"{row['profit_impact_pct']:+.1f}%",
            })

        mfr_profit = mfr_skus["profit_impact"].sum()
        mfr_badge_color = "success" if mfr_profit >= 0 else "danger"

        manufacturer_sections.append(
            dbc.Card([
                dbc.CardHeader(
                    dbc.Row([
                        dbc.Col(html.H5(mfr, className="mb-0"), width="auto"),
                        dbc.Col(
                            dbc.Badge(
                                f"\u00a3{mfr_profit:+,.0f} total impact",
                                color=mfr_badge_color,
                                className="fs-6",
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            html.Span(f"{len(mfr_skus)} SKUs", className="text-muted"),
                            width="auto",
                        ),
                    ], align="center", justify="between"),
                ),
                dbc.CardBody(
                    dash_table.DataTable(
                        data=table_data,
                        columns=[{"name": c, "id": c} for c in table_data[0]],
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "center", "padding": "6px", "fontSize": "0.85rem"},
                        style_header={
                            "backgroundColor": "#2c3e50",
                            "color": "white",
                            "fontWeight": "bold",
                        },
                        style_data_conditional=[
                            {
                                "if": {
                                    "filter_query": '{Action} = "Increase Price"',
                                    "column_id": "Action",
                                },
                                "backgroundColor": "#d4edda",
                                "color": "#155724",
                                "fontWeight": "bold",
                            },
                            {
                                "if": {
                                    "filter_query": '{Action} = "Decrease Price"',
                                    "column_id": "Action",
                                },
                                "backgroundColor": "#f8d7da",
                                "color": "#721c24",
                                "fontWeight": "bold",
                            },
                            {
                                "if": {
                                    "filter_query": '{Action} = "Hold Price"',
                                    "column_id": "Action",
                                },
                                "backgroundColor": "#e2e3e5",
                                "color": "#383d41",
                                "fontWeight": "bold",
                            },
                        ],
                    ),
                ),
            ], className="mb-3")
        )

    return html.Div([
        html.H3("All Manufacturers Overview", className="mb-1"),
        html.P("Price recommendations across all 20 beer SKUs", className="text-muted mb-3"),
        html.Hr(),
        summary_cards,
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_mfr), width=6),
            dbc.Col(dcc.Graph(figure=fig_actions), width=6),
        ], className="mb-4"),
        html.Hr(),
        html.H5("Market Share: Before vs After Price Actions", className="mb-3"),
        dcc.Graph(figure=fig_vol_share),
        dcc.Graph(figure=fig_rev_share, className="mt-2"),
        dcc.Graph(figure=fig_share_shift, className="mt-2 mb-4"),
        html.Hr(),
        html.H5("Impact of Recommended Price Changes", className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_waterfall), width=12),
        ], className="mb-4"),
        html.Hr(),
        html.H5("Manufacturer Breakdown", className="mb-3"),
        *manufacturer_sections,
    ])


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL VIEW — Single SKU (existing)
# ══════════════════════════════════════════════════════════════════════════════

def build_detail_layout(sku_id):
    if not sku_id:
        return html.Div("Select a SKU from the sidebar.", className="text-muted mt-4")

    sku_row = df[df["sku_id"] == sku_id].iloc[0]
    rec, scenarios = analyse_sku(sku_id, df)

    # Subtitle
    subtitle = f"{sku_row['manufacturer']} \u00b7 {sku_row['brand']} \u00b7 {sku_row['price_segment']}"

    # KPI cards
    kpis = [
        ("Current Price", f"\u00a3{sku_row['current_price_per_unit']:.2f}"),
        ("Volume 2025", f"{sku_row['volume_2025_units']:,.0f} units"),
        ("Elasticity", f"{sku_row['elasticity']:.2f}"),
        ("Cannibalization Rate", f"{sku_row['cannibalization_rate']:.0%}"),
        ("Profit % per mL", f"{sku_row['profit_pct_per_ml']:.0%}"),
    ]
    kpi_cards = dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.P(label, className="text-muted mb-1", style={"fontSize": "0.85rem"}),
                    html.H5(value, className="mb-0"),
                ]),
                className="text-center",
            ),
            width=True,
        )
        for label, value in kpis
    ], className="mb-3")

    # Recommendation banner
    action_colors = {
        "Increase Price": {"bg": "#d4edda", "text": "#155724"},
        "Decrease Price": {"bg": "#f8d7da", "text": "#721c24"},
        "Hold Price": {"bg": "#e2e3e5", "text": "#383d41"},
    }
    colors = action_colors.get(rec["action"], {"bg": "#e2e3e5", "text": "#383d41"})

    recommendation_row = dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4(rec["action"], className="mb-1"),
                    html.H5(
                        f"\u00a3{rec['recommended_price']:.2f} ({rec['recommended_scenario_pct']:+.0f}%)",
                        className="mb-0",
                    ),
                ]),
                style={
                    "backgroundColor": colors["bg"],
                    "color": colors["text"],
                    "textAlign": "center",
                },
            ),
            width=4,
        ),
        dbc.Col(
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.P("Net Profit Impact", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
                    html.H5(f"\u00a3{rec['expected_profit_impact']:,.0f}", className="mb-0"),
                    html.Small(f"{rec['expected_profit_impact_pct']:+.1f}%", className="text-muted"),
                ]), className="text-center")),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.P("Expected Volume \u0394", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
                    html.H5(f"{rec['expected_volume_change_pct']:+.1f}%", className="mb-0"),
                ]), className="text-center")),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.P("Recommended Price", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
                    html.H5(f"\u00a3{rec['recommended_price']:.4f}", className="mb-0"),
                    html.Small(f"vs \u00a3{sku_row['current_price_per_unit']:.2f} today", className="text-muted"),
                ]), className="text-center")),
            ]),
            width=8,
        ),
    ], className="mb-3")

    # Scenario table
    best_pct = rec["recommended_scenario_pct"]
    table_data = []
    for _, row in scenarios.iterrows():
        table_data.append({
            "Price \u0394 (%)": f"{row['scenario_pct']:+.0f}%",
            "New Price (\u00a3)": f"\u00a3{row['new_price']:.4f}",
            "New Volume (units)": f"{row['new_volume']:,.0f}",
            "Volume \u0394 (%)": f"{row['volume_change_pct']:+.1f}%",
            "Own SKU Profit (\u00a3)": f"\u00a3{row['own_profit']:,.0f}",
            "Sibling Profit \u0394 (\u00a3)": f"\u00a3{row['sibling_profit_delta']:,.0f}",
            "Net Profit (\u00a3)": f"\u00a3{row['net_profit']:,.0f}",
            "Profit Impact (\u00a3)": f"\u00a3{row['profit_impact']:+,.0f}",
            "Profit Impact (%)": f"{row['profit_impact_pct']:+.1f}%",
        })

    best_pct_str = f"{best_pct:+.0f}%"
    scenario_table = dash_table.DataTable(
        data=table_data,
        columns=[{"name": c, "id": c} for c in table_data[0]],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "0.9rem"},
        style_header={
            "backgroundColor": "#2c3e50",
            "color": "white",
            "fontWeight": "bold",
        },
        style_data_conditional=[
            {
                "if": {
                    "filter_query": '{Price \u0394 (%)} = "' + best_pct_str + '"',
                },
                "backgroundColor": "#d4edda",
                "fontWeight": "bold",
            }
        ],
    )

    # Profit chart
    bar_colors = [
        "#2ecc71" if p == best_pct else ("#e74c3c" if p < 0 else "#3498db")
        for p in scenarios["scenario_pct"]
    ]
    fig = go.Figure(
        go.Bar(
            x=[f"{p:+.0f}%" for p in scenarios["scenario_pct"]],
            y=scenarios["profit_impact"],
            marker_color=bar_colors,
            text=[f"\u00a3{v:+,.0f}" for v in scenarios["profit_impact"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis_title="Price Change Scenario",
        yaxis_title="Net Profit Impact (\u00a3)",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"),
        height=400,
        margin=dict(t=30),
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    # Competitor table
    comp_ids = [sku_row["competitor_sku_1"], sku_row["competitor_sku_2"]]
    comp_df = df[df["sku_id"].isin(comp_ids)]
    comp_data = []
    for _, r in comp_df.iterrows():
        comp_data.append({
            "SKU": r["sku_name"],
            "Segment": r["price_segment"],
            "Price (\u00a3)": f"\u00a3{r['current_price_per_unit']:.2f}",
            "Elasticity": f"{r['elasticity']:.2f}",
            "Cannibalization Rate": f"{r['cannibalization_rate']:.0%}",
            "Volume 2025": f"{r['volume_2025_units']:,.0f}",
        })

    competitor_table = dash_table.DataTable(
        data=comp_data,
        columns=[{"name": c, "id": c} for c in comp_data[0]] if comp_data else [],
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "0.9rem"},
        style_header={
            "backgroundColor": "#2c3e50",
            "color": "white",
            "fontWeight": "bold",
        },
    )

    return html.Div([
        html.H3("Beer SKU Price Recommender", className="mb-1"),
        html.P(subtitle, className="text-muted mb-3"),
        html.Hr(),
        kpi_cards,
        html.Hr(),
        html.H5("Recommended Action"),
        recommendation_row,
        html.Hr(),
        html.H5("Scenario Analysis"),
        html.Div(scenario_table, className="mb-4"),
        html.H5("Profit Impact by Scenario"),
        dcc.Graph(figure=fig),
        html.Hr(),
        html.H5("Sibling / Competitor SKUs"),
        competitor_table,
    ])


# ── Cascading filter callbacks ───────────────────────────────────────────────
@callback(
    Output("brand-select", "options"),
    Output("brand-select", "value"),
    Input("manufacturer-select", "value"),
)
def update_brands(manufacturer):
    if not manufacturer:
        return [], None
    filtered = df[df["manufacturer"] == manufacturer]
    brands = sorted(filtered["brand"].unique())
    options = [{"label": b, "value": b} for b in brands]
    return options, brands[0]


@callback(
    Output("segment-select", "options"),
    Output("segment-select", "value"),
    Input("manufacturer-select", "value"),
    Input("brand-select", "value"),
)
def update_segments(manufacturer, brand):
    if not manufacturer or not brand:
        return [], None
    filtered = df[(df["manufacturer"] == manufacturer) & (df["brand"] == brand)]
    segments = sorted(filtered["price_segment"].unique())
    options = [{"label": "All", "value": "All"}] + [
        {"label": s, "value": s} for s in segments
    ]
    return options, "All"


@callback(
    Output("sku-select", "options"),
    Output("sku-select", "value"),
    Input("manufacturer-select", "value"),
    Input("brand-select", "value"),
    Input("segment-select", "value"),
)
def update_skus(manufacturer, brand, segment):
    if not manufacturer or not brand:
        return [], None
    filtered = df[(df["manufacturer"] == manufacturer) & (df["brand"] == brand)]
    if segment and segment != "All":
        filtered = filtered[filtered["price_segment"] == segment]
    options = [
        {"label": row["sku_name"], "value": row["sku_id"]}
        for _, row in filtered.iterrows()
    ]
    return options, options[0]["value"] if options else None


if __name__ == "__main__":
    app.run(debug=True)
