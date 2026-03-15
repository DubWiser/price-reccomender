"""
Shared design-system constants and UI helpers.

Extracted from app.py to avoid circular imports when page modules need
the same colors, chart layout, or card builders.
"""

from dash import html
import dash_bootstrap_components as dbc

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

# ── Variant of CHART_LAYOUT with yaxis stripped (for charts that set custom yaxis) ──
CHART_LAYOUT_NO_YAXIS = {k: v for k, v in CHART_LAYOUT.items() if k != "yaxis"}
CHART_LAYOUT_NO_AXES = {k: v for k, v in CHART_LAYOUT.items() if k not in ("xaxis", "yaxis")}

# ── Nav button class name constants ──────────────────────────────────────────
NAV_BTN_ACTIVE = "nav-btn-active w-100 mb-2"
NAV_BTN_INACTIVE = "nav-btn-inactive w-100 mb-2"

# ── Shared DataTable styles (use as **TABLE_STYLE in DataTable kwargs) ────────
TABLE_STYLE_CELL = {
    "textAlign": "center", "padding": "8px", "fontSize": "13px",
    "backgroundColor": CHARCOAL, "color": BODY_TEXT,
    "border": "none", "borderBottom": f"0.5px solid {BORDER}",
}
TABLE_STYLE_HEADER = {
    "backgroundColor": CHARCOAL, "color": WARM_GRAY, "fontWeight": "500",
    "borderBottom": f"1px solid {GOLD}", "textTransform": "uppercase",
    "fontSize": "11px", "letterSpacing": "0.08em",
}

# ── Manufacturer logo mapping ────────────────────────────────────────────────
LOGO_MAP = {
    "AB InBev": "/assets/logos/ab_inbev.png",
    "Heineken": "/assets/logos/heineken.png",
    "Carlsberg": "/assets/logos/carlsberg.png",
    "Molson Coors": "/assets/logos/molson_coors.png",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

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
