"""Shared utilities for Vercel serverless Python functions.

NOT exposed as an API endpoint (leading underscore).
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import tempfile
from typing import Any, Dict, Optional, Tuple, Type
from uuid import uuid4

# ---------------------------------------------------------------------------
# Path setup -- add src/ so ``import vendsim`` and ``import agents`` work
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from vendsim.config import EnvConfig  # noqa: E402
from vendsim.web_runner import run_simulation  # noqa: E402

# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def read_body(handler) -> dict:
    """Read and parse JSON body from a BaseHTTPRequestHandler."""
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length)
    return json.loads(raw) if raw else {}


def send_json(handler, data: Any, status: int = 200) -> None:
    """Send a JSON response."""
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def send_cors(handler) -> None:
    """Handle CORS preflight."""
    handler.send_response(200)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_env_config(cfg: dict) -> EnvConfig:
    return EnvConfig(
        horizon=int(cfg.get("horizon_days", 180)),
        initial_cash=float(cfg.get("initial_cash", 1500.0)),
        max_po_lines_per_day=int(cfg.get("max_po_lines_per_day", 5)),
        min_order_qty=int(cfg.get("min_order_qty", 5)),
        max_visits_per_7d=int(cfg.get("max_visits_per_7d", 3)),
        max_units_per_visit=int(cfg.get("max_units_per_visit", 60)),
        visit_fixed_cost=float(cfg.get("visit_fixed_cost", 25.0)),
        holding_cost_per_unit_day=float(cfg.get("holding_cost_per_unit_day", 0.01)),
        stockout_penalty_per_unit=float(cfg.get("stockout_penalty_per_unit", 0.50)),
    )


# ---------------------------------------------------------------------------
# Agent loading
# ---------------------------------------------------------------------------

def load_baseline_agents() -> Tuple[Type, Type]:
    from agents.baseline_procurement import BaselineProcurementAgent
    from agents.baseline_replenishment import BaselineReplenishmentAgent
    return BaselineProcurementAgent, BaselineReplenishmentAgent


FORBIDDEN = [
    "import os", "import sys", "subprocess", "socket",
    "open(", "eval", "exec", "__import__",
]


def _check_code(code: str) -> Optional[str]:
    for pat in FORBIDDEN:
        if pat in code:
            return f"Forbidden pattern: {pat!r}"
    return None


def _import_from_file(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_student_agents(student_code: dict) -> Tuple[Type, Type]:
    """Load student agents from code strings.

    Parameters
    ----------
    student_code : dict with keys ``procurement`` and ``replenishment``

    Returns (ProcurementAgentClass, ReplenishmentAgentClass)
    """
    proc_code = student_code.get("procurement", "")
    rep_code = student_code.get("replenishment", "")

    for label, code in [("procurement", proc_code), ("replenishment", rep_code)]:
        err = _check_code(code)
        if err:
            raise ValueError(f"Student {label} code rejected: {err}")

    uid = uuid4().hex[:12]
    tmpdir = tempfile.mkdtemp(prefix="vendsim_")

    proc_path = os.path.join(tmpdir, "student_procurement.py")
    with open(proc_path, "w") as f:
        f.write(proc_code)

    rep_path = os.path.join(tmpdir, "student_replenishment.py")
    with open(rep_path, "w") as f:
        f.write(rep_code)

    proc_mod = _import_from_file(proc_path, f"student_proc_{uid}")
    if not hasattr(proc_mod, "StudentProcurementAgent"):
        raise ImportError("student_procurement.py must define StudentProcurementAgent")

    rep_mod = _import_from_file(rep_path, f"student_rep_{uid}")
    if not hasattr(rep_mod, "StudentReplenishmentAgent"):
        raise ImportError("student_replenishment.py must define StudentReplenishmentAgent")

    return proc_mod.StudentProcurementAgent, rep_mod.StudentReplenishmentAgent


def resolve_agents(body: dict) -> Tuple[Type, Type]:
    """Return (proc_cls, rep_cls) based on request body."""
    agent_type = body.get("agent_type", "baseline")
    if agent_type == "baseline":
        return load_baseline_agents()
    student_code = body.get("student_code")
    if not student_code:
        raise ValueError("student_code required when agent_type is not 'baseline'")
    return load_student_agents(student_code)
