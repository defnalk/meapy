"""Packed-column hydraulic design calculations.

Provides the :func:`flooding_velocity` function implementing the
Leva/Eckert Generalised Pressure Drop Correlation (GPDC) for packed
absorption columns.

Reference:
    Coulson, J. M., & Richardson, J. F. (2002). *Chemical Engineering
    Volume 2* (5th ed.), Chapter 11 — Liquid–gas systems: packed towers.
    Butterworth-Heinemann.

    Eckert, J. S. (1970). Selecting the proper distillation column packing.
    *Chemical Engineering Progress*, 66(3), 39–44.

    Kister, H. Z. & Gill, D. R. (1991). Predict flood point and pressure
    drop for modern random packings. *Chemical Engineering Progress*,
    87(2), 32–42.

Typical usage example::

    from meapy.column import flooding_velocity

    u_flood, K4, dp = flooding_velocity(
        F_p=200.0,        # packing factor, 1/m
        rho_L=1008.0,     # liquid density, kg/m³
        rho_G=1.2,        # gas density, kg/m³
        mu_L=1.6e-3,      # liquid viscosity, Pa·s
        L_G_ratio=2.5,    # liquid-to-gas mass flow ratio, kg/kg
    )
"""

from __future__ import annotations

import logging
import math

__all__ = ["flooding_velocity"]

logger = logging.getLogger(__name__)

# Physical constants used in the GPDC
_G: float = 9.81  # m/s²
_MU_WATER: float = 1.0e-3  # Pa·s (reference viscosity at 20 °C)

# GPDC flooding-line correlation coefficients (natural-log form).
# Fitted to the Eckert (1970) flooding curve as reproduced in
# Coulson & Richardson Vol 2, Fig 11.44.
#
#     ln(K₄_flood) = c0 + c1·ln(FLV) + c2·(ln(FLV))²
#
_C0: float = -3.5021
_C1: float = -1.028
_C2: float = -0.11093

# Kister & Gill (1991) pressure-drop-at-flooding coefficient (SI).
# Original: ΔP = 0.115 · F_p^0.7  [in H₂O / ft, F_p in ft⁻¹]
# Converted: ΔP (Pa/m) = _KG_COEFF · F_p_m^0.7
# _KG_COEFF = 0.115 · (1/3.28084)^0.7 · 248.84/0.3048 ≈ 40.9
_KG_COEFF: float = 0.115 * (1.0 / 3.28084) ** 0.7 * 248.84 / 0.3048


def flooding_velocity(
    F_p: float,
    rho_L: float,
    rho_G: float,
    mu_L: float,
    L_G_ratio: float,
) -> tuple[float, float, float]:
    """Compute the flooding gas velocity from the Leva/Eckert GPDC.

    Implements the Generalised Pressure Drop Correlation (GPDC) flooding
    line for counter-current gas–liquid flow through random or structured
    packings (Coulson & Richardson Vol 2, Chapter 11, Fig 11.44).

    The capacity parameter at flooding is defined as:

        K₄ = u_G² · F_p · ρ_G · (μ_L / μ_water)^0.1
             / ((ρ_L − ρ_G) · g)

    The flooding line is correlated as:

        ln(K₄) = −3.5021 − 1.028·ln(FLV) − 0.11093·(ln(FLV))²

    where FLV = (L/G)·(ρ_G/ρ_L)^0.5 is the flow parameter.

    Pressure drop at flooding is estimated from the Kister & Gill (1991)
    correlation.

    Args:
        F_p: Packing factor in 1/m.  Must be positive.  Typical values:
            50–100 for structured, 100–300 for random packings.
        rho_L: Liquid density in kg/m³.  Must be positive.
        rho_G: Gas-phase density in kg/m³.  Must be positive and < *rho_L*.
        mu_L: Liquid dynamic viscosity in Pa·s.  Must be positive.
        L_G_ratio: Mass-flow ratio of liquid to gas (L/G), dimensionless.
            Must be positive.

    Returns:
        A tuple ``(u_flood_m_s, capacity_parameter, pressure_drop_pa_m)``:

        * **u_flood_m_s** — superficial gas velocity at flooding in m/s.
        * **capacity_parameter** — dimensionless K₄ at the flooding point.
        * **pressure_drop_pa_m** — estimated pressure drop at flooding
          in Pa per metre of packed height (Kister & Gill, 1991).

    Raises:
        ValueError: If any argument violates the physical constraints
            above, or if the flow parameter falls outside the valid
            range of the GPDC correlation.

    Example::

        >>> u, K4, dp = flooding_velocity(200.0, 1008.0, 1.2, 1.6e-3, 2.5)
        >>> round(u, 3)
        1.168
    """
    # --- Input validation ---------------------------------------------------
    for name, val in (
        ("F_p", F_p),
        ("rho_L", rho_L),
        ("rho_G", rho_G),
        ("mu_L", mu_L),
        ("L_G_ratio", L_G_ratio),
    ):
        if val <= 0.0:
            raise ValueError(f"{name} must be positive, got {val!r}.")
    if rho_G >= rho_L:
        raise ValueError(
            f"rho_G ({rho_G}) must be less than rho_L ({rho_L}); "
            "gas density cannot exceed liquid density."
        )

    # --- Flow parameter (GPDC abscissa) ------------------------------------
    FLV = L_G_ratio * math.sqrt(rho_G / rho_L)

    if FLV < 0.001 or FLV > 10.0:
        logger.warning(
            "Flow parameter FLV=%.4g is outside the GPDC correlation range "
            "[0.001, 10]. Results may be unreliable.",
            FLV,
        )

    # --- Capacity parameter at flooding (GPDC ordinate) --------------------
    ln_FLV = math.log(FLV)
    ln_K4_flood = _C0 + _C1 * ln_FLV + _C2 * ln_FLV**2
    K4_flood = math.exp(ln_K4_flood)

    # --- Flooding velocity --------------------------------------------------
    # K₄ = u² · F_p · ρ_G · (μ_L/μ_water)^0.1 / ((ρ_L - ρ_G) · g)
    # Solve for u:
    numerator = K4_flood * (rho_L - rho_G) * _G
    denominator = F_p * rho_G * (mu_L / _MU_WATER) ** 0.1
    u_flood = math.sqrt(numerator / denominator)

    # --- Pressure drop at flooding (Kister & Gill, 1991) -------------------
    pressure_drop = _KG_COEFF * F_p**0.7

    logger.debug(
        "flooding_velocity: FLV=%.4f, K4=%.6f, u_flood=%.4f m/s, ΔP=%.1f Pa/m",
        FLV,
        K4_flood,
        u_flood,
        pressure_drop,
    )

    return u_flood, K4_flood, pressure_drop
