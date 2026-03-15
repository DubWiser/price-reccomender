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

# ── AB InBev Design System palette ────────────────────────────────────────────
MIDNIGHT = "#1A1A1A"
CHARCOAL = "#2C2C2C"
CREAM = "#F5F0E8"
GOLD = "#C9A84C"
GOLD_LIGHT = "#E8C97A"
WARM_GRAY = "#8A8070"
ABI_NAVY = "#1A3A5C"
ALERT_RED = "#C0392B"
FOREST_GREEN = "#4A7C59"
BORDER = "#3A3530"
BODY_TEXT = "#C2BDB5"
HEADING_TEXT = "#F5F0E8"

# Legacy aliases used in layout code
NAVY = ABI_NAVY
GREEN = FOREST_GREEN
AMBER = WARM_GRAY
WHITE = CREAM
CHART_GREEN = GOLD          # positive = Gold per design system
CHART_RED = ALERT_RED
CHART_AMBER = ABI_NAVY      # hold/neutral = Navy per design system
CHART_BLUE = ABI_NAVY

# ── Required columns for uploaded files ──────────────────────────────────────
REQUIRED_COLS = [
    "sku_id", "manufacturer", "brand", "sku_name", "price_segment",
    "current_price_per_unit", "elasticity", "cannibalization_rate",
    "profit_pct_per_ml", "volume_2025_units", "unit_volume_ml",
    "competitor_sku_1", "competitor_sku_2",
]

# ── Default data ─────────────────────────────────────────────────────────────
default_df = load_data()

# ── Manufacturer logo mapping ────────────────────────────────────────────────
LOGO_MAP = {
    "AB InBev": "/assets/logos/ab_inbev.png",
    "Heineken": "/assets/logos/heineken.png",
    "Carlsberg": "/assets/logos/carlsberg.png",
    "Molson Coors": "/assets/logos/molson_coors.png",
}

# ── Chart layout defaults ────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    plot_bgcolor=CHARCOAL,
    paper_bgcolor=CHARCOAL,
    font=dict(family="Inter, sans-serif", color=BODY_TEXT, size=13),
    xaxis=dict(
        gridcolor=BORDER, gridwidth=0.5, griddash="dash",
        linecolor=BORDER, linewidth=0.5,
        tickfont=dict(size=11, color=WARM_GRAY),
        title_font=dict(size=11, color=WARM_GRAY),
    ),
    yaxis=dict(
        gridcolor=BORDER, gridwidth=0.5, griddash="dash",
        showline=False,
        tickfont=dict(size=11, color=WARM_GRAY),
        title_font=dict(size=11, color=WARM_GRAY),
    ),
    title_font=dict(size=15, color=HEADING_TEXT, family="Inter, sans-serif"),
    legend_font=dict(color=BODY_TEXT, size=11),
)

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Beer SKU Price Recommender",
    suppress_callback_exceptions=True,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def make_kpi_card(label, value, value_color=None):
    style = {}
    if value_color:
        style["color"] = value_color
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.P(label, className="kpi-label mb-1"),
        html.Div(value, className="kpi-value mb-0", style=style),
    ]), className="kpi-card text-center"), width=True)


def section_title(text):
    return html.H5(text, className="section-title mb-3")


# ── Layout ───────────────────────────────────────────────────────────────────
sidebar = html.Div(
    id="sidebar",
    children=[
        html.H4("Price Recommender", className="mb-0"),
        html.Small("Beer SKU Portfolio Optimizer", className="d-block mb-3",
                   style={"color": WARM_GRAY, "fontSize": "11px", "letterSpacing": "0.1em",
                          "textTransform": "uppercase"}),
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
            dbc.Button("Overview", id="btn-overview",
                       className="nav-btn-active w-100 mb-2", size="sm"),
            dbc.Button("Simulator", id="btn-simulator",
                       className="nav-btn-inactive w-100 mb-2", size="sm"),
            dbc.Button("SKU Detail", id="btn-detail",
                       className="nav-btn-inactive w-100 mb-2", size="sm"),
        ]),
        dcc.Store(id="view-select", data="overview"),
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
    Output("btn-overview", "className"),
    Output("btn-simulator", "className"),
    Output("btn-detail", "className"),
    Input("btn-overview", "n_clicks"),
    Input("btn-simulator", "n_clicks"),
    Input("btn-detail", "n_clicks"),
    prevent_initial_call=True,
)
def handle_nav_click(n1, n2, n3):
    from dash import ctx
    button_map = {"btn-overview": "overview", "btn-simulator": "simulator", "btn-detail": "detail"}
    view = button_map.get(ctx.triggered_id, "overview")
    classes = {
        "overview": ("nav-btn-active w-100 mb-2", "nav-btn-inactive w-100 mb-2", "nav-btn-inactive w-100 mb-2"),
        "simulator": ("nav-btn-inactive w-100 mb-2", "nav-btn-active w-100 mb-2", "nav-btn-inactive w-100 mb-2"),
        "detail": ("nav-btn-inactive w-100 mb-2", "nav-btn-inactive w-100 mb-2", "nav-btn-active w-100 mb-2"),
    }
    c = classes[view]
    return view, c[0], c[1], c[2]


@callback(
    Output("sku-filters", "style"),
    Input("view-select", "data"),
)
def toggle_filters(view):
    return {"display": "none"} if view in ("overview", "simulator") else {"display": "block"}


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
    if view == "overview":
        return build_overview_layout(df)
    if view == "simulator":
        return build_simulator_layout(df)
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
# OVERVIEW VIEW
# ══════════════════════════════════════════════════════════════════════════════

def build_overview_layout(df):
    if df.empty:
        return html.Div("No data loaded. Upload a CSV or Excel file.", className="text-muted mt-4")

    overview_df = build_overview_data(df)
    if overview_df.empty:
        return html.Div("Could not analyse any SKUs. Check your data.", className="text-muted mt-4")

    manufacturers = sorted(overview_df["manufacturer"].unique())
    total_skus = len(overview_df)
    increase_count = int((overview_df["action"] == "Increase Price").sum())
    decrease_count = int((overview_df["action"] == "Decrease Price").sum())
    hold_count = int((overview_df["action"] == "Hold Price").sum())
    total_profit_impact = overview_df["profit_impact"].sum()

    summary_cards = dbc.Row([
        make_kpi_card("Total SKUs", str(total_skus)),
        make_kpi_card("Increase", str(increase_count), CHART_GREEN),
        make_kpi_card("Decrease", str(decrease_count), CHART_RED),
        make_kpi_card("Hold", str(hold_count), CHART_AMBER),
        make_kpi_card("Portfolio Impact",
                      f"\u00a3{total_profit_impact:+,.0f}",
                      CHART_GREEN if total_profit_impact >= 0 else CHART_RED),
    ], className="mb-4")

    # Verdict table with red/amber/green
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
            {"name": "Current Price (\u00a3)", "id": "Current Price", "type": "numeric"},
            {"name": "Verdict", "id": "Verdict"},
            {"name": "New Price (\u00a3)", "id": "New Price", "type": "numeric"},
            {"name": "Price Change", "id": "Price Change"},
            {"name": "Revenue Impact (\u00a3)", "id": "Revenue Impact", "type": "numeric"},
            {"name": "Impact %", "id": "Impact %", "type": "numeric"},
        ],
        sort_action="native",
        sort_mode="multi",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px",
                         "backgroundColor": CHARCOAL, "color": BODY_TEXT,
                         "border": "none", "borderBottom": f"0.5px solid {BORDER}"},
        style_header={"backgroundColor": CHARCOAL, "color": WARM_GRAY, "fontWeight": "500",
                       "borderBottom": f"1px solid {GOLD}", "textTransform": "uppercase",
                       "fontSize": "11px", "letterSpacing": "0.08em"},
        style_data_conditional=[
            {"if": {"filter_query": '{Verdict} = "Increase"', "column_id": "Verdict"},
             "backgroundColor": "rgba(201,168,76,0.15)", "color": GOLD, "fontWeight": "500"},
            {"if": {"filter_query": '{Verdict} = "Decrease"', "column_id": "Verdict"},
             "backgroundColor": "rgba(192,57,43,0.15)", "color": ALERT_RED, "fontWeight": "500"},
            {"if": {"filter_query": '{Verdict} = "Hold"', "column_id": "Verdict"},
             "backgroundColor": "rgba(26,58,92,0.15)", "color": ABI_NAVY, "fontWeight": "500"},
        ],
        page_size=50,
    )

    # Charts with AB InBev palette
    mfr_impact = overview_df.groupby("manufacturer")["profit_impact"].sum().reset_index()
    mfr_impact = mfr_impact.sort_values("profit_impact", ascending=True)
    fig_mfr = go.Figure(go.Bar(
        x=mfr_impact["profit_impact"], y=mfr_impact["manufacturer"], orientation="h",
        marker_color=[CHART_GREEN if v >= 0 else CHART_RED for v in mfr_impact["profit_impact"]],
        text=[f"\u00a3{v:+,.0f}" for v in mfr_impact["profit_impact"]], textposition="outside",
    ))
    fig_mfr.update_layout(**CHART_LAYOUT, title="Profit Impact by Manufacturer",
                          height=300, margin=dict(t=40, l=150))
    fig_mfr.add_vline(x=0, line_dash="dash", line_color=BORDER)

    action_color_map = {"Increase Price": GOLD, "Decrease Price": ALERT_RED, "Hold Price": ABI_NAVY}
    action_counts = overview_df.groupby(["manufacturer", "action"]).size().reset_index(name="count")
    fig_actions = go.Figure()
    for action in ["Decrease Price", "Hold Price", "Increase Price"]:
        subset = action_counts[action_counts["action"] == action]
        fig_actions.add_trace(go.Bar(
            x=subset["manufacturer"], y=subset["count"],
            name=action, marker_color=action_color_map[action],
        ))
    fig_actions.update_layout(**CHART_LAYOUT, barmode="stack", title="Action Distribution",
                              yaxis_title="SKUs", height=300, margin=dict(t=40),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    # Market share charts
    mfr_order = sorted(overview_df["manufacturer"].unique())
    mfr_colors = dict(zip(mfr_order, [GOLD, ABI_NAVY, WARM_GRAY, FOREST_GREEN, GOLD_LIGHT]))
    pie_colors = [mfr_colors.get(m, WARM_GRAY) for m in mfr_order]

    mfr_vol_current = overview_df.groupby("manufacturer")["volume"].sum()
    mfr_vol_projected = overview_df.groupby("manufacturer")["projected_volume"].sum()
    mfr_rev_current = overview_df.groupby("manufacturer")["revenue"].sum()
    mfr_rev_projected = overview_df.groupby("manufacturer")["projected_revenue"].sum()

    total_vol_current = mfr_vol_current.sum()
    total_vol_projected = mfr_vol_projected.sum()
    vol_share_current = (mfr_vol_current / total_vol_current * 100).round(1)
    vol_share_projected = (mfr_vol_projected / total_vol_projected * 100).round(1)
    vol_share_delta = (vol_share_projected - vol_share_current).round(2)

    total_rev_current = mfr_rev_current.sum()
    total_rev_projected = mfr_rev_projected.sum()
    rev_share_current = (mfr_rev_current / total_rev_current * 100).round(1)
    rev_share_projected = (mfr_rev_projected / total_rev_projected * 100).round(1)
    rev_share_delta = (rev_share_projected - rev_share_current).round(2)

    fig_vol_share = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]],
                                   subplot_titles=["Current Volume Share", "Projected Volume Share"])
    fig_vol_share.add_trace(go.Pie(labels=mfr_order, values=[mfr_vol_current[m] for m in mfr_order],
                                    hole=0.45, marker_colors=pie_colors, textinfo="label+percent",
                                    textposition="outside"), row=1, col=1)
    fig_vol_share.add_trace(go.Pie(labels=mfr_order, values=[mfr_vol_projected[m] for m in mfr_order],
                                    hole=0.45, marker_colors=pie_colors, textinfo="label+percent",
                                    textposition="outside"), row=1, col=2)
    fig_vol_share.update_layout(**CHART_LAYOUT, title="Volume Market Share", height=380,
                                 margin=dict(t=60, b=20), showlegend=False)

    fig_rev_share = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]],
                                   subplot_titles=["Current Revenue Share", "Projected Revenue Share"])
    fig_rev_share.add_trace(go.Pie(labels=mfr_order, values=[mfr_rev_current[m] for m in mfr_order],
                                    hole=0.45, marker_colors=pie_colors, textinfo="label+percent",
                                    textposition="outside"), row=1, col=1)
    fig_rev_share.add_trace(go.Pie(labels=mfr_order, values=[mfr_rev_projected[m] for m in mfr_order],
                                    hole=0.45, marker_colors=pie_colors, textinfo="label+percent",
                                    textposition="outside"), row=1, col=2)
    fig_rev_share.update_layout(**CHART_LAYOUT, title="Revenue Market Share", height=380,
                                 margin=dict(t=60, b=20), showlegend=False)

    fig_share_shift = go.Figure()
    fig_share_shift.add_trace(go.Bar(x=mfr_order, y=[vol_share_delta[m] for m in mfr_order],
                                      name="Volume Share \u0394", marker_color=ABI_NAVY,
                                      text=[f"{vol_share_delta[m]:+.2f}pp" for m in mfr_order],
                                      textposition="outside"))
    fig_share_shift.add_trace(go.Bar(x=mfr_order, y=[rev_share_delta[m] for m in mfr_order],
                                      name="Revenue Share \u0394", marker_color=GOLD,
                                      text=[f"{rev_share_delta[m]:+.2f}pp" for m in mfr_order],
                                      textposition="outside"))
    fig_share_shift.update_layout(**CHART_LAYOUT, title="Market Share Shift (pp)",
                                   yaxis_title="Change (pp)", barmode="group", height=350, margin=dict(t=40),
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_share_shift.add_hline(y=0, line_dash="dash", line_color=BORDER)

    sku_sorted = overview_df.sort_values("profit_impact", ascending=True)
    fig_waterfall = go.Figure(go.Bar(
        x=sku_sorted["profit_impact"], y=sku_sorted["sku_name"], orientation="h",
        marker_color=[GOLD if a == "Increase Price" else ALERT_RED if a == "Decrease Price" else ABI_NAVY
                      for a in sku_sorted["action"]],
        text=[f"\u00a3{v:+,.0f}" for v in sku_sorted["profit_impact"]], textposition="outside",
    ))
    fig_waterfall.update_layout(**CHART_LAYOUT, title="Profit Impact by SKU",
                                 height=max(400, len(sku_sorted) * 28), margin=dict(t=40, l=220))
    fig_waterfall.add_vline(x=0, line_dash="dash", line_color=BORDER)

    # Logo banner
    logo_banner = dbc.Row([
        dbc.Col(
            html.Img(src=LOGO_MAP.get(m, ""), style={"height": "36px", "objectFit": "contain"}),
            width="auto", className="d-flex align-items-center",
        )
        for m in manufacturers if m in LOGO_MAP
    ], className="logo-banner mb-3 g-4", justify="center")

    return html.Div([
        html.H3("Portfolio Price Recommendations", className="page-title mb-1"),
        html.P(f"Analysing {total_skus} SKUs across {len(manufacturers)} manufacturers",
               className="page-subtitle mb-2"),
        logo_banner,
        html.Hr(),
        summary_cards,
        html.Hr(),
        dbc.Row([
            dbc.Col(section_title("Verdict Table")),
            dbc.Col(
                dbc.Button("Export CSV", id="btn-export-csv", className="export-btn", size="sm"),
                width="auto",
            ),
        ], justify="between", align="center", className="mb-2"),
        verdict_table,
        html.Hr(className="mt-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_mfr), width=6),
            dbc.Col(dcc.Graph(figure=fig_actions), width=6),
        ], className="mb-4"),
        html.Hr(),
        section_title("Market Share: Before vs After"),
        dcc.Graph(figure=fig_vol_share),
        dcc.Graph(figure=fig_rev_share, className="mt-2"),
        dcc.Graph(figure=fig_share_shift, className="mt-2 mb-4"),
        html.Hr(),
        section_title("Profit Impact by SKU"),
        dcc.Graph(figure=fig_waterfall),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO SIMULATOR VIEW
# ══════════════════════════════════════════════════════════════════════════════

def build_simulator_layout(df):
    if df.empty:
        return html.Div("No data loaded.", className="text-muted mt-4")

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
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px",
                         "backgroundColor": CHARCOAL, "color": BODY_TEXT,
                         "border": "none", "borderBottom": f"0.5px solid {BORDER}"},
        style_header={"backgroundColor": CHARCOAL, "color": WARM_GRAY, "fontWeight": "500",
                       "borderBottom": f"1px solid {GOLD}", "textTransform": "uppercase",
                       "fontSize": "11px", "letterSpacing": "0.08em"},
        style_data_conditional=[{
            "if": {"state": "selected"},
            "backgroundColor": "rgba(201,168,76,0.15)", "border": f"1px solid {GOLD}",
        }],
        page_size=50,
    )

    return html.Div([
        html.H3("Scenario Simulator", className="page-title mb-1"),
        html.P("Select a SKU, adjust its price, and see live portfolio-wide impact.",
               className="page-subtitle mb-3"),
        html.Hr(),
        section_title("Select a SKU"),
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

    summary = dbc.Row([
        make_kpi_card("SKUs Adjusted", str(adjusted_count)),
        make_kpi_card("Baseline Profit", f"\u00a3{total_baseline:,.0f}"),
        make_kpi_card("Simulated Profit", f"\u00a3{total_new:,.0f}"),
        make_kpi_card("Total Impact",
                      f"\u00a3{total_impact:+,.0f} ({total_impact_pct:+.1f}%)",
                      CHART_GREEN if total_impact >= 0 else CHART_RED),
    ], className="mb-4")

    changed_skus = sim_df[sim_df["price_change_pct"] != 0].sort_values("profit_impact", ascending=True)

    if not changed_skus.empty:
        fig_impact = go.Figure(go.Bar(
            x=changed_skus["profit_impact"], y=changed_skus["sku_name"], orientation="h",
            marker_color=[CHART_GREEN if v >= 0 else CHART_RED for v in changed_skus["profit_impact"]],
            text=[f"\u00a3{v:+,.0f}" for v in changed_skus["profit_impact"]], textposition="outside",
        ))
        fig_impact.update_layout(**CHART_LAYOUT, title="Impact of Adjusted SKUs",
                                  height=max(250, len(changed_skus) * 35), margin=dict(t=40, l=220))
        fig_impact.add_vline(x=0, line_dash="dash", line_color=BORDER)
        impact_chart = dcc.Graph(figure=fig_impact)
    else:
        impact_chart = html.P("Adjust a SKU price to see impact.", className="text-muted text-center my-4")

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
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px",
                         "backgroundColor": CHARCOAL, "color": BODY_TEXT,
                         "border": "none", "borderBottom": f"0.5px solid {BORDER}"},
        style_header={"backgroundColor": CHARCOAL, "color": WARM_GRAY, "fontWeight": "500",
                       "borderBottom": f"1px solid {GOLD}", "textTransform": "uppercase",
                       "fontSize": "11px", "letterSpacing": "0.08em"},
        style_data_conditional=[
            {"if": {"filter_query": "{_changed} = 1"}, "backgroundColor": "rgba(201,168,76,0.08)", "fontWeight": "500"},
            {"if": {"filter_query": "{Profit Impact} > 0", "column_id": "Profit Impact"}, "color": GOLD},
            {"if": {"filter_query": "{Profit Impact} < 0", "column_id": "Profit Impact"}, "color": ALERT_RED},
        ],
        page_size=50,
    )

    mfr_impact = sim_df.groupby("manufacturer")["profit_impact"].sum().reset_index()
    mfr_impact = mfr_impact.sort_values("profit_impact", ascending=True)
    fig_mfr = go.Figure(go.Bar(
        x=mfr_impact["profit_impact"], y=mfr_impact["manufacturer"], orientation="h",
        marker_color=[CHART_GREEN if v >= 0 else CHART_RED for v in mfr_impact["profit_impact"]],
        text=[f"\u00a3{v:+,.0f}" for v in mfr_impact["profit_impact"]], textposition="outside",
    ))
    fig_mfr.update_layout(**CHART_LAYOUT, title="Impact by Manufacturer", height=250, margin=dict(t=40, l=150))
    fig_mfr.add_vline(x=0, line_dash="dash", line_color=BORDER)

    return html.Div([
        section_title("Portfolio Impact"),
        summary,
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
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px",
                         "backgroundColor": CHARCOAL, "color": BODY_TEXT,
                         "border": "none", "borderBottom": f"0.5px solid {BORDER}"},
        style_header={"backgroundColor": CHARCOAL, "color": WARM_GRAY, "fontWeight": "500",
                       "borderBottom": f"1px solid {GOLD}", "textTransform": "uppercase",
                       "fontSize": "11px", "letterSpacing": "0.08em"},
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
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px",
                         "backgroundColor": CHARCOAL, "color": BODY_TEXT,
                         "border": "none", "borderBottom": f"0.5px solid {BORDER}"},
        style_header={"backgroundColor": CHARCOAL, "color": WARM_GRAY, "fontWeight": "500",
                       "borderBottom": f"1px solid {GOLD}", "textTransform": "uppercase",
                       "fontSize": "11px", "letterSpacing": "0.08em"},
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
