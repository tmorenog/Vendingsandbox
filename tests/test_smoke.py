"""Smoke tests for VendSim.

- Instantiate env with baseline agents, seed=123
- Run 30 days
- Assert KPI keys exist and are finite
- Assert deterministic: same seed yields same total_profit and fill_rate
"""
from __future__ import annotations

import math
import os
import sys
import unittest

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vendsim.config import EnvConfig
from vendsim.env import VendingEnv
from vendsim.metrics import compute_kpis, compute_score
from vendsim.scenarios import (
    NormalScenario,
    StressCashShockScenario,
    StressDemandSurgeScenario,
    StressVendorDisruptionScenario,
)
from agents.baseline_procurement import BaselineProcurementAgent
from agents.baseline_replenishment import BaselineReplenishmentAgent


def _make_env(seed: int = 123, horizon: int = 30, scenario=None):
    cfg = EnvConfig(horizon=horizon)
    proc = BaselineProcurementAgent()
    rep = BaselineReplenishmentAgent()
    sc = scenario or NormalScenario()
    return VendingEnv(proc, rep, cfg=cfg, seed=seed, scenario=sc)


class TestSmokeBaseline(unittest.TestCase):
    """Basic smoke tests with baseline agents."""

    def test_run_30_days_no_crash(self):
        env = _make_env(seed=123, horizon=30)
        kpis = env.run()
        self.assertEqual(kpis["days"], 30)

    def test_kpi_keys_present(self):
        env = _make_env(seed=123, horizon=30)
        kpis = env.run()
        required_keys = [
            "total_profit", "total_revenue", "total_procurement_cost",
            "total_visit_cost", "total_holding_cost", "total_stockout_penalty",
            "fill_rate", "visits_total", "stockout_days_by_sku",
            "cash_min", "total_units_sold", "total_units_lost", "days", "score",
        ]
        for key in required_keys:
            self.assertIn(key, kpis, f"Missing KPI key: {key}")

    def test_kpis_finite(self):
        env = _make_env(seed=123, horizon=30)
        kpis = env.run()
        for key in ("total_profit", "fill_rate", "cash_min", "score"):
            val = kpis[key]
            self.assertTrue(math.isfinite(val), f"KPI {key} is not finite: {val}")

    def test_deterministic(self):
        """Same seed must produce identical results."""
        env1 = _make_env(seed=123, horizon=30)
        kpis1 = env1.run()

        env2 = _make_env(seed=123, horizon=30)
        kpis2 = env2.run()

        self.assertEqual(kpis1["total_profit"], kpis2["total_profit"])
        self.assertEqual(kpis1["fill_rate"], kpis2["fill_rate"])
        self.assertEqual(kpis1["visits_total"], kpis2["visits_total"])
        self.assertEqual(kpis1["total_units_sold"], kpis2["total_units_sold"])

    def test_different_seeds_differ(self):
        """Different seeds should (almost certainly) produce different results."""
        env1 = _make_env(seed=1, horizon=60)
        kpis1 = env1.run()

        env2 = _make_env(seed=999, horizon=60)
        kpis2 = env2.run()

        # At least one metric should differ
        differs = (
            kpis1["total_profit"] != kpis2["total_profit"]
            or kpis1["fill_rate"] != kpis2["fill_rate"]
        )
        self.assertTrue(differs, "Two different seeds produced identical results")

    def test_full_horizon_180(self):
        """Full 180-day episode completes without error."""
        env = _make_env(seed=42, horizon=180)
        kpis = env.run()
        self.assertEqual(kpis["days"], 180)
        self.assertGreater(kpis["total_revenue"], 0)

    def test_fill_rate_bounded(self):
        env = _make_env(seed=123, horizon=60)
        kpis = env.run()
        self.assertGreaterEqual(kpis["fill_rate"], 0.0)
        self.assertLessEqual(kpis["fill_rate"], 1.0)

    def test_score_bounded(self):
        env = _make_env(seed=123, horizon=60)
        kpis = env.run()
        self.assertGreaterEqual(kpis["score"], -1.0)
        self.assertLessEqual(kpis["score"], 1.0)


class TestSmokeScenarios(unittest.TestCase):
    """Verify stress scenarios run without crashing."""

    def test_demand_surge(self):
        env = _make_env(seed=77, horizon=60, scenario=StressDemandSurgeScenario())
        kpis = env.run()
        self.assertEqual(kpis["days"], 60)
        self.assertTrue(math.isfinite(kpis["total_profit"]))

    def test_vendor_disruption(self):
        env = _make_env(seed=77, horizon=60, scenario=StressVendorDisruptionScenario())
        kpis = env.run()
        self.assertEqual(kpis["days"], 60)
        self.assertTrue(math.isfinite(kpis["total_profit"]))

    def test_cash_shock(self):
        env = _make_env(seed=77, horizon=60, scenario=StressCashShockScenario())
        kpis = env.run()
        self.assertEqual(kpis["days"], 60)
        self.assertTrue(math.isfinite(kpis["total_profit"]))


class TestSmokeStudentStubs(unittest.TestCase):
    """Ensure student stubs can run without crashing."""

    def test_student_stubs_run(self):
        from agents.student_procurement import StudentProcurementAgent
        from agents.student_replenishment import StudentReplenishmentAgent

        cfg = EnvConfig(horizon=30)
        proc = StudentProcurementAgent()
        rep = StudentReplenishmentAgent()
        env = VendingEnv(proc, rep, cfg=cfg, seed=123)
        kpis = env.run()
        self.assertEqual(kpis["days"], 30)
        self.assertTrue(math.isfinite(kpis["score"]))


class TestWebRunner(unittest.TestCase):
    """Tests for the web_runner.run_simulation function."""

    def test_run_simulation_returns_required_keys(self):
        from vendsim.web_runner import run_simulation

        cfg = EnvConfig(horizon=30)
        result = run_simulation(
            cfg,
            BaselineProcurementAgent,
            BaselineReplenishmentAgent,
            seed=42,
            scenario_name="normal",
        )
        self.assertIn("daily", result)
        self.assertIn("kpis", result)
        self.assertIn("meta", result)

        # Check daily structure
        self.assertEqual(len(result["daily"]), 30)
        day0 = result["daily"][0]
        for key in (
            "day", "profit", "cash", "units_sold", "units_lost",
            "fill_rate", "visit", "machine_on_hand", "stockroom_on_hand",
        ):
            self.assertIn(key, day0, f"Missing daily key: {key}")

        # Check KPIs
        kpis = result["kpis"]
        self.assertIn("score", kpis)
        self.assertIn("total_profit", kpis)

        # Check meta
        meta = result["meta"]
        self.assertEqual(meta["seed"], 42)
        self.assertEqual(meta["scenario"], "normal")
        self.assertEqual(meta["horizon"], 30)

    def test_run_simulation_stress_scenarios(self):
        from vendsim.web_runner import run_simulation

        cfg = EnvConfig(horizon=30)
        for sc in ("demand_surge", "vendor_disruption", "cash_shock"):
            result = run_simulation(
                cfg,
                BaselineProcurementAgent,
                BaselineReplenishmentAgent,
                seed=77,
                scenario_name=sc,
            )
            self.assertEqual(len(result["daily"]), 30)
            self.assertTrue(math.isfinite(result["kpis"]["score"]))


if __name__ == "__main__":
    unittest.main()
