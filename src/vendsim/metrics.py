"""KPI calculation helpers for VendSim."""
from __future__ import annotations

from typing import Any, Dict, List


def compute_kpis(daily_logs: List[dict]) -> Dict[str, Any]:
    """Compute episode-level KPIs from the list of daily log dicts.

    Each daily log is expected to have keys:
        revenue, procurement_cost, visit_cost, holding_cost,
        stockout_penalty, units_sold, units_lost, visited (bool),
        machine_on_hand (dict[sku->int]), cash
    """
    if not daily_logs:
        return _empty_kpis()

    total_revenue = sum(d["revenue"] for d in daily_logs)
    total_procurement = sum(d["procurement_cost"] for d in daily_logs)
    total_visit_cost = sum(d["visit_cost"] for d in daily_logs)
    total_holding = sum(d["holding_cost"] for d in daily_logs)
    total_stockout_pen = sum(d["stockout_penalty"] for d in daily_logs)

    total_profit = (total_revenue - total_procurement - total_visit_cost
                    - total_holding - total_stockout_pen)

    total_sold = sum(d["units_sold"] for d in daily_logs)
    total_lost = sum(d["units_lost"] for d in daily_logs)
    fill_rate = (total_sold / (total_sold + total_lost)
                 if (total_sold + total_lost) > 0 else 1.0)

    visits_total = sum(1 for d in daily_logs if d["visited"])

    # Stockout days by SKU
    skus = list(daily_logs[0]["machine_on_hand"].keys())
    stockout_days: Dict[str, int] = {}
    for sku in skus:
        stockout_days[sku] = sum(
            1 for d in daily_logs if d["machine_on_hand"].get(sku, 0) == 0
        )

    cash_min = min(d["cash"] for d in daily_logs)

    return {
        "total_profit": round(total_profit, 2),
        "total_revenue": round(total_revenue, 2),
        "total_procurement_cost": round(total_procurement, 2),
        "total_visit_cost": round(total_visit_cost, 2),
        "total_holding_cost": round(total_holding, 2),
        "total_stockout_penalty": round(total_stockout_pen, 2),
        "fill_rate": round(fill_rate, 4),
        "visits_total": visits_total,
        "stockout_days_by_sku": stockout_days,
        "cash_min": round(cash_min, 2),
        "total_units_sold": total_sold,
        "total_units_lost": total_lost,
        "days": len(daily_logs),
    }


def compute_score(kpis: Dict[str, Any], horizon: int = 180) -> float:
    """Compute a single scalar score from KPIs.

    score = 0.4 * normalized_profit + 0.4 * fill_rate - 0.2 * visit_rate_penalty

    normalized_profit: profit / (horizon * 10), clipped to [0, 1]
    visit_rate_penalty: visits_total / horizon, clipped to [0, 1]
    """
    # Normalize profit: ~$10/day is "perfect"
    norm_profit = kpis["total_profit"] / (horizon * 10.0)
    norm_profit = max(0.0, min(1.0, norm_profit))

    fill = kpis["fill_rate"]

    visit_penalty = kpis["visits_total"] / horizon
    visit_penalty = max(0.0, min(1.0, visit_penalty))

    score = 0.4 * norm_profit + 0.4 * fill - 0.2 * visit_penalty
    return round(score, 4)


def _empty_kpis() -> Dict[str, Any]:
    return {
        "total_profit": 0.0, "total_revenue": 0.0,
        "total_procurement_cost": 0.0, "total_visit_cost": 0.0,
        "total_holding_cost": 0.0, "total_stockout_penalty": 0.0,
        "fill_rate": 0.0, "visits_total": 0, "stockout_days_by_sku": {},
        "cash_min": 0.0, "total_units_sold": 0, "total_units_lost": 0,
        "days": 0,
    }
