"""Shared helpers for the Streamlit web app.

Handles:
- Project path setup (so ``import vendsim`` and ``import agents`` work)
- Building an ``EnvConfig`` from session-state dicts
- Loading student agent code safely (security checks + dynamic import)
"""
from __future__ import annotations

import importlib
import importlib.util
import pathlib
import sys
import tempfile
import textwrap
from typing import Any, Dict, Optional, Tuple, Type
from uuid import uuid4

# ---------------------------------------------------------------------------
# Path setup -- must be called once at import time
# ---------------------------------------------------------------------------
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Now these imports are available everywhere that imports utils_web
from vendsim.config import EnvConfig  # noqa: E402
from vendsim.scenarios import ALL_SCENARIOS  # noqa: E402

# ---------------------------------------------------------------------------
# Default configuration dict (mirrors EnvConfig defaults)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: Dict[str, Any] = {
    "horizon_days": 180,
    "initial_cash": 1500.0,
    "max_po_lines_per_day": 5,
    "min_order_qty": 5,
    "max_visits_per_7d": 3,
    "max_units_per_visit": 60,
    "visit_fixed_cost": 25.0,
    "holding_cost_per_unit_day": 0.01,
    "stockout_penalty_per_unit": 0.50,
}

SCENARIO_NAMES = list(ALL_SCENARIOS.keys())

# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_env_config(cfg_dict: Dict[str, Any]) -> EnvConfig:
    """Build an ``EnvConfig`` from the session-state config dict."""
    return EnvConfig(
        horizon=int(cfg_dict.get("horizon_days", 180)),
        initial_cash=float(cfg_dict.get("initial_cash", 1500.0)),
        max_po_lines_per_day=int(cfg_dict.get("max_po_lines_per_day", 5)),
        min_order_qty=int(cfg_dict.get("min_order_qty", 5)),
        max_visits_per_7d=int(cfg_dict.get("max_visits_per_7d", 3)),
        max_units_per_visit=int(cfg_dict.get("max_units_per_visit", 60)),
        visit_fixed_cost=float(cfg_dict.get("visit_fixed_cost", 25.0)),
        holding_cost_per_unit_day=float(cfg_dict.get("holding_cost_per_unit_day", 0.01)),
        stockout_penalty_per_unit=float(cfg_dict.get("stockout_penalty_per_unit", 0.50)),
    )


# ---------------------------------------------------------------------------
# Baseline agent loaders
# ---------------------------------------------------------------------------

def load_baseline_agents() -> Tuple[Type, Type]:
    """Return (BaselineProcurementAgent, BaselineReplenishmentAgent) classes."""
    from agents.baseline_procurement import BaselineProcurementAgent
    from agents.baseline_replenishment import BaselineReplenishmentAgent
    return BaselineProcurementAgent, BaselineReplenishmentAgent


# ---------------------------------------------------------------------------
# Student code safety & dynamic import
# ---------------------------------------------------------------------------

FORBIDDEN_SUBSTRINGS = [
    "import os",
    "import sys",
    "subprocess",
    "socket",
    "open(",
    "eval",
    "exec",
    "__import__",
]


def check_student_code(code: str) -> Optional[str]:
    """Return an error message if *code* contains forbidden patterns, else None."""
    for pattern in FORBIDDEN_SUBSTRINGS:
        if pattern in code:
            return f"Forbidden pattern found: ``{pattern}``"
    return None


def _import_module_from_file(filepath: pathlib.Path, module_name: str):
    """Import a Python file as a module with a unique name."""
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec from {filepath}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_student_agents_from_code(
    procurement_code: str,
    replenishment_code: str,
) -> Tuple[Type, Type]:
    """Write student code to temp files, validate, and dynamically import.

    Returns
    -------
    (StudentProcurementAgent class, StudentReplenishmentAgent class)

    Raises
    ------
    ValueError  if code fails safety checks
    ImportError if required classes are not found
    """
    # Safety checks
    for label, code in [("procurement", procurement_code),
                        ("replenishment", replenishment_code)]:
        err = check_student_code(code)
        if err:
            raise ValueError(f"Student {label} code rejected: {err}")

    uid = uuid4().hex[:12]
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="vendsim_student_"))

    # Write procurement
    proc_path = tmpdir / "student_procurement.py"
    proc_path.write_text(procurement_code, encoding="utf-8")

    # Write replenishment
    rep_path = tmpdir / "student_replenishment.py"
    rep_path.write_text(replenishment_code, encoding="utf-8")

    # Import procurement
    proc_mod = _import_module_from_file(proc_path, f"student_proc_{uid}")
    if not hasattr(proc_mod, "StudentProcurementAgent"):
        raise ImportError(
            "student_procurement.py must define class ``StudentProcurementAgent``"
        )

    # Import replenishment
    rep_mod = _import_module_from_file(rep_path, f"student_rep_{uid}")
    if not hasattr(rep_mod, "StudentReplenishmentAgent"):
        raise ImportError(
            "student_replenishment.py must define class ``StudentReplenishmentAgent``"
        )

    return proc_mod.StudentProcurementAgent, rep_mod.StudentReplenishmentAgent


def load_student_agents_from_files(
    proc_file_bytes: bytes,
    rep_file_bytes: bytes,
) -> Tuple[Type, Type]:
    """Load student agents from uploaded file bytes."""
    procurement_code = proc_file_bytes.decode("utf-8")
    replenishment_code = rep_file_bytes.decode("utf-8")
    return load_student_agents_from_code(procurement_code, replenishment_code)
