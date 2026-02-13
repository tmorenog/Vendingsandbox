# Vending Machine Digital Ops Sandbox

A simulation environment for business school students to practice supply-chain
decision-making.  You manage **one vending machine** and **one local stockroom**
by implementing two agent policies:

1. **ProcurementAgent** -- decides what to order from vendors into the stockroom
2. **ReplenishmentAgent** -- decides when to visit the machine and what to restock

Everything else (customers, vendors, evaluation) is provided.

---

## Quickstart

```bash
# No dependencies needed -- standard library only, Python 3.11+

# Run a single episode with the baseline agents
cd src
python -m run_episode --seed 42 --agent baseline

# Run a single episode with your student agents
python -m run_episode --seed 42 --agent student

# Evaluate across 50 seeds and 4 scenarios (baseline vs student)
python -m evaluate --seeds 50 --horizon 180
```

---

## Architecture

```
Day loop (180 days):
  1. ProcurementAgent.act(obs) -> place purchase orders with vendors
  2. Vendors confirm POs (partial fills, lead times, costs)
  3. ReplenishmentAgent.act(obs) -> optionally visit machine & restock
  4. Customers arrive, attempt purchases (substitution / abandonment)
  5. POs that have reached their ETA arrive at stockroom
  6. Daily costs computed (holding, stockout penalty, visit cost)
```

Students edit **only** two files:
- `src/agents/student_procurement.py`
- `src/agents/student_replenishment.py`

---

## API Contract

### ProcurementAgent.act(obs) -> action

**Observation (`obs`):**

| Key | Type | Description |
|-----|------|-------------|
| `day` | `int` | Current simulation day (0-indexed) |
| `cash` | `float` | Cash on hand |
| `stockroom_on_hand` | `dict[str,int]` | Stockroom inventory per SKU |
| `machine_on_hand` | `dict[str,int]` | Machine inventory per SKU |
| `sales_last_7d` | `dict[str,list[int]]` | Last 7 days of machine sales per SKU |
| `open_pos` | `list[dict]` | Open purchase orders (see below) |
| `vendor_scorecard` | `dict[str,dict]` | 30-day rolling vendor stats |
| `constraints` | `dict` | `max_po_lines_per_day`, `min_order_qty`, `cash_must_cover_orders` |

Each open PO dict:
```python
{"po_id": str, "vendor": str, "sku": str, "ordered_qty": int,
 "confirmed_qty": int|None, "unit_cost": float|None,
 "eta_day": int, "status": "open"|"arrived"|"cancelled"}
```

Vendor scorecard per vendor:
```python
{"avg_fill_rate": float, "avg_lead_time": float, "avg_unit_cost": float}
```

**Action (return value):**
```python
{
    "pos": [
        {"vendor": "A", "sku": "SKU_01", "qty": 20, "mode": "standard"},
        {"vendor": "B", "sku": "SKU_07", "qty": 10, "mode": "expedite"},
    ],
    "note": "optional logging string"
}
```

### ReplenishmentAgent.act(obs) -> action

**Observation (`obs`):**

| Key | Type | Description |
|-----|------|-------------|
| `day` | `int` | Current simulation day |
| `stockroom_on_hand` | `dict[str,int]` | Stockroom inventory per SKU |
| `machine_on_hand` | `dict[str,int]` | Machine inventory per SKU |
| `machine_capacity` | `dict[str,int]` | Max units per SKU in machine (15 each) |
| `sales_last_7d` | `dict[str,list[int]]` | Last 7 days of machine sales |
| `days_since_visit` | `int` | Days since last restocking visit |
| `constraints` | `dict` | `max_visits_per_7d`, `max_units_per_visit` |

**Action (return value):**
```python
{
    "visit": True,
    "restock": {"SKU_01": 10, "SKU_07": 15, "SKU_03": 8},
    "note": "optional"
}
```

---

## Constraints Enforcement

The environment enforces all constraints deterministically:

| Constraint | Enforcement |
|------------|-------------|
| `max_po_lines_per_day` (5) | Extra PO lines are dropped |
| `min_order_qty` (5) | Qty below minimum is clipped up; zero-qty lines are dropped |
| `cash_must_cover_orders` | Qty reduced to what cash affords; cancelled if below min |
| `max_visits_per_7d` (3) | Visit denied if rolling 7-day count is at limit |
| `max_units_per_visit` (60) | Restock quantities truncated |
| Stockroom/machine capacity | Quantities clipped to available space |

Violations are recorded as warnings in the daily log (accessible via `env.daily_logs`).

---

## Vendors

Three vendors with distinct profiles (hidden regime not visible to students):

| Vendor | Cost | Reliability | Lead Time | Special |
|--------|------|-------------|-----------|---------|
| A | Low | Less reliable | Medium | Disrupts often |
| B | High | Very reliable | Short | Rarely disrupts |
| C | Medium | Medium | Medium | Good expedite option |

Vendor behaviour includes:
- **Hidden 2-state Markov regime** (NORMAL / DISRUPTED) -- not exposed
- **Partial fills**: confirmed qty drawn from Binomial(ordered_qty, fill_prob)
- **Variable lead times**: sampled from discrete distribution per regime
- **Cost noise**: small random variation around base cost

Students observe only the **vendor scorecard** (30-day rolling averages).

---

## Customers

- Arrivals: Poisson(base_rate * dow_multiplier * demand_regime * churn_factor)
- Each customer has a preferred SKU (weighted random)
- If preferred SKU is out of stock:
  - 40% chance of trying up to 3 substitutes
  - Otherwise the customer leaves (lost sale)
- **Memory/churn**: if 7-day fill rate < 70%, arrival rate decays by 3%/day;
  if fill rate is high, it recovers slowly (bounded to [0.6, 1.1])

---

## Scoring

```
score = 0.4 * normalized_profit + 0.4 * fill_rate - 0.2 * visit_rate_penalty
```

Where:
- `normalized_profit = clamp(total_profit / (horizon * 10), 0, 1)`
- `fill_rate = units_sold / (units_sold + units_lost)`
- `visit_rate_penalty = clamp(visits / horizon, 0, 1)`

**Evaluation** runs 4 scenarios (normal + 3 stress tests) with weighted average:
- Normal: 40%
- Demand surge: 20%
- Vendor disruption: 20%
- Cash shock: 20%

---

## Default Parameters

| Parameter | Value |
|-----------|-------|
| SKUs | 12 |
| Machine capacity per SKU | 15 |
| Stockroom capacity per SKU | 200 |
| Initial machine stock | 50% full (7 units/SKU) |
| Initial stockroom stock | 30 units/SKU |
| Initial cash | $1,500 |
| Horizon | 180 days |
| Visit fixed cost | $25 |
| Visit handling cost | $0.05/unit |
| Holding cost | $0.01/unit/day |
| Stockout penalty | $0.50/unit lost |

---

## Tips for Students Using Codex

Paste the API contract above and ask for an `act()` policy. For example:

> "Given this observation schema for a vending machine procurement agent,
> write an act() method that uses a newsvendor-style ordering policy with
> safety stock based on 7-day sales variance. Choose vendors based on
> their scorecard fill rate and cost trade-off."

Key ideas to explore:
- **Demand forecasting**: use `sales_last_7d` to estimate daily demand
- **Safety stock**: buffer against demand variance and lead-time uncertainty
- **Vendor selection**: balance cost vs reliability using the scorecard
- **Visit scheduling**: minimise visits while keeping fill rate high
- **Cash management**: don't over-order and run out of cash
- **Coordination**: procurement and replenishment should work together

---

## Web App (Vercel / Next.js)

A Next.js frontend with Vercel serverless Python API functions. Deployable to
Vercel or runnable locally.

### Deploy to Vercel

1. Push this repo to GitHub.
2. Import the repo at [vercel.com/new](https://vercel.com/new).
3. Vercel auto-detects Next.js and the Python functions in `api/`.
4. No environment variables needed.

### Run locally

```bash
npm install
npm run dev          # Next.js dev server on http://localhost:3000
```

The Python API endpoints (`/api/simulate`, `/api/evaluate`, `/api/validate_agent`)
require `vercel dev` to serve locally (the Vercel CLI runs both the Next.js dev
server and the Python functions together):

```bash
npm i -g vercel
vercel dev           # serves everything on http://localhost:3000
```

### Local Streamlit alternative

A Streamlit-based UI is also available in `webapp/`:

```bash
pip install streamlit matplotlib
streamlit run webapp/app.py
```

### Providing student agents in the web UI

On the **Run Simulation** page, select one of:

- **Baseline** -- uses the built-in baseline agents.
- **Student Upload** -- upload two `.py` files.
- **Student Paste** -- paste code into text areas.

Each file must define one class:

- `student_procurement.py` -> `class StudentProcurementAgent` with `act(self, obs: dict) -> dict`
- `student_replenishment.py` -> `class StudentReplenishmentAgent` with `act(self, obs: dict) -> dict`

---

## Project Structure

```
src/
  vendsim/
    config.py          # Dataclasses and default parameters
    env.py             # Main environment and step loop
    customers.py       # Customer agents (provided)
    vendors.py         # Vendor agents (provided)
    metrics.py         # KPI calculation helpers
    scenarios.py       # Normal + stress scenarios
    web_runner.py      # High-level simulation callable for web UIs
  agents/
    baseline_procurement.py    # Baseline procurement agent
    baseline_replenishment.py  # Baseline replenishment agent
    student_procurement.py     # YOUR CODE HERE
    student_replenishment.py   # YOUR CODE HERE
  run_episode.py       # Run single seed, print KPIs
  evaluate.py          # Run many seeds, print table + score
app/                   # Next.js frontend (App Router)
  layout.tsx           # Root layout with navigation
  page.tsx             # Home page
  globals.css          # Tailwind global styles
  configure/page.tsx   # Configuration page
  run/page.tsx         # Run simulation + charts page
api/                   # Vercel serverless Python functions
  _utils.py            # Shared helpers (not an endpoint)
  simulate.py          # POST /api/simulate
  evaluate.py          # POST /api/evaluate
  validate_agent.py    # POST /api/validate_agent
lib/                   # Shared TypeScript modules
  types.ts             # Type definitions
  defaults.ts          # Default config values
webapp/                # Streamlit alternative (local only)
  app.py               # Streamlit entrypoint
  utils_web.py         # Shared helpers
  pages/               # Streamlit pages
tests/
  test_smoke.py        # Smoke tests
```
