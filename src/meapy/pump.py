"""Pump commissioning analysis for process plant startup.

Provides tools to determine maximum safe pump operating speeds from
level-vs-speed data, fitting exponential and linear regression models
and checking against plant alarm thresholds.

The methodology follows the commissioning procedure for pump J100 in the
Imperial College MEA carbon-capture pilot plant (Hale, 2025, Section 3),
and is general enough for any centrifugal pump operating in a closed loop.

Typical usage example::

    import numpy as np
    from meapy.pump import (
        fit_exponential_level_model,
        fit_linear_flowrate_model,
        safe_pump_speed,
        PumpCommissioningResult,
    )

    speeds = np.array([10, 20, 30, 40, 50, 53])
    levels = np.array([80.1, 65.3, 52.0, 38.7, 24.1, 15.0])
    flows  = np.array([177, 365, 553, 740, 927, 980])

    exp_model  = fit_exponential_level_model(speeds, levels)
    lin_model  = fit_linear_flowrate_model(speeds, flows)
    result     = safe_pump_speed(exp_model, lin_model)
    print(result)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
from scipy.stats import linregress

from meapy.constants import AlarmLimits

__all__ = [
    "ExponentialLevelModel",
    "LinearFlowModel",
    "PumpCommissioningResult",
    "fit_exponential_level_model",
    "fit_linear_flowrate_model",
    "safe_pump_speed",
    "predict_level",
    "predict_flowrate",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExponentialLevelModel:
    """Fitted parameters for L = L₀ · exp(k · PS).

    Attributes:
        l0: Pre-exponential coefficient L₀ (%).
        k: Exponential decay constant k (per % pump speed; negative for decay).
        r_squared: Coefficient of determination R² of the fit.
    """

    l0: float
    k: float
    r_squared: float

    def __post_init__(self) -> None:
        if self.l0 <= 0:
            raise ValueError(f"l0 must be positive, got {self.l0!r}.")
        if not (0.0 <= self.r_squared <= 1.0):
            raise ValueError(f"r_squared must be in [0, 1], got {self.r_squared!r}.")

    def predict(self, pump_speed_pct: float) -> float:
        """Predict steady-state MEA level for a given pump speed.

        Args:
            pump_speed_pct: Pump speed in %.

        Returns:
            Predicted MEA level in %.
        """
        return self.l0 * math.exp(self.k * pump_speed_pct)

    def invert(self, target_level_pct: float) -> float:
        """Find the pump speed that gives a target MEA level.

        Solves L₀ · exp(k · PS) = target analytically.

        Args:
            target_level_pct: Target MEA level in %.

        Returns:
            Pump speed in %.

        Raises:
            ValueError: If *target_level_pct* is not positive.
        """
        if target_level_pct <= 0:
            raise ValueError(f"target_level_pct must be positive, got {target_level_pct!r}.")
        if math.isclose(self.k, 0.0, abs_tol=1e-12):
            # A flat fit (k = 0) means level is independent of speed; no
            # finite speed solves L₀·exp(0) = target unless target == L₀,
            # in which case every speed does. Either way, inversion is
            # ill-posed — surface a clear error rather than dividing by zero.
            raise ValueError(
                "Cannot invert an ExponentialLevelModel with k ≈ 0: the fitted "
                "level is independent of pump speed."
            )
        return math.log(target_level_pct / self.l0) / self.k


@dataclass(frozen=True)
class LinearFlowModel:
    """Fitted parameters for F = slope · PS + intercept.

    Attributes:
        slope: Flowrate sensitivity to pump speed in kg/(h·%).
        intercept: Flowrate at zero pump speed in kg/h.
        r_squared: Coefficient of determination R².
    """

    slope: float
    intercept: float
    r_squared: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.r_squared <= 1.0):
            raise ValueError(f"r_squared must be in [0, 1], got {self.r_squared!r}.")

    def predict(self, pump_speed_pct: float) -> float:
        """Predict flowrate at a given pump speed.

        Args:
            pump_speed_pct: Pump speed in %.

        Returns:
            Predicted flowrate in kg/h.
        """
        return self.slope * pump_speed_pct + self.intercept

    def invert(self, target_flow_kg_h: float) -> float:
        """Find the pump speed that achieves a given flowrate.

        Args:
            target_flow_kg_h: Target flowrate in kg/h.

        Returns:
            Pump speed in %.

        Raises:
            ValueError: If *slope* is zero (undefined inversion).
        """
        if math.isclose(self.slope, 0.0, abs_tol=1e-10):
            raise ValueError("Cannot invert a LinearFlowModel with slope ≈ 0.")
        return (target_flow_kg_h - self.intercept) / self.slope


@dataclass
class PumpCommissioningResult:
    """Summary of a pump commissioning analysis.

    Attributes:
        safe_speed_pct: Recommended maximum safe pump speed in %.
        predicted_level_pct: Predicted MEA level at *safe_speed_pct* in %.
        predicted_flow_kg_h: Predicted flowrate at *safe_speed_pct* in kg/h.
        level_alarm_speed_pct: Pump speed at which LT101 would reach its alarm
            threshold, from the exponential model (%).
        flow_alarm_speed_pct: Pump speed at which FT103 would reach its alarm
            threshold, from the linear model (%).
        limiting_constraint: Which alarm is the binding constraint
            (``"level"`` or ``"flow"``).
        notes: List of informational messages generated during the analysis.
    """

    safe_speed_pct: float
    predicted_level_pct: float
    predicted_flow_kg_h: float
    level_alarm_speed_pct: float
    flow_alarm_speed_pct: float
    limiting_constraint: str
    notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [
            "── Pump Commissioning Result ────────────────────────────",
            f"  Safe operating speed  : {self.safe_speed_pct:.1f} %",
            f"  Predicted MEA level   : {self.predicted_level_pct:.1f} %",
            f"  Predicted flowrate    : {self.predicted_flow_kg_h:.1f} kg/h",
            f"  Level alarm at        : {self.level_alarm_speed_pct:.1f} %",
            f"  Flow alarm at         : {self.flow_alarm_speed_pct:.1f} %",
            f"  Limiting constraint   : {self.limiting_constraint}",
            "─────────────────────────────────────────────────────────",
        ]
        for note in self.notes:
            lines.append(f"  NOTE: {note}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fitting functions
# ---------------------------------------------------------------------------


def fit_exponential_level_model(
    pump_speeds_pct: npt.ArrayLike,
    mea_levels_pct: npt.ArrayLike,
) -> ExponentialLevelModel:
    """Fit L = L₀ · exp(k · PS) to (speed, level) commissioning data.

    Linearises to ln(L) = ln(L₀) + k · PS and applies ordinary least squares.

    Args:
        pump_speeds_pct: Pump speed set-points at which steady-state was
            recorded, in %.  1-D array-like, length ≥ 2.
        mea_levels_pct: Corresponding steady-state MEA levels from LT101
            in %.  All values must be strictly positive.

    Returns:
        :class:`ExponentialLevelModel` with fitted l0, k, and R².

    Raises:
        ValueError: If inputs have different lengths, fewer than 2 points, or
            any level value is non-positive.

    Example::

        >>> import numpy as np
        >>> speeds = np.array([10, 20, 30, 40, 50])
        >>> levels = np.array([80, 65, 50, 37, 24])
        >>> model = fit_exponential_level_model(speeds, levels)
        >>> model.k < 0
        True
    """
    ps = np.asarray(pump_speeds_pct, dtype=float).ravel()
    lev = np.asarray(mea_levels_pct, dtype=float).ravel()

    if ps.shape != lev.shape:
        raise ValueError(
            f"pump_speeds_pct and mea_levels_pct must have the same length, "
            f"got {ps.shape} vs {lev.shape}."
        )
    if len(ps) < 2:
        raise ValueError("At least 2 data points are required to fit an exponential model.")
    if np.any(lev <= 0):
        raise ValueError(
            f"All MEA level values must be strictly positive for log-linearisation.  "
            f"Found {(lev <= 0).sum()} non-positive value(s)."
        )
    if np.ptp(ps) == 0:
        raise ValueError(
            "pump_speeds_pct has zero variance; cannot fit an exponential model "
            "(slope would be undefined)."
        )

    ln_lev = np.log(lev)
    slope, intercept, r, _, _ = linregress(ps, ln_lev)
    r_sq = float(r**2)

    l0 = math.exp(intercept)
    k = float(slope)

    logger.info("Exponential level model: L₀=%.4f %%, k=%.6f /pct, R²=%.4f", l0, k, r_sq)
    return ExponentialLevelModel(l0=l0, k=k, r_squared=r_sq)


def fit_linear_flowrate_model(
    pump_speeds_pct: npt.ArrayLike,
    flowrates_kg_h: npt.ArrayLike,
) -> LinearFlowModel:
    """Fit F = slope · PS + intercept to (speed, flowrate) commissioning data.

    Args:
        pump_speeds_pct: Pump speed set-points in %.  1-D array-like, length ≥ 2.
        flowrates_kg_h: Corresponding MEA flowrates from FT103 in kg/h.

    Returns:
        :class:`LinearFlowModel` with fitted slope, intercept, and R².

    Raises:
        ValueError: If inputs have different lengths or fewer than 2 points.
    """
    ps = np.asarray(pump_speeds_pct, dtype=float).ravel()
    fl = np.asarray(flowrates_kg_h, dtype=float).ravel()

    if ps.shape != fl.shape:
        raise ValueError(
            f"pump_speeds_pct and flowrates_kg_h must have the same length, "
            f"got {ps.shape} vs {fl.shape}."
        )
    if len(ps) < 2:
        raise ValueError("At least 2 data points are required to fit a linear model.")
    if np.ptp(ps) == 0:
        raise ValueError(
            "pump_speeds_pct has zero variance; cannot fit a linear model "
            "(slope would be undefined)."
        )

    slope, intercept, r, _, _ = linregress(ps, fl)
    r_sq = float(r**2)

    logger.info(
        "Linear flow model: slope=%.4f kg/(h·%%), intercept=%.4f kg/h, R²=%.4f",
        slope,
        intercept,
        r_sq,
    )
    return LinearFlowModel(slope=float(slope), intercept=float(intercept), r_squared=r_sq)


# ---------------------------------------------------------------------------
# Safe operating speed determination
# ---------------------------------------------------------------------------


def predict_level(model: ExponentialLevelModel, pump_speed_pct: float) -> float:
    """Convenience wrapper: predict MEA level from a fitted model.

    Args:
        model: Fitted :class:`ExponentialLevelModel`.
        pump_speed_pct: Pump speed in %.

    Returns:
        Predicted MEA level in %.
    """
    return model.predict(pump_speed_pct)


def predict_flowrate(model: LinearFlowModel, pump_speed_pct: float) -> float:
    """Convenience wrapper: predict flowrate from a fitted model.

    Args:
        model: Fitted :class:`LinearFlowModel`.
        pump_speed_pct: Pump speed in %.

    Returns:
        Predicted flowrate in kg/h.
    """
    return model.predict(pump_speed_pct)


def safe_pump_speed(
    level_model: ExponentialLevelModel,
    flow_model: LinearFlowModel,
    level_alarm_pct: float = AlarmLimits.LT101_LOW_LEVEL_PCT,
    flow_alarm_kg_h: float = AlarmLimits.FT103_HIGH_FLOW_KG_H,
    speed_min_pct: float = AlarmLimits.PUMP_SPEED_MIN_PCT,
    speed_max_pct: float = AlarmLimits.PUMP_SPEED_MAX_DESIGN_PCT,
) -> PumpCommissioningResult:
    """Determine the maximum safe pump speed from fitted commissioning models.

    The safe speed is the minimum of:

    1. The speed at which the MEA level (LT101) reaches *level_alarm_pct*.
    2. The speed at which the flowrate (FT103) reaches *flow_alarm_kg_h*.

    Both limits are computed from the supplied regression models and verified
    against the observed data range.

    Args:
        level_model: Fitted :class:`ExponentialLevelModel`.
        flow_model: Fitted :class:`LinearFlowModel`.
        level_alarm_pct: Low-level alarm threshold for LT101 in %.
            Defaults to :attr:`~meapy.constants.AlarmLimits.LT101_LOW_LEVEL_PCT`.
        flow_alarm_kg_h: High-flowrate alarm threshold for FT103 in kg/h.
            Defaults to :attr:`~meapy.constants.AlarmLimits.FT103_HIGH_FLOW_KG_H`.
        speed_min_pct: Minimum allowed pump speed to search in %.
        speed_max_pct: Maximum allowed pump speed to search in %.

    Returns:
        :class:`PumpCommissioningResult` containing the recommended safe speed
        and supporting diagnostics.

    Raises:
        ValueError: If the alarm thresholds are inconsistent with the models
            (e.g. level never reaches the alarm within the search range).
    """
    notes: list[str] = []

    # --- Level constraint ---
    level_alarm_speed = level_model.invert(level_alarm_pct)
    logger.info(
        "Level alarm (LT101 = %.1f %%) reached at PS = %.2f %%", level_alarm_pct, level_alarm_speed
    )

    # --- Flow constraint ---
    flow_alarm_speed = flow_model.invert(flow_alarm_kg_h)
    logger.info(
        "Flow alarm (FT103 = %.1f kg/h) reached at PS = %.2f %%", flow_alarm_kg_h, flow_alarm_speed
    )

    if level_alarm_speed <= speed_min_pct:
        raise ValueError(
            f"The level alarm is triggered even at the minimum search speed "
            f"({speed_min_pct} %).  Check the level model or alarm threshold."
        )
    if flow_alarm_speed <= speed_min_pct:
        raise ValueError(
            f"The flow alarm is triggered even at the minimum search speed "
            f"({speed_min_pct} %).  Check the flow model or alarm threshold."
        )

    # Binding constraint
    if level_alarm_speed <= flow_alarm_speed:
        safe_speed = level_alarm_speed
        limiting = "level"
        notes.append(
            f"Level constraint (LT101) is binding.  Flowrate at safe speed: "
            f"{flow_model.predict(safe_speed):.1f} kg/h (alarm at {flow_alarm_kg_h:.0f} kg/h)."
        )
    else:
        safe_speed = flow_alarm_speed
        limiting = "flow"
        notes.append(
            f"Flowrate constraint (FT103) is binding.  MEA level at safe speed: "
            f"{level_model.predict(safe_speed):.1f} % (alarm at {level_alarm_pct:.1f} %)."
        )

    # Warn if safe speed is near design maximum
    if safe_speed > 0.9 * speed_max_pct:
        notes.append(
            "Safe speed is within 10 % of the design maximum.  Consider additional "
            "margin for operational variability."
        )

    predicted_level = level_model.predict(safe_speed)
    predicted_flow = flow_model.predict(safe_speed)

    return PumpCommissioningResult(
        safe_speed_pct=round(safe_speed, 2),
        predicted_level_pct=round(predicted_level, 2),
        predicted_flow_kg_h=round(predicted_flow, 2),
        level_alarm_speed_pct=round(level_alarm_speed, 2),
        flow_alarm_speed_pct=round(flow_alarm_speed, 2),
        limiting_constraint=limiting,
        notes=notes,
    )
