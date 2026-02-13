"""Configure simulation parameters."""
from __future__ import annotations

import streamlit as st

# Ensure src/ is on the path
import sys, pathlib  # noqa: E401,E402
_webapp = pathlib.Path(__file__).resolve().parent.parent
if str(_webapp) not in sys.path:
    sys.path.insert(0, str(_webapp))

from utils_web import DEFAULT_CONFIG  # noqa: E402

st.header("Simulation Configuration")

# Initialise session state with defaults
if "config_dict" not in st.session_state:
    st.session_state["config_dict"] = dict(DEFAULT_CONFIG)

cfg = st.session_state["config_dict"]

# --- Layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("General")
    cfg["horizon_days"] = st.number_input(
        "Horizon (days)", min_value=10, max_value=730, value=int(cfg["horizon_days"]), step=10,
    )
    cfg["initial_cash"] = st.number_input(
        "Initial cash ($)", min_value=0.0, max_value=100_000.0,
        value=float(cfg["initial_cash"]), step=100.0, format="%.2f",
    )

    st.subheader("Procurement constraints")
    cfg["max_po_lines_per_day"] = st.number_input(
        "Max PO lines / day", min_value=1, max_value=50, value=int(cfg["max_po_lines_per_day"]),
    )
    cfg["min_order_qty"] = st.number_input(
        "Min order qty", min_value=1, max_value=100, value=int(cfg["min_order_qty"]),
    )

with col2:
    st.subheader("Replenishment constraints")
    cfg["max_visits_per_7d"] = st.number_input(
        "Max visits / 7 days", min_value=1, max_value=14, value=int(cfg["max_visits_per_7d"]),
    )
    cfg["max_units_per_visit"] = st.number_input(
        "Max units / visit", min_value=1, max_value=500, value=int(cfg["max_units_per_visit"]),
    )

    st.subheader("Cost model")
    cfg["visit_fixed_cost"] = st.number_input(
        "Visit fixed cost ($)", min_value=0.0, max_value=500.0,
        value=float(cfg["visit_fixed_cost"]), step=5.0, format="%.2f",
    )
    cfg["holding_cost_per_unit_day"] = st.number_input(
        "Holding cost ($/unit/day)", min_value=0.0, max_value=1.0,
        value=float(cfg["holding_cost_per_unit_day"]), step=0.005, format="%.4f",
    )
    cfg["stockout_penalty_per_unit"] = st.number_input(
        "Stockout penalty ($/unit)", min_value=0.0, max_value=10.0,
        value=float(cfg["stockout_penalty_per_unit"]), step=0.10, format="%.2f",
    )

st.divider()

if st.button("Reset to defaults"):
    st.session_state["config_dict"] = dict(DEFAULT_CONFIG)
    st.rerun()

st.success("Configuration saved to session. Go to **Run Simulation** to launch.")
st.json(cfg)
