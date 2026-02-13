/** Simulation configuration sent to the API. */
export interface SimConfig {
  horizon_days: number;
  initial_cash: number;
  max_po_lines_per_day: number;
  min_order_qty: number;
  max_visits_per_7d: number;
  max_units_per_visit: number;
  visit_fixed_cost: number;
  holding_cost_per_unit_day: number;
  stockout_penalty_per_unit: number;
}

/** One day of simulation output. */
export interface DailyEntry {
  day: number;
  profit: number;
  revenue: number;
  procurement_cost: number;
  visit_cost: number;
  holding_cost: number;
  stockout_penalty: number;
  cash: number;
  units_sold: number;
  units_lost: number;
  fill_rate: number;
  visit: number;
  machine_on_hand: Record<string, number>;
  stockroom_on_hand: Record<string, number>;
}

/** Episode-level KPIs. */
export interface Kpis {
  total_profit: number;
  total_revenue: number;
  total_procurement_cost: number;
  total_visit_cost: number;
  total_holding_cost: number;
  total_stockout_penalty: number;
  fill_rate: number;
  visits_total: number;
  stockout_days_by_sku: Record<string, number>;
  cash_min: number;
  total_units_sold: number;
  total_units_lost: number;
  days: number;
  score: number;
  warnings_count: number;
}

/** Metadata for a simulation run. */
export interface Meta {
  scenario: string;
  seed: number;
  horizon: number;
  n_skus: number;
  initial_cash: number;
}

/** Single simulation result. */
export interface SimulationResult {
  daily: DailyEntry[];
  kpis: Kpis;
  meta: Meta;
}

/** Per-seed summary in evaluate mode. */
export interface SeedRow {
  seed: number;
  profit: number;
  fill_rate: number;
  visits: number;
  score: number;
  revenue: number;
  procurement: number;
  holding: number;
  stockout_pen: number;
}

/** Full evaluate result from the API. */
export interface EvaluateResult {
  per_seed: SeedRow[];
  averages: {
    profit: number;
    fill_rate: number;
    score: number;
    visits: number;
  };
  representative: SimulationResult;
}

export type AgentMode = "baseline" | "upload" | "paste";
export type RunMode = "single" | "evaluate";

export const SCENARIOS = [
  "normal",
  "demand_surge",
  "vendor_disruption",
  "cash_shock",
] as const;

export type Scenario = (typeof SCENARIOS)[number];
