"""Baseline Replenishment Agent -- threshold-based restocking visits.

Strategy:
- Visit if any of the top-4 SKUs (by margin * velocity) are projected to
  stock out within 2 days based on 7-day average sales.
- When visiting, top up those SKUs to machine capacity, prioritising by
  margin * velocity.
- Intentionally simple and beatable.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# Default prices (duplicated here so baseline is self-contained)
_PRICES = {
    "SKU_01": 2.50, "SKU_02": 1.75, "SKU_03": 3.00, "SKU_04": 2.00,
    "SKU_05": 1.50, "SKU_06": 2.25, "SKU_07": 3.50, "SKU_08": 1.25,
    "SKU_09": 2.75, "SKU_10": 2.00, "SKU_11": 1.50, "SKU_12": 3.25,
}


class BaselineReplenishmentAgent:
    """Threshold-based restocking heuristic."""

    def __init__(self) -> None:
        self.stockout_horizon: int = 2   # days look-ahead

    def act(self, obs: dict) -> dict:
        stockroom: Dict[str, int] = obs["stockroom_on_hand"]
        machine: Dict[str, int] = obs["machine_on_hand"]
        capacity: Dict[str, int] = obs["machine_capacity"]
        sales_7d: Dict[str, List[int]] = obs["sales_last_7d"]
        constraints = obs["constraints"]
        max_units = constraints["max_units_per_visit"]

        # Compute avg daily sales per SKU
        avg_sales: Dict[str, float] = {}
        for sku in machine:
            s = sales_7d.get(sku, [0]*7)
            avg_sales[sku] = sum(s) / max(len(s), 1)

        # Score SKUs by margin * velocity
        scores: List[Tuple[float, str]] = []
        for sku in machine:
            price = _PRICES.get(sku, 2.0)
            margin = price * 0.5  # rough margin proxy
            velocity = avg_sales.get(sku, 0)
            scores.append((margin * velocity, sku))
        scores.sort(reverse=True)

        # Check if any top-4 SKU is projected to stock out
        top_skus = [sku for _, sku in scores[:4]]
        need_visit = False
        for sku in top_skus:
            days_of_stock = (machine.get(sku, 0) / avg_sales[sku]
                             if avg_sales[sku] > 0 else 999)
            if days_of_stock < self.stockout_horizon:
                need_visit = True
                break

        if not need_visit:
            return {"visit": False, "restock": {}, "note": "baseline-no-visit"}

        # Build restock plan: top up by priority
        restock: Dict[str, int] = {}
        units_left = max_units
        for _, sku in scores:
            if units_left <= 0:
                break
            gap = capacity.get(sku, 0) - machine.get(sku, 0)
            available = stockroom.get(sku, 0)
            move = min(gap, available, units_left)
            if move > 0:
                restock[sku] = move
                units_left -= move

        return {"visit": True, "restock": restock, "note": "baseline-threshold"}
