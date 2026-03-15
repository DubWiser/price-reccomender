"""Cannibalization Analysis page."""

import plotly.graph_objects as go
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

from theme import (
    CHARCOAL, GOLD, WARM_GRAY, ALERT_RED, FOREST_GREEN,
    BORDER, BODY_TEXT, CHART_LAYOUT,
    TABLE_STYLE_CELL, TABLE_STYLE_HEADER,
    make_kpi_card, section_title,
)
from pricing_engine import compute_cannibalization_risk, generate_cross_elasticity_matrix


def build_cannibalization_layout(df):
    if df.empty:
        return html.Div("No data loaded.", className="text-muted mt-4")

    cann_df = compute_cannibalization_risk(df)
    total = len(cann_df)
    high = cann_df[cann_df["severity"] == "High"]
    moderate = cann_df[cann_df["severity"] == "Moderate"]
    low = cann_df[cann_df["severity"] == "Low"]

    # ── KPI cards ──
    kpis = dbc.Row([
        make_kpi_card("Total SKUs", str(total)),
        make_kpi_card("High Risk", str(len(high)), ALERT_RED),
        make_kpi_card("Moderate", str(len(moderate)), GOLD),
        make_kpi_card("Low Risk", str(len(low)), FOREST_GREEN),
    ], className="mb-4")

    # ── Cannibalization % bar chart ──
    sorted_cann = cann_df.sort_values("cannibalization_rate", ascending=True)
    sev_colors = {"High": ALERT_RED, "Moderate": GOLD, "Low": FOREST_GREEN}
    bar_colors = [sev_colors[s] for s in sorted_cann["severity"]]

    fig_rate = go.Figure(go.Bar(
        x=sorted_cann["cannibalization_rate"] * 100,
        y=sorted_cann["sku_name"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{r:.0f}%" for r in sorted_cann["cannibalization_rate"] * 100],
        textposition="outside",
    ))
    fig_rate.update_layout(
        **CHART_LAYOUT,
        title="Cannibalization Rate by SKU",
        xaxis_title="Cannibalization Rate (%)",
        height=max(400, total * 28),
        margin=dict(t=40, l=220),
    )

    # ── Volume at risk stacked bar ──
    sorted_vol = cann_df.sort_values("cannibalised_volume", ascending=True)
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(
        x=sorted_vol["cannibalised_volume"],
        y=sorted_vol["sku_name"],
        orientation="h",
        name="Cannibalised",
        marker_color=ALERT_RED,
        text=[f"{v:,.0f}" for v in sorted_vol["cannibalised_volume"]],
        textposition="inside",
    ))
    fig_vol.add_trace(go.Bar(
        x=sorted_vol["safe_volume"],
        y=sorted_vol["sku_name"],
        orientation="h",
        name="Safe Volume",
        marker_color=FOREST_GREEN,
    ))
    fig_vol.update_layout(
        **CHART_LAYOUT,
        barmode="stack",
        title="Volume at Risk: Cannibalised vs Safe",
        xaxis_title="Volume (units)",
        height=max(400, total * 28),
        margin=dict(t=40, l=220),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # ── Cannibalization matrix table ──
    cross_matrix = generate_cross_elasticity_matrix(df)
    skus = df["sku_id"].tolist()
    sku_names = df.set_index("sku_id")["sku_name"].to_dict()
    mfr_map = df.set_index("sku_id")["manufacturer"].to_dict()

    matrix_data = []
    for row_sku in skus:
        row_dict = {"SKU": sku_names[row_sku], "Manufacturer": mfr_map[row_sku]}
        own_mfr_total = 0.0
        for col_sku in skus:
            val = cross_matrix.loc[row_sku, col_sku]
            col_label = col_sku.replace("SKU0", "S")
            row_dict[col_label] = round(val, 3)
            if mfr_map[row_sku] == mfr_map[col_sku] and row_sku != col_sku:
                own_mfr_total += val
        row_dict["Own-Mfr Risk"] = round(own_mfr_total, 3)
        matrix_data.append(row_dict)

    col_labels = [s.replace("SKU0", "S") for s in skus]
    matrix_cols = (
        [{"name": "SKU", "id": "SKU"}, {"name": "Manufacturer", "id": "Manufacturer"}]
        + [{"name": c, "id": c, "type": "numeric"} for c in col_labels]
        + [{"name": "Own-Mfr Risk", "id": "Own-Mfr Risk", "type": "numeric"}]
    )

    # Highlight same-manufacturer cells with gold tint
    style_cond = []
    for row_sku in skus:
        for col_sku in skus:
            if row_sku == col_sku:
                continue
            if mfr_map[row_sku] == mfr_map[col_sku]:
                col_label = col_sku.replace("SKU0", "S")
                row_name = sku_names[row_sku]
                style_cond.append({
                    "if": {"filter_query": f'{{SKU}} = "{row_name}"', "column_id": col_label},
                    "backgroundColor": "rgba(201,168,76,0.12)",
                })

    matrix_table = dash_table.DataTable(
        data=matrix_data,
        columns=matrix_cols,
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={**TABLE_STYLE_CELL, "padding": "4px 6px", "fontSize": "11px", "minWidth": "50px"},
        style_header={**TABLE_STYLE_HEADER, "fontSize": "10px", "letterSpacing": "0.06em"},
        style_data_conditional=style_cond + [
            {"if": {"column_id": "Own-Mfr Risk"},
             "fontWeight": "600", "color": GOLD, "borderLeft": f"1px solid {GOLD}"},
        ],
        style_cell_conditional=[
            {"if": {"column_id": "SKU"}, "textAlign": "left", "minWidth": "160px"},
            {"if": {"column_id": "Manufacturer"}, "textAlign": "left", "minWidth": "100px"},
        ],
        page_size=50,
    )

    return html.Div([
        html.H3("Cannibalization Analysis", className="page-title mb-1"),
        html.P("Intra-portfolio cannibalization risk and cross-SKU impact",
               className="page-subtitle mb-3"),
        html.Hr(),
        kpis,
        html.Hr(),
        section_title("Cannibalization Rate"),
        dcc.Graph(figure=fig_rate),
        html.Hr(),
        section_title("Volume at Risk"),
        dcc.Graph(figure=fig_vol),
        html.Hr(),
        section_title("Cross-SKU Cannibalization Matrix"),
        html.P("Gold-tinted cells indicate same-manufacturer pairs. "
               "\"Own-Mfr Risk\" sums cross-elasticity exposure within the same manufacturer.",
               style={"fontSize": "12px", "color": WARM_GRAY}),
        matrix_table,
    ])
