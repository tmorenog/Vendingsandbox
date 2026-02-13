"""Run Simulation page -- agent selection, run controls, and charts."""
from __future__ import annotations

import traceback
from typing import Any, Dict, List, Tuple, Type

import matplotlib.pyplot as plt
import streamlit as st

# Ensure src/ is on the path
import sys, pathlib  # noqa: E401
_webapp = pathlib.Path(__file__).resolve().parent.parent
if str(_webapp) not in sys.path:
    sys.path.insert(0, str(_webapp))

from utils_web import (  # noqa: E402
    DEFAULT_CONFIG,
    SCENARIO_NAMES,
    build_env_config,
    load_baseline_agents,
    load_student_agents_from_code,
    load_student_agents_from_files,
)
from vendsim.web_runner import run_simulation  # noqa: E402

st.header("Run Simulation")

# ── Ensure config exists ──────────────────────────────────────────────────
if "config_dict" not in st.session_state:
    st.session_state["config_dict"] = dict(DEFAULT_CONFIG)
cfg_dict = st.session_state["config_dict"]

# ══════════════════════════════════════════════════════════════════════════
# A) Agent selection
# ══════════════════════════════════════════════════════════════════════════
st.subheader("Agent selection")

agent_mode = st.radio(
    "Agent source",
    ["Baseline", "Student Upload", "Student Paste"],
    horizontal=True,
)

proc_cls: Type | None = None
rep_cls: Type | None = None
agent_error: str | None = None

if agent_mode == "Baseline":
    proc_cls, rep_cls = load_baseline_agents()

elif agent_mode == "Student Upload":
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        proc_file = st.file_uploader(
            "student_procurement.py", type=["py"], key="proc_upload",
        )
    with col_up2:
        rep_file = st.file_uploader(
            "student_replenishment.py", type=["py"], key="rep_upload",
        )
    if proc_file and rep_file:
        try:
            proc_cls, rep_cls = load_student_agents_from_files(
                proc_file.getvalue(), rep_file.getvalue(),
            )
            st.success("Student agents loaded successfully.")
        except Exception as exc:
            agent_error = str(exc)
            st.error(f"Failed to load student agents: {agent_error}")
    else:
        st.info("Upload both .py files to continue.")

elif agent_mode == "Student Paste":
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        proc_code = st.text_area(
            "student_procurement.py",
            height=300,
            key="proc_paste",
            placeholder="class StudentProcurementAgent:\n    def act(self, obs):\n        ...",
        )
    with col_p2:
        rep_code = st.text_area(
            "student_replenishment.py",
            height=300,
            key="rep_paste",
            placeholder="class StudentReplenishmentAgent:\n    def act(self, obs):\n        ...",
        )
    if proc_code.strip() and rep_code.strip():
        try:
            proc_cls, rep_cls = load_student_agents_from_code(proc_code, rep_code)
            st.success("Student agents loaded successfully.")
        except Exception as exc:
            agent_error = str(exc)
            st.error(f"Failed to load student agents: {agent_error}")
    else:
        st.info("Paste code for both agents to continue.")

# ══════════════════════════════════════════════════════════════════════════
# B) Scenario selection
# ══════════════════════════════════════════════════════════════════════════
st.subheader("Scenario")
scenario_name = st.selectbox("Scenario", SCENARIO_NAMES, index=0)

# ══════════════════════════════════════════════════════════════════════════
# C) Run controls
# ══════════════════════════════════════════════════════════════════════════
st.subheader("Run controls")
run_mode = st.radio("Run mode", ["Single run", "Evaluate (N seeds)"], horizontal=True)

if run_mode == "Single run":
    seed = st.number_input("Seed", min_value=0, max_value=999_999, value=42)
else:
    eval_col1, eval_col2 = st.columns(2)
    with eval_col1:
        n_seeds = st.number_input("Number of seeds", min_value=1, max_value=500, value=20)
    with eval_col2:
        seed_start = st.number_input("Starting seed", min_value=0, max_value=999_999, value=0)

run_button = st.button(
    "Run", type="primary", disabled=(proc_cls is None or rep_cls is None),
)

# ══════════════════════════════════════════════════════════════════════════
# D) Execution & Outputs
# ══════════════════════════════════════════════════════════════════════════

def _run_single(
    proc: Type, rep: Type, cfg_d: dict, sc: str, s: int,
) -> Dict[str, Any]:
    config = build_env_config(cfg_d)
    return run_simulation(config, proc, rep, seed=s, scenario_name=sc)


# ── Chart helpers ─────────────────────────────────────────────────────────

def _cumulative(values: List[float]) -> List[float]:
    out: list[float] = []
    total = 0.0
    for v in values:
        total += v
        out.append(total)
    return out


def plot_daily_charts(daily: List[dict], meta: dict) -> None:
    """Render all daily charts using matplotlib."""
    days = [d["day"] for d in daily]
    profits = [d["profit"] for d in daily]
    cum_profits = _cumulative(profits)
    cash = [d["cash"] for d in daily]
    fill_rates = [d["fill_rate"] for d in daily]
    sold = [d["units_sold"] for d in daily]
    lost = [d["units_lost"] for d in daily]

    # --- Row 1: Profit charts ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    ax = axes[0]
    ax.bar(days, profits, width=1.0, color="steelblue", alpha=0.7)
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.set_title("Daily Profit")
    ax.set_xlabel("Day")
    ax.set_ylabel("Profit ($)")

    ax = axes[1]
    ax.plot(days, cum_profits, color="darkgreen", linewidth=1.5)
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.set_title("Cumulative Profit")
    ax.set_xlabel("Day")
    ax.set_ylabel("Cumulative ($)")
    ax.fill_between(days, cum_profits, alpha=0.15, color="green")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # --- Row 2: Cash & Fill Rate ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    ax = axes[0]
    ax.plot(days, cash, color="darkorange", linewidth=1.5)
    ax.set_title("Cash on Hand")
    ax.set_xlabel("Day")
    ax.set_ylabel("Cash ($)")
    ax.fill_between(days, cash, alpha=0.15, color="orange")

    ax = axes[1]
    ax.plot(days, fill_rates, color="teal", linewidth=1.5)
    ax.axhline(0.70, color="red", linestyle="--", linewidth=0.8, label="Churn threshold (70%)")
    ax.set_title("Daily Fill Rate")
    ax.set_xlabel("Day")
    ax.set_ylabel("Fill Rate")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # --- Row 3: Units sold / lost ---
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.bar(days, sold, width=1.0, color="mediumseagreen", alpha=0.7, label="Sold")
    ax.bar(days, [-l for l in lost], width=1.0, color="indianred", alpha=0.7, label="Lost")
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.set_title("Units Sold vs Lost Sales")
    ax.set_xlabel("Day")
    ax.set_ylabel("Units")
    ax.legend(fontsize=9)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # --- Row 4: Inventory trajectories (user selects SKUs) ---
    all_skus = sorted(daily[0]["machine_on_hand"].keys())
    selected_skus = st.multiselect(
        "Select SKUs for inventory chart",
        all_skus,
        default=all_skus[:3],
        key="sku_select_inv",
    )
    if selected_skus:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for sku in selected_skus:
            machine_inv = [d["machine_on_hand"].get(sku, 0) for d in daily]
            stockroom_inv = [d["stockroom_on_hand"].get(sku, 0) for d in daily]
            axes[0].plot(days, machine_inv, linewidth=1.2, label=sku)
            axes[1].plot(days, stockroom_inv, linewidth=1.2, label=sku)

        axes[0].set_title("Machine Inventory")
        axes[0].set_xlabel("Day")
        axes[0].set_ylabel("Units")
        axes[0].legend(fontsize=7, ncol=2)

        axes[1].set_title("Stockroom Inventory")
        axes[1].set_xlabel("Day")
        axes[1].set_ylabel("Units")
        axes[1].legend(fontsize=7, ncol=2)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)


def show_kpi_cards(kpis: dict) -> None:
    """Display KPI metric cards."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Profit", f"${kpis['total_profit']:,.2f}")
    c2.metric("Fill Rate", f"{kpis['fill_rate']:.2%}")
    c3.metric("Score", f"{kpis['score']:.4f}")
    c4.metric("Visits", f"{kpis['visits_total']}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Revenue", f"${kpis['total_revenue']:,.2f}")
    c6.metric("Procurement Cost", f"${kpis['total_procurement_cost']:,.2f}")
    c7.metric("Holding Cost", f"${kpis['total_holding_cost']:,.2f}")
    c8.metric("Stockout Penalty", f"${kpis['total_stockout_penalty']:,.2f}")


# ── Execution ─────────────────────────────────────────────────────────────

if run_button and proc_cls is not None and rep_cls is not None:
    try:
        if run_mode == "Single run":
            with st.spinner(f"Running simulation (seed={seed}) ..."):
                result = _run_single(proc_cls, rep_cls, cfg_dict, scenario_name, seed)

            st.subheader("KPI Summary")
            show_kpi_cards(result["kpis"])

            st.subheader("Daily Charts")
            plot_daily_charts(result["daily"], result["meta"])

        else:  # Evaluate mode
            seeds = list(range(seed_start, seed_start + n_seeds))
            all_results: List[Dict[str, Any]] = []
            progress = st.progress(0, text="Running evaluations ...")

            for i, s in enumerate(seeds):
                r = _run_single(proc_cls, rep_cls, cfg_dict, scenario_name, s)
                all_results.append(r)
                progress.progress((i + 1) / len(seeds), text=f"Seed {s} done ({i+1}/{len(seeds)})")

            progress.empty()

            # Build summary table
            rows = []
            for r in all_results:
                k = r["kpis"]
                rows.append({
                    "seed": r["meta"]["seed"],
                    "profit": k["total_profit"],
                    "fill_rate": k["fill_rate"],
                    "visits": k["visits_total"],
                    "score": k["score"],
                    "revenue": k["total_revenue"],
                    "procurement": k["total_procurement_cost"],
                    "holding": k["total_holding_cost"],
                    "stockout_pen": k["total_stockout_penalty"],
                })

            st.subheader("Per-Seed Results")
            st.dataframe(rows, use_container_width=True)

            # Averages
            n = len(rows)
            avg_profit = sum(r["profit"] for r in rows) / n
            avg_fill = sum(r["fill_rate"] for r in rows) / n
            avg_score = sum(r["score"] for r in rows) / n
            avg_visits = sum(r["visits"] for r in rows) / n

            st.subheader("Average KPIs")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Avg Profit", f"${avg_profit:,.2f}")
            mc2.metric("Avg Fill Rate", f"{avg_fill:.2%}")
            mc3.metric("Avg Score", f"{avg_score:.4f}")
            mc4.metric("Avg Visits", f"{avg_visits:.1f}")

            # Bar chart of scores
            fig, ax = plt.subplots(figsize=(14, 4))
            bar_seeds = [r["seed"] for r in rows]
            bar_scores = [r["score"] for r in rows]
            ax.bar(bar_seeds, bar_scores, color="steelblue", alpha=0.8)
            ax.axhline(avg_score, color="red", linestyle="--", linewidth=1, label=f"Mean={avg_score:.4f}")
            ax.set_title("Score by Seed")
            ax.set_xlabel("Seed")
            ax.set_ylabel("Score")
            ax.legend(fontsize=9)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

            # Show daily charts for representative seed (median score)
            sorted_results = sorted(all_results, key=lambda r: r["kpis"]["score"])
            median_result = sorted_results[len(sorted_results) // 2]
            st.subheader(
                f"Daily Charts -- representative seed {median_result['meta']['seed']} "
                f"(median score = {median_result['kpis']['score']:.4f})"
            )
            plot_daily_charts(median_result["daily"], median_result["meta"])

    except Exception:
        st.error("Simulation failed. See traceback below.")
        with st.expander("Traceback", expanded=True):
            st.code(traceback.format_exc())
