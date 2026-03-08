"""Example: Pump J100 Commissioning Analysis.

Reproduces the pump commissioning analysis from the Imperial College
carbon-capture pilot-plant report (Hale, 2025, Section 3), demonstrating
how meapy determines the maximum safe operating speed of pump J100.

Run with::

    python examples/pump_commissioning.py
"""

from __future__ import annotations

import logging

import numpy as np

from meapy.constants import AlarmLimits
from meapy.pump import (
    fit_exponential_level_model,
    fit_linear_flowrate_model,
    safe_pump_speed,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# ---------------------------------------------------------------------------
# Raw commissioning data — from Table C.5.1, Appendix C, pilot-plant report
# ---------------------------------------------------------------------------
PUMP_SPEEDS_PCT = np.array([10, 20, 30, 35, 40, 45, 50, 53], dtype=float)
MEA_LEVELS_PCT  = np.array([80.1, 65.3, 52.0, 45.8, 38.7, 31.2, 24.1, 15.0], dtype=float)
FLOWRATES_KG_H  = np.array([177.5, 365.2, 552.8, 646.0, 740.4, 833.7, 927.0, 980.1], dtype=float)


def main() -> None:
    print("=" * 58)
    print("  meapy — Pump J100 Commissioning Analysis")
    print("  Imperial College MEA Carbon Capture Pilot Plant")
    print("=" * 58)

    # 1. Fit regression models
    print("\nFitting models to commissioning data …")
    level_model = fit_exponential_level_model(PUMP_SPEEDS_PCT, MEA_LEVELS_PCT)
    flow_model  = fit_linear_flowrate_model(PUMP_SPEEDS_PCT, FLOWRATES_KG_H)

    print(f"  Exponential level model : L = {level_model.l0:.3f} · exp({level_model.k:.5f} · PS)")
    print(f"    R² = {level_model.r_squared:.4f}  (target: > 0.95)")
    print(f"  Linear flow model       : F = {flow_model.slope:.4f} · PS + ({flow_model.intercept:.4f})")
    print(f"    R² = {flow_model.r_squared:.4f}  (target: > 0.98)")

    # 2. Determine safe speed
    print("\nDetermining maximum safe pump speed …")
    result = safe_pump_speed(
        level_model,
        flow_model,
        level_alarm_pct=AlarmLimits.LT101_LOW_LEVEL_PCT,
        flow_alarm_kg_h=AlarmLimits.FT103_HIGH_FLOW_KG_H,
    )
    print(result)

    # 3. Print a sensitivity scan
    print("\nSensitivity scan: predicted level & flowrate at various speeds:")
    print(f"{'Speed (%)':>10}  {'Level (%)':>10}  {'Flow (kg/h)':>12}")
    print("─" * 36)
    for ps in [30, 40, 50, 53, 55, 60, 63]:
        lvl  = level_model.predict(ps)
        flow = flow_model.predict(ps)
        flag = " ← SAFE LIMIT" if abs(ps - result.safe_speed_pct) < 1.5 else ""
        flag += " ⚠ FLOW ALARM" if flow >= AlarmLimits.FT103_HIGH_FLOW_KG_H else ""
        flag += " ⚠ LEVEL ALARM" if lvl <= AlarmLimits.LT101_LOW_LEVEL_PCT else ""
        print(f"{ps:>10.0f}  {lvl:>10.1f}  {flow:>12.1f}{flag}")

    print("\nDone. See src/meapy/pump.py for full API documentation.\n")


if __name__ == "__main__":
    main()
