"""Batch plant-session analysis with pandas DataFrame integration.

Provides :class:`PlantSession`, which accepts a time-indexed DataFrame of
raw plant transmitter data, identifies steady-state windows, and runs
the full meapy analysis pipeline (heat transfer, mass transfer, pump
commissioning) on each window.

Requires the ``pandas`` optional dependency (``pip install meapy[data]``).

Typical usage example::

    import pandas as pd
    from meapy.session import PlantSession

    df = pd.read_csv("plant_run.csv", parse_dates=["timestamp"], index_col="timestamp")
    session = PlantSession(
        df,
        column_map={
            "mea_flow_kg_h": "FT103",
            "t_mea_in_c": "TT201",
            "t_mea_out_c": "TT202",
            "t_utility_in_c": "TT301",
            "t_utility_out_c": "TT302",
            "utility_flow_kg_h": "FT201",
        },
    )
    result = session.run(
        cp_mea_j_kg_k=3940.0,
        cp_utility_j_kg_k=4182.0,
        area_m2=0.30,
    )
    print(result.summary)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from meapy.heat_transfer import analyse_exchanger
from meapy.mass_transfer import koga_profile
from meapy.pump import (
    PumpCommissioningResult,
    fit_exponential_level_model,
    fit_linear_flowrate_model,
    safe_pump_speed,
)
from meapy.utils import steady_state

try:
    import pandas as pd
except ImportError as _exc:
    raise ImportError(
        "pandas is required for meapy.session. "
        "Install it with: pip install meapy[data]"
    ) from _exc

__all__ = [
    "PlantSession",
    "WindowResult",
    "PlantSessionResult",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class WindowResult:
    """Results for a single steady-state window.

    Attributes:
        start: Start timestamp of the window.
        end: End timestamp of the window.
        heat_transfer: Output of :func:`~meapy.heat_transfer.analyse_exchanger`,
            or ``None`` if heat-transfer columns were not mapped.
        koga: K_OGa profile array from :func:`~meapy.mass_transfer.koga_profile`,
            or ``None`` if mass-transfer columns were not mapped.
        pump: Output of :func:`~meapy.pump.safe_pump_speed`, or ``None`` if
            pump columns were not mapped.
    """

    start: Any  # pd.Timestamp
    end: Any  # pd.Timestamp
    heat_transfer: dict[str, float] | None = None
    koga: npt.NDArray[np.float64] | None = None
    pump: PumpCommissioningResult | None = None


@dataclass
class PlantSessionResult:
    """Aggregated results across all steady-state windows.

    Attributes:
        windows: Per-window results.
        summary: DataFrame with one row per window and columns for the key
            metrics from each analysis module.
    """

    windows: list[WindowResult] = field(default_factory=list)
    summary: Any = None  # pd.DataFrame, typed as Any to avoid runtime dep at class level


# ---------------------------------------------------------------------------
# Column-name groups expected by each analysis module
# ---------------------------------------------------------------------------

_HEAT_TRANSFER_COLS = {
    "mea_flow_kg_h",
    "t_mea_in_c",
    "t_mea_out_c",
    "utility_flow_kg_h",
    "t_utility_in_c",
    "t_utility_out_c",
}

_MASS_TRANSFER_COLS = {
    "inert_gas_flow_mol_s",
    "cross_section_m2",
}

_PUMP_COLS = {
    "pump_speed_pct",
    "mea_level_pct",
    "mea_flow_kg_h",
}


# ---------------------------------------------------------------------------
# PlantSession
# ---------------------------------------------------------------------------


class PlantSession:
    """Batch analysis driver for a single plant operating session.

    Args:
        df: A pandas DataFrame with a :class:`~pandas.DatetimeIndex`.
            Each row is a timestamped sample from the plant DCS / historian.
        column_map: Maps meapy parameter names to the DataFrame column
            names (e.g. ``{"mea_flow_kg_h": "FT103"}``).  Only columns
            relevant to the analyses you intend to run need to be mapped.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        column_map: dict[str, str],
    ) -> None:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError(
                "DataFrame must have a DatetimeIndex. "
                "Use pd.to_datetime() on the index first."
            )
        self._df = df
        self._column_map = dict(column_map)

        # Validate that mapped columns exist in the DataFrame
        missing = [
            col for col in self._column_map.values() if col not in df.columns
        ]
        if missing:
            raise ValueError(
                f"The following mapped columns are missing from the DataFrame: {missing}"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, param: str) -> str:
        """Return the DataFrame column name for a meapy parameter name."""
        return self._column_map[param]

    def _has_cols(self, required: set[str]) -> bool:
        """Check if all *required* meapy param names are mapped."""
        return required.issubset(self._column_map)

    def _window_mean(
        self,
        start: int,
        end: int,
        param: str,
    ) -> float:
        """Mean of a mapped column within a steady-state window."""
        col = self._resolve(param)
        return float(self._df[col].iloc[start : end + 1].mean())

    def _window_series(
        self,
        start: int,
        end: int,
        param: str,
    ) -> npt.NDArray[np.float64]:
        """NumPy array of a mapped column within a steady-state window."""
        col = self._resolve(param)
        return self._df[col].iloc[start : end + 1].to_numpy(dtype=float)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        steady_col: str | None = None,
        steady_window: int = 30,
        steady_tol: float = 1.0,
        cp_mea_j_kg_k: float = 3940.0,
        cp_utility_j_kg_k: float = 4182.0,
        area_m2: float = 0.30,
        sampling_heights_m: list[float] | None = None,
        co2_columns: list[str] | None = None,
    ) -> PlantSessionResult:
        """Run the full analysis pipeline on all steady-state windows.

        Args:
            steady_col: meapy parameter name whose mapped column is used
                for steady-state detection.  Defaults to the first mapped
                column if not specified.
            steady_window: Window size passed to :func:`~meapy.utils.steady_state`.
            steady_tol: Tolerance passed to :func:`~meapy.utils.steady_state`.
            cp_mea_j_kg_k: MEA heat capacity in J/(kg*K) (fixed value).
            cp_utility_j_kg_k: Utility heat capacity in J/(kg*K).
            area_m2: Heat-exchanger area in m^2.
            sampling_heights_m: Column sampling-port heights for K_OGa
                profiling.
            co2_columns: DataFrame column names for CO2 vol% at each
                sampling height (ordered bottom to top).

        Returns:
            :class:`PlantSessionResult` containing per-window results and
            a summary DataFrame.
        """
        # Determine which column to use for steady-state detection
        if steady_col is not None:
            ss_series = self._df[self._resolve(steady_col)].to_numpy(dtype=float)
        else:
            first_param = next(iter(self._column_map))
            ss_series = self._df[self._column_map[first_param]].to_numpy(dtype=float)

        regions = steady_state(ss_series, window=steady_window, tol=steady_tol)
        logger.info("PlantSession.run: found %d steady-state windows", len(regions))

        can_ht = self._has_cols(_HEAT_TRANSFER_COLS)
        can_mt = (
            self._has_cols(_MASS_TRANSFER_COLS)
            and sampling_heights_m is not None
            and co2_columns is not None
        )
        can_pump = self._has_cols(_PUMP_COLS)

        window_results: list[WindowResult] = []
        summary_rows: list[dict[str, Any]] = []

        for start, end in regions:
            ts_start = self._df.index[start]
            ts_end = self._df.index[end]
            wr = WindowResult(start=ts_start, end=ts_end)
            row: dict[str, Any] = {"start": ts_start, "end": ts_end}

            # --- Heat transfer -------------------------------------------
            if can_ht:
                try:
                    ht = analyse_exchanger(
                        mea_flow_kg_h=self._window_mean(start, end, "mea_flow_kg_h"),
                        cp_mea_j_kg_k=cp_mea_j_kg_k,
                        t_mea_in_c=self._window_mean(start, end, "t_mea_in_c"),
                        t_mea_out_c=self._window_mean(start, end, "t_mea_out_c"),
                        utility_flow_kg_h=self._window_mean(start, end, "utility_flow_kg_h"),
                        cp_utility_j_kg_k=cp_utility_j_kg_k,
                        t_utility_in_c=self._window_mean(start, end, "t_utility_in_c"),
                        t_utility_out_c=self._window_mean(start, end, "t_utility_out_c"),
                        area_m2=area_m2,
                    )
                    wr.heat_transfer = ht
                    for k, v in ht.items():
                        row[k] = v
                except (ValueError, ZeroDivisionError) as exc:
                    logger.warning(
                        "Heat-transfer failed for window %s–%s: %s",
                        ts_start, ts_end, exc,
                    )

            # --- Mass transfer -------------------------------------------
            if can_mt:
                assert sampling_heights_m is not None
                assert co2_columns is not None
                try:
                    y_vals: list[float] = []
                    for col_name in co2_columns:
                        mean_pct = float(self._df[col_name].iloc[start : end + 1].mean())
                        y_vals.append(mean_pct / 100.0)

                    koga = koga_profile(
                        inert_gas_flow_mol_s=self._window_mean(start, end, "inert_gas_flow_mol_s"),
                        cross_section_m2=self._window_mean(start, end, "cross_section_m2"),
                        sampling_heights_m=sampling_heights_m,
                        y_values=y_vals,
                    )
                    wr.koga = koga
                    valid = koga[~np.isnan(koga)]
                    row["koga_mean"] = float(np.mean(valid)) if valid.size > 0 else float("nan")
                except (ValueError, ZeroDivisionError) as exc:
                    logger.warning(
                        "Mass-transfer failed for window %s–%s: %s",
                        ts_start, ts_end, exc,
                    )

            # --- Pump commissioning --------------------------------------
            if can_pump:
                try:
                    speeds = self._window_series(start, end, "pump_speed_pct")
                    levels = self._window_series(start, end, "mea_level_pct")
                    flows = self._window_series(start, end, "mea_flow_kg_h")

                    if len(speeds) >= 2:
                        level_model = fit_exponential_level_model(speeds, levels)
                        flow_model = fit_linear_flowrate_model(speeds, flows)
                        pump_result = safe_pump_speed(level_model, flow_model)
                        wr.pump = pump_result
                        row["safe_speed_pct"] = pump_result.safe_speed_pct
                        row["limiting_constraint"] = pump_result.limiting_constraint
                except (ValueError, RuntimeError) as exc:
                    logger.warning(
                        "Pump analysis failed for window %s–%s: %s",
                        ts_start, ts_end, exc,
                    )

            window_results.append(wr)
            summary_rows.append(row)

        summary_df = pd.DataFrame(summary_rows) if summary_rows else pd.DataFrame()
        return PlantSessionResult(windows=window_results, summary=summary_df)
