"""Student Replenishment Agent -- EDIT THIS FILE.

Your task: implement the `act` method to decide when to visit the vending
machine and how much of each SKU to move from the stockroom into the machine.

=== OBSERVATION (obs) ===
obs is a dict with these keys:
  "day"               : int       -- current simulation day (0-indexed)
  "stockroom_on_hand" : dict[str, int]  -- stockroom inventory per SKU
  "machine_on_hand"   : dict[str, int]  -- vending machine inventory per SKU
  "machine_capacity"  : dict[str, int]  -- max units per SKU in the machine
  "sales_last_7d"     : dict[str, list[int]]  -- last 7 days of machine sales per SKU
  "days_since_visit"  : int       -- days since the last restocking visit
  "constraints"       : dict with:
        max_visits_per_7d (int), max_units_per_visit (int)

=== ACTION (return value) ===
Return a dict:
  "visit"   : bool -- True to make a restocking visit today
  "restock" : dict[str, int] -- units to move from stockroom to machine per SKU
               (ignored if visit is False)
  "note"    : str (optional, for your own logging)

=== RULES ===
- At most max_visits_per_7d visits per rolling 7-day window (default 3).
- sum(restock.values()) must be <= max_units_per_visit (default 60).
- restock[sku] must be <= stockroom_on_hand[sku].
- machine_on_hand[sku] + restock[sku] must be <= machine_capacity[sku].
- Violations are clipped by the environment.
"""
from __future__ import annotations

from typing import Dict, List


def forecast_daily(sales_7d: List[int]) -> float:
    """Simple helper: average daily sales from a 7-day history list."""
    return sum(sales_7d) / max(len(sales_7d), 1)


class StudentReplenishmentAgent:
    """Implement your replenishment policy here."""

    def __init__(self) -> None:
        pass  # Add any state you need

    def act(self, obs: dict) -> dict:
        # TODO: Replace this with your replenishment policy.
        # The baseline just never visits -- you can do better!
        return {"visit": False, "restock": {}, "note": "student-stub"}
