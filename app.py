import sys
import io
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc

from pricing_engine import load_data, analyse_sku, run_scenarios, recommend, baseline_profit, simulate_portfolio
from theme import (
    MIDNIGHT, CHARCOAL, GOLD, WARM_GRAY, ABI_NAVY,
    ALERT_RED, FOREST_GREEN, BORDER, BODY_TEXT, HEADING_TEXT,
    NAVY, CHART_GREEN, CHART_RED,
    CHART_LAYOUT, CHART_LAYOUT_NO_YAXIS, CHART_LAYOUT_NO_AXES,
    NAV_BTN_ACTIVE, NAV_BTN_INACTIVE,
    TABLE_STYLE_CELL, TABLE_STYLE_HEADER,
    LOGO_MAP, make_kpi_card, section_title,
)
from pages import build_elasticity_layout, build_cannibalization_layout, build_executive_summary_layout

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
    external_stylesheets=[dbc.themes.DARKLY],
    title="Beer SKU Price Recommender",
    suppress_callback_exceptions=True,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

# Navigation button definitions: (id, label, view_key)
NAV_BUTTONS = [
    ("btn-simulator", "Simulator", "simulator"),
    ("btn-detail", "SKU Detail", "detail"),
    ("btn-elasticity", "Elasticity", "elasticity"),
    ("btn-cannibalization", "Cannibalization", "cannibalization"),
    ("btn-executive", "Executive Summary", "executive"),
]


def build_overview_data(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, sku in df.iterrows():
        try:
            rec, scenarios = analyse_sku(sku["sku_id"], df)
        except Exception:
            continue
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
    if not contents or not filename:
        return None, "No file provided."
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

    if uploaded_df.empty:
        return None, "Uploaded file is empty."

    missing = [c for c in REQUIRED_COLS if c not in uploaded_df.columns]
    if missing:
        return None, f"Missing columns: {', '.join(missing)}"

    # Drop rows with critical missing values
    critical = ["sku_id", "current_price_per_unit", "elasticity", "volume_2025_units"]
    before = len(uploaded_df)
    uploaded_df = uploaded_df.dropna(subset=critical)
    dropped = before - len(uploaded_df)

    if uploaded_df.empty:
        return None, "All rows had missing critical data."

    return uploaded_df, (f"Dropped {dropped} rows with missing data. " if dropped > 0 else None)


# ── Layout ───────────────────────────────────────────────────────────────────
sidebar = html.Div(
    id="sidebar",
    children=[
        html.Img(
            src="/assets/logos/pricepint_logo_v2.svg",
            style={"width": "100%", "display": "block", "marginBottom": "8px"},
        ),
        html.Hr(),
        dbc.Label("Data Source"),
        dcc.Upload(
            id="upload-data",
            children=dbc.Button("Upload CSV / Excel", className="upload-btn w-100 mb-2", size="sm"),
            accept=".csv,.xlsx,.xls",
        ),
        html.Div(id="upload-status", className="mb-2"),
        html.Hr(),
        dbc.Label("Navigate"),
        html.Div([
            dbc.Button("Simulator", id="btn-simulator",
                       className=NAV_BTN_ACTIVE, size="sm"),
            dbc.Button("SKU Detail", id="btn-detail",
                       className=NAV_BTN_INACTIVE, size="sm"),
        ]),
        dbc.Label("Analytics", className="mt-2"),
        html.Div([
            dbc.Button("Elasticity", id="btn-elasticity",
                       className=NAV_BTN_INACTIVE, size="sm"),
            dbc.Button("Cannibalization", id="btn-cannibalization",
                       className=NAV_BTN_INACTIVE, size="sm"),
            dbc.Button("Executive Summary", id="btn-executive",
                       className=NAV_BTN_INACTIVE, size="sm"),
        ]),
        dcc.Store(id="view-select", data="simulator"),
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
        "position": "fixed", "top": 0, "left": 0, "bottom": 0,
        "width": "16%", "padding": "24px 16px", "overflowY": "auto",
    },
)

content = html.Div(id="main-content", style={"marginLeft": "18%", "padding": "32px 48px"})

app.layout = html.Div([
    dcc.Store(id="data-store", data=default_df.to_json(date_format="iso", orient="split")),
    dcc.Store(id="sim-price-changes", data={}),
    dcc.Download(id="download-csv"),
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

    uploaded_df, msg = parse_upload(contents, filename)
    if uploaded_df is None:
        return no_update, dbc.Alert(msg, color="danger", className="py-1 px-2 mb-0",
                                    style={"fontSize": "0.75rem"})

    warning = msg if msg else ""
    status = dbc.Alert(
        f"{warning}Loaded {filename} — {len(uploaded_df)} SKUs",
        color="success" if not warning else "warning",
        className="py-1 px-2 mb-0", style={"fontSize": "0.75rem"},
    )
    return uploaded_df.to_json(date_format="iso", orient="split"), status


# ── Populate manufacturer dropdown ───────────────────────────────────────────
@callback(
    Output("manufacturer-select", "options"),
    Output("manufacturer-select", "value"),
    Input("data-store", "data"),
)
def update_manufacturer_options(json_data):
    if not json_data:
        return [], None
    df = pd.read_json(io.StringIO(json_data), orient="split")
    manufacturers = sorted(df["manufacturer"].unique())
    options = [{"label": m, "value": m} for m in manufacturers]
    return options, manufacturers[0]


# ── Navigation ───────────────────────────────────────────────────────────────
@callback(
    Output("view-select", "data"),
    *[Output(btn_id, "className") for btn_id, _, _ in NAV_BUTTONS],
    *[Input(btn_id, "n_clicks") for btn_id, _, _ in NAV_BUTTONS],
    prevent_initial_call=True,
)
def handle_nav_click(*args):
    from dash import ctx
    button_map = {btn_id: view for btn_id, _, view in NAV_BUTTONS}
    view = button_map.get(ctx.triggered_id, "simulator")
    classes = []
    for _, _, v in NAV_BUTTONS:
        classes.append(NAV_BTN_ACTIVE if v == view else NAV_BTN_INACTIVE)
    return (view, *classes)


@callback(
    Output("sku-filters", "style"),
    Input("view-select", "data"),
)
def toggle_filters(view):
    # Only show SKU filters for detail view
    return {"display": "block"} if view == "detail" else {"display": "none"}


@callback(
    Output("main-content", "children"),
    Input("view-select", "data"),
    Input("sku-select", "value"),
    Input("data-store", "data"),
)
def render_view(view, sku_id, json_data):
    if not json_data:
        return html.Div("Loading...", className="text-muted mt-4")
    df = pd.read_json(io.StringIO(json_data), orient="split")
    if view == "simulator":
        return build_simulator_layout(df)
    if view == "elasticity":
        return build_elasticity_layout(df)
    if view == "cannibalization":
        return build_cannibalization_layout(df)
    if view == "executive":
        return build_executive_summary_layout(df)
    return build_detail_layout(sku_id, df)


# ── CSV Export callback ──────────────────────────────────────────────────────
@callback(
    Output("download-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    State("data-store", "data"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, json_data):
    if not n_clicks:
        return no_update
    df = pd.read_json(io.StringIO(json_data), orient="split")
    overview_df = build_overview_data(df)
    export = overview_df[[
        "sku_name", "manufacturer", "brand", "segment", "current_price",
        "action", "recommended_price", "scenario_pct", "profit_impact", "profit_impact_pct",
    ]].rename(columns={
        "sku_name": "SKU", "manufacturer": "Manufacturer", "brand": "Brand",
        "segment": "Segment", "current_price": "Current Price",
        "action": "Verdict", "recommended_price": "Recommended Price",
        "scenario_pct": "Price Change %", "profit_impact": "Profit Impact",
        "profit_impact_pct": "Profit Impact %",
    })
    return dcc.send_data_frame(export.to_csv, "price_recommendations.csv", index=False)


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO SIMULATOR VIEW
# ══════════════════════════════════════════════════════════════════════════════

def build_simulator_layout(df):
    if df.empty:
        return html.Div("No data loaded.", className="text-muted mt-4")

    sku_list = []
    for _, row in df[df["manufacturer"] == "AB InBev"].iterrows():
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
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data_conditional=[{
            "if": {"state": "selected"},
            "backgroundColor": "rgba(201,168,76,0.15)", "border": f"1px solid {GOLD}",
        }],
        page_size=50,
    )

    return html.Div([
        html.H3("Scenario Simulator", className="page-title mb-1"),
        html.P("Select an AB InBev SKU, adjust its price, and see live portfolio-wide impact.",
               className="page-subtitle mb-3"),
        html.Hr(),
        section_title("Select an AB InBev SKU"),
        sku_table,
        html.Hr(),
        html.Div(id="sim-controls", className="mb-4"),
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

    adjusted = {k: v for k, v in price_changes.items() if v != 0}
    badge = ""
    if adjusted:
        badge = dbc.Badge(f"{len(adjusted)} adjusted", color="warning",
                          text_color="dark", className="ms-2")

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H5([f"Adjust: {row['SKU']}", badge], className="mb-1",
                         style={"color": HEADING_TEXT}),
                html.P(f"{row['Manufacturer']} \u00b7 {row['Brand']} \u00b7 \u00a3{row['Current Price']:.2f}",
                       className="page-subtitle mb-2"),
            ]),
            dbc.Col(
                dbc.Button("Reset All", id="sim-reset-btn", size="sm",
                           style={"backgroundColor": "transparent", "border": f"0.5px solid {GOLD}",
                                  "color": GOLD, "fontSize": "11px", "letterSpacing": "0.08em",
                                  "textTransform": "uppercase", "borderRadius": "4px"}),
                width="auto", className="d-flex align-items-center",
            ),
        ], justify="between"),
        dcc.Slider(
            id="sim-price-slider", min=-20, max=20, step=1, value=current_val,
            marks={i: {"label": f"{i:+d}%", "style": {"fontSize": "0.75rem"}} for i in range(-20, 25, 5)},
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

    # ── Market share reallocation ─────────────────────────────────────────────
    # Volume that leaves an AB InBev SKU is split:
    #   cannibalization_rate  → stays in AB InBev (siblings absorb)
    #   (1 - cannibalization_rate) → goes to / comes from competitors
    # Net AB InBev vol change per adjusted SKU = own_vol_change × (1 - cann_rate)
    total_market_vol = df["volume_2025_units"].sum()
    abi_baseline_vol = df[df["manufacturer"] == "AB InBev"]["volume_2025_units"].sum()
    abi_baseline_share = abi_baseline_vol / total_market_vol * 100

    cann_rate_map = df.set_index("sku_id")["cannibalization_rate"].to_dict()
    adjusted_abi = sim_df[
        (sim_df["manufacturer"] == "AB InBev") & (sim_df["price_change_pct"] != 0)
    ]

    wf_measures = ["absolute"]
    wf_x = ["AB InBev\nBaseline"]
    wf_y = [abi_baseline_share]
    wf_text = [f"{abi_baseline_share:.1f}%"]
    running_share = abi_baseline_share
    total_net_abi_vol_change = 0.0  # accumulated in same pass — no second iterrows

    for _, row in adjusted_abi.iterrows():
        cann_rate = cann_rate_map.get(row["sku_id"], 0.1)
        own_vol_change = row["new_volume"] - row["current_volume"]
        # Net volume that crosses manufacturer boundary
        net_abi_vol_change = own_vol_change * (1 - cann_rate)
        total_net_abi_vol_change += net_abi_vol_change
        share_change = net_abi_vol_change / total_market_vol * 100
        running_share += share_change

        label = row["sku_name"].replace(" Can", "").replace(" Bottle", "")
        wf_measures.append("relative")
        wf_x.append(label)
        wf_y.append(share_change)
        wf_text.append(f"{share_change:+.2f}pp")

    wf_measures.append("total")
    wf_x.append("AB InBev\nFinal")
    wf_y.append(0)  # Plotly computes running total for "total" bars
    wf_text.append(f"{running_share:.1f}%")

    share_delta = running_share - abi_baseline_share

    fig_waterfall = go.Figure(go.Waterfall(
        orientation="v",
        measure=wf_measures,
        x=wf_x,
        y=wf_y,
        text=wf_text,
        textposition="outside",
        connector=dict(line=dict(color=BORDER, width=1, dash="dot")),
        increasing=dict(marker=dict(color=CHART_GREEN)),
        decreasing=dict(marker=dict(color=CHART_RED)),
        totals=dict(marker=dict(color=ABI_NAVY)),
        hovertemplate="%{x}: %{text}<extra></extra>",
    ))
    fig_waterfall.update_layout(
        **CHART_LAYOUT_NO_YAXIS,
        title=f"AB InBev Volume Market Share: Before \u2192 After  ({share_delta:+.2f}pp)",
        height=380,
        margin=dict(t=50, b=60),
        yaxis=dict(
            gridcolor=BORDER, gridwidth=0.5, griddash="dash",
            showline=False, ticksuffix="%",
            tickfont=dict(size=11, color=WARM_GRAY),
            title=dict(text="Market Share (%)", font=dict(size=11, color=WARM_GRAY)),
        ),
    )

    abi_share_kpi = make_kpi_card(
        "ABI Share Before", f"{abi_baseline_share:.1f}%", BODY_TEXT
    )
    abi_share_after_kpi = make_kpi_card(
        "ABI Share After", f"{running_share:.1f}%",
        CHART_GREEN if share_delta >= 0 else CHART_RED
    )
    abi_share_delta_kpi = make_kpi_card(
        "Share Δ", f"{share_delta:+.2f}pp",
        CHART_GREEN if share_delta >= 0 else CHART_RED
    )

    # ── Existing profit impact chart ──────────────────────────────────────────
    changed_skus = sim_df[sim_df["price_change_pct"] != 0].sort_values("profit_impact", ascending=True)

    if not changed_skus.empty:
        fig_impact = go.Figure(go.Bar(
            x=changed_skus["profit_impact"], y=changed_skus["sku_name"], orientation="h",
            marker_color=[CHART_GREEN if v >= 0 else CHART_RED for v in changed_skus["profit_impact"]],
            text=[f"\u00a3{v:+,.0f}" for v in changed_skus["profit_impact"]], textposition="outside",
        ))
        fig_impact.update_layout(**CHART_LAYOUT, title="Profit Impact of Adjusted SKUs",
                                  height=max(250, len(changed_skus) * 35), margin=dict(t=40, l=220))
        fig_impact.add_vline(x=0, line_dash="dash", line_color=BORDER)
        impact_chart = dcc.Graph(figure=fig_impact)
    else:
        impact_chart = html.P("Adjust a SKU price to see impact.", className="text-muted text-center my-4")

    summary = dbc.Row([
        make_kpi_card("SKUs Adjusted", str(adjusted_count)),
        make_kpi_card("Baseline Profit", f"\u00a3{total_baseline:,.0f}"),
        make_kpi_card("Simulated Profit", f"\u00a3{total_new:,.0f}"),
        make_kpi_card("Total Impact",
                      f"\u00a3{total_impact:+,.0f} ({total_impact_pct:+.1f}%)",
                      CHART_GREEN if total_impact >= 0 else CHART_RED),
        abi_share_kpi,
        abi_share_after_kpi,
        abi_share_delta_kpi,
    ], className="mb-4")

    result_data = []
    for _, row in sim_df.iterrows():
        result_data.append({
            "SKU": row["sku_name"], "Manufacturer": row["manufacturer"],
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
            {"name": "SKU", "id": "SKU"}, {"name": "Manufacturer", "id": "Manufacturer"},
            {"name": "Current (\u00a3)", "id": "Current Price", "type": "numeric"},
            {"name": "Change", "id": "Change"},
            {"name": "New (\u00a3)", "id": "New Price", "type": "numeric"},
            {"name": "Vol \u0394", "id": "Volume Change"},
            {"name": "Profit Impact (\u00a3)", "id": "Profit Impact", "type": "numeric"},
        ],
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data_conditional=[
            {"if": {"filter_query": "{_changed} = 1"}, "backgroundColor": "rgba(201,168,76,0.08)", "fontWeight": "500"},
            {"if": {"filter_query": "{Profit Impact} > 0", "column_id": "Profit Impact"}, "color": GOLD},
            {"if": {"filter_query": "{Profit Impact} < 0", "column_id": "Profit Impact"}, "color": ALERT_RED},
        ],
        page_size=50,
    )

    # ── Competitor volume redistribution ──────────────────────────────────────
    # total_net_abi_vol_change accumulated in the waterfall loop above (no second pass)
    competitor_vol_gain_total = -total_net_abi_vol_change

    non_abi = df[df["manufacturer"] != "AB InBev"]
    non_abi_vol_by_mfr = non_abi.groupby("manufacturer")["volume_2025_units"].sum()
    non_abi_total_vol = non_abi_vol_by_mfr.sum()

    # Per-manufacturer volume change and market share delta
    all_mfr_vol = df.groupby("manufacturer")["volume_2025_units"].sum()
    mfr_vol_change = {"AB InBev": total_net_abi_vol_change}
    for mfr, mfr_vol in non_abi_vol_by_mfr.items():
        comp_share = mfr_vol / non_abi_total_vol if non_abi_total_vol > 0 else 0
        mfr_vol_change[mfr] = competitor_vol_gain_total * comp_share

    mfr_share_before = (all_mfr_vol / total_market_vol * 100).to_dict()
    mfr_share_delta = {m: mfr_vol_change.get(m, 0) / total_market_vol * 100
                       for m in mfr_share_before}
    mfr_share_after = {m: mfr_share_before[m] + mfr_share_delta[m]
                       for m in mfr_share_before}

    # Build per-manufacturer extra profit from volume absorption
    competitor_extra_profit = {}
    for mfr, mfr_vol in non_abi_vol_by_mfr.items():
        share = mfr_vol / non_abi_total_vol if non_abi_total_vol > 0 else 0
        vol_gain = competitor_vol_gain_total * share
        mfr_df = df[df["manufacturer"] == mfr]
        avg_price = mfr_df["current_price_per_unit"].mean()
        avg_profit_pct = mfr_df["profit_pct_per_ml"].mean()
        avg_ml = mfr_df["unit_volume_ml"].mean()
        competitor_extra_profit[mfr] = vol_gain * avg_price * avg_ml * avg_profit_pct

    mfr_impact = sim_df.groupby("manufacturer")["profit_impact"].sum().reset_index()
    mfr_impact["profit_impact"] = mfr_impact.apply(
        lambda r: r["profit_impact"] + competitor_extra_profit.get(r["manufacturer"], 0),
        axis=1,
    )
    mfr_impact = mfr_impact.sort_values("profit_impact", ascending=True)
    fig_mfr = go.Figure(go.Bar(
        x=mfr_impact["profit_impact"], y=mfr_impact["manufacturer"], orientation="h",
        marker_color=[CHART_GREEN if v >= 0 else CHART_RED for v in mfr_impact["profit_impact"]],
        text=[f"\u00a3{v:+,.0f}" for v in mfr_impact["profit_impact"]], textposition="outside",
    ))
    fig_mfr.update_layout(
        **CHART_LAYOUT,
        title="Profit Impact by Manufacturer (incl. volume redistribution)",
        height=250, margin=dict(t=40, l=150),
    )
    fig_mfr.add_vline(x=0, line_dash="dash", line_color=BORDER)

    # ── Market share delta chart (all manufacturers) ──────────────────────────
    ms_mfrs = sorted(mfr_share_delta.keys(),
                     key=lambda m: mfr_share_delta[m], reverse=True)
    ms_deltas = [mfr_share_delta[m] for m in ms_mfrs]
    ms_colors = [CHART_GREEN if d >= 0 else CHART_RED for d in ms_deltas]

    fig_ms_delta = go.Figure(go.Bar(
        x=ms_mfrs,
        y=ms_deltas,
        marker_color=ms_colors,
        text=[f"{d:+.2f}pp" for d in ms_deltas],
        textposition="outside",
        hovertemplate="%{x}<br>Before: %{customdata[0]:.1f}%<br>After: %{customdata[1]:.1f}%<br>Δ: %{y:+.2f}pp<extra></extra>",
        customdata=[[mfr_share_before[m], mfr_share_after[m]] for m in ms_mfrs],
    ))
    fig_ms_delta.update_layout(
        **CHART_LAYOUT_NO_YAXIS,
        title="Volume Market Share \u0394 by Manufacturer (pp)",
        height=320,
        margin=dict(t=50, b=40),
        yaxis=dict(
            gridcolor=BORDER, gridwidth=0.5, griddash="dash",
            showline=False, ticksuffix="pp",
            tickfont=dict(size=11, color=WARM_GRAY),
            title=dict(text="\u0394 Market Share (pp)", font=dict(size=11, color=WARM_GRAY)),
            zeroline=True, zerolinecolor=BORDER, zerolinewidth=1,
        ),
    )

    # Before / after / delta table for all manufacturers
    ms_table_data = []
    for m in ms_mfrs:
        ms_table_data.append({
            "Manufacturer": m,
            "Before (%)": round(mfr_share_before[m], 2),
            "After (%)": round(mfr_share_after[m], 2),
            "\u0394 (pp)": round(mfr_share_delta[m], 3),
            "Vol Gained": f"{mfr_vol_change.get(m, 0):+,.0f}",
        })

    ms_table = dash_table.DataTable(
        data=ms_table_data,
        columns=[
            {"name": "Manufacturer", "id": "Manufacturer"},
            {"name": "Before (%)", "id": "Before (%)", "type": "numeric"},
            {"name": "After (%)", "id": "After (%)", "type": "numeric"},
            {"name": "\u0394 (pp)", "id": "\u0394 (pp)", "type": "numeric"},
            {"name": "Volume Gained (units)", "id": "Vol Gained"},
        ],
        style_table={"overflowX": "auto"},
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data_conditional=[
            {"if": {"filter_query": "{\u0394 (pp)} > 0", "column_id": "\u0394 (pp)"},
             "color": CHART_GREEN, "fontWeight": "500"},
            {"if": {"filter_query": "{\u0394 (pp)} < 0", "column_id": "\u0394 (pp)"},
             "color": CHART_RED, "fontWeight": "500"},
            {"if": {"filter_query": "{Vol Gained} contains \"+\"", "column_id": "Vol Gained"},
             "color": CHART_GREEN},
            {"if": {"filter_query": "{Vol Gained} contains \"-\"", "column_id": "Vol Gained"},
             "color": CHART_RED},
        ],
    )

    return html.Div([
        section_title("Portfolio Impact"),
        summary,
        html.Hr(),
        section_title("AB InBev Market Share: Before \u2192 After"),
        html.P(
            "Volume lost/gained by AB InBev SKUs is split: cannibalization rate stays within AB InBev "
            "(siblings absorb), the remainder shifts to/from competitors.",
            style={"fontSize": "12px", "color": WARM_GRAY, "marginBottom": "8px"},
        ),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_waterfall), width=7),
            dbc.Col([
                dcc.Graph(figure=fig_ms_delta),
                ms_table,
            ], width=5),
        ], className="mb-2"),
        html.Hr(),
        section_title("Profit Impact by SKU"),
        dbc.Row([
            dbc.Col(impact_chart, width=7),
            dbc.Col(dcc.Graph(figure=fig_mfr), width=5),
        ], className="mb-4"),
        html.Hr(),
        section_title("Simulated Results"),
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
        ("Cannibalization", f"{sku_row['cannibalization_rate']:.0%}"),
        ("Profit % / mL", f"{sku_row['profit_pct_per_ml']:.0%}"),
    ]
    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P(label, className="kpi-label mb-1"),
            html.H5(value, className="kpi-value mb-0"),
        ]), className="kpi-card text-center"), width=True)
        for label, value in kpis
    ], className="mb-3")

    rec_class_map = {
        "Increase Price": "rec-increase",
        "Decrease Price": "rec-decrease",
        "Hold Price": "rec-hold",
    }
    rec_class = rec_class_map.get(rec["action"], "rec-hold")
    rec_text_color = {
        "Increase Price": GOLD,
        "Decrease Price": ALERT_RED,
        "Hold Price": BODY_TEXT,
    }

    recommendation_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4(rec["action"], className="mb-1", style={"fontWeight": "700"}),
            html.H5(f"\u00a3{rec['recommended_price']:.2f} ({rec['recommended_scenario_pct']:+.0f}%)", className="mb-0"),
        ]), className=rec_class, style={"textAlign": "center",
                                        "color": rec_text_color.get(rec["action"], NAVY)}), width=4),
        dbc.Col(dbc.Row([
            make_kpi_card("Net Profit Impact", f"\u00a3{rec['expected_profit_impact']:,.0f}"),
            make_kpi_card("Volume \u0394", f"{rec['expected_volume_change_pct']:+.1f}%"),
            make_kpi_card("New Price", f"\u00a3{rec['recommended_price']:.4f}"),
        ]), width=8),
    ], className="mb-3")

    best_pct = rec["recommended_scenario_pct"]
    table_data = []
    for _, row in scenarios.iterrows():
        table_data.append({
            "Price \u0394 (%)": f"{row['scenario_pct']:+.0f}%",
            "New Price (\u00a3)": f"\u00a3{row['new_price']:.4f}",
            "New Volume": f"{row['new_volume']:,.0f}",
            "Vol \u0394 (%)": f"{row['volume_change_pct']:+.1f}%",
            "Own Profit (\u00a3)": f"\u00a3{row['own_profit']:,.0f}",
            "Sibling \u0394 (\u00a3)": f"\u00a3{row['sibling_profit_delta']:,.0f}",
            "Net Profit (\u00a3)": f"\u00a3{row['net_profit']:,.0f}",
            "Impact (\u00a3)": f"\u00a3{row['profit_impact']:+,.0f}",
            "Impact (%)": f"{row['profit_impact_pct']:+.1f}%",
        })

    best_pct_str = f"{best_pct:+.0f}%"
    scenario_table = dash_table.DataTable(
        data=table_data,
        columns=[{"name": c, "id": c} for c in table_data[0]],
        style_table={"overflowX": "auto"},
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data_conditional=[{
            "if": {"filter_query": '{Price \u0394 (%)} = "' + best_pct_str + '"'},
            "backgroundColor": "rgba(201,168,76,0.15)", "fontWeight": "500",
        }],
    )

    bar_colors = [
        GOLD if p == best_pct else (ALERT_RED if p < 0 else ABI_NAVY)
        for p in scenarios["scenario_pct"]
    ]
    fig = go.Figure(go.Bar(
        x=[f"{p:+.0f}%" for p in scenarios["scenario_pct"]],
        y=scenarios["profit_impact"], marker_color=bar_colors,
        text=[f"\u00a3{v:+,.0f}" for v in scenarios["profit_impact"]], textposition="outside",
    ))
    fig.update_layout(**CHART_LAYOUT, xaxis_title="Scenario", yaxis_title="Profit Impact (\u00a3)",
                       height=400, margin=dict(t=30))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER)

    comp_ids = [sku_row["competitor_sku_1"], sku_row["competitor_sku_2"]]
    comp_df = df[df["sku_id"].isin(comp_ids)]
    comp_data = []
    for _, r in comp_df.iterrows():
        comp_data.append({
            "SKU": r["sku_name"], "Segment": r["price_segment"],
            "Price (\u00a3)": f"\u00a3{r['current_price_per_unit']:.2f}",
            "Elasticity": f"{r['elasticity']:.2f}",
            "Cannib. Rate": f"{r['cannibalization_rate']:.0%}",
            "Volume": f"{r['volume_2025_units']:,.0f}",
        })

    competitor_table = dash_table.DataTable(
        data=comp_data,
        columns=[{"name": c, "id": c} for c in comp_data[0]] if comp_data else [],
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
    )

    mfr_logo = LOGO_MAP.get(sku_row["manufacturer"], "")
    detail_header = dbc.Row([
        dbc.Col(
            html.Img(src=mfr_logo, style={"height": "40px", "objectFit": "contain"}) if mfr_logo else html.Span(),
            width="auto", className="d-flex align-items-center me-3",
        ),
        dbc.Col([
            html.H3(sku_row["sku_name"], className="page-title mb-0"),
            html.P(subtitle, className="page-subtitle mb-0"),
        ]),
    ], align="center", className="mb-3")

    return html.Div([
        detail_header,
        html.Hr(),
        kpi_cards,
        html.Hr(),
        section_title("Recommended Action"),
        recommendation_row,
        html.Hr(),
        section_title("Scenario Analysis"),
        html.Div(scenario_table, className="mb-4"),
        section_title("Profit Impact by Scenario"),
        dcc.Graph(figure=fig),
        html.Hr(),
        section_title("Sibling / Competitor SKUs"),
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
    return [{"label": b, "value": b} for b in brands], brands[0]


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
    return [{"label": "All", "value": "All"}] + [{"label": s, "value": s} for s in segments], "All"


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
