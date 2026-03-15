"""Executive Summary page."""

import pandas as pd
from dash import html
import dash_bootstrap_components as dbc

from pricing_engine import analyse_sku, generate_executive_insights
from theme import (
    CHARCOAL, GOLD, GOLD_LIGHT, WARM_GRAY, ALERT_RED, FOREST_GREEN,
    ABI_NAVY, BORDER, BODY_TEXT, HEADING_TEXT, MIDNIGHT,
    make_kpi_card, section_title,
)


def _exec_card(title, body_children):
    """A dark-styled card for the 2×2 executive grid."""
    return dbc.Card([
        dbc.CardHeader(
            html.H5(title, className="mb-0",
                     style={"color": GOLD, "fontSize": "15px", "fontWeight": "500"}),
            style={"backgroundColor": CHARCOAL, "borderBottom": f"1px solid {BORDER}",
                    "padding": "12px 16px"},
        ),
        dbc.CardBody(body_children, style={"padding": "16px"}),
    ], className="exec-panel h-100",
       style={"backgroundColor": CHARCOAL, "border": f"0.5px solid {BORDER}",
              "borderRadius": "8px"})


def build_executive_summary_layout(df, overview_data=None):
    if df.empty:
        return html.Div("No data loaded.", className="text-muted mt-4")

    # Build overview_data if not provided
    if overview_data is None:
        rows = []
        for _, sku in df.iterrows():
            try:
                rec, _ = analyse_sku(sku["sku_id"], df)
            except Exception:
                continue
            rows.append({
                "sku_id": sku["sku_id"],
                "sku_name": sku["sku_name"],
                "manufacturer": sku["manufacturer"],
                "action": rec["action"],
            })
        overview_data = pd.DataFrame(rows)

    insights = generate_executive_insights(df, overview_data)
    ms = insights["market_structure"]
    er = insights["elasticity_risks"]
    ct = insights["cannibalization_threats"]
    recs = insights["recommendations"]

    # ── Panel 1: Market Structure ──
    mfr_tiles = []
    for m in ms["manufacturers"]:
        share = ms["volume_shares"].get(m, 0)
        count = ms["sku_counts"].get(m, 0)
        is_leader = m == ms["market_leader"]
        tile_style = {
            "backgroundColor": MIDNIGHT, "borderRadius": "6px", "padding": "10px 14px",
            "border": f"1px solid {GOLD}" if is_leader else f"0.5px solid {BORDER}",
        }
        mfr_tiles.append(
            dbc.Col(html.Div([
                html.Div(m, style={"color": HEADING_TEXT, "fontSize": "13px", "fontWeight": "500"}),
                html.Div(f"{share}% share", style={"color": GOLD, "fontSize": "18px", "fontWeight": "300",
                                                     "fontFamily": "'SF Mono', monospace"}),
                html.Div(f"{count} SKUs", style={"color": WARM_GRAY, "fontSize": "11px"}),
            ], style=tile_style), width=6, className="mb-2")
        )

    market_body = [
        dbc.Row(mfr_tiles),
        html.Hr(style={"borderColor": BORDER}),
        html.Div([
            html.Span(f"{ms['total_skus']} SKUs", style={"color": HEADING_TEXT, "fontWeight": "500"}),
            html.Span(" across ", style={"color": WARM_GRAY}),
            html.Span(f"{len(ms['manufacturers'])} manufacturers",
                       style={"color": HEADING_TEXT, "fontWeight": "500"}),
            html.Span(" in ", style={"color": WARM_GRAY}),
            html.Span(f"{len(ms['segments'])} segments",
                       style={"color": HEADING_TEXT, "fontWeight": "500"}),
        ], style={"fontSize": "13px"}),
    ]

    # ── Panel 2: Elasticity Risk Zones ──
    elas_items = []
    for i, insight in enumerate(er["insights"], 1):
        elas_items.append(html.Div([
            html.Span(f"{i}. ", style={"color": GOLD, "fontWeight": "600"}),
            html.Span(insight, style={"color": BODY_TEXT}),
        ], className="insight-item mb-2", style={"fontSize": "13px", "lineHeight": "1.5"}))

    zone_summary = html.Div([
        html.Span(f"{er['highly_elastic_count']} highly elastic",
                   style={"color": ALERT_RED, "fontWeight": "500"}),
        html.Span(" · ", style={"color": WARM_GRAY}),
        html.Span(f"{er['elastic_count']} elastic",
                   style={"color": GOLD, "fontWeight": "500"}),
        html.Span(" · ", style={"color": WARM_GRAY}),
        html.Span(f"{er['inelastic_count']} inelastic",
                   style={"color": FOREST_GREEN, "fontWeight": "500"}),
    ], className="mb-3", style={"fontSize": "13px"})

    elas_body = [zone_summary] + elas_items

    # ── Panel 3: Cannibalization Threats ──
    cann_items = []
    if ct["by_manufacturer"]:
        for m, data in ct["by_manufacturer"].items():
            sku_list = ", ".join(data["skus"][:3])
            vol = data["volume_at_risk"]
            cann_items.append(html.Div([
                html.Div(m, style={"color": GOLD, "fontSize": "13px", "fontWeight": "500"}),
                html.Div(f"{sku_list}", style={"color": BODY_TEXT, "fontSize": "12px"}),
                html.Div(f"{vol:,.0f} units at risk",
                         style={"color": ALERT_RED, "fontSize": "12px", "fontWeight": "500"}),
            ], className="insight-item mb-2",
               style={"backgroundColor": MIDNIGHT, "borderRadius": "4px",
                       "padding": "8px 12px", "border": f"0.5px solid {BORDER}"}))
    else:
        cann_items.append(html.P("No high-risk cannibalization detected.", style={"color": WARM_GRAY}))

    cann_summary = html.Div([
        html.Span(f"{ct['high_risk_count']} high risk",
                   style={"color": ALERT_RED, "fontWeight": "500"}),
        html.Span(" · ", style={"color": WARM_GRAY}),
        html.Span(f"{ct['moderate_count']} moderate",
                   style={"color": GOLD, "fontWeight": "500"}),
        html.Span(" · ", style={"color": WARM_GRAY}),
        html.Span(f"{ct['low_count']} low risk",
                   style={"color": FOREST_GREEN, "fontWeight": "500"}),
    ], className="mb-3", style={"fontSize": "13px"})

    cann_body = [cann_summary] + cann_items

    # ── Panel 4: Pricing Recommendations ──
    rec_items = []
    for i, r in enumerate(recs, 1):
        arrow_color = FOREST_GREEN if r["direction"] == "↑" else ALERT_RED if r["direction"] == "↓" else GOLD
        rec_items.append(html.Div([
            dbc.Row([
                dbc.Col(
                    html.Div(r["direction"],
                             style={"fontSize": "24px", "color": arrow_color, "fontWeight": "700",
                                    "textAlign": "center", "lineHeight": "1"}),
                    width=1,
                ),
                dbc.Col([
                    html.Div(r["sku"], style={"color": HEADING_TEXT, "fontSize": "13px", "fontWeight": "500"}),
                    html.Div(r["rationale"], style={"color": WARM_GRAY, "fontSize": "12px", "lineHeight": "1.4"}),
                ]),
            ], align="center"),
        ], className="insight-item mb-2",
           style={"backgroundColor": MIDNIGHT, "borderRadius": "4px",
                   "padding": "10px 12px", "border": f"0.5px solid {BORDER}"}))

    # ── Assemble 2×2 grid ──
    return html.Div([
        html.H3("Executive Summary", className="page-title mb-1"),
        html.P("Portfolio-wide insights and actionable pricing recommendations",
               className="page-subtitle mb-3"),
        html.Hr(),
        dbc.Row([
            dbc.Col(_exec_card("Market Structure", market_body), width=6, className="mb-3"),
            dbc.Col(_exec_card("Elasticity Risk Zones", elas_body), width=6, className="mb-3"),
        ]),
        dbc.Row([
            dbc.Col(_exec_card("Cannibalization Threats", cann_body), width=6, className="mb-3"),
            dbc.Col(_exec_card("Pricing Recommendations", rec_items), width=6, className="mb-3"),
        ]),
    ])
