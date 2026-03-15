import sys
import io
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, dash_table, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc

from pricing_engine import load_data, analyse_sku, run_scenarios, recommend, baseline_profit, simulate_portfolio

# ── Required columns for uploaded files ──────────────────────────────────────
REQUIRED_COLS = [
    "sku_id", "manufacturer", "brand", "sku_name", "price_segment",
    "current_price_per_unit", "elasticity", "cannibalization_rate",
    "profit_pct_per_ml", "volume_2025_units", "unit_volume_ml",
    "competitor_sku_1", "competitor_sku_2",
]

# ── Default data ─────────────────────────────────────────────────────────────
default_df = load_data()

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Beer SKU Price Recommender",
    suppress_callback_exceptions=True,
)


def build_overview_data(df: pd.DataFrame) -> pd.DataFrame:
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


def parse_upload(contents, filename):
    """Parse uploaded CSV or Excel file. Returns (df, error_msg)."""
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    try:
        if filename.endswith(".csv"):
            uploaded_df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        elif filename.endswith((".xlsx", ".xls")):
            uploaded_df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None, f"Unsupported file type: {filename}. Use .csv or .xlsx"
    except Exception as e:
        return None, f"Error reading file: {e}"

    missing = [c for c in REQUIRED_COLS if c not in uploaded_df.columns]
    if missing:
        return None, f"Missing columns: {', '.join(missing)}"

    return uploaded_df, None


# ── Layout ───────────────────────────────────────────────────────────────────
sidebar = html.Div(
    [
        html.H4("Price Recommender", className="mb-3"),
        html.Hr(),
        # File upload
        dbc.Label("Upload Portfolio"),
        dcc.Upload(
            id="upload-data",
            children=dbc.Button(
                "Upload CSV / Excel",
                color="primary",
                className="w-100 mb-2",
                size="sm",
            ),
            accept=".csv,.xlsx,.xls",
        ),
        html.Div(id="upload-status", className="mb-2"),
        html.Hr(),
        # View selector
        dbc.Label("View"),
        dbc.Select(
            id="view-select",
            options=[
                {"label": "All Manufacturers", "value": "overview"},
                {"label": "Scenario Simulator", "value": "simulator"},
                {"label": "SKU Detail", "value": "detail"},
            ],
            value="overview",
        ),
        html.Div(
            id="sku-filters",
            children=[
                dbc.Label("Manufacturer", className="mt-3"),
                dbc.Select(id="manufacturer-select"),
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

content = html.Div(id="main-content", style={"marginLeft": "18%", "padding": "2rem"})

app.layout = html.Div([
    dcc.Store(id="data-store", data=default_df.to_json(date_format="iso", orient="split")),
    dcc.Store(id="sim-price-changes", data={}),
    sidebar,
    content,
])


# ── Upload callback ──────────────────────────────────────────────────────────
@callback(
    Output("data-store", "data"),
    Output("upload-status", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def handle_upload(contents, filename):
    if contents is None:
        return no_update, no_update

    uploaded_df, error = parse_upload(contents, filename)
    if error:
        return no_update, dbc.Alert(error, color="danger", className="py-1 px-2 mb-0", style={"fontSize": "0.8rem"})

    status = dbc.Alert(
        f"Loaded {filename} — {len(uploaded_df)} SKUs",
        color="success",
        className="py-1 px-2 mb-0",
        style={"fontSize": "0.8rem"},
    )
    return uploaded_df.to_json(date_format="iso", orient="split"), status


# ── Populate manufacturer dropdown from data ─────────────────────────────────
@callback(
    Output("manufacturer-select", "options"),
    Output("manufacturer-select", "value"),
    Input("data-store", "data"),
)
def update_manufacturer_options(json_data):
    df = pd.read_json(io.StringIO(json_data), orient="split")
    manufacturers = sorted(df["manufacturer"].unique())
    options = [{"label": m, "value": m} for m in manufacturers]
    return options, manufacturers[0]


# ── Show/hide SKU filters based on view ──────────────────────────────────────
@callback(
    Output("sku-filters", "style"),
    Input("view-select", "value"),
)
def toggle_filters(view):
    if view in ("overview", "simulator"):
        return {"display": "none"}
    return {"display": "block"}


# ── Route to correct view ───────────────────────────────────────────────────
@callback(
    Output("main-content", "children"),
    Input("view-select", "value"),
    Input("sku-select", "value"),
    Input("data-store", "data"),
)
def render_view(view, sku_id, json_data):
    df = pd.read_json(io.StringIO(json_data), orient="split")
    if view == "overview":
        return build_overview_layout(df)
    if view == "simulator":
        return build_simulator_layout(df)
    return build_detail_layout(sku_id, df)


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW VIEW
# ══════════════════════════════════════════════════════════════════════════════

def build_overview_layout(df):
    overview_df = build_overview_data(df)
    manufacturers = sorted(overview_df["manufacturer"].unique())
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

    # ── Sortable verdict table (Iteration 1 core feature) ────────────────
    verdict_data = []
    for _, row in overview_df.iterrows():
        verdict_data.append({
            "SKU": row["sku_name"],
            "Manufacturer": row["manufacturer"],
            "Brand": row["brand"],
            "Segment": row["segment"],
            "Current Price": round(row["current_price"], 2),
            "Verdict": row["action"].replace(" Price", ""),
            "New Price": round(row["recommended_price"], 2),
            "Price Change": f"{row['scenario_pct']:+.0f}%",
            "Revenue Impact": round(row["profit_impact"], 0),
            "Impact %": round(row["profit_impact_pct"], 1),
        })

    verdict_table = dash_table.DataTable(
        id="verdict-table",
        data=verdict_data,
        columns=[
            {"name": "SKU", "id": "SKU"},
            {"name": "Manufacturer", "id": "Manufacturer"},
            {"name": "Brand", "id": "Brand"},
            {"name": "Segment", "id": "Segment"},
            {"name": "Current Price (\u00a3)", "id": "Current Price", "type": "numeric",
             "format": {"specifier": "$.2f"}},
            {"name": "Verdict", "id": "Verdict"},
            {"name": "New Price (\u00a3)", "id": "New Price", "type": "numeric",
             "format": {"specifier": "$.2f"}},
            {"name": "Price Change", "id": "Price Change"},
            {"name": "Revenue Impact (\u00a3)", "id": "Revenue Impact", "type": "numeric",
             "format": {"specifier": "$,.0f"}},
            {"name": "Impact %", "id": "Impact %", "type": "numeric",
             "format": {"specifier": "+.1f"}},
        ],
        sort_action="native",
        sort_mode="multi",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "0.9rem"},
        style_header={
            "backgroundColor": "#2c3e50",
            "color": "white",
            "fontWeight": "bold",
        },
        style_data_conditional=[
            {
                "if": {"filter_query": '{Verdict} = "Increase"', "column_id": "Verdict"},
                "backgroundColor": "#d4edda", "color": "#155724", "fontWeight": "bold",
            },
            {
                "if": {"filter_query": '{Verdict} = "Decrease"', "column_id": "Verdict"},
                "backgroundColor": "#f8d7da", "color": "#721c24", "fontWeight": "bold",
            },
            {
                "if": {"filter_query": '{Verdict} = "Hold"', "column_id": "Verdict"},
                "backgroundColor": "#e2e3e5", "color": "#383d41", "fontWeight": "bold",
            },
        ],
        page_size=50,
    )

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

    # Action distribution by manufacturer
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

    # Market share donut charts
    mfr_vol_current = overview_df.groupby("manufacturer")["volume"].sum()
    mfr_vol_projected = overview_df.groupby("manufacturer")["projected_volume"].sum()
    mfr_rev_current = overview_df.groupby("manufacturer")["revenue"].sum()
    mfr_rev_projected = overview_df.groupby("manufacturer")["projected_revenue"].sum()

    total_vol_current = mfr_vol_current.sum()
    total_vol_projected = mfr_vol_projected.sum()
    vol_share_current = (mfr_vol_current / total_vol_current * 100).round(1)
    vol_share_projected = (mfr_vol_projected / total_vol_projected * 100).round(1)
    vol_share_delta = (vol_share_projected - vol_share_current).round(2)

    mfr_order = sorted(overview_df["manufacturer"].unique())
    mfr_colors = dict(zip(mfr_order, px.colors.qualitative.Set2))
    pie_colors = [mfr_colors[m] for m in mfr_order]

    fig_vol_share = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["Current Volume Share", "Projected Volume Share"],
    )
    fig_vol_share.add_trace(go.Pie(
        labels=mfr_order, values=[mfr_vol_current[m] for m in mfr_order],
        hole=0.45, marker_colors=pie_colors, textinfo="label+percent", textposition="outside",
    ), row=1, col=1)
    fig_vol_share.add_trace(go.Pie(
        labels=mfr_order, values=[mfr_vol_projected[m] for m in mfr_order],
        hole=0.45, marker_colors=pie_colors, textinfo="label+percent", textposition="outside",
    ), row=1, col=2)
    fig_vol_share.update_layout(
        title="Volume Market Share: Before vs After Price Actions",
        height=380, margin=dict(t=60, b=20), showlegend=False,
    )

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
        labels=mfr_order, values=[mfr_rev_current[m] for m in mfr_order],
        hole=0.45, marker_colors=pie_colors, textinfo="label+percent", textposition="outside",
    ), row=1, col=1)
    fig_rev_share.add_trace(go.Pie(
        labels=mfr_order, values=[mfr_rev_projected[m] for m in mfr_order],
        hole=0.45, marker_colors=pie_colors, textinfo="label+percent", textposition="outside",
    ), row=1, col=2)
    fig_rev_share.update_layout(
        title="Revenue Market Share: Before vs After Price Actions",
        height=380, margin=dict(t=60, b=20), showlegend=False,
    )

    # Market share shift bar
    fig_share_shift = go.Figure()
    fig_share_shift.add_trace(go.Bar(
        x=mfr_order, y=[vol_share_delta[m] for m in mfr_order],
        name="Volume Share \u0394", marker_color="#3498db",
        text=[f"{vol_share_delta[m]:+.2f}pp" for m in mfr_order], textposition="outside",
    ))
    fig_share_shift.add_trace(go.Bar(
        x=mfr_order, y=[rev_share_delta[m] for m in mfr_order],
        name="Revenue Share \u0394", marker_color="#e67e22",
        text=[f"{rev_share_delta[m]:+.2f}pp" for m in mfr_order], textposition="outside",
    ))
    fig_share_shift.update_layout(
        title="Market Share Shift After Price Actions (percentage points)",
        yaxis_title="Change (pp)", barmode="group", plot_bgcolor="white",
        yaxis=dict(gridcolor="#eeeeee"), height=350, margin=dict(t=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_share_shift.add_hline(y=0, line_dash="dash", line_color="gray")

    # Per-SKU profit impact bar
    sku_sorted = overview_df.sort_values("profit_impact", ascending=True)
    fig_waterfall = go.Figure(go.Bar(
        x=sku_sorted["profit_impact"], y=sku_sorted["sku_name"], orientation="h",
        marker_color=[
            "#2ecc71" if a == "Increase Price" else "#e74c3c" if a == "Decrease Price" else "#95a5a6"
            for a in sku_sorted["action"]
        ],
        text=[f"\u00a3{v:+,.0f}" for v in sku_sorted["profit_impact"]], textposition="outside",
    ))
    fig_waterfall.update_layout(
        title="Profit Impact by SKU (All Manufacturers)",
        xaxis_title="Profit Impact (\u00a3)", plot_bgcolor="white",
        xaxis=dict(gridcolor="#eeeeee"),
        height=max(400, len(sku_sorted) * 28), margin=dict(t=40, l=220),
    )
    fig_waterfall.add_vline(x=0, line_dash="dash", line_color="gray")

    return html.Div([
        html.H3("Portfolio Price Recommendations", className="mb-1"),
        html.P(f"Analysing {total_skus} SKUs across {len(manufacturers)} manufacturers",
               className="text-muted mb-3"),
        html.Hr(),
        summary_cards,
        html.Hr(),
        html.H5("Verdict Table", className="mb-3"),
        html.P("Click column headers to sort. Use filter row to search.", className="text-muted mb-2",
               style={"fontSize": "0.85rem"}),
        verdict_table,
        html.Hr(className="mt-4"),
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
        dcc.Graph(figure=fig_waterfall),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO SIMULATOR VIEW (Iteration 2)
# ══════════════════════════════════════════════════════════════════════════════

def build_simulator_layout(df):
    """Build the scenario simulator page with SKU selector and price slider."""
    sku_list = []
    for _, row in df.iterrows():
        sku_list.append({
            "sku_id": row["sku_id"],
            "SKU": row["sku_name"],
            "Manufacturer": row["manufacturer"],
            "Brand": row["brand"],
            "Segment": row["price_segment"],
            "Current Price": round(row["current_price_per_unit"], 2),
            "Elasticity": round(row["elasticity"], 2),
        })

    sku_table = dash_table.DataTable(
        id="sim-sku-table",
        data=sku_list,
        columns=[
            {"name": "SKU", "id": "SKU"},
            {"name": "Manufacturer", "id": "Manufacturer"},
            {"name": "Brand", "id": "Brand"},
            {"name": "Segment", "id": "Segment"},
            {"name": "Price (\u00a3)", "id": "Current Price", "type": "numeric"},
            {"name": "Elasticity", "id": "Elasticity", "type": "numeric"},
        ],
        row_selectable="single",
        selected_rows=[0],
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto", "maxHeight": "300px", "overflowY": "auto"},
        style_cell={"textAlign": "center", "padding": "6px", "fontSize": "0.85rem"},
        style_header={"backgroundColor": "#2c3e50", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[{
            "if": {"state": "selected"},
            "backgroundColor": "#d4edda", "border": "1px solid #28a745",
        }],
        page_size=50,
    )

    return html.Div([
        html.H3("Scenario Simulator", className="mb-1"),
        html.P("Click a SKU, drag the price slider, and see live portfolio impact.",
               className="text-muted mb-3"),
        html.Hr(),
        # SKU selector table
        html.H5("Select a SKU", className="mb-2"),
        sku_table,
        html.Hr(),
        # Selected SKU controls
        html.Div(id="sim-controls", className="mb-4"),
        # Results
        html.Div(id="sim-results"),
    ])


@callback(
    Output("sim-controls", "children"),
    Input("sim-sku-table", "selected_rows"),
    Input("sim-sku-table", "data"),
    State("sim-price-changes", "data"),
)
def update_sim_controls(selected_rows, table_data, price_changes):
    if not selected_rows or not table_data:
        return html.Div("Select a SKU from the table above.", className="text-muted")

    row = table_data[selected_rows[0]]
    sku_id = row["sku_id"]
    current_val = price_changes.get(sku_id, 0)

    # Count how many SKUs have been adjusted
    adjusted = {k: v for k, v in price_changes.items() if v != 0}
    adjusted_badge = ""
    if adjusted:
        adjusted_badge = dbc.Badge(
            f"{len(adjusted)} SKU{'s' if len(adjusted) > 1 else ''} adjusted",
            color="info", className="ms-2",
        )

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H5([
                    f"Adjust Price: {row['SKU']}",
                    adjusted_badge,
                ], className="mb-1"),
                html.P(
                    f"{row['Manufacturer']} \u00b7 {row['Brand']} \u00b7 Current: \u00a3{row['Current Price']:.2f}",
                    className="text-muted mb-2",
                ),
            ]),
            dbc.Col(
                dbc.Button("Reset All", id="sim-reset-btn", color="outline-secondary", size="sm"),
                width="auto", className="d-flex align-items-center",
            ),
        ], justify="between"),
        dcc.Slider(
            id="sim-price-slider",
            min=-20, max=20, step=1,
            value=current_val,
            marks={i: f"{i:+d}%" for i in range(-20, 25, 5)},
            tooltip={"placement": "bottom", "always_visible": True},
        ),
        html.Div(id="sim-selected-sku-id", children=sku_id, style={"display": "none"}),
    ])


@callback(
    Output("sim-price-changes", "data"),
    Input("sim-price-slider", "value"),
    Input("sim-reset-btn", "n_clicks"),
    State("sim-selected-sku-id", "children"),
    State("sim-price-changes", "data"),
    prevent_initial_call=True,
)
def update_price_changes(slider_val, reset_clicks, sku_id, price_changes):
    from dash import ctx
    if ctx.triggered_id == "sim-reset-btn":
        return {}
    if sku_id and slider_val is not None:
        price_changes[sku_id] = slider_val
    return price_changes


@callback(
    Output("sim-results", "children"),
    Input("sim-price-changes", "data"),
    Input("data-store", "data"),
)
def update_sim_results(price_changes, json_data):
    df = pd.read_json(io.StringIO(json_data), orient="split")
    sim_df = simulate_portfolio(df, price_changes)

    total_baseline = sim_df["baseline_profit"].sum()
    total_new = sim_df["new_profit"].sum()
    total_impact = sim_df["profit_impact"].sum()
    total_impact_pct = (total_impact / total_baseline * 100) if total_baseline else 0

    adjusted_count = sum(1 for v in price_changes.values() if v != 0)
    impact_color = "#155724" if total_impact >= 0 else "#721c24"

    summary = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("SKUs Adjusted", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(str(adjusted_count), className="mb-0"),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Baseline Portfolio Profit", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(f"\u00a3{total_baseline:,.0f}", className="mb-0"),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Simulated Portfolio Profit", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(f"\u00a3{total_new:,.0f}", className="mb-0"),
        ]), className="text-center"), width=True),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Total Profit Impact", className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H4(f"\u00a3{total_impact:+,.0f}", className="mb-0", style={"color": impact_color}),
            html.Small(f"{total_impact_pct:+.1f}%", className="text-muted"),
        ]), className="text-center"), width=True),
    ], className="mb-4")

    # Per-SKU impact chart — only show SKUs that were adjusted or have non-zero impact
    changed_skus = sim_df[sim_df["price_change_pct"] != 0].sort_values("profit_impact", ascending=True)

    if not changed_skus.empty:
        fig_impact = go.Figure(go.Bar(
            x=changed_skus["profit_impact"],
            y=changed_skus["sku_name"],
            orientation="h",
            marker_color=["#2ecc71" if v >= 0 else "#e74c3c" for v in changed_skus["profit_impact"]],
            text=[f"\u00a3{v:+,.0f}" for v in changed_skus["profit_impact"]],
            textposition="outside",
        ))
        fig_impact.update_layout(
            title="Profit Impact of Adjusted SKUs",
            xaxis_title="Profit Impact (\u00a3)",
            plot_bgcolor="white",
            xaxis=dict(gridcolor="#eeeeee"),
            height=max(250, len(changed_skus) * 35),
            margin=dict(t=40, l=220),
        )
        fig_impact.add_vline(x=0, line_dash="dash", line_color="gray")
        impact_chart = dcc.Graph(figure=fig_impact)
    else:
        impact_chart = html.P("Adjust a SKU price above to see the impact.",
                              className="text-muted text-center my-4")

    # Results table — show all SKUs with adjusted ones highlighted
    result_data = []
    for _, row in sim_df.iterrows():
        result_data.append({
            "SKU": row["sku_name"],
            "Manufacturer": row["manufacturer"],
            "Current Price": round(row["current_price"], 2),
            "Change": f"{row['price_change_pct']:+.0f}%",
            "New Price": round(row["new_price"], 2),
            "Volume Change": f"{row['volume_change_pct']:+.1f}%",
            "Profit Impact": round(row["profit_impact"], 0),
            "_changed": 1 if row["price_change_pct"] != 0 else 0,
        })

    result_table = dash_table.DataTable(
        data=result_data,
        columns=[
            {"name": "SKU", "id": "SKU"},
            {"name": "Manufacturer", "id": "Manufacturer"},
            {"name": "Current Price (\u00a3)", "id": "Current Price", "type": "numeric"},
            {"name": "Change", "id": "Change"},
            {"name": "New Price (\u00a3)", "id": "New Price", "type": "numeric"},
            {"name": "Volume Change", "id": "Volume Change"},
            {"name": "Profit Impact (\u00a3)", "id": "Profit Impact", "type": "numeric"},
        ],
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "6px", "fontSize": "0.85rem"},
        style_header={"backgroundColor": "#2c3e50", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[
            {
                "if": {"filter_query": "{_changed} = 1"},
                "backgroundColor": "#fff3cd", "fontWeight": "bold",
            },
            {
                "if": {"filter_query": "{Profit Impact} > 0", "column_id": "Profit Impact"},
                "color": "#155724",
            },
            {
                "if": {"filter_query": "{Profit Impact} < 0", "column_id": "Profit Impact"},
                "color": "#721c24",
            },
        ],
        page_size=50,
    )

    # Manufacturer-level impact
    mfr_impact = sim_df.groupby("manufacturer")["profit_impact"].sum().reset_index()
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
        title="Simulated Profit Impact by Manufacturer",
        xaxis_title="Profit Impact (\u00a3)",
        plot_bgcolor="white",
        xaxis=dict(gridcolor="#eeeeee"),
        height=250,
        margin=dict(t=40, l=150),
    )
    fig_mfr.add_vline(x=0, line_dash="dash", line_color="gray")

    return html.Div([
        html.H5("Portfolio Impact", className="mb-3"),
        summary,
        dbc.Row([
            dbc.Col(impact_chart, width=7),
            dbc.Col(dcc.Graph(figure=fig_mfr), width=5),
        ], className="mb-4"),
        html.Hr(),
        html.H5("All SKUs — Simulated Results", className="mb-3"),
        result_table,
    ])


# ══════════════════════════════════════════════════════════════════════════════
# DETAIL VIEW
# ══════════════════════════════════════════════════════════════════════════════

def build_detail_layout(sku_id, df):
    if not sku_id:
        return html.Div("Select a SKU from the sidebar.", className="text-muted mt-4")

    matches = df[df["sku_id"] == sku_id]
    if matches.empty:
        return html.Div("SKU not found in current data.", className="text-muted mt-4")

    sku_row = matches.iloc[0]
    rec, scenarios = analyse_sku(sku_id, df)

    subtitle = f"{sku_row['manufacturer']} \u00b7 {sku_row['brand']} \u00b7 {sku_row['price_segment']}"

    kpis = [
        ("Current Price", f"\u00a3{sku_row['current_price_per_unit']:.2f}"),
        ("Volume 2025", f"{sku_row['volume_2025_units']:,.0f} units"),
        ("Elasticity", f"{sku_row['elasticity']:.2f}"),
        ("Cannibalization Rate", f"{sku_row['cannibalization_rate']:.0%}"),
        ("Profit % per mL", f"{sku_row['profit_pct_per_ml']:.0%}"),
    ]
    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P(label, className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H5(value, className="mb-0"),
        ]), className="text-center"), width=True)
        for label, value in kpis
    ], className="mb-3")

    action_colors = {
        "Increase Price": {"bg": "#d4edda", "text": "#155724"},
        "Decrease Price": {"bg": "#f8d7da", "text": "#721c24"},
        "Hold Price": {"bg": "#e2e3e5", "text": "#383d41"},
    }
    colors = action_colors.get(rec["action"], {"bg": "#e2e3e5", "text": "#383d41"})

    recommendation_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4(rec["action"], className="mb-1"),
            html.H5(f"\u00a3{rec['recommended_price']:.2f} ({rec['recommended_scenario_pct']:+.0f}%)", className="mb-0"),
        ]), style={"backgroundColor": colors["bg"], "color": colors["text"], "textAlign": "center"}), width=4),
        dbc.Col(dbc.Row([
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
        ]), width=8),
    ], className="mb-3")

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
        style_header={"backgroundColor": "#2c3e50", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[{
            "if": {"filter_query": '{Price \u0394 (%)} = "' + best_pct_str + '"'},
            "backgroundColor": "#d4edda", "fontWeight": "bold",
        }],
    )

    bar_colors = [
        "#2ecc71" if p == best_pct else ("#e74c3c" if p < 0 else "#3498db")
        for p in scenarios["scenario_pct"]
    ]
    fig = go.Figure(go.Bar(
        x=[f"{p:+.0f}%" for p in scenarios["scenario_pct"]],
        y=scenarios["profit_impact"],
        marker_color=bar_colors,
        text=[f"\u00a3{v:+,.0f}" for v in scenarios["profit_impact"]],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis_title="Price Change Scenario", yaxis_title="Net Profit Impact (\u00a3)",
        plot_bgcolor="white", yaxis=dict(gridcolor="#eeeeee"), height=400, margin=dict(t=30),
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

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
        style_header={"backgroundColor": "#2c3e50", "color": "white", "fontWeight": "bold"},
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
    Input("data-store", "data"),
)
def update_brands(manufacturer, json_data):
    if not manufacturer:
        return [], None
    df = pd.read_json(io.StringIO(json_data), orient="split")
    filtered = df[df["manufacturer"] == manufacturer]
    brands = sorted(filtered["brand"].unique())
    options = [{"label": b, "value": b} for b in brands]
    return options, brands[0]


@callback(
    Output("segment-select", "options"),
    Output("segment-select", "value"),
    Input("manufacturer-select", "value"),
    Input("brand-select", "value"),
    Input("data-store", "data"),
)
def update_segments(manufacturer, brand, json_data):
    if not manufacturer or not brand:
        return [], None
    df = pd.read_json(io.StringIO(json_data), orient="split")
    filtered = df[(df["manufacturer"] == manufacturer) & (df["brand"] == brand)]
    segments = sorted(filtered["price_segment"].unique())
    options = [{"label": "All", "value": "All"}] + [{"label": s, "value": s} for s in segments]
    return options, "All"


@callback(
    Output("sku-select", "options"),
    Output("sku-select", "value"),
    Input("manufacturer-select", "value"),
    Input("brand-select", "value"),
    Input("segment-select", "value"),
    Input("data-store", "data"),
)
def update_skus(manufacturer, brand, segment, json_data):
    if not manufacturer or not brand:
        return [], None
    df = pd.read_json(io.StringIO(json_data), orient="split")
    filtered = df[(df["manufacturer"] == manufacturer) & (df["brand"] == brand)]
    if segment and segment != "All":
        filtered = filtered[filtered["price_segment"] == segment]
    options = [{"label": row["sku_name"], "value": row["sku_id"]} for _, row in filtered.iterrows()]
    return options, options[0]["value"] if options else None


if __name__ == "__main__":
    app.run(debug=True)
