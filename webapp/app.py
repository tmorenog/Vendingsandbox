"""Streamlit entrypoint for the Vending Machine Digital Ops Sandbox.

Run with:
    streamlit run webapp/app.py
"""
from __future__ import annotations

import streamlit as st

# Ensure src/ is importable (side-effect of importing utils_web)
import utils_web  # noqa: F401

st.set_page_config(
    page_title="VendSim -- Vending Machine Sandbox",
    page_icon=":shopping_cart:",
    layout="wide",
)

st.title("Vending Machine Digital Ops Sandbox")

st.markdown(
    """
Welcome to **VendSim** -- a supply-chain simulation for managing one vending
machine and its local stockroom.

### How to use this app

1. **Configure** -- Set simulation parameters (horizon, costs, constraints).
2. **Run Simulation** -- Choose agents, pick a scenario, and run.

Use the sidebar to navigate between pages.

---

**Student agents** must define two classes:

- `StudentProcurementAgent` with `act(self, obs: dict) -> dict`
- `StudentReplenishmentAgent` with `act(self, obs: dict) -> dict`

You can upload `.py` files or paste code directly in the Run page.
"""
)
