# Beer SKU Price Recommender

Revenue managers have elasticity and cannibalization data but no systematic way to turn it into pricing actions. This tool ends the guessing.

Upload a CSV or Excel file of beer SKUs with elasticity, cannibalization, price, volume, and margin data — get a verdict table showing **raise / hold / cut** per SKU, optimized for total portfolio revenue.

## Quick Start

```bash
uv sync
uv run python app.py
# Open http://localhost:8050
```

## How It Works

1. Upload your SKU portfolio (CSV or Excel) or use the built-in sample data
2. The pricing engine evaluates 5 price scenarios per SKU (-10%, -5%, 0%, +5%, +10%)
3. For each scenario it calculates:
   - Volume impact using own-price elasticity
   - Cannibalization impact on sibling SKUs within the same manufacturer
   - Net profit impact (own SKU + sibling effects)
4. The scenario with highest net profit is recommended as the verdict

## Features

- **CSV/Excel upload** — drag-and-drop or click to upload your portfolio
- **Sortable verdict table** — sort and filter by any column, color-coded verdicts
- **Portfolio overview** — summary KPIs, profit impact by manufacturer, action distribution
- **Market share analysis** — before vs after donut charts for volume and revenue share
- **SKU detail view** — drill into individual SKUs with scenario tables and profit charts
- **Competitor context** — see sibling/competitor SKU data alongside recommendations

## Input Format

Your CSV/Excel must include these columns:

| Column | Description |
|--------|-------------|
| `sku_id` | Unique SKU identifier |
| `manufacturer` | Manufacturer name |
| `brand` | Brand name |
| `sku_name` | Human-readable SKU name |
| `price_segment` | Core, Premium, or Value |
| `current_price_per_unit` | Current unit price |
| `elasticity` | Own-price elasticity (negative) |
| `cannibalization_rate` | Cross-SKU cannibalization rate (0-1) |
| `profit_pct_per_ml` | Profit percentage per mL |
| `volume_2025_units` | Current volume in units |
| `unit_volume_ml` | Volume per unit in mL |
| `competitor_sku_1` | First competitor SKU ID |
| `competitor_sku_2` | Second competitor SKU ID |

A sample portfolio with 42 SKUs is included at `data/full_portfolio.xlsx`.

## Tech Stack

Python · Pandas · Dash · Plotly · dash-bootstrap-components · uv

## Tests

```bash
uv run pytest tests/ -v
```

## Project Structure

```
app.py                    — Dash UI entry point
src/pricing_engine.py     — Rule-based pricing logic
data/sample_skus.csv      — 20-SKU sample dataset
data/full_portfolio.xlsx  — 42-SKU full portfolio
tests/                    — Test suite
docs/features.md          — Feature specification
```
