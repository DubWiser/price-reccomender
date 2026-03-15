"""Elasticity Analysis page."""

import plotly.graph_objects as go
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

from theme import (
    CHARCOAL, GOLD, WARM_GRAY, ALERT_RED, FOREST_GREEN,
    BORDER, BODY_TEXT, CHART_LAYOUT, CHART_LAYOUT_NO_AXES,
    TABLE_STYLE_CELL, TABLE_STYLE_HEADER,
    make_kpi_card, section_title,
)
from pricing_engine import generate_cross_elasticity_matrix


def build_elasticity_layout(df):
    if df.empty:
        return html.Div("No data loaded.", className="text-muted mt-4")

    total = len(df)
    highly_elastic = df[df["elasticity"] < -2.0]
    elastic = df[(df["elasticity"] >= -2.0) & (df["elasticity"] < -1.5)]
    inelastic = df[df["elasticity"] >= -1.5]

    # ── KPI cards ──
    kpis = dbc.Row([
        make_kpi_card("Total SKUs", str(total)),
        make_kpi_card("Highly Elastic", str(len(highly_elastic)), ALERT_RED),
        make_kpi_card("Elastic", str(len(elastic)), GOLD),
        make_kpi_card("Inelastic", str(len(inelastic)), FOREST_GREEN),
    ], className="mb-4")

    # ── Own-price elasticity bar chart ──
    sorted_df = df.sort_values("elasticity", ascending=True)
    bar_colors = []
    for e in sorted_df["elasticity"]:
        if e < -2.0:
            bar_colors.append(ALERT_RED)
        elif e < -1.5:
            bar_colors.append(GOLD)
        else:
            bar_colors.append(FOREST_GREEN)

    fig_elas = go.Figure(go.Bar(
        x=sorted_df["elasticity"],
        y=sorted_df["sku_name"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{e:.2f}" for e in sorted_df["elasticity"]],
        textposition="outside",
    ))
    fig_elas.update_layout(
        **CHART_LAYOUT,
        title="Own-Price Elasticity by SKU",
        height=max(400, total * 28),
        margin=dict(t=40, l=220),
    )
    fig_elas.add_vline(x=-2.0, line_dash="dot", line_color=ALERT_RED,
                       annotation_text="Highly Elastic", annotation_position="top")
    fig_elas.add_vline(x=-1.5, line_dash="dot", line_color=GOLD,
                       annotation_text="Elastic", annotation_position="top")

    # ── Cross-elasticity heatmap ──
    cross_matrix = generate_cross_elasticity_matrix(df)
    abbrev = [s.replace("SKU0", "S") for s in cross_matrix.index]

    fig_heat = go.Figure(go.Heatmap(
        z=cross_matrix.values,
        x=abbrev,
        y=abbrev,
        colorscale=[[0, CHARCOAL], [0.3, "#F5F0E8"], [0.6, GOLD], [1.0, "#6B4C1A"]],
        zmin=0, zmax=0.3,
        text=cross_matrix.values.round(3),
        texttemplate="%{text:.3f}",
        textfont=dict(size=9),
        hovertemplate="Row: %{y}<br>Col: %{x}<br>Cross-elasticity: %{z:.3f}<extra></extra>",
        colorbar=dict(title="Cross-ε", tickfont=dict(color=BODY_TEXT),
                      title_font=dict(color=BODY_TEXT)),
    ))
    fig_heat.update_layout(
        **CHART_LAYOUT_NO_AXES,
        title="Cross-Elasticity Matrix (Synthetic)",
        height=600,
        margin=dict(t=40, l=60, b=60),
        xaxis=dict(tickfont=dict(size=10, color=WARM_GRAY), tickangle=-45),
        yaxis=dict(tickfont=dict(size=10, color=WARM_GRAY), autorange="reversed"),
    )

    # ── Interpretation table ──
    table_data = []
    for _, row in sorted_df.iterrows():
        e = row["elasticity"]
        if e < -2.0:
            zone = "Highly Elastic"
            implication = "Very price-sensitive — price increases will significantly reduce volume."
        elif e < -1.5:
            zone = "Elastic"
            implication = "Moderately sensitive — small price changes have noticeable volume impact."
        else:
            zone = "Inelastic"
            implication = "Low sensitivity — price increases feasible with limited volume loss."

        table_data.append({
            "SKU": row["sku_name"],
            "Manufacturer": row["manufacturer"],
            "Segment": row["price_segment"],
            "Elasticity": round(e, 2),
            "Zone": zone,
            "Pricing Implication": implication,
        })

    interp_table = dash_table.DataTable(
        data=table_data,
        columns=[
            {"name": "SKU", "id": "SKU"},
            {"name": "Manufacturer", "id": "Manufacturer"},
            {"name": "Segment", "id": "Segment"},
            {"name": "Elasticity", "id": "Elasticity", "type": "numeric"},
            {"name": "Zone", "id": "Zone"},
            {"name": "Pricing Implication", "id": "Pricing Implication"},
        ],
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data_conditional=[
            {"if": {"filter_query": '{Zone} = "Highly Elastic"', "column_id": "Zone"},
             "backgroundColor": "rgba(192,57,43,0.15)", "color": ALERT_RED, "fontWeight": "500"},
            {"if": {"filter_query": '{Zone} = "Elastic"', "column_id": "Zone"},
             "backgroundColor": "rgba(201,168,76,0.15)", "color": GOLD, "fontWeight": "500"},
            {"if": {"filter_query": '{Zone} = "Inelastic"', "column_id": "Zone"},
             "backgroundColor": "rgba(74,124,89,0.15)", "color": FOREST_GREEN, "fontWeight": "500"},
        ],
        style_cell_conditional=[
            {"if": {"column_id": "Pricing Implication"}, "textAlign": "left", "minWidth": "250px"},
        ],
        page_size=50,
    )

    return html.Div([
        html.H3("Elasticity Analysis", className="page-title mb-1"),
        html.P("Own-price elasticity and cross-elasticity across the SKU portfolio",
               className="page-subtitle mb-3"),
        html.Hr(),
        kpis,
        html.Hr(),
        section_title("Own-Price Elasticity"),
        dcc.Graph(figure=fig_elas),
        html.Hr(),
        section_title("Cross-Elasticity Heatmap"),
        dcc.Graph(figure=fig_heat),
        html.Hr(),
        section_title("Elasticity Interpretation"),
        interp_table,
    ])
