"""Unit tests for meapy.pump."""

from __future__ import annotations

import math

import numpy as np
import pytest

from meapy.pump import (
    ExponentialLevelModel,
    LinearFlowModel,
    PumpCommissioningResult,
    fit_exponential_level_model,
    fit_linear_flowrate_model,
    predict_flowrate,
    predict_level,
    safe_pump_speed,
)


# ---------------------------------------------------------------------------
# ExponentialLevelModel
# ---------------------------------------------------------------------------


class TestExponentialLevelModel:
    def test_predict_at_zero_speed(self):
        model = ExponentialLevelModel(l0=96.0, k=-0.036, r_squared=0.98)
        assert model.predict(0.0) == pytest.approx(96.0)

    def test_predict_decreases_with_speed(self):
        model = ExponentialLevelModel(l0=96.0, k=-0.036, r_squared=0.98)
        assert model.predict(10.0) < model.predict(0.0)
        assert model.predict(50.0) < model.predict(10.0)

    def test_invert_round_trip(self):
        model = ExponentialLevelModel(l0=96.0, k=-0.036, r_squared=0.98)
        ps = 40.0
        level = model.predict(ps)
        assert model.invert(level) == pytest.approx(ps, rel=1e-6)

    def test_invalid_l0_raises(self):
        with pytest.raises(ValueError):
            ExponentialLevelModel(l0=-1.0, k=-0.036, r_squared=0.98)

    def test_invalid_r2_raises(self):
        with pytest.raises(ValueError):
            ExponentialLevelModel(l0=96.0, k=-0.036, r_squared=1.5)

    def test_invert_nonpositive_level_raises(self):
        model = ExponentialLevelModel(l0=96.0, k=-0.036, r_squared=0.98)
        with pytest.raises(ValueError):
            model.invert(0.0)


# ---------------------------------------------------------------------------
# LinearFlowModel
# ---------------------------------------------------------------------------


class TestLinearFlowModel:
    def test_predict_linear(self):
        model = LinearFlowModel(slope=18.754, intercept=-9.81, r_squared=0.99)
        assert model.predict(10.0) == pytest.approx(18.754 * 10 - 9.81)

    def test_invert_round_trip(self):
        model = LinearFlowModel(slope=18.754, intercept=-9.81, r_squared=0.99)
        flow = 800.0
        speed = model.invert(flow)
        assert model.predict(speed) == pytest.approx(flow, rel=1e-6)

    def test_zero_slope_invert_raises(self):
        model = LinearFlowModel(slope=0.0, intercept=500.0, r_squared=0.0)
        with pytest.raises(ValueError):
            model.invert(800.0)


# ---------------------------------------------------------------------------
# fit_exponential_level_model
# ---------------------------------------------------------------------------


class TestFitExponentialLevelModel:
    def test_fitted_k_is_negative(self, commissioning_speeds, commissioning_levels):
        model = fit_exponential_level_model(commissioning_speeds, commissioning_levels)
        assert model.k < 0

    def test_r_squared_high(self, commissioning_speeds, commissioning_levels):
        model = fit_exponential_level_model(commissioning_speeds, commissioning_levels)
        # Real pilot-plant data is noisy; require only a reasonable fit
        assert model.r_squared > 0.85

    def test_predictions_reasonable(self, commissioning_speeds, commissioning_levels):
        model = fit_exponential_level_model(commissioning_speeds, commissioning_levels)
        # Check interior points (exclude extremes where extrapolation is poorest)
        for ps, lev in zip(commissioning_speeds[1:-1], commissioning_levels[1:-1]):
            predicted = model.predict(ps)
            assert abs(predicted - lev) / lev < 0.30  # within 30 % for noisy data

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            fit_exponential_level_model([10, 20, 30], [80, 65])

    def test_too_few_points_raise(self):
        with pytest.raises(ValueError):
            fit_exponential_level_model([10], [80])

    def test_nonpositive_levels_raise(self):
        with pytest.raises(ValueError):
            fit_exponential_level_model([10, 20], [80, -5])


# ---------------------------------------------------------------------------
# fit_linear_flowrate_model
# ---------------------------------------------------------------------------


class TestFitLinearFlowrateModel:
    def test_fitted_slope_positive(self, commissioning_speeds, commissioning_flows):
        model = fit_linear_flowrate_model(commissioning_speeds, commissioning_flows)
        assert model.slope > 0

    def test_r_squared_high(self, commissioning_speeds, commissioning_flows):
        model = fit_linear_flowrate_model(commissioning_speeds, commissioning_flows)
        assert model.r_squared > 0.99

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            fit_linear_flowrate_model([10, 20, 30], [177, 365])


# ---------------------------------------------------------------------------
# safe_pump_speed
# ---------------------------------------------------------------------------


class TestSafePumpSpeed:
    def test_returns_result_object(self, level_model, flow_model):
        result = safe_pump_speed(level_model, flow_model)
        assert isinstance(result, PumpCommissioningResult)

    def test_safe_speed_below_both_alarm_speeds(self, level_model, flow_model):
        result = safe_pump_speed(level_model, flow_model)
        assert result.safe_speed_pct <= result.level_alarm_speed_pct
        assert result.safe_speed_pct <= result.flow_alarm_speed_pct

    def test_limiting_constraint_is_valid(self, level_model, flow_model):
        result = safe_pump_speed(level_model, flow_model)
        assert result.limiting_constraint in {"level", "flow"}

    def test_predicted_level_above_alarm(self, level_model, flow_model):
        result = safe_pump_speed(level_model, flow_model)
        # Predicted level at safe speed should be at or above alarm threshold
        assert result.predicted_level_pct >= 10.0 - 0.5  # small tolerance

    def test_predicted_flow_below_alarm(self, level_model, flow_model):
        result = safe_pump_speed(level_model, flow_model)
        assert result.predicted_flow_kg_h <= 1000.0 + 1.0

    def test_str_representation(self, level_model, flow_model):
        result = safe_pump_speed(level_model, flow_model)
        s = str(result)
        assert "Safe operating speed" in s
        assert "%" in s

    def test_custom_thresholds(self, level_model, flow_model):
        # Tighter flow alarm → lower safe speed
        r_default = safe_pump_speed(level_model, flow_model, flow_alarm_kg_h=1000)
        r_tight = safe_pump_speed(level_model, flow_model, flow_alarm_kg_h=800)
        assert r_tight.safe_speed_pct <= r_default.safe_speed_pct


# ---------------------------------------------------------------------------
# predict_level / predict_flowrate
# ---------------------------------------------------------------------------


class TestConvenienceWrappers:
    def test_predict_level_matches_model(self, level_model):
        assert predict_level(level_model, 30.0) == level_model.predict(30.0)

    def test_predict_flowrate_matches_model(self, flow_model):
        assert predict_flowrate(flow_model, 30.0) == flow_model.predict(30.0)
