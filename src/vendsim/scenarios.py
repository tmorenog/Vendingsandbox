"""Scenario definitions for VendSim.

Each scenario is a callable that receives (env, day) and may mutate
environment state to simulate stress conditions.
"""
from __future__ import annotations

import random as _random_mod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vendsim.env import VendingEnv


@dataclass
class Scenario:
    """Base scenario -- no-op (normal conditions)."""
    name: str = "normal"

    def setup(self, env: "VendingEnv", rng: _random_mod.Random) -> None:
        """Called once at episode start."""
        pass

    def on_day(self, env: "VendingEnv", day: int) -> None:
        """Called at the start of each day, before agent actions."""
        pass

    def teardown(self, env: "VendingEnv", day: int) -> None:
        """Called at end of each day, after all processing."""
        pass


class NormalScenario(Scenario):
    """Default: no special events."""
    name: str = "normal"


@dataclass
class StressDemandSurgeScenario(Scenario):
    """For a random 5-day window, demand regime multiplier is 2.0."""
    name: str = "demand_surge"
    surge_start: int = -1
    surge_duration: int = 5
    surge_multiplier: float = 2.0
    _original_multiplier: float = 1.0

    def setup(self, env: "VendingEnv", rng: _random_mod.Random) -> None:
        # Pick a random start day in [20, horizon-30]
        lo = 20
        hi = max(lo + 1, env.cfg.horizon - 30)
        self.surge_start = rng.randint(lo, hi)
        self._original_multiplier = env.cfg.demand_regime_multiplier

    def on_day(self, env: "VendingEnv", day: int) -> None:
        if self.surge_start <= day < self.surge_start + self.surge_duration:
            env._demand_regime_multiplier = self.surge_multiplier
        else:
            env._demand_regime_multiplier = self._original_multiplier


@dataclass
class StressVendorDisruptionScenario(Scenario):
    """Force Vendor A into DISRUPTED for 10 days mid-episode."""
    name: str = "vendor_disruption"
    disruption_start: int = -1
    disruption_duration: int = 10

    def setup(self, env: "VendingEnv", rng: _random_mod.Random) -> None:
        lo = 30
        hi = max(lo + 1, env.cfg.horizon - 40)
        self.disruption_start = rng.randint(lo, hi)

    def on_day(self, env: "VendingEnv", day: int) -> None:
        vendor_a = env.vendor_mgr.vendors.get("A")
        if vendor_a is None:
            return
        if self.disruption_start <= day < self.disruption_start + self.disruption_duration:
            vendor_a.force_regime("DISRUPTED")

    def teardown(self, env: "VendingEnv", day: int) -> None:
        # After the disruption window, let normal Markov resume
        pass


@dataclass
class StressCashShockScenario(Scenario):
    """Remove $300 cash at a random day (floor at 0)."""
    name: str = "cash_shock"
    shock_day: int = -1
    shock_amount: float = 300.0
    _applied: bool = False

    def setup(self, env: "VendingEnv", rng: _random_mod.Random) -> None:
        lo = 20
        hi = max(lo + 1, env.cfg.horizon - 20)
        self.shock_day = rng.randint(lo, hi)
        self._applied = False

    def on_day(self, env: "VendingEnv", day: int) -> None:
        if day == self.shock_day and not self._applied:
            env.cash = max(0.0, env.cash - self.shock_amount)
            env._warnings.append(
                f"Day {day}: Cash shock applied (-${self.shock_amount:.0f})")
            self._applied = True


ALL_SCENARIOS = {
    "normal": NormalScenario,
    "demand_surge": StressDemandSurgeScenario,
    "vendor_disruption": StressVendorDisruptionScenario,
    "cash_shock": StressCashShockScenario,
}
