"""High-level simulation runner for the web UI.

Provides a single ``run_simulation`` function that creates the environment,
runs one episode, and returns structured daily data + KPIs ready for charting.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from vendsim.config import EnvConfig
from vendsim.env import VendingEnv
from vendsim.metrics import compute_kpis, compute_score
from vendsim.scenarios import ALL_SCENARIOS, NormalScenario


def run_simulation(
    config: EnvConfig,
    procurement_agent_cls: Type,
    replenishment_agent_cls: Type,
    seed: int = 42,
    scenario_name: str = "normal",
) -> Dict[str, Any]:
    """Run one episode and return structured results for the web UI.

    Parameters
    ----------
    config : EnvConfig
        Simulation configuration.
    procurement_agent_cls : type
        Class with an ``act(self, obs: dict) -> dict`` method.
    replenishment_agent_cls : type
        Class with an ``act(self, obs: dict) -> dict`` method.
    seed : int
        Random seed for this episode.
    scenario_name : str
        One of the keys in ``ALL_SCENARIOS``.

    Returns
    -------
    dict with keys:
        "daily"  : list[dict]  -- per-day metrics (see below)
        "kpis"   : dict        -- episode-level KPIs
        "meta"   : dict        -- scenario, seed, config summary
    """
    scenario_cls = ALL_SCENARIOS.get(scenario_name, NormalScenario)
    scenario = scenario_cls()

    proc_agent = procurement_agent_cls()
    rep_agent = replenishment_agent_cls()

    env = VendingEnv(proc_agent, rep_agent, cfg=config, seed=seed, scenario=scenario)
    env.reset()

    horizon = config.horizon
    for _ in range(horizon):
        env.step()

    # Build KPIs
    kpis = compute_kpis(env.daily_logs)
    kpis["score"] = compute_score(kpis, horizon)
    kpis["warnings_count"] = len(env._warnings)

    # Standardise daily logs for the web UI
    daily: List[Dict[str, Any]] = []
    for log in env.daily_logs:
        sold = log["units_sold"]
        lost = log["units_lost"]
        total = sold + lost
        fill = sold / total if total > 0 else 1.0
        profit = (
            log["revenue"]
            - log["procurement_cost"]
            - log["visit_cost"]
            - log["holding_cost"]
            - log["stockout_penalty"]
        )
        daily.append({
            "day": log["day"],
            "profit": round(profit, 4),
            "revenue": log["revenue"],
            "procurement_cost": log["procurement_cost"],
            "visit_cost": log["visit_cost"],
            "holding_cost": log["holding_cost"],
            "stockout_penalty": log["stockout_penalty"],
            "cash": log["cash"],
            "units_sold": sold,
            "units_lost": lost,
            "fill_rate": round(fill, 4),
            "visit": 1 if log["visited"] else 0,
            "machine_on_hand": dict(log["machine_on_hand"]),
            "stockroom_on_hand": dict(log["stockroom_on_hand"]),
        })

    meta = {
        "scenario": scenario_name,
        "seed": seed,
        "horizon": horizon,
        "n_skus": len(config.skus),
        "initial_cash": config.initial_cash,
    }

    return {"daily": daily, "kpis": kpis, "meta": meta}
