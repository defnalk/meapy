"""Utility functions for data handling, unit conversions, and I/O.

This module provides helper functions that are shared across the meapy
sub-modules, including steady-state detection, unit conversions, and
simple statistical helpers.

Typical usage example::

    from meapy.utils import steady_state_mean, kg_h_to_mol_s, summarise_array

    mean_val = steady_state_mean([45.1, 45.3, 45.2, 45.4], window=3, tol=0.5)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

__all__ = [
    "steady_state_mean",
    "kg_h_to_mol_s",
    "mol_s_to_kg_h",
    "celsius_to_kelvin",
    "kelvin_to_celsius",
    "summarise_array",
    "rolling_mean",
]

logger = logging.getLogger(__name__)


def steady_state_mean(
    values: Sequence[float],
    window: int = 3,
    tol: float = 1.0,
) -> float:
    """Return the mean of the trailing *window* values if they satisfy a steady-state criterion.

    A reading window is considered steady-state when the peak-to-peak
    variation within the window is ≤ *tol*.

    Args:
        values: Time-series of measurements.  Length must be ≥ *window*.
        window: Number of trailing readings to include in the mean.
        tol: Maximum allowable peak-to-peak variation within the window.

    Returns:
        Arithmetic mean of the trailing *window* values.

    Raises:
        ValueError: If *values* has fewer than *window* entries, *window* < 1,
            or *tol* < 0.
        RuntimeError: If the trailing window does not satisfy the
            steady-state criterion.

    Example::

        >>> steady_state_mean([45.0, 45.1, 45.2, 45.1], window=3, tol=0.5)
        45.13333333333333
    """
    if window < 1:
        raise ValueError(f"window must be ≥ 1, got {window!r}.")
    if tol < 0:
        raise ValueError(f"tol must be non-negative, got {tol!r}.")
    vals = list(values)
    if len(vals) < window:
        raise ValueError(
            f"Need at least {window} values to compute a steady-state mean, got {len(vals)}."
        )

    tail = vals[-window:]
    spread = max(tail) - min(tail)
    if spread > tol:
        raise RuntimeError(
            f"Steady-state criterion not met: peak-to-peak variation in the "
            f"trailing {window} readings is {spread:.4g}, which exceeds the "
            f"tolerance of {tol:.4g}."
        )
    mean = float(np.mean(tail))
    logger.debug("steady_state_mean: window=%d, spread=%.4g, mean=%.6g", window, spread, mean)
    return mean


def kg_h_to_mol_s(
    flow_kg_h: float,
    molar_mass_g_mol: float,
) -> float:
    """Convert a mass flowrate from kg/h to mol/s.

    Args:
        flow_kg_h: Mass flowrate in kg/h.  Must be non-negative.
        molar_mass_g_mol: Molar mass of the species in g/mol.  Must be positive.

    Returns:
        Molar flowrate in mol/s.

    Raises:
        ValueError: If *flow_kg_h* is negative or *molar_mass_g_mol* ≤ 0.

    Example::

        >>> round(kg_h_to_mol_s(44.01, 44.01), 6)
        0.277778
    """
    if flow_kg_h < 0:
        raise ValueError(f"flow_kg_h must be non-negative, got {flow_kg_h!r}.")
    if molar_mass_g_mol <= 0:
        raise ValueError(f"molar_mass_g_mol must be positive, got {molar_mass_g_mol!r}.")
    return flow_kg_h * 1_000.0 / (molar_mass_g_mol * 3_600.0)


def mol_s_to_kg_h(
    flow_mol_s: float,
    molar_mass_g_mol: float,
) -> float:
    """Convert a molar flowrate from mol/s to kg/h.

    Args:
        flow_mol_s: Molar flowrate in mol/s.  Must be non-negative.
        molar_mass_g_mol: Molar mass of the species in g/mol.  Must be positive.

    Returns:
        Mass flowrate in kg/h.

    Raises:
        ValueError: If *flow_mol_s* is negative or *molar_mass_g_mol* ≤ 0.
    """
    if flow_mol_s < 0:
        raise ValueError(f"flow_mol_s must be non-negative, got {flow_mol_s!r}.")
    if molar_mass_g_mol <= 0:
        raise ValueError(f"molar_mass_g_mol must be positive, got {molar_mass_g_mol!r}.")
    return flow_mol_s * molar_mass_g_mol * 3_600.0 / 1_000.0


def celsius_to_kelvin(t_c: float) -> float:
    """Convert a temperature from Celsius to Kelvin.

    Args:
        t_c: Temperature in °C.  Must be ≥ −273.15 K.

    Returns:
        Temperature in K.

    Raises:
        ValueError: If *t_c* is below absolute zero.
    """
    if t_c < -273.15:
        raise ValueError(f"Temperature {t_c} °C is below absolute zero.")
    return t_c + 273.15


def kelvin_to_celsius(t_k: float) -> float:
    """Convert a temperature from Kelvin to Celsius.

    Args:
        t_k: Temperature in K.  Must be non-negative.

    Returns:
        Temperature in °C.

    Raises:
        ValueError: If *t_k* is negative.
    """
    if t_k < 0:
        raise ValueError(f"Temperature {t_k} K is negative; unphysical.")
    return t_k - 273.15


def summarise_array(arr: npt.ArrayLike) -> dict[str, float]:
    """Return basic descriptive statistics for a numeric array.

    Args:
        arr: 1-D numeric array-like.

    Returns:
        Dictionary with keys ``mean``, ``std``, ``min``, ``max``, and ``n``.

    Raises:
        ValueError: If *arr* is empty.
    """
    a = np.asarray(arr, dtype=float).ravel()
    if a.size == 0:
        raise ValueError("Cannot summarise an empty array.")
    return {
        "mean": float(np.mean(a)),
        "std": float(np.std(a, ddof=1)) if a.size > 1 else 0.0,
        "min": float(np.min(a)),
        "max": float(np.max(a)),
        "n": float(a.size),
    }


def rolling_mean(arr: npt.ArrayLike, window: int) -> npt.NDArray[np.float64]:
    """Compute a simple (un-weighted) rolling mean with edge padding.

    Args:
        arr: 1-D numeric array-like.
        window: Number of elements to include in each rolling window.  Must be ≥ 1.

    Returns:
        Array of the same length as *arr* containing the rolling means.
        Leading values where a full window is not available are computed
        using a progressively expanding window.

    Raises:
        ValueError: If *window* < 1.
    """
    if window < 1:
        raise ValueError(f"window must be ≥ 1, got {window!r}.")
    a = np.asarray(arr, dtype=float).ravel()
    result = np.empty_like(a)
    for i in range(len(a)):
        start = max(0, i - window + 1)
        result[i] = np.mean(a[start : i + 1])
    return result
