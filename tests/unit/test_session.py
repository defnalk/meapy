"""Unit tests for meapy.session."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from meapy.session import PlantSession, PlantSessionResult, WindowResult


@pytest.fixture
def steady_df():
    """DataFrame with a clear steady-state region for heat-transfer analysis."""
    n = 100
    idx = pd.date_range("2025-01-01", periods=n, freq="1min")
    rng = np.random.default_rng(42)
    data = {
        "FT103": np.concatenate([
            rng.normal(900, 50, 30),   # noisy
            np.full(40, 900.0) + rng.normal(0, 0.1, 40),  # steady
            rng.normal(900, 50, 30),   # noisy
        ]),
        "TT201": np.concatenate([
            rng.normal(85, 5, 30),
            np.full(40, 85.0) + rng.normal(0, 0.05, 40),
            rng.normal(85, 5, 30),
        ]),
        "TT202": np.concatenate([
            rng.normal(42, 5, 30),
            np.full(40, 42.0) + rng.normal(0, 0.05, 40),
            rng.normal(42, 5, 30),
        ]),
        "FT201": np.concatenate([
            rng.normal(800, 50, 30),
            np.full(40, 800.0) + rng.normal(0, 0.1, 40),
            rng.normal(800, 50, 30),
        ]),
        "TT301": np.concatenate([
            rng.normal(30, 3, 30),
            np.full(40, 30.0) + rng.normal(0, 0.05, 40),
            rng.normal(30, 3, 30),
        ]),
        "TT302": np.concatenate([
            rng.normal(68, 3, 30),
            np.full(40, 68.0) + rng.normal(0, 0.05, 40),
            rng.normal(68, 3, 30),
        ]),
    }
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def column_map():
    return {
        "mea_flow_kg_h": "FT103",
        "t_mea_in_c": "TT201",
        "t_mea_out_c": "TT202",
        "utility_flow_kg_h": "FT201",
        "t_utility_in_c": "TT301",
        "t_utility_out_c": "TT302",
    }


class TestPlantSession:
    def test_creates_session(self, steady_df, column_map):
        session = PlantSession(steady_df, column_map)
        assert session is not None

    def test_missing_column_raises(self, steady_df, column_map):
        column_map["t_mea_in_c"] = "NONEXISTENT"
        with pytest.raises(ValueError, match="missing"):
            PlantSession(steady_df, column_map)

    def test_non_datetime_index_raises(self, column_map):
        df = pd.DataFrame({"FT103": [1, 2], "TT201": [3, 4], "TT202": [5, 6],
                           "FT201": [7, 8], "TT301": [9, 10], "TT302": [11, 12]})
        with pytest.raises(ValueError, match="DatetimeIndex"):
            PlantSession(df, column_map)

    def test_run_returns_result(self, steady_df, column_map):
        session = PlantSession(steady_df, column_map)
        result = session.run(steady_window=10, steady_tol=2.0)
        assert isinstance(result, PlantSessionResult)
        assert isinstance(result.windows, list)

    def test_run_finds_steady_windows(self, steady_df, column_map):
        session = PlantSession(steady_df, column_map)
        result = session.run(steady_window=10, steady_tol=2.0)
        assert len(result.windows) > 0

    def test_window_has_heat_transfer(self, steady_df, column_map):
        session = PlantSession(steady_df, column_map)
        result = session.run(steady_window=10, steady_tol=2.0)
        ht_windows = [w for w in result.windows if w.heat_transfer is not None]
        assert len(ht_windows) > 0
        assert "u_kw_m2_k" in ht_windows[0].heat_transfer

    def test_summary_is_dataframe(self, steady_df, column_map):
        session = PlantSession(steady_df, column_map)
        result = session.run(steady_window=10, steady_tol=2.0)
        assert isinstance(result.summary, pd.DataFrame)
        if not result.summary.empty:
            assert "start" in result.summary.columns
