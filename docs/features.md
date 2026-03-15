# Features

## Domain
Beer SKU price recommendation tool.

## Core Objective
Suggest optimal price actions for beer SKUs based on elasticity and cannibalization rate.

## Inputs (SKU level)
- Manufacturer name
- SKU name
- Brand name
- Price segment: Core / Value / Premium
- 2 competitor SKUs (within same manufacturer)
- SKU-level own-price elasticity
- SKU-level cannibalization rate (cross-SKU within manufacturer)
- Profit % per mL
- Actual volume sold in 2025 (mL or units)

## Output
- Recommended price action: Increase / Hold / Decrease
- Expected volume impact (own + cannibalized)
- Expected profit impact (£ or %)
- Scenario comparison (e.g., +5%, +10%, -5%)

## Tech Stack
- Python (pandas, numpy) for data and pricing logic
- Streamlit for UI
- Rule/ML-based recommendation engine

## Recommendation Logic
- Use own-price elasticity to project volume change for each price scenario
- Apply cannibalization rate to estimate volume shift to/from competitor SKUs within the same manufacturer
- Calculate net profit impact = (new price × new volume × profit% per mL) vs baseline
- Recommend the scenario with highest profit impact that doesn't excessively cannibalize sibling SKUs
