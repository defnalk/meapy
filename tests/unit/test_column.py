"""Unit tests for meapy.column."""

from __future__ import annotations

import math

import pytest

from meapy.column import flooding_velocity


class TestFloodingVelocity:
    def test_returns_three_floats(self):
        u, K4, dp = flooding_velocity(200.0, 1008.0, 1.2, 1.6e-3, 2.5)
        assert isinstance(u, float)
        assert isinstance(K4, float)
        assert isinstance(dp, float)

    def test_positive_results(self):
        u, K4, dp = flooding_velocity(200.0, 1008.0, 1.2, 1.6e-3, 2.5)
        assert u > 0
        assert K4 > 0
        assert dp > 0

    def test_flooding_velocity_reasonable_range(self):
        # Typical flooding velocities for packed columns are 0.5–3 m/s
        u, _, _ = flooding_velocity(200.0, 1008.0, 1.2, 1.6e-3, 2.5)
        assert 0.1 <= u <= 5.0

    def test_higher_packing_factor_lowers_velocity(self):
        u1, _, _ = flooding_velocity(100.0, 1000.0, 1.2, 1e-3, 2.0)
        u2, _, _ = flooding_velocity(300.0, 1000.0, 1.2, 1e-3, 2.0)
        assert u2 < u1

    def test_higher_liquid_ratio_lowers_velocity(self):
        u1, _, _ = flooding_velocity(200.0, 1000.0, 1.2, 1e-3, 1.0)
        u2, _, _ = flooding_velocity(200.0, 1000.0, 1.2, 1e-3, 5.0)
        assert u2 < u1

    def test_pressure_drop_scales_with_packing_factor(self):
        _, _, dp1 = flooding_velocity(100.0, 1000.0, 1.2, 1e-3, 2.0)
        _, _, dp2 = flooding_velocity(300.0, 1000.0, 1.2, 1e-3, 2.0)
        assert dp2 > dp1

    @pytest.mark.parametrize(
        "fp,rl,rg,mu,lg",
        [
            (0.0, 1000.0, 1.2, 1e-3, 2.0),
            (200.0, 0.0, 1.2, 1e-3, 2.0),
            (200.0, 1000.0, 0.0, 1e-3, 2.0),
            (200.0, 1000.0, 1.2, 0.0, 2.0),
            (200.0, 1000.0, 1.2, 1e-3, 0.0),
        ],
    )
    def test_nonpositive_input_raises(self, fp, rl, rg, mu, lg):
        with pytest.raises(ValueError, match="positive"):
            flooding_velocity(fp, rl, rg, mu, lg)

    def test_gas_denser_than_liquid_raises(self):
        with pytest.raises(ValueError, match="rho_G"):
            flooding_velocity(200.0, 1.0, 1.2, 1e-3, 2.0)
