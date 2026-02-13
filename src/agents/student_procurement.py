"""Student Procurement Agent -- EDIT THIS FILE.

Your task: implement the `act` method to decide which purchase orders to place
each day.  You may add helper methods and state to the class.

=== OBSERVATION (obs) ===
obs is a dict with these keys:
  "day"               : int       -- current simulation day (0-indexed)
  "cash"              : float     -- cash on hand
  "stockroom_on_hand" : dict[str, int]  -- stockroom inventory per SKU
  "machine_on_hand"   : dict[str, int]  -- vending machine inventory per SKU
  "sales_last_7d"     : dict[str, list[int]]  -- last 7 days of machine sales per SKU
  "open_pos"          : list[dict]  -- open purchase orders, each with keys:
        po_id, vendor, sku, ordered_qty, confirmed_qty, unit_cost, eta_day, status
  "vendor_scorecard"  : dict[str, dict]  -- rolling 30-day stats per vendor:
        avg_fill_rate, avg_lead_time, avg_unit_cost
  "constraints"       : dict with:
        max_po_lines_per_day (int), min_order_qty (int), cash_must_cover_orders (bool)

=== ACTION (return value) ===
Return a dict:
  "pos"  : list of PO line dicts, each with keys:
        "vendor" : "A" | "B" | "C"
        "sku"    : one of the 12 SKU strings
        "qty"    : int  (>= min_order_qty)
        "mode"   : "standard" | "expedite"
  "note" : str (optional, for your own logging)

=== RULES ===
- At most max_po_lines_per_day PO lines per day (default 5).
- qty must be >= min_order_qty (default 5).
- If cash_must_cover_orders is True, total expected spend must be <= cash.
- Violations are clipped/dropped by the environment.
"""
from __future__ import annotations

from typing import Dict, List


def forecast_daily(sales_7d: List[int]) -> float:
    """Simple helper: average daily sales from a 7-day history list."""
    return sum(sales_7d) / max(len(sales_7d), 1)


class StudentProcurementAgent:
    """Implement your procurement policy here."""

    def __init__(self) -> None:
        pass  # Add any state you need

    def act(self, obs: dict) -> dict:
        # TODO: Replace this with your procurement policy.
        # The baseline just does nothing -- you can do better!
        return {"pos": [], "note": "student-stub"}
