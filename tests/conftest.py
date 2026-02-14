"""Shared pytest fixtures for meapy test suite.

Fixtures defined here are available to both ``tests/unit/`` and
``tests/integration/`` without additional imports.
"""

from __future__ import annotations

import numpy as np
import pytest

from meapy.pump import (
    ExponentialLevelModel,
    LinearFlowModel,
    fit_exponential_level_model,
    fit_linear_flowrate_model,
)

# ---------------------------------------------------------------------------
# Heat transfer fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def c100_inputs() -> dict:
    """Representative steady-state data point for heat exchanger C100.

    Values correspond to Experiment B, data point 3, as recorded in the
    Imperial College pilot-plant runs (Hale, 2025, Appendix H.5).

    Returns:
        Dictionary of keyword arguments suitable for
        :func:`meapy.heat_transfer.analyse_exchanger`.
    """
    return {
        "mea_flow_kg_h": 900.0,
        "cp_mea_j_kg_k": 3940.0,
        "t_mea_in_c": 85.0,
        "t_mea_out_c": 42.0,
        "utility_flow_kg_h": 800.0,
        "cp_utility_j_kg_k": 3940.0,
        "t_utility_in_c": 30.0,
        "t_utility_out_c": 68.0,
        "area_m2": 0.30,
    }


@pytest.fixture
def c200_inputs() -> dict:
    """Representative steady-state data point for heat exchanger C200 (trim cooler).

    Returns:
        Dictionary of keyword arguments suitable for
        :func:`meapy.heat_transfer.analyse_exchanger`.
    """
    return {
        "mea_flow_kg_h": 900.0,
        "cp_mea_j_kg_k": 3940.0,
        "t_mea_in_c": 42.0,
        "t_mea_out_c": 25.0,
        "utility_flow_kg_h": 722.0,
        "cp_utility_j_kg_k": 4182.0,  # water
        "t_utility_in_c": 15.0,
        "t_utility_out_c": 30.0,
        "area_m2": 0.25,
    }


# ---------------------------------------------------------------------------
# Mass transfer fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def experiment_a_composition() -> dict:
    """CO₂ vol% readings from Experiment A (lowest MEA flowrate).

    Sampling port heights and concentrations taken from Figure 5.2.1
    of the main pilot-plant report.
    """
    return {
        "heights_m": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
        "co2_vol_pct": [14.0, 11.5, 9.0, 6.0, 3.5, 1.5],
    }


@pytest.fixture
def experiment_c_composition() -> dict:
    """CO₂ vol% readings from Experiment C (highest MEA flowrate)."""
    return {
        "heights_m": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
        "co2_vol_pct": [14.0, 9.0, 5.5, 3.0, 1.5, 0.8],
    }


# ---------------------------------------------------------------------------
# Pump commissioning fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def commissioning_speeds() -> np.ndarray:
    """Pump speed set-points used during J100 commissioning."""
    return np.array([10.0, 20.0, 30.0, 40.0, 50.0, 53.0], dtype=float)


@pytest.fixture
def commissioning_levels() -> np.ndarray:
    """Steady-state MEA levels from LT101 at each commissioning speed."""
    return np.array([80.1, 65.3, 52.0, 38.7, 24.1, 15.0], dtype=float)


@pytest.fixture
def commissioning_flows() -> np.ndarray:
    """Steady-state flowrates from FT103 at each commissioning speed."""
    return np.array([177.5, 365.2, 552.8, 740.4, 927.0, 980.1], dtype=float)


@pytest.fixture
def level_model(commissioning_speeds, commissioning_levels) -> ExponentialLevelModel:
    """Fitted exponential level model from commissioning data."""
    return fit_exponential_level_model(commissioning_speeds, commissioning_levels)


@pytest.fixture
def flow_model(commissioning_speeds, commissioning_flows) -> LinearFlowModel:
    """Fitted linear flowrate model from commissioning data."""
    return fit_linear_flowrate_model(commissioning_speeds, commissioning_flows)
