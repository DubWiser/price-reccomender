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

### Iteration 0 — Magic moment (20 min, terminal only, no UI)
A Python script that takes a hardcoded list of 5 SKUs with elasticity + cannibalization + current price + volume, runs the revenue optimization logic, and prints raise/hold/cut verdicts to the terminal. No UI. Proves the math works.

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
- Use basic Tailwind for styling — no custom CSS
- console.log for error handling is fine
- alert() instead of toast notifications is fine
- Page refresh instead of reactive state updates is fine

## How to use this file
- Before building any feature, check: is it listed above?
- Before adding scope, check: is it in the cuts list?
- When the user says "checkpoint", commit with a descriptive message
- When the user asks for something not in this spec, push back:
  "That's not in the feature spec. Want to add it to a later iteration?"