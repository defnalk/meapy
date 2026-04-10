"""Shared input-validation helpers (private module).

Centralises the ``if x <= 0: raise ValueError(...)`` pattern that
recurs across public modules.  Not part of the public API.
"""

from __future__ import annotations

import logging
from collections.abc import Sized

__all__: list[str] = []  # private — nothing exported

logger = logging.getLogger(__name__)


def require_positive(name: str, value: float) -> None:
    """Raise :exc:`ValueError` if *value* is not strictly positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value!r}.")


def require_non_negative(name: str, value: float) -> None:
    """Raise :exc:`ValueError` if *value* is negative."""
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value!r}.")


def require_in_range(
    name: str,
    value: float,
    lo: float,
    hi: float,
    *,
    lo_inclusive: bool = True,
    hi_inclusive: bool = False,
) -> None:
    """Raise :exc:`ValueError` if *value* falls outside [lo, hi) (default).

    Bracket style is controlled by *lo_inclusive* and *hi_inclusive*.
    """
    lo_ok = value >= lo if lo_inclusive else value > lo
    hi_ok = value <= hi if hi_inclusive else value < hi
    if not (lo_ok and hi_ok):
        lo_br = "[" if lo_inclusive else "("
        hi_br = "]" if hi_inclusive else ")"
        raise ValueError(
            f"{name} must be in {lo_br}{lo}, {hi}{hi_br}, got {value!r}."
        )


def require_same_length(**arrays: Sized) -> None:
    """Raise :exc:`ValueError` if the passed arrays differ in length.

    Usage::

        require_same_length(speeds=ps_array, levels=lev_array)
    """
    if not arrays:
        return
    items = list(arrays.items())
    ref_name, ref_arr = items[0]
    ref_len = len(ref_arr)
    for arr_name, arr in items[1:]:
        if len(arr) != ref_len:
            raise ValueError(
                f"{ref_name} and {arr_name} must have the same length, "
                f"got {ref_len} and {len(arr)}."
            )
