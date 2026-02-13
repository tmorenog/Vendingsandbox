#!/usr/bin/env python3
"""Run a single episode and print KPIs.

Usage:
    python -m run_episode [--seed 42] [--horizon 180] [--agent baseline|student]
                          [--scenario normal|demand_surge|vendor_disruption|cash_shock]
"""
from __future__ import annotations

import argparse
import sys
import os

# Ensure src/ is on the path so we can import vendsim and agents
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vendsim.config import EnvConfig
from vendsim.env import VendingEnv
from vendsim.scenarios import ALL_SCENARIOS


def load_agents(agent_type: str):
    """Return (procurement_agent, replenishment_agent) instances."""
    if agent_type == "baseline":
        from agents.baseline_procurement import BaselineProcurementAgent
        from agents.baseline_replenishment import BaselineReplenishmentAgent
        return BaselineProcurementAgent(), BaselineReplenishmentAgent()
    elif agent_type == "student":
        from agents.student_procurement import StudentProcurementAgent
        from agents.student_replenishment import StudentReplenishmentAgent
        return StudentProcurementAgent(), StudentReplenishmentAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single VendSim episode.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--horizon", type=int, default=180)
    parser.add_argument("--agent", choices=["baseline", "student"], default="baseline")
    parser.add_argument("--scenario", choices=list(ALL_SCENARIOS.keys()), default="normal")
    args = parser.parse_args()

    cfg = EnvConfig(horizon=args.horizon)
    scenario = ALL_SCENARIOS[args.scenario]()
    proc, rep = load_agents(args.agent)
    env = VendingEnv(proc, rep, cfg=cfg, seed=args.seed, scenario=scenario)

    kpis = env.run()

    print(f"\n{'='*60}")
    print(f"  VendSim Episode  |  agent={args.agent}  seed={args.seed}")
    print(f"  scenario={args.scenario}  horizon={args.horizon}")
    print(f"{'='*60}")
    for key, val in kpis.items():
        if key == "stockout_days_by_sku":
            total_stockout = sum(val.values())
            print(f"  {key:30s} : {total_stockout} total across SKUs")
        else:
            print(f"  {key:30s} : {val}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
