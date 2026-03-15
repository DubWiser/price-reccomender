# Price Elasticity, Cannibalisation & Market Share Analytics Dashboard

## Overview

This prompt specification defines an interactive analytics dashboard for analysing price elasticity, cannibalisation, and market share dynamics across a competitive market. The dashboard enables users to understand real market dynamics and simulate pricing decisions to achieve higher share or margin at a manufacturer level.

---

## Input Data Schema

The following fields are required for every SKU in the market. All SKUs combined must sum to 100% market share.

| Field | Type | Description |
|---|---|---|
| `manufacturer` | string | Manufacturer/company name |
| `brand` | string | Brand name within the manufacturer portfolio |
| `price_segment` | enum | `Premium`, `Mid`, or `Value` |
| `sku_id` | string | Unique SKU identifier |
| `price` | float | Current retail price |
| `volume` | integer | Units sold in the period |
| `own_elasticity` | float | Own-price elasticity coefficient (typically negative) |
| `cross_elasticity` | float (matrix) | Cross-price elasticity vs every other SKU in the market |
| `cannibalisation_pct` | float | % of SKU volume being cannibalised by own-manufacturer SKUs |

> **Constraint:** Market share is calculated as `volume / total_market_volume`. All SKUs must represent 100% of the defined market. No external volume gain is modelled — price simulation only reallocates existing volume across SKUs.

---

## Dashboard Structure

The dashboard is organised into five pages/tabs:

### 1. Market Overview

**Purpose:** Establish the baseline competitive landscape.

**Visuals & components:**
- **KPI cards** — total SKUs, market-leading manufacturer (combined share), total market volume, average price point
- **Market share donut chart** — one segment per SKU, colour-coded
- **Bubble chart** — X axis: price, Y axis: volume, bubble size: market share percentage
- **SKU summary table** — manufacturer, brand, segment badge, price, volume, market share (with inline bar), own elasticity

---

### 2. Elasticity Analysis

**Purpose:** Identify which SKUs are most sensitive to price changes and which compete directly with one another.

**Visuals & components:**
- **Own-price elasticity horizontal bar chart** — colour-coded by sensitivity zone:
  - Red: highly elastic (e < −2.0)
  - Amber: elastic (−2.0 ≤ e < −1.5)
  - Green: inelastic (e ≥ −1.5)
- **Cross-price elasticity heatmap** — rows = price-raising SKU, columns = SKU receiving volume. Cell intensity indicates substitution strength. Same-manufacturer pairs highlighted differently.
- **Interpretation table** — for each SKU: elasticity value, sensitivity label, plain-language pricing implication

**Elasticity legend:**

| Coefficient | Classification | Pricing implication |
|---|---|---|
| < −2.0 | Highly elastic | Price increases will rapidly erode volume |
| −2.0 to −1.5 | Elastic | Small increases possible with monitoring |
| −1.5 to −1.0 | Moderately elastic | Some pricing headroom available |
| > −1.0 | Inelastic | Pricing power — selective increases viable |

---

### 3. Cannibalisation Analysis

**Purpose:** Quantify internal portfolio leakage — volume being lost to own-brand SKUs rather than competed away externally.

**Visuals & components:**
- **Cannibalisation % bar chart** — per SKU, colour-coded by severity (>15% = high risk, 10–15% = moderate, <10% = low)
- **Volume at risk stacked bar chart** — for each SKU, shows cannibalised volume vs safe volume
- **Cannibalisation matrix** — full cross-SKU table showing cross-elasticity values, with same-manufacturer pairs highlighted to reveal internal leakage. Final column shows total own-manufacturer risk score per SKU.

---

### 4. Price Simulator

**Purpose:** Allow users to model the market share and revenue impact of changing one or more SKU prices. Volume is conserved — gains for one SKU come at the expense of others.

**Mechanics:**
- For each SKU with a price change, compute volume change using:
  ```
  ΔMS_i = own_elasticity_i × (ΔPrice_i / BasePrice_i) × BaseMS_i
  ```
- Redistribute total market share so all SKUs still sum to 100%
- No new volume enters the market — it is purely redistributive

**Controls:**
- Price sliders per SKU — range: ±30–40% of base price
- "Run simulation" button
- "Reset" button to restore base prices

**Outputs:**
- **Before/after market share bar chart** — base (faded) vs simulated (solid) per SKU
- **Manufacturer-level KPI cards** — market leader (base vs simulated), revenue index change
- **SKU-level impact table** — base price, new price, price change %, base MS%, simulated MS%, MS delta (pp), volume delta (units)

**Constraint to enforce:** Total market volume remains fixed. Volume gained by one SKU is lost by others. There is no modelling of category expansion.

---

### 5. Executive Summary

**Purpose:** A slide-format one-pager for senior stakeholders capturing key market dynamics and recommended actions.

**Slide structure (4 panels):**

#### Panel 1 — Market structure at a glance
- Manufacturer share breakdown with visual tiles
- KPI summary: total SKUs, number of high-elasticity SKUs, average cannibalisation rate

#### Panel 2 — Elasticity risk zones
- Numbered insights identifying the most elastic SKUs and their competitive exposure
- Flag SKUs where price increases carry material volume risk

#### Panel 3 — Cannibalisation: internal threats
- Numbered insights per manufacturer highlighting the highest internal leakage pairs
- Note value-segment performance (typically low cannibalisation = well-differentiated)

#### Panel 4 — Pricing strategy recommendations
- 3–5 actionable recommendations derived from the analysis
- Format: `[Direction icon] Manufacturer — SKU action` + supporting rationale
- Each recommendation should specify: which SKU, which direction (raise/hold/cut), estimated impact, and why it is safe or risky

---

## Simulation Rules & Constraints

1. **Zero-sum volume** — total market volume is fixed. Price changes only redistribute share across SKUs.
2. **Elasticity-driven reallocation** — own-price elasticity drives the originating SKU's volume change; cross-elasticity determines where that volume flows.
3. **No manufacturer scope limitation** — a SKU can gain volume from any other SKU in the market, not just direct competitors.
4. **Manufacturer-level reporting** — while simulation operates at SKU level, results must be aggregated to manufacturer level for share and revenue impact.
5. **Revenue index** — computed as `Σ (simulated_volume_i × new_price_i)` vs `Σ (base_volume_i × base_price_i)`. This reflects both share and price effects.

---

## Colour & Segment Conventions

| Segment | Colour |
|---|---|
| Premium | Blue |
| Mid | Green |
| Value | Amber |

| Elasticity zone | Colour |
|---|---|
| Highly elastic (e < −2) | Red |
| Elastic (−2 to −1.5) | Amber |
| Inelastic (e > −1.5) | Green |

| Cannibalisation severity | Threshold |
|---|---|
| High | > 15% |
| Moderate | 10–15% |
| Low | < 10% |

---

## Key Analytical Questions This Dashboard Answers

1. Which SKUs have the most pricing power, and where is volume at risk?
2. Which manufacturer has the strongest combined market position?
3. Where is own-portfolio cannibalisation creating the biggest drag on manufacturer share?
4. If we raise SKU X's price by 5%, how much volume moves — and where does it go?
5. What is the optimal pricing action to grow manufacturer share without triggering category loss?
6. Which SKU pairs are most substitutable, and does that create competitive or internal risk?

---

## Notes for Implementation

- All market share values must sum to exactly 100% at all times, including post-simulation
- The simulator should update in real time (or on button press) as sliders are adjusted
- Cross-elasticity values should be stored as an N×N matrix where `cross[i][j]` = elasticity of SKU j with respect to SKU i's price
- The executive summary should auto-generate from the data — it is not manually authored
- Cannibalisation % is directional: it represents the share of SKU i's volume that is being drawn away by other SKUs from the same manufacturer