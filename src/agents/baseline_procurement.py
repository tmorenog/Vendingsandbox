"""Baseline Procurement Agent -- reorder-point heuristic.

Strategy:
- For each SKU, compute a reorder point = avg_daily_sales * (avg_lead_time + 7)
- If stockroom + pipeline inventory < reorder point, place an order.
- Choose the cheapest vendor by avg_unit_cost, unless their fill rate is too low.
- Intentionally simple and beatable.
"""
from __future__ import annotations

from typing import Dict, List


class BaselineProcurementAgent:
    """Reorder-point procurement: order when stockroom is low."""

    def __init__(self) -> None:
        self.lead_time_buffer: int = 7   # safety buffer in days

    def act(self, obs: dict) -> dict:
        day: int = obs["day"]
        cash: float = obs["cash"]
        stockroom: Dict[str, int] = obs["stockroom_on_hand"]
        machine: Dict[str, int] = obs["machine_on_hand"]
        sales_7d: Dict[str, List[int]] = obs["sales_last_7d"]
        open_pos: List[dict] = obs["open_pos"]
        scorecard: Dict[str, dict] = obs["vendor_scorecard"]
        constraints = obs["constraints"]

        max_lines = constraints["max_po_lines_per_day"]
        min_qty = constraints["min_order_qty"]

        # Pipeline inventory per SKU (open PO confirmed or ordered qty)
        pipeline: Dict[str, int] = {}
        for po in open_pos:
            sku = po["sku"]
            qty = po.get("confirmed_qty") or po.get("ordered_qty", 0)
            pipeline[sku] = pipeline.get(sku, 0) + qty

        # Choose vendor: cheapest with fill_rate >= 0.60
        best_vendor = self._pick_vendor(scorecard)

        avg_lead = scorecard.get(best_vendor, {}).get("avg_lead_time", 3.0)

        po_lines = []
        for sku in sorted(stockroom.keys()):
            if len(po_lines) >= max_lines:
                break

            avg_sales = sum(sales_7d.get(sku, [0]*7)) / 7.0
            reorder_point = avg_sales * (avg_lead + self.lead_time_buffer)
            position = stockroom.get(sku, 0) + pipeline.get(sku, 0)

            if position < reorder_point:
                order_qty = max(min_qty, int(reorder_point - position + 0.5))
                # Quick cash check (rough)
                est_cost = scorecard.get(best_vendor, {}).get("avg_unit_cost", 0.5)
                if est_cost <= 0:
                    est_cost = 0.5
                if order_qty * est_cost > cash * 0.5:
                    order_qty = max(min_qty, int(cash * 0.4 / est_cost))
                if order_qty >= min_qty:
                    po_lines.append({
                        "vendor": best_vendor,
                        "sku": sku,
                        "qty": order_qty,
                        "mode": "standard",
                    })

        return {"pos": po_lines, "note": "baseline-reorder-point"}

    @staticmethod
    def _pick_vendor(scorecard: Dict[str, dict]) -> str:
        """Pick cheapest vendor with acceptable fill rate."""
        candidates = []
        for v, sc in scorecard.items():
            if sc.get("avg_fill_rate", 0) >= 0.60:
                candidates.append((sc.get("avg_unit_cost", 999), v))
        if not candidates:
            # Fall back to highest fill rate vendor
            return max(scorecard, key=lambda v: scorecard[v].get("avg_fill_rate", 0))
        candidates.sort()
        return candidates[0][1]
