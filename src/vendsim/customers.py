"""Customer agents -- generate daily demand with substitution and churn."""
from __future__ import annotations

import math
import random as _random_mod
from typing import Dict, List, Tuple

from vendsim.config import EnvConfig


class CustomerManager:
    """Generates daily customer arrivals and purchase attempts."""

    def __init__(self, cfg: EnvConfig, rng: _random_mod.Random) -> None:
        self.cfg = cfg
        self.rng = rng
        self.arrival_multiplier: float = 1.0   # churn/recovery factor
        # Build CDF for SKU preference sampling
        self._sku_list = list(cfg.skus)
        weights = [cfg.preference_weights.get(s, 1.0) for s in self._sku_list]
        total = sum(weights)
        self._sku_probs = [w / total for w in weights]

    # ------------------------------------------------------------------
    def _sample_sku(self) -> str:
        """Weighted random choice of a preferred SKU."""
        r = self.rng.random()
        cumulative = 0.0
        for sku, p in zip(self._sku_list, self._sku_probs):
            cumulative += p
            if r < cumulative:
                return sku
        return self._sku_list[-1]

    def _sample_substitute(self, exclude: str) -> str:
        """Sample a substitute SKU (weighted, excluding *exclude*)."""
        remaining = [(s, p) for s, p in zip(self._sku_list, self._sku_probs)
                     if s != exclude]
        if not remaining:
            return exclude
        total = sum(p for _, p in remaining)
        r = self.rng.random() * total
        cumulative = 0.0
        for sku, p in remaining:
            cumulative += p
            if r < cumulative:
                return sku
        return remaining[-1][0]

    # ------------------------------------------------------------------
    def simulate_day(
        self,
        day: int,
        machine_on_hand: Dict[str, int],
        demand_regime_multiplier: float,
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Run customer arrivals for one day.

        Returns:
            sales: dict[sku -> units sold]
            lost:  dict[sku -> units of demand that could not be fulfilled]
        """
        cfg = self.cfg
        c = cfg.customer

        # Day-of-week (0=Mon)
        dow = day % 7
        dow_mult = c.dow_multipliers[dow]

        lam = (c.base_arrival_rate * dow_mult
               * demand_regime_multiplier * self.arrival_multiplier)
        n_customers = self._poisson(lam)

        sales: Dict[str, int] = {s: 0 for s in cfg.skus}
        lost: Dict[str, int] = {s: 0 for s in cfg.skus}

        # Local copy of machine inventory for intra-day depletion
        inv = dict(machine_on_hand)

        for _ in range(n_customers):
            preferred = self._sample_sku()

            if inv.get(preferred, 0) > 0:
                inv[preferred] -= 1
                sales[preferred] += 1
                continue

            # Preferred OOS -- try substitution?
            if self.rng.random() < c.p_substitute:
                bought = False
                tried = {preferred}
                for _ in range(c.max_substitute_tries):
                    alt = self._sample_substitute(preferred)
                    if alt in tried:
                        continue
                    tried.add(alt)
                    if inv.get(alt, 0) > 0:
                        inv[alt] -= 1
                        sales[alt] += 1
                        bought = True
                        break
                if not bought:
                    lost[preferred] += 1
            else:
                lost[preferred] += 1

        return sales, lost

    # ------------------------------------------------------------------
    def update_churn(self, fill_rate_7d: float) -> None:
        """Adjust arrival multiplier based on recent service quality."""
        c = self.cfg.customer
        if fill_rate_7d < c.churn_fill_threshold:
            self.arrival_multiplier *= c.churn_decay
        else:
            self.arrival_multiplier *= c.recovery_rate
        # Keep bounded
        self.arrival_multiplier = max(0.60, min(1.10, self.arrival_multiplier))

    # ------------------------------------------------------------------
    def _poisson(self, lam: float) -> int:
        """Knuth Poisson sampler using instance RNG."""
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= self.rng.random()
            if p < L:
                return k - 1
