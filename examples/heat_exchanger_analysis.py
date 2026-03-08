"""Example: Heat Exchanger Performance Analysis.

Reproduces the C100 and C200 analysis from the Imperial College carbon-capture
pilot-plant report (Hale, 2025, Section 4), showing how meapy's
heat_transfer module can be used to evaluate thermal performance across
multiple experimental runs.

Run with::

    python examples/heat_exchanger_analysis.py
"""

from __future__ import annotations

import logging

import numpy as np

from meapy.constants import MEAProperties, HeatExchangerParams
from meapy.heat_transfer import analyse_exchanger

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# ---------------------------------------------------------------------------
# Experimental dataset — five runs, one representative steady-state point each
# ---------------------------------------------------------------------------
# Columns: mea_flow_kg_h, t_mea_in, t_mea_out, util_flow_kg_h, t_util_in, t_util_out
C100_DATA = [
    # exp   mea_flow  T_mea_in  T_mea_out  util_flow  T_util_in  T_util_out
    ("A",   750,      83.1,     40.2,       650,       28.5,      65.1),
    ("B",   820,      84.5,     41.5,       720,       29.3,      66.8),
    ("C",   900,      85.0,     42.0,       800,       30.0,      68.0),
    ("D",   680,      82.3,     39.8,       590,       27.8,      64.2),
    ("E",   980,      85.8,     43.1,       870,       31.2,      69.5),
]

C200_DATA = [
    ("A",   750,      40.2,     25.5,       722,       14.5,      29.1),
    ("B",   820,      41.5,     26.3,       719,       14.8,      30.2),
    ("C",   900,      42.0,     26.8,       716,       15.0,      31.0),
    ("D",   680,      39.8,     25.0,       541,       14.2,      28.5),
    ("E",   980,      43.1,     27.5,      1615,       15.5,      22.0),
]

CP_MEA = MEAProperties.CP_15_PCT_AT_40C
CP_WATER = 4182.0  # J/(kg·K)


def run_analysis(
    dataset: list,
    hx_name: str,
    area_m2: float,
    cp_utility: float,
) -> None:
    """Run and print the heat exchanger analysis for one exchanger across all experiments.

    Args:
        dataset: List of tuples (label, mea_flow, t_mea_in, t_mea_out,
            util_flow, t_util_in, t_util_out).
        hx_name: Human-readable exchanger name (e.g. "C100").
        area_m2: Heat-transfer area in m².
        cp_utility: Specific heat capacity of the utility stream in J/(kg·K).
    """
    print(f"\n{'─'*65}")
    print(f"  {hx_name} — Heat Exchanger Analysis")
    print(f"{'─'*65}")
    header = f"{'Exp':>4}  {'U (kW/m²K)':>11}  {'η':>6}  {'ε':>6}  {'Q_loss (W)':>10}  {'LMTD (K)':>8}"
    print(header)
    print("─" * 65)

    u_values = []
    for row in dataset:
        label, mea_flow, t_mi, t_mo, u_flow, t_ui, t_uo = row
        try:
            res = analyse_exchanger(
                mea_flow_kg_h=mea_flow,
                cp_mea_j_kg_k=CP_MEA,
                t_mea_in_c=t_mi,
                t_mea_out_c=t_mo,
                utility_flow_kg_h=u_flow,
                cp_utility_j_kg_k=cp_utility,
                t_utility_in_c=t_ui,
                t_utility_out_c=t_uo,
                area_m2=area_m2,
            )
            u_kw = res["u_kw_m2_k"]
            u_values.append(u_kw)
            print(
                f"{label:>4}  {u_kw:>11.3f}  {res['efficiency']:>6.3f}  "
                f"{res['effectiveness']:>6.3f}  {res['q_loss_w']:>10.1f}  "
                f"{res['lmtd_k']:>8.2f}"
            )
        except ValueError as exc:
            print(f"{label:>4}  {'ERROR':>11}  {'—':>6}  {'—':>6}  {'—':>10}  {'—':>8}  [{exc}]")

    if u_values:
        print("─" * 65)
        print(f"  Mean U = {np.mean(u_values):.3f} kW/(m²·K)   "
              f"[Literature range: {HeatExchangerParams.U_LITERATURE_MIN_KW}–"
              f"{HeatExchangerParams.U_LITERATURE_MAX_KW} kW/(m²·K)]")


def main() -> None:
    """Entry point."""
    print("=" * 65)
    print("  meapy — Heat Exchanger Performance Analysis")
    print("  Imperial College MEA Carbon Capture Pilot Plant")
    print("=" * 65)

    run_analysis(C100_DATA, "C100 (intercooler, counter-current MEA↔MEA)", area_m2=0.30, cp_utility=CP_MEA)
    run_analysis(C200_DATA, "C200 (trim cooler, MEA↔cooling water)",       area_m2=0.25, cp_utility=CP_WATER)

    print("\nDone. See src/meapy/heat_transfer.py for full API documentation.\n")


if __name__ == "__main__":
    main()
