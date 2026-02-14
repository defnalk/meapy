"""Unit tests for meapy.mass_transfer."""

from __future__ import annotations

import math

import numpy as np
import pytest

from meapy.mass_transfer import (
    absorption_factor,
    composition_profile,
    hog,
    koga_from_flux,
    koga_profile,
    mole_fraction_to_ratio,
    mole_ratio_to_fraction,
    ntu_og,
)

# ---------------------------------------------------------------------------
# Mole fraction / ratio conversions
# ---------------------------------------------------------------------------


class TestMoleFractionConversions:
    @pytest.mark.parametrize(
        "y,expected_Y",
        [
            (0.0, 0.0),
            (0.5, 1.0),
            (0.1, 0.1 / 0.9),
            (0.14, 0.14 / 0.86),
        ],
    )
    def test_fraction_to_ratio(self, y, expected_Y):
        assert mole_fraction_to_ratio(y) == pytest.approx(expected_Y, rel=1e-6)

    @pytest.mark.parametrize(
        "Y,expected_y",
        [
            (0.0, 0.0),
            (1.0, 0.5),
            (0.1 / 0.9, 0.1),
        ],
    )
    def test_ratio_to_fraction(self, Y, expected_y):
        assert mole_ratio_to_fraction(Y) == pytest.approx(expected_y, rel=1e-6)

    def test_round_trip(self):
        for y in [0.01, 0.05, 0.10, 0.15, 0.20]:
            assert mole_ratio_to_fraction(mole_fraction_to_ratio(y)) == pytest.approx(y, rel=1e-9)

    @pytest.mark.parametrize("y", [-0.1, 1.0, 1.5])
    def test_fraction_to_ratio_invalid(self, y):
        with pytest.raises(ValueError):
            mole_fraction_to_ratio(y)

    def test_ratio_to_fraction_negative_raises(self):
        with pytest.raises(ValueError):
            mole_ratio_to_fraction(-0.1)


# ---------------------------------------------------------------------------
# koga_from_flux
# ---------------------------------------------------------------------------


class TestKOGaFromFlux:
    def test_positive_result(self):
        koga = koga_from_flux(
            inert_gas_flow_mol_s=0.012,
            cross_section_m2=7.854e-3,
            packed_height_m=1.0,
            y_bottom=0.14,
            y_top=0.02,
        )
        assert koga > 0

    def test_higher_separation_gives_higher_koga(self):
        # Same conditions, larger (y_bottom − y_top) → more driving force
        k1 = koga_from_flux(0.012, 7.854e-3, 1.0, 0.14, 0.02)
        k2 = koga_from_flux(0.012, 7.854e-3, 1.0, 0.14, 0.07)  # less separation
        assert k1 > k2

    def test_taller_column_gives_lower_koga(self):
        # Same inlet/outlet fractions, taller section → K_OGa per unit height falls
        k1 = koga_from_flux(0.012, 7.854e-3, 1.0, 0.14, 0.02)
        k2 = koga_from_flux(0.012, 7.854e-3, 2.0, 0.14, 0.02)
        assert k1 > k2

    @pytest.mark.parametrize(
        "y_bot,y_top",
        [
            (0.02, 0.14),  # reversed — y_top > y_bottom
            (0.05, 0.05),  # equal — no absorption
        ],
    )
    def test_no_absorption_raises(self, y_bot, y_top):
        with pytest.raises(ValueError):
            koga_from_flux(0.012, 7.854e-3, 1.0, y_bot, y_top)

    @pytest.mark.parametrize(
        "flow,area,height",
        [
            (0.0, 7.854e-3, 1.0),
            (-0.01, 7.854e-3, 1.0),
            (0.012, 0.0, 1.0),
            (0.012, 7.854e-3, 0.0),
        ],
    )
    def test_nonpositive_geometry_raises(self, flow, area, height):
        with pytest.raises(ValueError):
            koga_from_flux(flow, area, height, 0.14, 0.02)


# ---------------------------------------------------------------------------
# koga_profile
# ---------------------------------------------------------------------------


class TestKOGaProfile:
    def test_profile_length_correct(self, experiment_a_composition):
        heights = experiment_a_composition["heights_m"]
        y_vals = [v / 100 for v in experiment_a_composition["co2_vol_pct"]]
        result = koga_profile(0.012, 7.854e-3, heights, y_vals)
        assert len(result) == len(heights) - 1

    def test_nan_for_inverted_sections(self):
        heights = [0.5, 1.5, 2.5]
        # y values that imply upward mass transfer in section 1
        y_vals = [0.05, 0.10, 0.02]
        result = koga_profile(0.012, 7.854e-3, heights, y_vals)
        assert np.isnan(result[0])
        assert not np.isnan(result[1])

    def test_mismatched_length_raises(self):
        with pytest.raises(ValueError):
            koga_profile(0.012, 7.854e-3, [0.5, 1.5, 2.5], [0.14, 0.09])

    def test_single_height_raises(self):
        with pytest.raises(ValueError):
            koga_profile(0.012, 7.854e-3, [0.5], [0.14])


# ---------------------------------------------------------------------------
# composition_profile
# ---------------------------------------------------------------------------


class TestCompositionProfile:
    def test_shape(self, experiment_a_composition):
        h, y = composition_profile(
            experiment_a_composition["heights_m"],
            experiment_a_composition["co2_vol_pct"],
        )
        assert h.shape == y.shape == (6,)

    def test_decreasing_along_column(self, experiment_a_composition):
        _, y = composition_profile(
            experiment_a_composition["heights_m"],
            experiment_a_composition["co2_vol_pct"],
        )
        # CO₂ should decrease from bottom to top
        assert all(y[i] >= y[i + 1] for i in range(len(y) - 1))

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match="100"):
            composition_profile([0.5], [105.0])

    def test_negative_concentration_raises(self):
        with pytest.raises(ValueError):
            composition_profile([0.5], [-1.0])


# ---------------------------------------------------------------------------
# ntu_og
# ---------------------------------------------------------------------------


class TestNTUOG:
    def test_positive_result(self):
        val = ntu_og(0.14, 0.02)
        assert val > 0

    def test_matches_log_ratio(self):
        Y_b = mole_fraction_to_ratio(0.14)
        Y_t = mole_fraction_to_ratio(0.02)
        expected = math.log(Y_b / Y_t)
        assert ntu_og(0.14, 0.02) == pytest.approx(expected, rel=1e-6)

    def test_invalid_fractions_raise(self):
        with pytest.raises(ValueError):
            ntu_og(0.02, 0.14)  # y_top ≥ y_bottom


# ---------------------------------------------------------------------------
# hog
# ---------------------------------------------------------------------------


class TestHOG:
    def test_units_consistent(self):
        koga = 12.0  # mol/(m³·s)
        flux = 1.5  # mol/(m²·s)
        assert hog(koga, flux) == pytest.approx(flux / koga)

    def test_zero_koga_raises(self):
        with pytest.raises(ValueError):
            hog(0.0, 1.5)


# ---------------------------------------------------------------------------
# absorption_factor
# ---------------------------------------------------------------------------


class TestAbsorptionFactor:
    def test_feasible_factor_greater_than_one(self):
        a = absorption_factor(liquid_flow_mol_s=0.10, gas_flow_mol_s=0.02, m_slope=2.0)
        assert a > 1.0

    @pytest.mark.parametrize(
        "liq,gas,m",
        [
            (0.0, 0.02, 2.0),
            (0.10, 0.0, 2.0),
            (0.10, 0.02, 0.0),
        ],
    )
    def test_nonpositive_inputs_raise(self, liq, gas, m):
        with pytest.raises(ValueError):
            absorption_factor(liq, gas, m)
