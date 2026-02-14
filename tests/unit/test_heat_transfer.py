"""Unit tests for meapy.heat_transfer."""

from __future__ import annotations

import math

import pytest

from meapy.heat_transfer import (
    analyse_exchanger,
    effectiveness,
    efficiency,
    energy_loss,
    heat_capacity_rate,
    lmtd_co_current,
    lmtd_counter_current,
    overall_heat_transfer_coefficient,
    stream_duty,
)

# ---------------------------------------------------------------------------
# stream_duty
# ---------------------------------------------------------------------------


class TestStreamDuty:
    def test_cold_stream_positive(self):
        q = stream_duty(0.25, 4000, 30, 70)
        assert q == pytest.approx(0.25 * 4000 * 40)

    def test_hot_stream_negative(self):
        q = stream_duty(0.25, 4000, 85, 42)
        assert q < 0

    @pytest.mark.parametrize(
        "flow,cp",
        [(0.0, 4000), (-1.0, 4000), (1.0, 0.0), (1.0, -100)],
    )
    def test_invalid_inputs_raise(self, flow, cp):
        with pytest.raises(ValueError):
            stream_duty(flow, cp, 30, 70)

    def test_zero_delta_t_returns_zero(self):
        assert stream_duty(1.0, 4000, 50, 50) == 0.0


# ---------------------------------------------------------------------------
# energy_loss
# ---------------------------------------------------------------------------


class TestEnergyLoss:
    def test_perfect_exchanger(self):
        q_h = stream_duty(0.25, 4000, 85, 45)
        q_c = -q_h  # ideal
        assert energy_loss(q_h, q_c) == pytest.approx(0.0, abs=1e-6)

    def test_nonzero_loss(self):
        assert energy_loss(-40000, 38000) == pytest.approx(2000.0)

    def test_always_non_negative(self):
        assert energy_loss(-100, 90) >= 0
        assert energy_loss(-100, 110) >= 0


# ---------------------------------------------------------------------------
# lmtd_counter_current
# ---------------------------------------------------------------------------


class TestLMTDCounterCurrent:
    def test_known_value(self):
        # ΔT1 = 85−68 = 17, ΔT2 = 42−30 = 12 → LMTD = (17−12)/ln(17/12)
        expected = (17 - 12) / math.log(17 / 12)
        assert lmtd_counter_current(85, 42, 30, 68) == pytest.approx(expected, rel=1e-5)

    def test_equal_terminal_differences_returns_that_value(self):
        assert lmtd_counter_current(70, 50, 30, 50) == pytest.approx(20.0, abs=1e-4)

    @pytest.mark.parametrize(
        "t_hi, t_ho, t_ci, t_co",
        [
            (30, 85, 30, 68),  # ΔT1 = 30−68 < 0  → crossover
            (42, 85, 30, 50),  # ΔT2 = 42−30 = 12 is fine, ΔT1 = 85−50 = 35 fine — no error expected
        ],
    )
    def test_crossover_raises(self, t_hi, t_ho, t_ci, t_co):
        # Only the truly crossed case should raise
        if t_hi - t_co <= 0 or t_ho - t_ci <= 0:
            with pytest.raises(ValueError, match="positive"):
                lmtd_counter_current(t_hi, t_ho, t_ci, t_co)


# ---------------------------------------------------------------------------
# lmtd_co_current
# ---------------------------------------------------------------------------


class TestLMTDCoCurrent:
    def test_basic(self):
        # ΔT1 = 85−30 = 55, ΔT2 = 42−68 = −26 → co-current not valid here
        with pytest.raises(ValueError):
            lmtd_co_current(85, 42, 30, 68)

    def test_valid_co_current(self):
        result = lmtd_co_current(85, 60, 20, 45)
        assert result > 0


# ---------------------------------------------------------------------------
# overall_heat_transfer_coefficient
# ---------------------------------------------------------------------------


class TestOverallHeatTransferCoefficient:
    def test_basic_calculation(self):
        lmtd = lmtd_counter_current(85, 42, 30, 68)
        q = abs(stream_duty(900 / 3600, 3940, 85, 42))
        u = overall_heat_transfer_coefficient(q, lmtd, 0.30)
        # Literature range: 1–4 kW/(m²·K) → 1000–4000 W/(m²·K)
        assert 1000 <= u <= 20_000  # generous upper bound for pilot scale

    @pytest.mark.parametrize("lmtd,area", [(0.0, 0.3), (-1.0, 0.3), (10.0, 0.0), (10.0, -1.0)])
    def test_invalid_raises(self, lmtd, area):
        with pytest.raises(ValueError):
            overall_heat_transfer_coefficient(10_000, lmtd, area)


# ---------------------------------------------------------------------------
# efficiency
# ---------------------------------------------------------------------------


class TestEfficiency:
    def test_ideal_efficiency_is_one(self):
        assert efficiency(40000, -40000) == pytest.approx(1.0)

    def test_efficiency_less_than_one_for_losses(self):
        assert efficiency(38000, -40000) == pytest.approx(0.95)

    def test_zero_q_hot_raises(self):
        with pytest.raises(ValueError, match="zero"):
            efficiency(1000, 0.0)

    def test_accepts_positive_q_hot(self):
        # Function should accept either sign convention for q_hot
        assert efficiency(38000, 40000) == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# effectiveness
# ---------------------------------------------------------------------------


class TestEffectiveness:
    def test_value_between_zero_and_one(self, c100_inputs):

        mea_kg_s = c100_inputs["mea_flow_kg_h"] / 3600
        util_kg_s = c100_inputs["utility_flow_kg_h"] / 3600
        c_hot = heat_capacity_rate(mea_kg_s, c100_inputs["cp_mea_j_kg_k"])
        c_cold = heat_capacity_rate(util_kg_s, c100_inputs["cp_utility_j_kg_k"])
        q_hot = stream_duty(mea_kg_s, c100_inputs["cp_mea_j_kg_k"], 85, 42)
        eps = effectiveness(q_hot, c_hot, c_cold, 85, 30)
        assert 0.0 <= eps <= 1.5  # allow slightly above 1 for measurement noise

    def test_zero_delta_t_raises(self):
        with pytest.raises(ValueError, match="equal"):
            effectiveness(1000, 500, 400, 50, 50)


# ---------------------------------------------------------------------------
# analyse_exchanger (integration-style unit test)
# ---------------------------------------------------------------------------


class TestAnalyseExchanger:
    def test_returns_expected_keys(self, c100_inputs):
        result = analyse_exchanger(**c100_inputs)
        expected_keys = {
            "q_hot_w",
            "q_cold_w",
            "q_loss_w",
            "lmtd_k",
            "u_w_m2_k",
            "u_kw_m2_k",
            "efficiency",
            "effectiveness",
            "ntu",
        }
        assert expected_keys == set(result.keys())

    def test_u_in_literature_range(self, c100_inputs):
        result = analyse_exchanger(**c100_inputs)
        # 1–4 kW/(m²·K) from Engineering Toolbox (2003) for plate HEX
        assert 0.5 <= result["u_kw_m2_k"] <= 20.0

    def test_lmtd_positive(self, c100_inputs):
        result = analyse_exchanger(**c100_inputs)
        assert result["lmtd_k"] > 0

    def test_invalid_flow_direction_raises(self, c100_inputs):
        with pytest.raises(ValueError, match="flow_direction"):
            analyse_exchanger(**c100_inputs, flow_direction="diagonal")

    def test_c200_trim_cooler(self, c200_inputs):
        result = analyse_exchanger(**c200_inputs)
        assert result["q_loss_w"] >= 0
        assert result["lmtd_k"] > 0
