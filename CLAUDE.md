# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Beer SKU price recommender built for an AI Buildathon. Suggests optimal price actions based on elasticity and cannibalization rate.

## Repository Structure

- `app.py` — Dash entry point (UI)
- `src/pricing_engine.py` — core rule-based pricing logic
- `data/sample_skus.csv` — 20 beer SKUs across AB InBev, Heineken, Carlsberg, Molson Coors
- `docs/features.md` — feature specification
- `rules/` — development guidelines (building, debug, frozen)

## Development Setup

Uses **uv** for package management.

```bash
uv sync
uv run python app.py
# App serves on http://localhost:8050
```

## Architecture

**Stack:** Python · Pandas · Dash · Plotly · uv

**Key files:**
- `src/pricing_engine.py` — elasticity-based volume projection, cannibalization impact on sibling SKUs, net profit calculation across price scenarios, recommendation selection
- `app.py` — Dash UI: sidebar SKU selector, KPI metrics, recommendation banner, scenario table, profit impact bar chart, sibling SKU panel
- `data/sample_skus.csv` — SKU data with elasticity, cannibalization rate, profit % per mL, 2025 volume

**Data flow:**
1. `load_data()` reads CSV from `data/` into a DataFrame
2. User selects manufacturer → brand → segment → SKU via sidebar
3. `run_scenarios()` evaluates 5 price scenarios (−10%, −5%, 0%, +5%, +10%) per SKU:
   - New volume = current_volume × (1 + elasticity × price_pct_change)
   - Sibling profit delta = volume shifted to siblings × their avg profit proxy
   - Net profit = own profit + sibling profit delta
4. `recommend()` picks the scenario with highest net profit and returns action label
5. UI renders KPIs, recommendation, scenario table (highlighted best row), bar chart, sibling SKU table
