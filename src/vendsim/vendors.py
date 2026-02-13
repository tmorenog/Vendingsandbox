"""Vendor agents -- simulate supplier behaviour with hidden regimes."""
from __future__ import annotations

import math
import random as _random_mod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from vendsim.config import EnvConfig, VendorProfile


@dataclass
class POLine:
    """A single purchase-order line tracked by the environment."""
    po_id: str
    vendor: str
    sku: str
    ordered_qty: int
    confirmed_qty: Optional[int] = None
    unit_cost: Optional[float] = None
    eta_day: int = 0
    status: str = "open"               # "open" | "arrived" | "cancelled"

    def to_dict(self) -> dict:
        return {
            "po_id": self.po_id,
            "vendor": self.vendor,
            "sku": self.sku,
            "ordered_qty": self.ordered_qty,
            "confirmed_qty": self.confirmed_qty,
            "unit_cost": self.unit_cost,
            "eta_day": self.eta_day,
            "status": self.status,
        }


class VendorAgent:
    """Simulates one vendor with a hidden 2-state Markov regime."""

    def __init__(self, profile: VendorProfile, cfg: EnvConfig,
                 rng: _random_mod.Random) -> None:
        self.profile = profile
        self.cfg = cfg
        self.rng = rng
        self.regime: str = "NORMAL"     # hidden from students
        # Rolling history for scorecard (last 30 days of fulfilled POs)
        self._history: List[dict] = []  # each: {day, fill_rate, lead_time, unit_cost}
        self._daily_confirmed_today: int = 0

    # ------------------------------------------------------------------
    def step_regime(self) -> None:
        """Advance the hidden Markov regime by one day."""
        p = self.profile
        if self.regime == "NORMAL":
            if self.rng.random() < p.p_normal_to_disrupted:
                self.regime = "DISRUPTED"
        else:
            if self.rng.random() < p.p_disrupted_to_normal:
                self.regime = "NORMAL"

    def begin_day(self) -> None:
        """Reset daily capacity counter."""
        self._daily_confirmed_today = 0

    # ------------------------------------------------------------------
    def process_po_line(self, sku: str, ordered_qty: int, mode: str,
                        current_day: int) -> POLine:
        """Return a POLine with confirmation details.

        Immediate confirmation model: vendor responds same-day with
        confirmed_qty, unit_cost, and eta_day.
        """
        p = self.profile
        regime = self.regime

        # --- Fill probability ------------------------------------------
        fill_prob = (p.fill_prob_normal if regime == "NORMAL"
                     else p.fill_prob_disrupted)

        # Binomial draw for confirmed_qty
        confirmed = sum(1 for _ in range(ordered_qty)
                        if self.rng.random() < fill_prob)

        # Apply daily capacity constraint
        remaining_cap = max(0, p.daily_capacity - self._daily_confirmed_today)
        confirmed = min(confirmed, remaining_cap)
        self._daily_confirmed_today += confirmed

        if confirmed == 0:
            # Nothing confirmed -- cancelled PO
            return POLine(
                po_id="", vendor=p.name, sku=sku,
                ordered_qty=ordered_qty, confirmed_qty=0,
                unit_cost=0.0, eta_day=current_day, status="cancelled",
            )

        # --- Lead time -------------------------------------------------
        if mode == "expedite":
            lead = self.rng.choice(p.lead_days_expedite)
        elif regime == "NORMAL":
            lead = self.rng.choice(p.lead_days_normal)
        else:
            lead = self.rng.choice(p.lead_days_disrupted)

        eta = current_day + lead

        # --- Unit cost -------------------------------------------------
        sku_base = self.cfg.sku_base_costs.get(sku, 1.0)
        cost = sku_base * p.base_cost_factor
        noise = 1.0 + self.rng.uniform(-p.cost_noise_half, p.cost_noise_half)
        cost *= noise
        if regime == "DISRUPTED":
            cost *= p.disrupted_cost_multiplier
        if mode == "expedite":
            cost *= p.expedite_multiplier
        cost = round(cost, 4)

        fill_rate = confirmed / ordered_qty if ordered_qty > 0 else 0.0
        self._history.append({
            "day": current_day,
            "fill_rate": fill_rate,
            "lead_time": lead,
            "unit_cost": cost,
        })

        return POLine(
            po_id="", vendor=p.name, sku=sku,
            ordered_qty=ordered_qty, confirmed_qty=confirmed,
            unit_cost=cost, eta_day=eta, status="open",
        )

    # ------------------------------------------------------------------
    def scorecard(self, current_day: int) -> dict:
        """Rolling 30-day scorecard visible to students."""
        window = [h for h in self._history if h["day"] > current_day - 30]
        if not window:
            return {"avg_fill_rate": 1.0, "avg_lead_time": 3.0,
                    "avg_unit_cost": 0.0}
        n = len(window)
        return {
            "avg_fill_rate": round(sum(h["fill_rate"] for h in window) / n, 4),
            "avg_lead_time": round(sum(h["lead_time"] for h in window) / n, 2),
            "avg_unit_cost": round(sum(h["unit_cost"] for h in window) / n, 4),
        }

    def force_regime(self, regime: str) -> None:
        """Used by stress scenarios to override the hidden regime."""
        self.regime = regime


class VendorManager:
    """Container that holds all vendor agents."""

    def __init__(self, cfg: EnvConfig, rng: _random_mod.Random) -> None:
        self.cfg = cfg
        self.vendors: Dict[str, VendorAgent] = {}
        for name, profile in cfg.vendor_profiles.items():
            # Each vendor gets its own RNG stream derived from the master
            v_rng = _random_mod.Random(rng.randint(0, 2**63))
            self.vendors[name] = VendorAgent(profile, cfg, v_rng)

    def begin_day(self) -> None:
        for v in self.vendors.values():
            v.begin_day()

    def step_regimes(self) -> None:
        for v in self.vendors.values():
            v.step_regime()

    def process_po_line(self, vendor: str, sku: str, ordered_qty: int,
                        mode: str, current_day: int) -> POLine:
        return self.vendors[vendor].process_po_line(
            sku, ordered_qty, mode, current_day)

    def scorecards(self, current_day: int) -> Dict[str, dict]:
        return {name: v.scorecard(current_day)
                for name, v in self.vendors.items()}
