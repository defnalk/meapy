"""Mass transfer analysis for packed-bed CO₂ absorption columns.

Implements the two-film theory formulation used to characterise counter-current
gas–liquid mass transfer in MEA absorption columns, including:

* Overall volumetric gas-phase mass transfer coefficient K_OGa
* Mole-ratio ↔ mole-fraction conversions
* Composition profiling along the column height
* NTU and HOG calculations for column design

The model follows the derivation in Treybal (1981) and the notation adopted
by the Imperial College pilot-plant analysis (Hale, 2025, Appendix I).

Typical usage example::

    from meapy.mass_transfer import koga_from_flux, composition_profile

    koga = koga_from_flux(
        inert_gas_flow_mol_s=0.012,
        cross_section_m2=7.854e-3,
        packed_height_m=1.0,
        y_bottom=0.14,
        y_top=0.02,
    )
    print(f"K_OGa = {koga:.2f} kmol/(m³·h)")
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from meapy._validation import require_in_range, require_positive

__all__ = [
    "mole_ratio_to_fraction",
    "mole_fraction_to_ratio",
    "koga_from_flux",
    "koga_profile",
    "composition_profile",
    "ntu_og",
    "hog",
    "absorption_factor",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mole-fraction / mole-ratio conversions
# ---------------------------------------------------------------------------


def mole_fraction_to_ratio(y: float) -> float:
    """Convert a gas-phase mole fraction to mole ratio Y = y / (1 − y).

    Args:
        y: Mole fraction of CO₂ in the gas phase.  Must satisfy 0 ≤ y < 1.

    Returns:
        Mole ratio Y (mol CO₂ / mol inert N₂).

    Raises:
        ValueError: If *y* is outside the range [0, 1).

    Example::

        >>> round(mole_fraction_to_ratio(0.12), 6)
        0.136364
    """
    if not (0.0 <= y < 1.0):
        raise ValueError(
            f"Mole fraction y must be in [0, 1), got {y!r}. "
            "A value >= 1 is not physically meaningful for a binary mixture."
        )
    return y / (1.0 - y)


def mole_ratio_to_fraction(Y: float) -> float:
    """Convert a gas-phase mole ratio Y to mole fraction y = Y / (1 + Y).

    Args:
        Y: Mole ratio Y (mol CO₂ / mol inert).  Must be non-negative.

    Returns:
        Mole fraction y.

    Raises:
        ValueError: If *Y* is negative.

    Example::

        >>> round(mole_ratio_to_fraction(0.136364), 6)
        0.12
    """
    if Y < 0.0:
        raise ValueError(f"Mole ratio Y must be non-negative, got {Y!r}.")
    return Y / (1.0 + Y)


# ---------------------------------------------------------------------------
# K_OGa — overall volumetric mass transfer coefficient
# ---------------------------------------------------------------------------


def koga_from_flux(
    inert_gas_flow_mol_s: float,
    cross_section_m2: float,
    packed_height_m: float,
    y_bottom: float,
    y_top: float,
) -> float:
    """Calculate K_OGa for a column section using the log-ratio driving force.

    Derived from two-film theory under dilute-solution / Henry's law
    assumptions (Treybal, 1981; Imperial College Hale 2025, Eq. I.2.2.7):

    K_OGa = (V' / (A_c · H)) · ln(Y_bottom / Y_top)

    where V' is the molar flowrate of inert gas (N₂), A_c is the column
    cross-sectional area, and H is the packed height of the section.

    Args:
        inert_gas_flow_mol_s: Molar flowrate of the inert carrier gas (N₂)
            in mol/s.  Must be positive.
        cross_section_m2: Column cross-sectional area in m².  Must be positive.
        packed_height_m: Height of the packed section being analysed in m.
            Must be positive.
        y_bottom: CO₂ mole fraction at the bottom of the section.  Must be
            in (0, 1).
        y_top: CO₂ mole fraction at the top of the section.  Must satisfy
            0 < y_top < y_bottom.

    Returns:
        K_OGa in mol/(m³·s).

    Raises:
        ValueError: If any argument violates the constraints above, or if the
            concentration profile implies upward mass transfer (y_top ≥ y_bottom).

    Example::

        >>> round(koga_from_flux(0.012, 7.854e-3, 1.0, 0.14, 0.02), 4)
        12.3695
    """
    require_positive("inert_gas_flow_mol_s", inert_gas_flow_mol_s)
    require_positive("cross_section_m2", cross_section_m2)
    require_positive("packed_height_m", packed_height_m)
    require_in_range("y_bottom", y_bottom, 0.0, 1.0, lo_inclusive=False, hi_inclusive=False)
    require_in_range("y_top", y_top, 0.0, 1.0, lo_inclusive=False, hi_inclusive=False)
    if y_top >= y_bottom:
        raise ValueError(
            f"y_top ({y_top}) must be less than y_bottom ({y_bottom}) for absorption. "
            "If y_top ≥ y_bottom the column section shows no net absorption — check "
            "data quality (possible analyser calibration issue)."
        )

    Y_bottom = mole_fraction_to_ratio(y_bottom)
    Y_top = mole_fraction_to_ratio(y_top)

    koga = (inert_gas_flow_mol_s / (cross_section_m2 * packed_height_m)) * math.log(
        Y_bottom / Y_top
    )
    logger.debug(
        "K_OGa = %.4f mol/(m³·s)  [V'=%.4f mol/s, Ac=%.4e m², H=%.2f m, Y_B/Y_T=%.4f]",
        koga,
        inert_gas_flow_mol_s,
        cross_section_m2,
        packed_height_m,
        Y_bottom / Y_top,
    )
    return koga


def koga_to_kmol_m3_h(koga_mol_m3_s: float) -> float:
    """Convert K_OGa from mol/(m³·s) to kmol/(m³·h).

    Args:
        koga_mol_m3_s: K_OGa in mol/(m³·s).

    Returns:
        K_OGa in kmol/(m³·h).
    """
    return koga_mol_m3_s * 3.6  # ×3600 s/h ÷ 1000 mol/kmol


def koga_profile(
    inert_gas_flow_mol_s: float,
    cross_section_m2: float,
    sampling_heights_m: Sequence[float],
    y_values: Sequence[float],
) -> npt.NDArray[np.float64]:
    """Compute a K_OGa profile for sequential column sections.

    Iterates over adjacent pairs of sampling ports (bottom → top) and applies
    :func:`koga_from_flux` to each segment.  Sections where absorption is
    absent (y_top ≥ y_bottom) are assigned ``np.nan`` with a logged warning.

    Args:
        inert_gas_flow_mol_s: Molar flowrate of inert gas in mol/s.
        cross_section_m2: Column cross-sectional area in m².
        sampling_heights_m: Ordered sequence of sampling port heights in m,
            from bottom (port 1) to top (port 6).  Length N.
        y_values: CO₂ mole fractions at each sampling port, ordered to match
            *sampling_heights_m*.  Length N.

    Returns:
        NumPy array of K_OGa values in kmol/(m³·h) for each of the N−1
        inter-port sections.  Problematic sections contain ``np.nan``.

    Raises:
        ValueError: If *sampling_heights_m* and *y_values* have different lengths,
            or if fewer than two ports are provided.
    """
    heights = list(sampling_heights_m)
    y_vals = list(y_values)

    if len(heights) != len(y_vals):
        raise ValueError(
            f"sampling_heights_m and y_values must have the same length, "
            f"got {len(heights)} and {len(y_vals)}."
        )
    if len(heights) < 2:
        raise ValueError("At least two sampling ports are required to compute a profile.")

    n_sections = len(heights) - 1
    result = np.full(n_sections, np.nan)

    for i in range(n_sections):
        h_bot, h_top = heights[i], heights[i + 1]
        y_bot, y_top = y_vals[i], y_vals[i + 1]
        section_height = h_top - h_bot

        try:
            koga_si = koga_from_flux(
                inert_gas_flow_mol_s, cross_section_m2, section_height, y_bot, y_top
            )
            result[i] = koga_to_kmol_m3_h(koga_si)
        except ValueError as exc:
            logger.warning(
                "Section %d–%d (%.2f–%.2f m): K_OGa set to NaN.  Reason: %s",
                i + 1,
                i + 2,
                h_bot,
                h_top,
                exc,
            )

    return result


# ---------------------------------------------------------------------------
# Composition profile
# ---------------------------------------------------------------------------


def composition_profile(
    sampling_heights_m: Sequence[float],
    co2_volume_pct: Sequence[float],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Build a CO₂ mole-fraction profile from gas-analyser readings.

    Converts volume-percent CO₂ (from the IR gas analysers) to mole fractions,
    assuming ideal-gas behaviour (volume % ≈ mole % at low concentrations).

    Args:
        sampling_heights_m: Heights of the sampling ports in m.
        co2_volume_pct: CO₂ concentration measured by the gas analyser at each
            port in vol%.  Values must be in [0, 100].

    Returns:
        A tuple ``(heights, y_co2)`` of NumPy arrays, where *heights* is in m
        and *y_co2* is dimensionless mole fraction.

    Raises:
        ValueError: If lengths differ or any concentration is outside [0, 100].
    """
    h = np.asarray(sampling_heights_m, dtype=float)
    pct = np.asarray(co2_volume_pct, dtype=float)

    if h.shape != pct.shape:
        raise ValueError(
            f"sampling_heights_m and co2_volume_pct must have the same shape, "
            f"got {h.shape} vs {pct.shape}."
        )
    if np.any(pct < 0) or np.any(pct > 100):
        raise ValueError(
            f"All CO₂ concentrations must be in [0, 100] vol%.  "
            f"Found min={pct.min():.2f}, max={pct.max():.2f}."
        )

    y_co2 = pct / 100.0
    logger.debug(
        "composition_profile: %d ports, y_CO2 range [%.4f, %.4f]", len(h), y_co2.min(), y_co2.max()
    )
    return h, y_co2


# ---------------------------------------------------------------------------
# Column design metrics
# ---------------------------------------------------------------------------


def ntu_og(
    y_bottom: float,
    y_top: float,
    m_slope: float = 0.0,
    x_in: float = 0.0,
    absorption_factor_val: float | None = None,
) -> float:
    """Compute the Number of Transfer Units (NTU_OG) for a packed absorber.

    When *m_slope* is zero (default), returns the dilute-system
    approximation NTU_OG ≈ ln(Y_bottom / Y_top).

    When *m_slope* > 0 and *absorption_factor_val* is given, applies the
    Kremser/Colburn equation for an absorber with linear equilibrium
    y* = m · x (Treybal, 1981; Coulson & Richardson Vol 2, Ch 11):

    NTU_OG = ln[(1 − 1/A)(y_in − m·x_in)/(y_out − m·x_in) + 1/A]
             / (1 − 1/A)

    where A = L / (m · G) is the absorption factor.

    Special cases handled internally:
    * A → ∞ (excess solvent, x_in = 0): NTU_OG → ln(y_in / y_out)
    * A = 1: NTU_OG = (y_in − y_out) / (y_out − m · x_in)

    Args:
        y_bottom: CO₂ mole fraction entering the absorber (bottom, = y_in).
        y_top: CO₂ mole fraction leaving the absorber (top, = y_out).
        m_slope: Henry's law slope m = y*/x (dimensionless).  Set to 0
            (default) to neglect equilibrium back-pressure.
        x_in: Liquid-phase mole fraction at the solvent inlet (top of
            absorber).  Only used when *m_slope* > 0.
        absorption_factor_val: Absorption factor A = L/(m·G).  Required
            when *m_slope* > 0.

    Returns:
        Dimensionless NTU_OG.

    Raises:
        ValueError: If *y_top* ≥ *y_bottom*, fractions are outside (0, 1),
            *m_slope* > 0 without *absorption_factor_val*, or
            *absorption_factor_val* ≤ 0.
    """
    for name, val in (("y_bottom", y_bottom), ("y_top", y_top)):
        if not (0.0 < val < 1.0):
            raise ValueError(f"{name} must be in (0, 1), got {val!r}.")
    if y_top >= y_bottom:
        raise ValueError(f"y_top ({y_top}) must be < y_bottom ({y_bottom}) for absorption.")

    # --- Dilute-system approximation (backward-compatible default) ----------
    if m_slope == 0.0:
        Y_b = mole_fraction_to_ratio(y_bottom)
        Y_t = mole_fraction_to_ratio(y_top)
        return math.log(Y_b / Y_t)

    # --- Kremser / Colburn equation -----------------------------------------
    if m_slope < 0.0:
        raise ValueError(f"m_slope must be non-negative, got {m_slope!r}.")
    if absorption_factor_val is None:
        raise ValueError(
            "absorption_factor_val (A = L/(m·G)) is required when m_slope > 0."
        )
    if absorption_factor_val <= 0.0:
        raise ValueError(
            f"absorption_factor_val must be positive, got {absorption_factor_val!r}."
        )

    A = absorption_factor_val
    y_in = y_bottom
    y_out = y_top
    y_star_in = m_slope * x_in  # equilibrium back-pressure at solvent inlet

    if y_out <= y_star_in:
        raise ValueError(
            f"y_out ({y_out}) must exceed m·x_in ({y_star_in}) for a feasible "
            "driving force at the top of the absorber."
        )

    ratio = (y_in - y_star_in) / (y_out - y_star_in)

    # Handle A ≈ 1 limit analytically: NTU_OG = (y_in − y_out)/(y_out − m·x_in)
    if math.isclose(A, 1.0, rel_tol=1e-8):
        ntu_val = (y_in - y_out) / (y_out - y_star_in)
    else:
        inv_A = 1.0 / A
        ntu_val = math.log((1.0 - inv_A) * ratio + inv_A) / (1.0 - inv_A)

    logger.debug(
        "ntu_og (Kremser): A=%.4f, y_in=%.4f, y_out=%.4f, m=%.4f, x_in=%.4f → NTU=%.4f",
        A, y_in, y_out, m_slope, x_in, ntu_val,
    )
    return ntu_val


def hog(
    koga_mol_m3_s: float,
    inert_gas_flux_mol_m2_s: float,
) -> float:
    """Compute the Height of a Transfer Unit H_OG = G' / (K_OGa).

    Args:
        koga_mol_m3_s: Overall volumetric mass transfer coefficient in mol/(m³·s).
        inert_gas_flux_mol_m2_s: Superficial molar flux of inert gas G' = V'/A_c
            in mol/(m²·s).

    Returns:
        H_OG in metres.

    Raises:
        ValueError: If either argument is non-positive.
    """
    require_positive("koga_mol_m3_s", koga_mol_m3_s)
    require_positive("inert_gas_flux_mol_m2_s", inert_gas_flux_mol_m2_s)
    return inert_gas_flux_mol_m2_s / koga_mol_m3_s


def absorption_factor(
    liquid_flow_mol_s: float,
    gas_flow_mol_s: float,
    m_slope: float,
) -> float:
    """Compute the absorption factor A = L / (m · G).

    The absorption factor determines the relative capacity of the liquid
    to absorb the solute compared with the equilibrium demand.  A > 1 is
    required for feasible absorption.

    Args:
        liquid_flow_mol_s: Molar flowrate of the absorbent liquid (MEA) in mol/s.
        gas_flow_mol_s: Molar flowrate of the carrier gas in mol/s.
        m_slope: Henry's law equilibrium constant m = y*/x.

    Returns:
        Dimensionless absorption factor A.

    Raises:
        ValueError: If any argument is non-positive.
    """
    require_positive("liquid_flow_mol_s", liquid_flow_mol_s)
    require_positive("gas_flow_mol_s", gas_flow_mol_s)
    require_positive("m_slope", m_slope)
    a = liquid_flow_mol_s / (m_slope * gas_flow_mol_s)
    logger.debug("absorption factor A = %.4f", a)
    return a
