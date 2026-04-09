"""Heat exchanger analysis for MEA-based carbon capture pilot plants.

This module provides functions for analysing shell-and-plate heat exchangers
commonly found in post-combustion carbon capture systems, including:

* Duty calculations for hot and cold streams (Q_hot, Q_cold)
* Energy loss quantification
* Log Mean Temperature Difference (LMTD) for counter-current operation
* Overall heat transfer coefficient *U*
* Thermal efficiency and NTU-effectiveness

The formulations match those presented in the Imperial College pilot-plant
analysis (Hale, 2025) and are consistent with standard chemical engineering
references (Coulson & Richardson, Vol. 1).

Typical usage example::

    import numpy as np
    from meapy.heat_transfer import (
        stream_duty,
        energy_loss,
        lmtd_counter_current,
        overall_heat_transfer_coefficient,
        efficiency,
        effectiveness,
    )

    Q_h = stream_duty(mass_flow_kg_s=0.25, cp_j_kg_k=3940, t_in=85, t_out=42)
    Q_c = stream_duty(mass_flow_kg_s=0.22, cp_j_kg_k=3940, t_in=30, t_out=68)
    U   = overall_heat_transfer_coefficient(Q_h, lmtd_counter_current(85, 42, 30, 68), area=0.30)
"""

from __future__ import annotations

import logging
import math

from meapy.constants import HeatExchangerParams

__all__ = [
    "stream_duty",
    "energy_loss",
    "lmtd_counter_current",
    "lmtd_co_current",
    "overall_heat_transfer_coefficient",
    "efficiency",
    "effectiveness",
    "ntu",
    "heat_capacity_rate",
    "analyse_exchanger",
]

logger = logging.getLogger(__name__)

# Convenience alias
_CONV = HeatExchangerParams.FLOW_UNIT_CONVERSION  # kg/h → kg/s


# ---------------------------------------------------------------------------
# Low-level building blocks
# ---------------------------------------------------------------------------


def stream_duty(
    mass_flow_kg_s: float,
    cp_j_kg_k: float,
    t_in_c: float,
    t_out_c: float,
) -> float:
    """Compute the sensible heat duty of a single stream.

    Uses Q = ṁ · cₚ · ΔT.  The sign of the result encodes the direction of
    heat flow: positive → heat absorbed (cold stream), negative → heat released
    (hot stream).

    Args:
        mass_flow_kg_s: Mass flowrate in kg/s.  Must be positive.
        cp_j_kg_k: Specific heat capacity in J/(kg·K).  Must be positive.
        t_in_c: Inlet temperature in °C.
        t_out_c: Outlet temperature in °C.

    Returns:
        Heat duty in watts (W).  Positive for a cold stream, negative for a
        hot stream.

    Raises:
        ValueError: If *mass_flow_kg_s* or *cp_j_kg_k* are not positive.

    Example::

        >>> stream_duty(0.25, 3940, 85, 42)
        -42505.0
    """
    if mass_flow_kg_s <= 0:
        raise ValueError(f"mass_flow_kg_s must be positive, got {mass_flow_kg_s!r}.")
    if cp_j_kg_k <= 0:
        raise ValueError(f"cp_j_kg_k must be positive, got {cp_j_kg_k!r}.")

    duty = mass_flow_kg_s * cp_j_kg_k * (t_out_c - t_in_c)
    logger.debug(
        "stream_duty: ṁ=%.4f kg/s, cₚ=%.1f J/(kg·K), ΔT=%.2f K → Q=%.2f W",
        mass_flow_kg_s,
        cp_j_kg_k,
        t_out_c - t_in_c,
        duty,
    )
    return duty


def energy_loss(q_hot_w: float, q_cold_w: float) -> float:
    """Compute the absolute energy-balance imbalance between hot and cold duties.

    Q_loss = |Q_hot + Q_cold|

    A perfect (adiabatic) exchanger has Q_loss = 0.  Any non-zero value
    represents unmeasured losses to the surroundings or instrumentation error.

    Args:
        q_hot_w: Duty of the hot stream in W (typically negative).
        q_cold_w: Duty of the cold stream in W (typically positive).

    Returns:
        Absolute energy loss in watts.

    Example::

        >>> energy_loss(-42505, 40100)
        2405.0
    """
    loss = abs(q_hot_w + q_cold_w)
    logger.debug("energy_loss: Q_hot=%.2f W, Q_cold=%.2f W → loss=%.2f W", q_hot_w, q_cold_w, loss)
    return loss


def lmtd_counter_current(
    t_hot_in_c: float,
    t_hot_out_c: float,
    t_cold_in_c: float,
    t_cold_out_c: float,
) -> float:
    """Calculate the Log Mean Temperature Difference for counter-current flow.

    ΔT_lm = (ΔT₁ − ΔT₂) / ln(ΔT₁ / ΔT₂)

    where ΔT₁ = T_hot_in − T_cold_out (hot end) and
          ΔT₂ = T_hot_out − T_cold_in  (cold end).

    Args:
        t_hot_in_c: Hot-stream inlet temperature in °C.
        t_hot_out_c: Hot-stream outlet temperature in °C.
        t_cold_in_c: Cold-stream inlet temperature in °C.
        t_cold_out_c: Cold-stream outlet temperature in °C.

    Returns:
        LMTD in K (equivalent to °C for differences).

    Raises:
        ValueError: If either terminal ΔT is non-positive, or if the resulting
            LMTD would be undefined (e.g. thermodynamic crossover).

    Example::

        >>> round(lmtd_counter_current(85, 42, 30, 68), 2)
        23.09
    """
    delta_t1 = t_hot_in_c - t_cold_out_c  # hot end
    delta_t2 = t_hot_out_c - t_cold_in_c  # cold end

    if delta_t1 <= 0 or delta_t2 <= 0:
        raise ValueError(
            f"Both terminal temperature differences must be positive for a valid "
            f"counter-current LMTD.  Got ΔT₁={delta_t1:.2f} K, ΔT₂={delta_t2:.2f} K.  "
            "Check for temperature crossover or reversed stream assignment."
        )

    if math.isclose(delta_t1, delta_t2, rel_tol=1e-6):
        # Avoid ln(1) = 0 division; limit equals ΔT directly
        lmtd = delta_t1
    else:
        lmtd = (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)

    logger.debug(
        "LMTD (counter-current): ΔT₁=%.3f K, ΔT₂=%.3f K → LMTD=%.4f K", delta_t1, delta_t2, lmtd
    )
    return lmtd


def lmtd_co_current(
    t_hot_in_c: float,
    t_hot_out_c: float,
    t_cold_in_c: float,
    t_cold_out_c: float,
) -> float:
    """Calculate the Log Mean Temperature Difference for co-current (parallel) flow.

    Args:
        t_hot_in_c: Hot-stream inlet temperature in °C.
        t_hot_out_c: Hot-stream outlet temperature in °C.
        t_cold_in_c: Cold-stream inlet temperature in °C.
        t_cold_out_c: Cold-stream outlet temperature in °C.

    Returns:
        LMTD in K.

    Raises:
        ValueError: If either terminal ΔT is non-positive.
    """
    delta_t1 = t_hot_in_c - t_cold_in_c  # inlet end
    delta_t2 = t_hot_out_c - t_cold_out_c  # outlet end

    if delta_t1 <= 0 or delta_t2 <= 0:
        raise ValueError(
            f"Both terminal ΔTs must be positive for co-current LMTD.  "
            f"Got ΔT₁={delta_t1:.2f} K, ΔT₂={delta_t2:.2f} K."
        )

    if math.isclose(delta_t1, delta_t2, rel_tol=1e-6):
        return delta_t1

    return (delta_t1 - delta_t2) / math.log(delta_t1 / delta_t2)


def overall_heat_transfer_coefficient(
    q_w: float,
    lmtd_k: float,
    area_m2: float,
) -> float:
    """Compute the overall heat transfer coefficient U.

    U = Q / (A · ΔT_lm)

    Args:
        q_w: Absolute heat duty in W (use the larger of |Q_hot|, |Q_cold|, or
            their mean; sign is ignored).
        lmtd_k: Log Mean Temperature Difference in K.
        area_m2: Effective heat-transfer area in m².  Must be positive.

    Returns:
        Overall heat transfer coefficient in W/(m²·K).

    Raises:
        ValueError: If *lmtd_k* or *area_m2* are not positive.

    Example::

        >>> round(overall_heat_transfer_coefficient(42505, 23.09, 0.30), 1)
        6136.9
    """
    if lmtd_k <= 0:
        raise ValueError(f"lmtd_k must be positive, got {lmtd_k!r}.")
    if area_m2 <= 0:
        raise ValueError(f"area_m2 must be positive, got {area_m2!r}.")

    u = abs(q_w) / (area_m2 * lmtd_k)
    logger.debug("U = %.2f W/(m²·K)  [Q=%.2f W, A=%.4f m², LMTD=%.4f K]", u, q_w, area_m2, lmtd_k)
    return u


def heat_capacity_rate(mass_flow_kg_s: float, cp_j_kg_k: float) -> float:
    """Compute the heat-capacity rate C = ṁ · cₚ.

    Args:
        mass_flow_kg_s: Mass flowrate in kg/s.
        cp_j_kg_k: Specific heat capacity in J/(kg·K).

    Returns:
        Heat-capacity rate in W/K.

    Raises:
        ValueError: If either argument is non-positive.
    """
    if mass_flow_kg_s <= 0:
        raise ValueError(f"mass_flow_kg_s must be positive, got {mass_flow_kg_s!r}.")
    if cp_j_kg_k <= 0:
        raise ValueError(f"cp_j_kg_k must be positive, got {cp_j_kg_k!r}.")
    return mass_flow_kg_s * cp_j_kg_k


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------


def efficiency(q_cold_w: float, q_hot_w: float) -> float:
    """Compute thermal efficiency η = Q_cold / |Q_hot|.

    An ideal adiabatic exchanger has η = 1.  Values >1 indicate measurement
    inconsistency (e.g. instrumentation drift or heat gain from surroundings).

    Args:
        q_cold_w: Heat absorbed by the cold stream in W (positive).
        q_hot_w: Heat released by the hot stream in W (negative convention, but
            the function accepts either sign).

    Returns:
        Dimensionless efficiency η.

    Raises:
        ValueError: If Q_hot is zero (undefined efficiency).
    """
    if math.isclose(q_hot_w, 0.0, abs_tol=1e-9):
        raise ValueError("q_hot_w must not be zero; efficiency is undefined.")
    eta = q_cold_w / abs(q_hot_w)
    logger.debug("efficiency η = %.4f", eta)
    if eta > 1.0:
        logger.warning(
            "Thermal efficiency η = %.4f exceeds unity (Q_cold=%.2f W, |Q_hot|=%.2f W). "
            "This indicates a measurement inconsistency: instrumentation drift, heat "
            "gain from surroundings, or a swapped hot/cold stream assignment. Verify "
            "transmitter calibration before trusting downstream U/ε/NTU values.",
            eta,
            q_cold_w,
            abs(q_hot_w),
        )
    return eta


def effectiveness(
    q_actual_w: float,
    c_hot_w_k: float,
    c_cold_w_k: float,
    t_hot_in_c: float,
    t_cold_in_c: float,
) -> float:
    """Compute heat exchanger effectiveness ε = Q_actual / Q_max.

    Q_max = C_min · (T_hot_in − T_cold_in)

    Args:
        q_actual_w: Actual heat transferred in W (positive magnitude).
        c_hot_w_k: Heat-capacity rate of the hot stream in W/K.
        c_cold_w_k: Heat-capacity rate of the cold stream in W/K.
        t_hot_in_c: Hot-stream inlet temperature in °C.
        t_cold_in_c: Cold-stream inlet temperature in °C.

    Returns:
        Dimensionless effectiveness ε ∈ [0, 1] for an ideal exchanger.

    Raises:
        ValueError: If the temperature difference is zero or if C_min ≤ 0.
    """
    delta_t_max = t_hot_in_c - t_cold_in_c
    if math.isclose(delta_t_max, 0.0, abs_tol=1e-6):
        raise ValueError(
            "Hot and cold stream inlet temperatures are equal; effectiveness is undefined."
        )

    c_min = min(c_hot_w_k, c_cold_w_k)
    if c_min <= 0:
        raise ValueError(f"C_min must be positive, got {c_min!r}.")

    q_max = c_min * delta_t_max
    eps = abs(q_actual_w) / q_max
    logger.debug("effectiveness ε = %.4f  [Q_actual=%.2f W, Q_max=%.2f W]", eps, q_actual_w, q_max)
    return eps


def ntu(
    u_w_m2_k: float,
    area_m2: float,
    c_min_w_k: float,
) -> float:
    """Compute the Number of Transfer Units for a heat exchanger.

    NTU = U · A / C_min

    Args:
        u_w_m2_k: Overall heat transfer coefficient in W/(m²·K).
        area_m2: Heat-transfer area in m².
        c_min_w_k: Minimum heat-capacity rate C_min in W/K.

    Returns:
        Dimensionless NTU.

    Raises:
        ValueError: If any argument is non-positive.
    """
    for name, val in (("u_w_m2_k", u_w_m2_k), ("area_m2", area_m2), ("c_min_w_k", c_min_w_k)):
        if val <= 0:
            raise ValueError(f"{name} must be positive, got {val!r}.")
    return u_w_m2_k * area_m2 / c_min_w_k


# ---------------------------------------------------------------------------
# High-level convenience wrapper
# ---------------------------------------------------------------------------


def analyse_exchanger(
    *,
    mea_flow_kg_h: float,
    cp_mea_j_kg_k: float,
    t_mea_in_c: float,
    t_mea_out_c: float,
    utility_flow_kg_h: float,
    cp_utility_j_kg_k: float,
    t_utility_in_c: float,
    t_utility_out_c: float,
    area_m2: float,
    flow_direction: str = "counter",
) -> dict[str, float]:
    """Run a complete thermal analysis of a single heat exchanger.

    Computes heat duties, energy loss, LMTD, U, η, ε, and NTU from raw
    transmitter readings.  Intended as the primary entry point for users who
    want a summary dict rather than individual function calls.

    Args:
        mea_flow_kg_h: MEA (process-side) mass flowrate in kg/h.
        cp_mea_j_kg_k: MEA specific heat capacity in J/(kg·K).
        t_mea_in_c: MEA inlet temperature in °C.
        t_mea_out_c: MEA outlet temperature in °C.
        utility_flow_kg_h: Utility-side (cooling water or rich MEA) flowrate in kg/h.
        cp_utility_j_kg_k: Utility specific heat capacity in J/(kg·K).
        t_utility_in_c: Utility inlet temperature in °C.
        t_utility_out_c: Utility outlet temperature in °C.
        area_m2: Effective heat-transfer area in m².
        flow_direction: ``"counter"`` (default) or ``"co"`` for co-current.

    Returns:
        A dictionary with keys:

        * ``q_hot_w`` — hot stream duty (W)
        * ``q_cold_w`` — cold stream duty (W)
        * ``q_loss_w`` — energy imbalance (W)
        * ``lmtd_k`` — log mean temperature difference (K)
        * ``u_w_m2_k`` — overall heat transfer coefficient (W/(m²·K))
        * ``u_kw_m2_k`` — same in kW/(m²·K)
        * ``efficiency`` — η (dimensionless)
        * ``effectiveness`` — ε (dimensionless)
        * ``ntu`` — Number of Transfer Units

    Raises:
        ValueError: If *flow_direction* is not ``"counter"`` or ``"co"``, or if
            any input violates physical constraints.

    Example::

        >>> result = analyse_exchanger(
        ...     mea_flow_kg_h=900, cp_mea_j_kg_k=3940,
        ...     t_mea_in_c=85, t_mea_out_c=42,
        ...     utility_flow_kg_h=800, cp_utility_j_kg_k=3940,
        ...     t_utility_in_c=30, t_utility_out_c=68,
        ...     area_m2=0.30,
        ... )
    """
    if flow_direction not in {"counter", "co"}:
        raise ValueError(f"flow_direction must be 'counter' or 'co', got {flow_direction!r}.")
    if math.isclose(t_mea_in_c, t_utility_in_c, abs_tol=1e-6):
        # Without a driving force there is no hot/cold assignment, LMTD is
        # undefined, and effectiveness divides by zero. Fail up front with a
        # message that names the real cause rather than letting a downstream
        # helper raise something cryptic.
        raise ValueError(
            f"t_mea_in_c ({t_mea_in_c}) and t_utility_in_c ({t_utility_in_c}) "
            "are equal; no driving force, exchanger analysis is undefined."
        )

    mea_kg_s = mea_flow_kg_h * _CONV
    util_kg_s = utility_flow_kg_h * _CONV

    # Determine hot vs cold
    if t_mea_in_c >= t_utility_in_c:
        t_hot_in, t_hot_out = t_mea_in_c, t_mea_out_c
        t_cold_in, t_cold_out = t_utility_in_c, t_utility_out_c
        q_hot = stream_duty(mea_kg_s, cp_mea_j_kg_k, t_mea_in_c, t_mea_out_c)
        q_cold = stream_duty(util_kg_s, cp_utility_j_kg_k, t_utility_in_c, t_utility_out_c)
        c_hot = heat_capacity_rate(mea_kg_s, cp_mea_j_kg_k)
        c_cold = heat_capacity_rate(util_kg_s, cp_utility_j_kg_k)
    else:
        t_hot_in, t_hot_out = t_utility_in_c, t_utility_out_c
        t_cold_in, t_cold_out = t_mea_in_c, t_mea_out_c
        q_hot = stream_duty(util_kg_s, cp_utility_j_kg_k, t_utility_in_c, t_utility_out_c)
        q_cold = stream_duty(mea_kg_s, cp_mea_j_kg_k, t_mea_in_c, t_mea_out_c)
        c_hot = heat_capacity_rate(util_kg_s, cp_utility_j_kg_k)
        c_cold = heat_capacity_rate(mea_kg_s, cp_mea_j_kg_k)

    q_loss = energy_loss(q_hot, q_cold)

    lmtd_fn = lmtd_counter_current if flow_direction == "counter" else lmtd_co_current
    lmtd_val = lmtd_fn(t_hot_in, t_hot_out, t_cold_in, t_cold_out)

    q_ref = (abs(q_hot) + abs(q_cold)) / 2.0
    u_val = overall_heat_transfer_coefficient(q_ref, lmtd_val, area_m2)

    eta = efficiency(q_cold, q_hot)
    eps = effectiveness(q_ref, c_hot, c_cold, t_hot_in, t_cold_in)
    ntu_val = ntu(u_val, area_m2, min(c_hot, c_cold))

    return {
        "q_hot_w": q_hot,
        "q_cold_w": q_cold,
        "q_loss_w": q_loss,
        "lmtd_k": lmtd_val,
        "u_w_m2_k": u_val,
        "u_kw_m2_k": u_val / 1_000.0,
        "efficiency": eta,
        "effectiveness": eps,
        "ntu": ntu_val,
    }
