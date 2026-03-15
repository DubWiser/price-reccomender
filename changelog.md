# Changelog

## Iteration 1 — CSV/Excel Upload + Sortable Verdict Table

**Status:** COMPLETED

**Planned scope:**
- Single-page web UI where user uploads a CSV/Excel file and sees a sortable verdict table (SKU name, current price, verdict, estimated revenue impact)

**Delivered:**
- [x] **File upload** — `dcc.Upload` component in sidebar accepting `.csv` and `.xlsx` files
- [x] **Column validation** — uploaded files checked for all 13 required columns; clear error messages on failure
- [x] **Dynamic data pipeline** — `dcc.Store` holds active dataset (default or uploaded); all callbacks react to data changes
- [x] **Sortable + filterable verdict table** — `DataTable` with native sorting (multi-column), native filtering, color-coded verdict cells (Increase/Hold/Decrease)
- [x] **Full portfolio Excel file** — `data/full_portfolio.xlsx` with 42 SKUs across 4 manufacturers (AB InBev, Heineken, Carlsberg, Molson Coors) and 17 brands
- [x] **All existing views preserved** — overview charts, SKU detail view, cascading filters all work with uploaded data
- [x] **14 tests passing** — pricing engine, upload parsing (CSV/Excel/invalid), overview data, verdict values

**Files changed:**
- `app.py` — added upload component, `dcc.Store` data pipeline, verdict table, dynamic filter callbacks
- `pyproject.toml` — added `openpyxl` dependency
- `docs/features.md` — updated iteration 0 status and tech stack

**Files added:**
- `data/full_portfolio.xlsx` — 42-SKU test portfolio
- `scripts/generate_portfolio.py` — portfolio generation script
- `tests/test_iteration1.py` — 14 tests for iteration 1

## Iteration 0 — Migrate from Streamlit to Dash

**Status:** COMPLETED

**Planned scope:**
- Rewrite `app.py` from Streamlit to Dash
- Swap `streamlit` dependency for `dash` + `dash-bootstrap-components` in `pyproject.toml`
- Update `CLAUDE.md` references
- Preserve all existing functionality: sidebar filters, KPI cards, recommendation banner, scenario table, profit chart, competitor table

**Delivered (planned):**
- [x] `app.py` — full rewrite to Dash with Bootstrap (Flatly theme)
- [x] Cascading sidebar filters via `@callback` chains (manufacturer → brand → segment → SKU)
- [x] KPI cards using `dbc.Card` components
- [x] Color-coded recommendation banner (green/red/gray)
- [x] `dash_table.DataTable` with conditional row highlighting for recommended scenario
- [x] Native `dcc.Graph` for Plotly profit impact bar chart
- [x] Competitor/sibling SKU table
- [x] `pyproject.toml` — swapped `streamlit>=1.50.0` for `dash>=2.17.0` + `dash-bootstrap-components>=1.6.0`
- [x] `CLAUDE.md` — updated stack, run command, and file descriptions
- [x] Run command changed: `uv run python app.py` (serves on `http://localhost:8050`)

**Delivered (beyond plan):**
- [x] **All Manufacturers Overview page** — new view showing all 20 SKUs across all manufacturers on one page, with per-manufacturer breakdown cards and color-coded action cells
- [x] **View switcher** in sidebar — dropdown to toggle between "All Manufacturers" (overview) and "SKU Detail" views; sidebar filters hide/show accordingly
- [x] **Summary KPI cards** on overview — total SKUs, action counts (increase/decrease/hold), total profit impact
- [x] **Profit impact by manufacturer** — horizontal bar chart
- [x] **Action distribution by manufacturer** — stacked bar chart
- [x] **Market share before vs after** — side-by-side donut charts for volume and revenue share, both summing to 100%, showing redistribution after recommended price actions
- [x] **Market share shift chart** — grouped bar showing percentage-point change in volume and revenue share per manufacturer
- [x] **Profit impact by SKU** — horizontal bar ranking all 20 SKUs, color-coded by action
- [x] Precomputed overview data (`build_overview_data()`) with revenue, projected volume, and projected revenue fields

**Files changed:**
- `app.py` — rewritten (Streamlit → Dash)
- `pyproject.toml` — dependency swap
- `CLAUDE.md` — updated references

**Files unchanged:**
- `src/pricing_engine.py` — no changes
- `data/sample_skus.csv` — no changes
