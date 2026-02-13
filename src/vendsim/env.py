"""VendingEnv -- the main simulation environment and step loop."""
from __future__ import annotations

import random as _random_mod
from collections import deque
from typing import Any, Dict, List, Optional, Protocol, Tuple

from vendsim.config import EnvConfig
from vendsim.customers import CustomerManager
from vendsim.metrics import compute_kpis, compute_score
from vendsim.scenarios import NormalScenario, Scenario
from vendsim.vendors import POLine, VendorManager


# ---------------------------------------------------------------------------
# Agent protocols (what students implement)
# ---------------------------------------------------------------------------
class ProcurementAgent(Protocol):
    def act(self, obs: dict) -> dict: ...


class ReplenishmentAgent(Protocol):
    def act(self, obs: dict) -> dict: ...


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
class VendingEnv:
    """Discrete-day simulation of one vending machine + stockroom."""

    def __init__(
        self,
        procurement_agent: ProcurementAgent,
        replenishment_agent: ReplenishmentAgent,
        cfg: Optional[EnvConfig] = None,
        seed: int = 42,
        scenario: Optional[Scenario] = None,
    ) -> None:
        self.cfg = cfg or EnvConfig()
        self.seed = seed
        self.rng = _random_mod.Random(seed)
        self.scenario = scenario or NormalScenario()

        self.proc_agent = procurement_agent
        self.rep_agent = replenishment_agent

        # --- State ---
        self.day: int = 0
        self.machine_on_hand: Dict[str, int] = {}
        self.stockroom_on_hand: Dict[str, int] = {}
        self.cash: float = 0.0
        self.open_pos: List[POLine] = []
        self._po_counter: int = 0

        # Sales history ring buffers (7 days)
        self.sales_history: Dict[str, deque] = {}
        self.lost_history: Dict[str, deque] = {}

        # Visit tracking (rolling 7-day window)
        self._visit_days: deque = deque()

        # Internal
        self._demand_regime_multiplier: float = self.cfg.demand_regime_multiplier
        self._warnings: List[str] = []
        self.daily_logs: List[dict] = []

        # Sub-systems
        self.vendor_mgr = VendorManager(
            self.cfg, _random_mod.Random(self.rng.randint(0, 2**63)))
        self.customer_mgr = CustomerManager(
            self.cfg, _random_mod.Random(self.rng.randint(0, 2**63)))

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Re-initialise all state for a new episode."""
        cfg = self.cfg
        self.rng = _random_mod.Random(self.seed)
        self.day = 0
        self._po_counter = 0
        self.open_pos = []
        self._warnings = []
        self.daily_logs = []
        self._visit_days = deque()
        self._demand_regime_multiplier = cfg.demand_regime_multiplier

        self.cash = cfg.initial_cash

        init_machine = max(1, int(cfg.capacity_machine * cfg.initial_machine_frac))
        self.machine_on_hand = {s: init_machine for s in cfg.skus}
        self.stockroom_on_hand = {s: cfg.initial_stockroom_units for s in cfg.skus}

        self.sales_history = {s: deque([0]*7, maxlen=7) for s in cfg.skus}
        self.lost_history = {s: deque([0]*7, maxlen=7) for s in cfg.skus}

        # Re-create subsystems with fresh RNG streams
        self.vendor_mgr = VendorManager(
            cfg, _random_mod.Random(self.rng.randint(0, 2**63)))
        self.customer_mgr = CustomerManager(
            cfg, _random_mod.Random(self.rng.randint(0, 2**63)))

        # Scenario setup
        self.scenario.setup(self, _random_mod.Random(self.rng.randint(0, 2**63)))

    # ------------------------------------------------------------------
    # Observations
    # ------------------------------------------------------------------
    def _obs_procurement(self) -> dict:
        cfg = self.cfg
        return {
            "day": self.day,
            "cash": round(self.cash, 2),
            "stockroom_on_hand": dict(self.stockroom_on_hand),
            "machine_on_hand": dict(self.machine_on_hand),
            "sales_last_7d": {s: list(self.sales_history[s]) for s in cfg.skus},
            "open_pos": [po.to_dict() for po in self.open_pos if po.status == "open"],
            "vendor_scorecard": self.vendor_mgr.scorecards(self.day),
            "constraints": {
                "max_po_lines_per_day": cfg.max_po_lines_per_day,
                "min_order_qty": cfg.min_order_qty,
                "cash_must_cover_orders": cfg.cash_must_cover_orders,
            },
        }

    def _obs_replenishment(self) -> dict:
        cfg = self.cfg
        days_since = self._days_since_visit()
        return {
            "day": self.day,
            "stockroom_on_hand": dict(self.stockroom_on_hand),
            "machine_on_hand": dict(self.machine_on_hand),
            "machine_capacity": {s: cfg.capacity_machine for s in cfg.skus},
            "sales_last_7d": {s: list(self.sales_history[s]) for s in cfg.skus},
            "days_since_visit": days_since,
            "constraints": {
                "max_visits_per_7d": cfg.max_visits_per_7d,
                "max_units_per_visit": cfg.max_units_per_visit,
            },
        }

    def _days_since_visit(self) -> int:
        if not self._visit_days:
            return self.day + 1  # never visited
        return self.day - self._visit_days[-1]

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------
    def step(self) -> dict:
        """Execute one day of simulation. Returns daily info dict."""
        cfg = self.cfg
        day_warnings: List[str] = []

        # --- Scenario hook: on_day ---
        self.scenario.on_day(self, self.day)

        # --- Vendor regime transitions ---
        self.vendor_mgr.step_regimes()
        self.vendor_mgr.begin_day()

        # === 1) Procurement agent ===
        obs_proc = self._obs_procurement()
        action_proc = self.proc_agent.act(obs_proc)
        po_lines_raw = action_proc.get("pos", [])

        # Validate & place POs
        day_procurement_cost = 0.0
        placed_lines = 0
        for line in po_lines_raw:
            if placed_lines >= cfg.max_po_lines_per_day:
                day_warnings.append(
                    f"Day {self.day}: Dropped PO line (max {cfg.max_po_lines_per_day}/day)")
                break

            vendor = line.get("vendor", "")
            sku = line.get("sku", "")
            qty = int(line.get("qty", 0))
            mode = line.get("mode", "standard")

            # Validate vendor
            if vendor not in cfg.vendor_profiles:
                day_warnings.append(f"Day {self.day}: Invalid vendor '{vendor}', skipped")
                continue
            # Validate SKU
            if sku not in cfg.skus:
                day_warnings.append(f"Day {self.day}: Invalid SKU '{sku}', skipped")
                continue
            # Validate mode
            if mode not in ("standard", "expedite"):
                mode = "standard"
                day_warnings.append(f"Day {self.day}: Invalid mode, defaulting to standard")
            # Clip qty to min_order_qty
            if qty < cfg.min_order_qty:
                if qty <= 0:
                    continue
                qty = cfg.min_order_qty
                day_warnings.append(
                    f"Day {self.day}: qty clipped up to min_order_qty={cfg.min_order_qty}")

            # Process through vendor
            po = self.vendor_mgr.process_po_line(vendor, sku, qty, mode, self.day)
            self._po_counter += 1
            po.po_id = f"PO-{self._po_counter:05d}"

            if po.status == "cancelled" or po.confirmed_qty == 0:
                # Nothing confirmed
                self.open_pos.append(po)
                placed_lines += 1
                continue

            # Cash check
            line_cost = po.unit_cost * po.confirmed_qty
            if cfg.cash_must_cover_orders and line_cost > self.cash:
                # Reduce confirmed_qty to what cash allows
                if po.unit_cost > 0:
                    affordable = int(self.cash / po.unit_cost)
                else:
                    affordable = po.confirmed_qty
                if affordable < cfg.min_order_qty:
                    po.confirmed_qty = 0
                    po.status = "cancelled"
                    day_warnings.append(
                        f"Day {self.day}: PO {po.po_id} cancelled, insufficient cash")
                else:
                    po.confirmed_qty = affordable
                    line_cost = po.unit_cost * po.confirmed_qty
                    day_warnings.append(
                        f"Day {self.day}: PO {po.po_id} qty reduced to {affordable} (cash)")

            if po.confirmed_qty and po.confirmed_qty > 0:
                self.cash -= line_cost
                day_procurement_cost += line_cost

            self.open_pos.append(po)
            placed_lines += 1

        # === 2) Replenishment agent ===
        obs_rep = self._obs_replenishment()
        action_rep = self.rep_agent.act(obs_rep)

        visit = bool(action_rep.get("visit", False))
        restock = action_rep.get("restock", {})
        day_visit_cost = 0.0
        visited = False

        if visit:
            # Check rolling visit constraint
            recent_visits = sum(
                1 for d in self._visit_days if d > self.day - 7)
            if recent_visits >= cfg.max_visits_per_7d:
                visit = False
                day_warnings.append(
                    f"Day {self.day}: Visit denied (max {cfg.max_visits_per_7d}/7d)")

        if visit:
            visited = True
            self._visit_days.append(self.day)
            # Keep deque bounded
            while (self._visit_days and
                   self._visit_days[0] <= self.day - 7):
                self._visit_days.popleft()

            total_units_moved = 0
            for sku in cfg.skus:
                qty = int(restock.get(sku, 0))
                if qty <= 0:
                    continue
                # Clip to stockroom availability
                qty = min(qty, self.stockroom_on_hand.get(sku, 0))
                # Clip to machine capacity
                space = cfg.capacity_machine - self.machine_on_hand.get(sku, 0)
                qty = min(qty, space)
                # Clip to per-visit max
                if total_units_moved + qty > cfg.max_units_per_visit:
                    qty = cfg.max_units_per_visit - total_units_moved
                if qty > 0:
                    self.stockroom_on_hand[sku] -= qty
                    self.machine_on_hand[sku] += qty
                    total_units_moved += qty

            day_visit_cost = (cfg.visit_fixed_cost
                              + cfg.visit_handling_cost_per_unit * total_units_moved)
            self.cash -= day_visit_cost

        # === 3) Customer arrivals ===
        sales, lost = self.customer_mgr.simulate_day(
            self.day, self.machine_on_hand, self._demand_regime_multiplier)

        # Apply sales to machine inventory
        day_revenue = 0.0
        total_sold = 0
        total_lost = 0
        for sku in cfg.skus:
            sold = sales.get(sku, 0)
            self.machine_on_hand[sku] = max(0, self.machine_on_hand[sku] - sold)
            day_revenue += sold * cfg.prices.get(sku, 0)
            total_sold += sold
            total_lost += lost.get(sku, 0)

        self.cash += day_revenue

        # Update sales/lost history
        for sku in cfg.skus:
            self.sales_history[sku].append(sales.get(sku, 0))
            self.lost_history[sku].append(lost.get(sku, 0))

        # === 4) PO arrivals ===
        arrived_pos = []
        for po in self.open_pos:
            if po.status == "open" and po.eta_day <= self.day:
                cqty = po.confirmed_qty or 0
                cap = cfg.capacity_stockroom
                space = cap - self.stockroom_on_hand.get(po.sku, 0)
                add = min(cqty, space)
                self.stockroom_on_hand[po.sku] = (
                    self.stockroom_on_hand.get(po.sku, 0) + add)
                po.status = "arrived"
                arrived_pos.append(po.po_id)

        # Clean up old arrived/cancelled POs (keep last 30 days)
        self.open_pos = [
            po for po in self.open_pos
            if po.status == "open" or po.eta_day > self.day - 30
        ]

        # === 5) Holding cost ===
        total_inv = (sum(self.machine_on_hand.values())
                     + sum(self.stockroom_on_hand.values()))
        day_holding_cost = total_inv * cfg.holding_cost_per_unit_day
        self.cash -= day_holding_cost

        # === 6) Stockout penalty ===
        day_stockout_penalty = total_lost * cfg.stockout_penalty_per_unit

        # === 7) Churn update ===
        sold_7d = sum(sum(self.sales_history[s]) for s in cfg.skus)
        lost_7d = sum(sum(self.lost_history[s]) for s in cfg.skus)
        fill_7d = sold_7d / (sold_7d + lost_7d) if (sold_7d + lost_7d) > 0 else 1.0
        self.customer_mgr.update_churn(fill_7d)

        # === Scenario teardown hook ===
        self.scenario.teardown(self, self.day)

        # === Daily log ===
        log = {
            "day": self.day,
            "revenue": round(day_revenue, 4),
            "procurement_cost": round(day_procurement_cost, 4),
            "visit_cost": round(day_visit_cost, 4),
            "holding_cost": round(day_holding_cost, 4),
            "stockout_penalty": round(day_stockout_penalty, 4),
            "units_sold": total_sold,
            "units_lost": total_lost,
            "visited": visited,
            "machine_on_hand": dict(self.machine_on_hand),
            "stockroom_on_hand": dict(self.stockroom_on_hand),
            "cash": round(self.cash, 2),
            "warnings": list(day_warnings),
        }
        self.daily_logs.append(log)

        # Advance day
        self.day += 1
        self._warnings.extend(day_warnings)

        return log

    # ------------------------------------------------------------------
    # Run full episode
    # ------------------------------------------------------------------
    def run(self, horizon: Optional[int] = None) -> Dict[str, Any]:
        """Reset and run a full episode. Returns KPIs dict."""
        self.reset()
        H = horizon or self.cfg.horizon
        for _ in range(H):
            self.step()
        kpis = compute_kpis(self.daily_logs)
        kpis["score"] = compute_score(kpis, H)
        kpis["warnings_count"] = len(self._warnings)
        return kpis
