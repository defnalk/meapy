"""Unit tests for meapy.utils."""

from __future__ import annotations

import numpy as np
import pytest

from meapy.utils import (
    celsius_to_kelvin,
    kelvin_to_celsius,
    kg_h_to_mol_s,
    mol_s_to_kg_h,
    rolling_mean,
    steady_state_mean,
    summarise_array,
)


class TestSteadyStateMean:
    def test_steady_window_returns_mean(self):
        vals = [45.0, 45.1, 45.2, 45.1]
        result = steady_state_mean(vals, window=3, tol=0.5)
        assert result == pytest.approx(np.mean([45.2, 45.1, 45.1]), rel=1e-9)

    def test_unstable_window_raises(self):
        with pytest.raises(RuntimeError, match="criterion"):
            steady_state_mean([40.0, 45.0, 50.0], window=3, tol=0.5)

    def test_too_few_values_raises(self):
        with pytest.raises(ValueError):
            steady_state_mean([45.0, 45.1], window=5)

    def test_negative_tol_raises(self):
        with pytest.raises(ValueError):
            steady_state_mean([45.0, 45.1, 45.0], tol=-0.1)


class TestUnitConversions:
    @pytest.mark.parametrize("flow_kg_h,mw,expected_mol_s", [
        (44.01, 44.01, 0.277778),   # 1 kg/h of CO₂ gas
        (3600.0, 18.015, 1000.0 / 18.015),  # 1 kg/s water
    ])
    def test_kg_h_to_mol_s(self, flow_kg_h, mw, expected_mol_s):
        assert kg_h_to_mol_s(flow_kg_h, mw) == pytest.approx(expected_mol_s, rel=1e-4)

    def test_kg_h_to_mol_s_roundtrip(self):
        mw = 61.08  # MEA
        flow = 900.0
        assert mol_s_to_kg_h(kg_h_to_mol_s(flow, mw), mw) == pytest.approx(flow, rel=1e-9)

    def test_negative_flow_raises(self):
        with pytest.raises(ValueError):
            kg_h_to_mol_s(-1.0, 44.01)

    def test_zero_mw_raises(self):
        with pytest.raises(ValueError):
            kg_h_to_mol_s(100.0, 0.0)

    def test_celsius_kelvin_roundtrip(self):
        for t in [0.0, 25.0, 100.0, -50.0]:
            assert kelvin_to_celsius(celsius_to_kelvin(t)) == pytest.approx(t)

    def test_below_absolute_zero_raises(self):
        with pytest.raises(ValueError):
            celsius_to_kelvin(-274.0)

    def test_negative_kelvin_raises(self):
        with pytest.raises(ValueError):
            kelvin_to_celsius(-1.0)


class TestSummariseArray:
    def test_basic_stats(self):
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = summarise_array(a)
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["n"] == 5

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            summarise_array([])

    def test_single_value_std_zero(self):
        stats = summarise_array([42.0])
        assert stats["std"] == 0.0


class TestRollingMean:
    def test_output_same_length(self):
        a = [1, 2, 3, 4, 5]
        result = rolling_mean(a, window=3)
        assert len(result) == len(a)

    def test_steady_series(self):
        a = [5.0] * 10
        np.testing.assert_allclose(rolling_mean(a, window=3), 5.0)

    def test_window_one_is_identity(self):
        a = np.array([1.0, 2.0, 3.0])
        np.testing.assert_allclose(rolling_mean(a, window=1), a)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            rolling_mean([1, 2, 3], window=0)
