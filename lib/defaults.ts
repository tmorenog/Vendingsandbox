import type { SimConfig } from "./types";

export const DEFAULT_CONFIG: SimConfig = {
  horizon_days: 180,
  initial_cash: 1500.0,
  max_po_lines_per_day: 5,
  min_order_qty: 5,
  max_visits_per_7d: 3,
  max_units_per_visit: 60,
  visit_fixed_cost: 25.0,
  holding_cost_per_unit_day: 0.01,
  stockout_penalty_per_unit: 0.5,
};
