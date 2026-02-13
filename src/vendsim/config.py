"""Configuration dataclasses and default parameters for VendSim."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# SKU catalogue
# ---------------------------------------------------------------------------
DEFAULT_SKUS: List[str] = [
    "SKU_01", "SKU_02", "SKU_03", "SKU_04",
    "SKU_05", "SKU_06", "SKU_07", "SKU_08",
    "SKU_09", "SKU_10", "SKU_11", "SKU_12",
]

# Retail prices per unit (students see these)
DEFAULT_PRICES: Dict[str, float] = {
    "SKU_01": 2.50, "SKU_02": 1.75, "SKU_03": 3.00, "SKU_04": 2.00,
    "SKU_05": 1.50, "SKU_06": 2.25, "SKU_07": 3.50, "SKU_08": 1.25,
    "SKU_09": 2.75, "SKU_10": 2.00, "SKU_11": 1.50, "SKU_12": 3.25,
}

# Customer preference weights (higher = more popular)
DEFAULT_PREFERENCE_WEIGHTS: Dict[str, float] = {
    "SKU_01": 1.5, "SKU_02": 1.0, "SKU_03": 1.8, "SKU_04": 1.2,
    "SKU_05": 0.8, "SKU_06": 1.1, "SKU_07": 2.0, "SKU_08": 0.7,
    "SKU_09": 1.3, "SKU_10": 1.0, "SKU_11": 0.6, "SKU_12": 1.6,
}


# ---------------------------------------------------------------------------
# Vendor config
# ---------------------------------------------------------------------------
@dataclass
class VendorProfile:
    """Configuration for a single vendor."""
    name: str
    # Base cost per SKU (multiplied by SKU factor)
    base_cost_factor: float          # multiplied with sku base cost
    # Fill probability by regime
    fill_prob_normal: float
    fill_prob_disrupted: float
    # Lead-time distributions (day counts, uniform choice)
    lead_days_normal: List[int] = field(default_factory=lambda: [2, 3])
    lead_days_disrupted: List[int] = field(default_factory=lambda: [4, 5, 6])
    lead_days_expedite: List[int] = field(default_factory=lambda: [1, 2])
    # Expedite cost multiplier
    expedite_multiplier: float = 1.0
    # Disrupted regime cost multiplier
    disrupted_cost_multiplier: float = 1.0
    # Markov transition probs: P(DISRUPTED | NORMAL), P(NORMAL | DISRUPTED)
    p_normal_to_disrupted: float = 0.03
    p_disrupted_to_normal: float = 0.15
    # Daily capacity (max confirmed units across all PO lines)
    daily_capacity: int = 200
    # Cost noise half-width (uniform +/-)
    cost_noise_half: float = 0.02


def default_vendor_profiles() -> Dict[str, VendorProfile]:
    """Return the three default vendor profiles."""
    return {
        "A": VendorProfile(
            name="A",
            base_cost_factor=0.40,         # cheapest
            fill_prob_normal=0.85,
            fill_prob_disrupted=0.45,
            lead_days_normal=[2, 3, 3],
            lead_days_disrupted=[5, 6, 7, 8],
            lead_days_expedite=[2, 3],
            expedite_multiplier=1.30,
            disrupted_cost_multiplier=1.25,
            p_normal_to_disrupted=0.07,    # disrupts more often
            p_disrupted_to_normal=0.12,
            daily_capacity=180,
            cost_noise_half=0.04,
        ),
        "B": VendorProfile(
            name="B",
            base_cost_factor=0.55,         # priciest
            fill_prob_normal=0.95,
            fill_prob_disrupted=0.75,
            lead_days_normal=[2, 2, 3],
            lead_days_disrupted=[3, 4, 4],
            lead_days_expedite=[1, 2],
            expedite_multiplier=1.25,
            disrupted_cost_multiplier=1.10,
            p_normal_to_disrupted=0.02,    # rarely disrupts
            p_disrupted_to_normal=0.25,
            daily_capacity=250,
            cost_noise_half=0.02,
        ),
        "C": VendorProfile(
            name="C",
            base_cost_factor=0.48,         # mid-range
            fill_prob_normal=0.90,
            fill_prob_disrupted=0.55,
            lead_days_normal=[2, 3, 3],
            lead_days_disrupted=[4, 5, 6],
            lead_days_expedite=[1, 1, 2],  # good expedite
            expedite_multiplier=1.20,
            disrupted_cost_multiplier=1.15,
            p_normal_to_disrupted=0.04,
            p_disrupted_to_normal=0.18,
            daily_capacity=200,
            cost_noise_half=0.03,
        ),
    }


# SKU base costs (used with vendor base_cost_factor)
DEFAULT_SKU_BASE_COSTS: Dict[str, float] = {
    "SKU_01": 1.20, "SKU_02": 0.80, "SKU_03": 1.50, "SKU_04": 1.00,
    "SKU_05": 0.70, "SKU_06": 1.10, "SKU_07": 1.80, "SKU_08": 0.55,
    "SKU_09": 1.30, "SKU_10": 0.90, "SKU_11": 0.65, "SKU_12": 1.60,
}


# ---------------------------------------------------------------------------
# Customer config
# ---------------------------------------------------------------------------
@dataclass
class CustomerConfig:
    """Parameters governing customer arrival and behaviour."""
    base_arrival_rate: float = 25.0       # mean customers per day
    # Day-of-week multipliers (Mon=0 .. Sun=6)
    dow_multipliers: List[float] = field(
        default_factory=lambda: [0.9, 0.9, 1.0, 1.0, 1.1, 1.2, 0.8]
    )
    p_substitute: float = 0.40           # prob customer tries substitute
    max_substitute_tries: int = 3
    # Memory / churn
    churn_fill_threshold: float = 0.70   # 7d fill rate below this => churn
    churn_decay: float = 0.97            # multiplier when fill rate low
    recovery_rate: float = 1.005         # multiplier when fill rate high (bounded)


# ---------------------------------------------------------------------------
# Environment / cost config
# ---------------------------------------------------------------------------
@dataclass
class EnvConfig:
    """Master configuration for the simulation environment."""
    skus: List[str] = field(default_factory=lambda: list(DEFAULT_SKUS))
    prices: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_PRICES))
    preference_weights: Dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PREFERENCE_WEIGHTS)
    )
    sku_base_costs: Dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SKU_BASE_COSTS)
    )
    vendor_profiles: Dict[str, VendorProfile] = field(
        default_factory=default_vendor_profiles
    )
    customer: CustomerConfig = field(default_factory=CustomerConfig)

    horizon: int = 180

    # Capacities
    capacity_machine: int = 15           # per SKU
    capacity_stockroom: int = 200        # per SKU

    # Initial inventories
    initial_machine_frac: float = 0.50   # fraction of machine capacity
    initial_stockroom_units: int = 30    # per SKU
    initial_cash: float = 1500.0

    # Constraints
    max_po_lines_per_day: int = 5
    min_order_qty: int = 5
    cash_must_cover_orders: bool = True
    max_visits_per_7d: int = 3
    max_units_per_visit: int = 60

    # Cost model
    visit_fixed_cost: float = 25.0
    visit_handling_cost_per_unit: float = 0.05
    holding_cost_per_unit_day: float = 0.01
    stockout_penalty_per_unit: float = 0.50
    waste_enabled: bool = False          # off by default

    # Demand regime multiplier (scenarios override this)
    demand_regime_multiplier: float = 1.0
