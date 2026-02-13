#!/usr/bin/env python3
"""Evaluate agents across multiple seeds and scenarios.

Usage:
    python -m evaluate [--seeds 50] [--horizon 180]

Runs both baseline and student agents through normal + 3 stress scenarios
and prints a summary table with scores.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vendsim.config import EnvConfig
from vendsim.env import VendingEnv
from vendsim.metrics import compute_score
from vendsim.scenarios import ALL_SCENARIOS


def load_agents(agent_type: str):
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


def run_evaluation(agent_type: str, num_seeds: int, horizon: int):
    """Run all scenarios and return aggregated results."""
    scenarios_to_run = ["normal", "demand_surge", "vendor_disruption", "cash_shock"]
    cfg = EnvConfig(horizon=horizon)

    results = {}
    for sc_name in scenarios_to_run:
        sc_results = []
        for seed in range(num_seeds):
            proc, rep = load_agents(agent_type)
            scenario = ALL_SCENARIOS[sc_name]()
            env = VendingEnv(proc, rep, cfg=cfg, seed=seed, scenario=scenario)
            kpis = env.run()
            sc_results.append(kpis)
        results[sc_name] = sc_results

    return results


def summarise(results: dict, horizon: int) -> dict:
    """Compute average KPIs per scenario."""
    summary = {}
    for sc_name, kpi_list in results.items():
        n = len(kpi_list)
        avg_profit = sum(k["total_profit"] for k in kpi_list) / n
        avg_fill = sum(k["fill_rate"] for k in kpi_list) / n
        avg_visits = sum(k["visits_total"] for k in kpi_list) / n
        avg_score = sum(k["score"] for k in kpi_list) / n
        summary[sc_name] = {
            "avg_profit": round(avg_profit, 2),
            "avg_fill_rate": round(avg_fill, 4),
            "avg_visits": round(avg_visits, 1),
            "avg_score": round(avg_score, 4),
        }
    return summary


def print_table(label: str, summary: dict) -> None:
    hdr = f"{'Scenario':<22} {'Profit':>10} {'Fill Rate':>10} {'Visits':>8} {'Score':>8}"
    print(f"\n  [{label}]")
    print(f"  {hdr}")
    print(f"  {'-'*len(hdr)}")
    for sc, s in summary.items():
        print(f"  {sc:<22} {s['avg_profit']:>10.2f} {s['avg_fill_rate']:>10.4f} "
              f"{s['avg_visits']:>8.1f} {s['avg_score']:>8.4f}")


def overall_score(summary: dict) -> float:
    """Weighted average across scenarios: normal=0.4, each stress=0.2."""
    weights = {"normal": 0.4, "demand_surge": 0.2,
               "vendor_disruption": 0.2, "cash_shock": 0.2}
    total = sum(weights.get(sc, 0) * s["avg_score"]
                for sc, s in summary.items())
    return round(total, 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate VendSim agents.")
    parser.add_argument("--seeds", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=180)
    args = parser.parse_args()

    print(f"\nVendSim Evaluation  |  seeds={args.seeds}  horizon={args.horizon}")
    print("=" * 70)

    for agent_type in ("baseline", "student"):
        t0 = time.time()
        results = run_evaluation(agent_type, args.seeds, args.horizon)
        elapsed = time.time() - t0
        summary = summarise(results, args.horizon)
        print_table(agent_type.upper(), summary)
        ov = overall_score(summary)
        print(f"  {'OVERALL SCORE':<22} {'':>10} {'':>10} {'':>8} {ov:>8.4f}")
        print(f"  (evaluated {args.seeds} seeds x 4 scenarios in {elapsed:.1f}s)")

    print("\n" + "=" * 70)
    print("Grading note: overall score weights --")
    print("  normal=0.4, demand_surge=0.2, vendor_disruption=0.2, cash_shock=0.2")
    print("  score = 0.4*norm_profit + 0.4*fill_rate - 0.2*visit_penalty")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
