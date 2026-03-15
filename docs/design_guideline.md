# AB InBev · UI Design System

> Design language, data visualization guidelines, chart rules, and component specs — extracted from AB InBev's visual identity. Use this as the system prompt or reference document for any UI built on the AB InBev brand.

---

## 1. Brand Identity

AB InBev is the world's largest brewer. The visual identity is **premium, restrained, and global**. Think boardroom, not playful. Gravitas over whimsy. Every design decision should feel confident, data-driven, and purposeful.

---

## 2. Color System

### Primary Palette

| Token | Hex | Usage |
|---|---|---|
| Midnight Black | `#1A1A1A` | Primary background (dark mode) |
| Charcoal | `#2C2C2C` | Secondary surface / card background |
| Cream White | `#F5F0E8` | Light surface / page background (light mode) |
| **AB Gold** | `#C9A84C` | **The single brand accent — use exclusively** |
| Gold Light | `#E8C97A` | Hover states, highlight variant |
| Warm Gray | `#8A8070` | Muted text, borders, tertiary elements |
| ABI Navy | `#1A3A5C` | Informational states |
| Alert Red | `#C0392B` | Negative values, errors, alerts only |

> **Rule:** AB Gold (`#C9A84C`) is the **only accent color**. Never introduce blue CTAs, green badges, or purple tags. All accent moments use Gold or its light variant.

### Data Visualization Series Colors

Use in this order for multi-series charts:

| Series | Hex | Use For |
|---|---|---|
| Series 1 | `#C9A84C` | Primary metric |
| Series 2 | `#1A3A5C` | Secondary metric |
| Series 3 | `#8A8070` | Tertiary / comparison data |
| Series 4 | `#4A7C59` | Growth / positive trend |
| Series 5 | `#E8C97A` | Highlight variant |
| Alert only | `#C0392B` | Negative values, breaches, errors |

> **Rule:** Lead with AB Gold for the primary series. Red is reserved and meaningful — never use it decoratively.

---

## 3. Typography

### Type Scale

| Role | Size | Weight | Notes |
|---|---|---|---|
| Display / Hero KPI | 28–40px | 300 (Light) | Letter-spacing +0.02em |
| Section Heading | 20px | 500 | — |
| Card Title | 15px | 500 | — |
| Body Copy | 13–14px | 400 | Line height 1.7 |
| Label / Axis | 11px | 500 | Uppercase, letter-spacing +0.10em |
| Data Figures | 13px | 400 | Monospace font, Gold color `#C9A84C` |

### Typography Rules

- Never use pure black (`#000`). Darkest text is `#1A1A1A` on light, `#F5F0E8` on dark.
- Body text on dark backgrounds: use `#C2BDB5` (muted cream) — not white.
- Uppercase + letter-spacing for all section labels, chart axis titles, tags, and badges.
- Gold color (`#C9A84C`) only on primary KPI numbers and key data callouts.
- Use thin weight (300) for hero numbers and large KPI figures — feels premium, not heavy.
- KPI units (e.g. "M", "%", "$") in Warm Gray beside the Gold figure.

---

## 4. Data Visualization Guidelines

### 4.1 Chart Type Selection

| Data Story | Chart Type | Notes |
|---|---|---|
| Volume comparison, rankings | Bar / Column | Vertical for time series, horizontal for ranked lists |
| Trends over time | Line | 1.5px strokes, area fill at 10–15% opacity |
| Portfolio / market share | Donut | Max 5 segments; merge small slices into "Other" (Warm Gray) |
| P&L bridges, variance | Waterfall | Gold = positive, Red = negative, Navy = totals |
| Brand × market grids | Heatmap | Single-hue cream-to-gold-to-dark-brown gradient only |
| Positioning, growth vs share | Scatter / Bubble | Bubble size = volume; label top 5 points only |

### 4.2 Chart Construction Rules

**Gridlines**
- Horizontal only. No vertical gridlines.
- 0.5px dashed. Color: `#3A3530` (dark mode) / `#D3CFC7` (light mode).

**Axes**
- Y-axis: hidden — gridlines substitute.
- X-axis: 0.5px solid line.
- Axis labels: 11px uppercase, Warm Gray (`#8A8070`).
- Set `autoSkip: false` with `maxRotation: 45` when ≤12 categories must all be visible.

**Data Labels**
- Show on bar tips only when N ≤ 8 data points.
- 11px monospace, aligned flush to bar tip.

**Legends**
- Always custom HTML, never default chart legends.
- Horizontal layout, positioned above the chart.
- Small 10×10 squares with inline value or percentage.
- Format: `[■ Series Name 42%]`

**Backgrounds**
- Charts sit on `#F5F0E8` in light mode, `#2C2C2C` in dark mode.
- Never pure white behind a chart canvas.

**Tooltips**
- Background: `#1A1A1A` panel.
- Value color: AB Gold (`#C9A84C`).
- Border radius: 6px. Font: 13px sans-serif.

**Color Assignment**
- Positive bars / primary series: AB Gold.
- Negative bars / deltas: Alert Red.
- Running totals: ABI Navy.
- Heatmaps: single-hue gradient only (Cream → Gold → Dark Brown). No rainbow scales.

**Number Formatting**
- Negative values: `-$5M` not `$-5M` — sign before currency symbol.
- Always round displayed numbers. Never show raw float artifacts like `0.30000000000004`.
- Use `toLocaleString()` for currency, `.toFixed(1)` for percentages.

**Layout**
- No outer border on chart canvas.
- Cards housing charts: 0.5px border, 8px radius.
- Minimum 24px padding inside all chart cards.
- Pad axis range 10% beyond data range for bubble/scatter to prevent edge clipping.

### 4.3 Waterfall Chart Specifics

- Positive contribution bars: AB Gold (`#C9A84C`)
- Negative contribution bars: Alert Red (`#C0392B`)
- Running total / subtotal bars: ABI Navy (`#1A3A5C`)
- Connector lines between bars: 0.5px dashed Warm Gray
- Use for: P&L bridges, volume variance, EBITDA decomposition, cost walkdowns

### 4.4 Heatmap / Matrix Specifics

- Color scale: single hue only — Cream (`#F5F0E8`) → Gold (`#C9A84C`) → Dark Brown (`#3A2A10`)
- Never use rainbow (ROYGBIV) scales — they distort magnitude perception
- Cell text: use darkest shade from the same ramp for readability
- Label format: 11px uppercase monospace

---

## 5. Layout & Component Specs

### 5.1 Cards

**Dark variant** (default)
```
background:    #2C2C2C
border:        0.5px solid #3A3530
border-radius: 8px
padding:       20px
```

**Light variant**
```
background:    #FFFFFF
border:        0.5px solid #D3CFC7
border-radius: 8px
padding:       20px
```

**Accent variant** (featured card)
```
all of the above +
border-left:   3px solid #C9A84C
```

### 5.2 Buttons

| Variant | Background | Border | Text Color |
|---|---|---|---|
| Primary | `#C9A84C` | none | `#1A1A1A` |
| Secondary | transparent | `0.5px solid #C9A84C` | `#C9A84C` |
| Danger | transparent | `0.5px solid #C0392B` | `#C0392B` |

All buttons: border-radius 4px. No gradients.

### 5.3 Badges / Tags

| Variant | Background | Text Color |
|---|---|---|
| Featured (Gold) | `rgba(201,168,76,0.15)` | `#C9A84C` |
| Informational (Navy) | `rgba(26,58,92,0.15)` | `#1A3A5C` |
| Alert (Red) | `rgba(192,57,43,0.15)` | `#C0392B` |

All badges: `11px`, uppercase, letter-spacing `0.08em`, padding `2px 8px`, border-radius `4px`.

### 5.4 Tables

- No outer border.
- Row dividers: 0.5px solid `#3A3530` (dark) / `#D3CFC7` (light).
- Header row: uppercase 11px labels + 1px Gold bottom border.
- Alternating rows: transparent / `rgba(245,240,232,0.04)`.

### 5.5 Metric / KPI Cards

```
background:    var(--color-background-secondary)
border:        none
border-radius: 8px
padding:       16px

Label:  13px, uppercase, Warm Gray, letter-spacing +0.08em
Value:  28–36px, weight 300, AB Gold (#C9A84C), monospace
Unit:   13px, Warm Gray, inline after value
```

Use in grids of 2–4 with 12px gap.

### 5.6 Dividers

- Horizontal only. No vertical dividers — use whitespace instead.
- 0.5px solid `#3A3530` (dark) / `#D3CFC7` (light).

---

## 6. Spacing System

Use only values from this scale. Never use odd numbers or off-scale values.

```
4px  · 8px  · 12px  · 16px  · 24px  · 32px  · 48px
```

---

## 7. Motion & Transitions

- Hover interactions: `150ms ease-out`
- Panel / drawer transitions: `250ms ease-out`
- No bounce, no spring physics. Subtle and purposeful only.
- Animate only `transform` and `opacity` for performance.
- Wrap animations in `@media (prefers-reduced-motion: no-preference)`.

---

## 8. Do's and Don'ts

### Do
- Lead every layout with whitespace — sparse is better than dense
- Use Gold exclusively for primary data callouts and accent moments
- Uppercase all section labels, axis titles, and badge text
- Use monospace font for all numeric data values
- Keep negative values in Alert Red; it must remain meaningful and rare
- Dark-first: design for `#1A1A1A` backgrounds by default

### Don't
- Don't use pure white (`#FFF`) or pure black (`#000`) anywhere
- Don't introduce a second accent color (no blue CTAs, green buttons, purple tags)
- Don't use rainbow color scales in heatmaps
- Don't add gradients except single-hue heatmap scales and hero shimmer
- Don't show all data labels on busy charts — label at N ≤ 8 only
- Don't put legends inside the chart canvas — always custom HTML above

---

## 9. Full System Prompt (Ready to Paste)

Copy the block below into any AI assistant, component generator, or design tool to enforce this system.

```
You are a UI assistant for AB InBev's internal analytics platform. Follow this design system exactly.

BRAND: Premium, restrained, global. Boardroom gravitas over playfulness. Data-driven and confident.

COLOR SYSTEM
  Primary background:   #1A1A1A  (Midnight Black)
  Secondary surface:    #2C2C2C  (Charcoal)
  Light surface:        #F5F0E8  (Cream White)
  Brand accent:         #C9A84C  (AB Gold) — the ONLY accent color
  Gold hover:           #E8C97A
  Muted text/borders:   #8A8070  (Warm Gray)
  Informational:        #1A3A5C  (ABI Navy)
  Negative/Alert:       #C0392B  (Alert Red)

  Data series order:
    1. #C9A84C  AB Gold       → primary metric
    2. #1A3A5C  ABI Navy      → secondary metric
    3. #8A8070  Warm Gray     → tertiary / comparison
    4. #4A7C59  Forest Green  → growth / positive
    5. #E8C97A  Gold Light    → highlight variant
    Alert only: #C0392B for negative values, breaches, errors

TYPOGRAPHY
  Display / KPI: 28–40px, weight 300, letter-spacing +0.02em
  Section heading: 20px, weight 500
  Card title: 15px, weight 500
  Body copy: 13–14px, weight 400, line-height 1.7
  Labels/axis: 11px, weight 500, uppercase, letter-spacing +0.1em
  Data figures: monospace font, color #C9A84C

  Rules:
  - Darkest text: #1A1A1A on light, #F5F0E8 on dark
  - Body text on dark: #C2BDB5 (muted cream)
  - Uppercase + letter-spacing for all labels, axis titles, tags
  - Gold only on primary KPI numbers and key data callouts

DATA VISUALIZATION
  Chart type selection:
    Bar/Column   → volume comparison, rankings, period-over-period
    Line         → trends over time, rolling averages
    Donut        → portfolio share, market split (max 5 segments)
    Waterfall    → P&L bridges, variance decomposition
    Heatmap      → brand×market grids, SKU contribution maps
    Scatter/Bubble → positioning maps, growth vs share quadrants

  Construction rules:
  - Gridlines: 0.5px dashed, horizontal only. #3A3530 dark / #D3CFC7 light
  - Y-axis hidden (gridlines substitute). X-axis 0.5px solid
  - Axis labels: 11px uppercase, Warm Gray
  - Data labels on bars only when ≤8 data points. 11px monospace, bar-tip aligned
  - Legends: custom HTML above chart. 10×10 squares with inline value/%
  - Chart background: #F5F0E8 light / #2C2C2C dark
  - Tooltips: #1A1A1A panel, Gold accent value, 6px radius, 13px sans
  - Negative bars: #C0392B. Positive: #C9A84C. Totals: #1A3A5C
  - Heatmaps: single-hue cream→gold→dark-brown gradient ONLY. No rainbow scales
  - Pad axis range 10% beyond data range for bubble/scatter charts

COMPONENTS
  Cards (dark):   bg #2C2C2C, border 0.5px #3A3530, radius 8px, padding 20px
  Cards (light):  bg #FFFFFF,  border 0.5px #D3CFC7, radius 8px, padding 20px
  Cards (accent): add border-left 3px solid #C9A84C

  Buttons:
    Primary:   bg #C9A84C, color #1A1A1A, no border, radius 4px
    Secondary: transparent, border 0.5px #C9A84C, color #C9A84C, radius 4px
    Danger:    transparent, border 0.5px #C0392B, color #C0392B, radius 4px

  Badges: 11px uppercase, letter-spacing 0.08em, padding 2px 8px, radius 4px
    Gold:  bg rgba(201,168,76,0.15), color #C9A84C
    Navy:  bg rgba(26,58,92,0.15),  color #1A3A5C
    Red:   bg rgba(192,57,43,0.15), color #C0392B

  Tables: no outer border. Row dividers 0.5px. Header uppercase 11px + Gold bottom border.
  Dividers: horizontal only. 0.5px solid. #3A3530 dark / #D3CFC7 light.

SPACING: 4 / 8 / 12 / 16 / 24 / 32 / 48px only.
MOTION:  150ms ease-out (hover). 250ms ease-out (panels). No bounce.
GRADIENTS: none except single-hue heatmap scales.

TONE: Data-driven, minimal prose. Numbers lead. Generous whitespace. One accent color.
```