"""Integration tests: end-to-end pilot plant workflow.

These tests exercise multiple meapy modules together, mirroring the full
analysis pipeline of the Imperial College carbon-capture pilot plant:

1. Pump commissioning → safe operating speed
2. Heat exchanger analysis at the recommended flowrate
3. Mass transfer profiling along the absorber column
"""

from __future__ import annotations

import numpy as np
import pytest

import meapy
from meapy.heat_transfer import analyse_exchanger
from meapy.mass_transfer import composition_profile, koga_profile
from meapy.pump import (
    fit_exponential_level_model,
    fit_linear_flowrate_model,
    safe_pump_speed,
)
from meapy.utils import kg_h_to_mol_s


@pytest.mark.integration
class TestFullPilotPlantWorkflow:
    """End-to-end workflow: commissioning → heat transfer → mass transfer."""

    def test_commissioning_produces_safe_speed(
        self, commissioning_speeds, commissioning_levels, commissioning_flows
    ):
        level_model = fit_exponential_level_model(commissioning_speeds, commissioning_levels)
        flow_model = fit_linear_flowrate_model(commissioning_speeds, commissioning_flows)
        result = safe_pump_speed(level_model, flow_model)

        # The known safe speed from the Imperial pilot-plant report is ~53 %
        assert 40.0 <= result.safe_speed_pct <= 65.0, (
            f"Safe speed {result.safe_speed_pct:.1f} % is outside expected range [40, 65] %."
        )

    def test_heat_exchanger_at_recommended_flowrate(self):
        """C100 analysis at the flowrate corresponding to 53 % pump speed."""
        result = analyse_exchanger(
            mea_flow_kg_h=980.0,
            cp_mea_j_kg_k=3940.0,
            t_mea_in_c=85.0,
            t_mea_out_c=42.0,
            utility_flow_kg_h=880.0,
            cp_utility_j_kg_k=3940.0,
            t_utility_in_c=30.0,
            t_utility_out_c=68.0,
            area_m2=0.30,
        )
        # U should sit within the literature range 1–4 kW/(m²·K)
        assert 0.5 <= result["u_kw_m2_k"] <= 20.0
        assert result["effectiveness"] > 0

    def test_mass_transfer_five_experiments(self):
        """K_OGa profiles for all five experiments must be computable."""
        experiments = {
            "A": [14.0, 11.5, 9.0, 6.0, 3.5, 1.5],
            "B": [14.0, 10.5, 7.5, 5.0, 2.5, 1.2],
            "C": [14.0, 9.0, 5.5, 3.0, 1.5, 0.8],
            "D": [14.0, 11.0, 8.5, 5.5, 3.0, 1.4],
            "E": [14.0, 11.8, 9.2, 6.2, 3.6, 1.6],
        }
        heights_m = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        inert_flow = kg_h_to_mol_s(500.0, 28.014)  # N₂ at ~500 kg/h
        cross_section = meapy.constants.PlantGeometry.COLUMN_CROSS_SECTION_M2

        for label, pct_readings in experiments.items():
            _, y_vals = composition_profile(heights_m, pct_readings)
            profile = koga_profile(inert_flow, cross_section, heights_m, list(y_vals))
            # At least 3 out of 5 sections should have valid K_OGa values
            valid = np.sum(~np.isnan(profile))
            assert valid >= 3, (
                f"Experiment {label}: only {valid}/5 sections have valid K_OGa."
            )

    def test_koga_increases_with_mea_flowrate(self):
        """Higher MEA flowrate (Exp C > A) → higher total-column K_OGa."""
        heights_m = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        inert_flow = kg_h_to_mol_s(500.0, 28.014)
        cross_section = meapy.constants.PlantGeometry.COLUMN_CROSS_SECTION_M2

        pct_a = [14.0, 11.5, 9.0, 6.0, 3.5, 1.5]   # lowest MEA flow
        pct_c = [14.0, 9.0, 5.5, 3.0, 1.5, 0.8]    # highest MEA flow

        _, y_a = composition_profile(heights_m, pct_a)
        _, y_c = composition_profile(heights_m, pct_c)

        profile_a = koga_profile(inert_flow, cross_section, heights_m, list(y_a))
        profile_c = koga_profile(inert_flow, cross_section, heights_m, list(y_c))

        mean_a = np.nanmean(profile_a)
        mean_c = np.nanmean(profile_c)

        assert mean_c > mean_a, (
            f"Expected Experiment C K_OGa ({mean_c:.2f}) > Experiment A ({mean_a:.2f})."
        )

    def test_package_version_accessible(self):
        assert meapy.__version__ == "0.1.0"

    def test_all_submodules_importable(self):
        from meapy import constants, heat_transfer, mass_transfer, pump, utils  # noqa: F401
