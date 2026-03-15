# Feature Spec — Buildathon Project
# This file is the single source of truth for what is being built.
# The AI editor should reference this file before writing any code.
# Do NOT add features that are not listed here.

## What this app does
The Core Problem Revenue managers have elasticity and cannibalization data but no systematic way to turn it into pricing actions. They guess. This tool ends the guessing.  App Upload a CSV of SKUs with elasticity, cannibalization, price, volume, competitor price, and margin — get a verdict table showing raise/hold/cut per SKU, optimized for total portfolio revenue, with a scenario simulator to test changes.

## Context
This is a buildathon project being built in a single day (~8 hours).
The user is building a web app from scratch using AI-assisted coding tools.
The goal is a working demo by 5:15 PM, not a production-ready product.
Prioritise shipping over polish. Working beats perfect.

## Build plan
The project is structured as a series of iterations.
Each iteration should be completed end-to-end before starting the next.
Iteration 0 is mandatory. The rest are stretch goals in priority order.
If the user is behind schedule, skip to the next iteration or cut scope.

### Iteration 0 — Magic moment (COMPLETED)
**Status:** COMPLETED

**Original scope:** A Python script that takes a hardcoded list of 5 SKUs with elasticity + cannibalization + current price + volume, runs the revenue optimization logic, and prints raise/hold/cut verdicts to the terminal. No UI. Proves the math works.

**What was delivered:**
- `src/pricing_engine.py` — rule-based pricing engine with elasticity-based volume projection, cannibalization impact on sibling SKUs, net profit calculation across 5 price scenarios (−10%, −5%, 0%, +5%, +10%), and recommendation selection
- `data/sample_skus.csv` — 20 beer SKUs across 4 manufacturers (AB InBev, Heineken, Carlsberg, Molson Coors) with elasticity, cannibalization rate, profit % per mL, 2025 volume, and competitor references
- `app.py` — full Dash web UI (ahead of plan) with:
  - All Manufacturers overview page with summary KPIs, per-manufacturer tables, market share charts, profit impact charts
  - SKU Detail view with cascading sidebar filters, KPI cards, recommendation banner, scenario table, profit impact bar chart, competitor table
- Math is proven and working end-to-end

### Iteration 1 — First real feature with UI (~1 hr)
A single-page web UI where the user pastes or uploads a CSV, and sees a sortable verdict table (SKU name, current price, verdict, estimated revenue impact).

### Iteration 2 — Second feature or improvement (~1 hr)
Add a scenario simulator — click any SKU, drag a price slider, and see live revenue impact across the whole portfolio accounting for cannibalization.

### Iteration 3 — Polish, auth, or secondary features (~1 hr)
Add competitor price context to the UI (flag SKUs where your price is significantly above/below competitor), and a summary header showing total portfolio revenue delta.

### Iteration 4 — Nice-to-haves (~30 min)
Export to CSV, color coding (red/amber/green), and edge case handling for missing data.

## What has been explicitly cut (do NOT build these)
Nothing specified — but always prefer less scope over more.

## Technical constraints
- No real database required — use JSON arrays or in-memory data for v1
- No user authentication needed until Iteration 3 at the earliest
- Desktop only — no mobile responsiveness needed
- console.log for error handling is fine
- alert() instead of toast notifications is fine
- Page refresh instead of reactive state updates is fine

## Actual tech stack (decided during Iteration 0)
- Python 3.9+
- pandas + numpy for data and pricing logic
- Dash + Plotly for UI (chosen over Streamlit for richer interactivity)
- dash-bootstrap-components (Flatly theme) for styling
- uv for package management

## Future Improvements — Enhanced Market Share Simulation

The current simulator uses own-price elasticity and a flat cannibalization rate. To properly assess the impact of one SKU within the portfolio and on competition, the following data and logic enhancements are needed:

### Within-portfolio (sibling) assessment
- **Cross-price elasticity between specific SKU pairs** — e.g. "if Budweiser 330ml drops 5%, Bud Light 330ml loses X% volume". The current flat cannibalization rate doesn't distinguish which sibling is affected or by how much.
- **Substitution hierarchy** — segment matters: a Premium SKU price cut steals more from other Premium SKUs than from Value SKUs. The engine should weight cannibalization by segment proximity.

### Competitive assessment
- **Competitor prices** (`competitor_price`) — external competitor pricing to calculate price gaps and flag vulnerability (e.g. "your SKU is 15% above the nearest competitor").
- **Price index vs category** (`price_index`) — where each SKU sits relative to segment average (100 = parity). Enables quick identification of over/under-priced SKUs.
- **Cross-manufacturer elasticity** (`cross_elasticity`) — volume sensitivity to competitor price changes. Enables modelling "if Heineken drops 5%, how much Budweiser volume is at risk?"

### Market context
- **Total market/category volume** (`market_volume_segment`) — needed to calculate actual market share rather than just relative portfolio share.
- **Channel split** (on-trade vs off-trade) — pricing dynamics differ significantly between channels; a single elasticity value may not capture this.

### Suggested new input columns

| Column | Type | Purpose |
|---|---|---|
| `competitor_price` | float | Direct competitor's current unit price |
| `price_index` | float | SKU price vs segment average (100 = parity) |
| `cross_elasticity` | float | Volume sensitivity to competitor price changes |
| `market_volume_segment` | int | Total market volume for the price segment |

### Impact on engine logic
- `simulate_portfolio()` should account for cross-SKU elasticity pairs, not just flat cannibalization
- Competitor price gaps should inform whether a price increase is safe (large gap = risky) or a decrease is warranted
- Market share calculations should use total market volume as denominator, not just portfolio volume

## How to use this file
- Before building any feature, check: is it listed above?
- Before adding scope, check: is it in the cuts list?
- When the user says "checkpoint", commit with a descriptive message
- When the user asks for something not in this spec, push back:
  "That's not in the feature spec. Want to add it to a later iteration?"
