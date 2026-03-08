"""meapy — MEA Carbon Capture Process Analysis Library.

meapy is a scientific Python library for analysing post-combustion CO₂ capture
processes based on monoethanolamine (MEA) absorption.  It provides:

* **heat_transfer** — LMTD, U-coefficient, efficiency, and effectiveness
  calculations for plate heat exchangers (C100/C200 intercooler/trim-cooler).
* **mass_transfer** — K_OGa, NTU, H_OG, and composition profiling for packed
  counter-current absorption columns (E101).
* **pump** — Exponential and linear regression models for pump commissioning,
  safe operating speed determination, and alarm-threshold checking (J100).
* **constants** — Curated MEA thermophysical properties, plant geometry, and
  alarm setpoints from DOW (2003) and Imperial College pilot-plant data (Hale, 2025).
* **utils** — Unit conversions, steady-state detection, and descriptive statistics.

Typical usage example::

    import meapy
    from meapy.heat_transfer import analyse_exchanger
    from meapy.mass_transfer import koga_profile
    from meapy.pump import fit_exponential_level_model, safe_pump_speed

    result = analyse_exchanger(
        mea_flow_kg_h=900, cp_mea_j_kg_k=3940,
        t_mea_in_c=85.0, t_mea_out_c=42.0,
        utility_flow_kg_h=800, cp_utility_j_kg_k=3940,
        t_utility_in_c=30.0, t_utility_out_c=68.0,
        area_m2=0.30,
    )
    print(f"U = {result['u_kw_m2_k']:.2f} kW/(m²·K)")

See the project README at https://github.com/defnalk/meapy for full documentation.
"""

from __future__ import annotations

import logging

from meapy import constants, heat_transfer, mass_transfer, pump, utils

__version__ = "0.1.0"
__author__ = "Defne Nihal Ertugrul"
__email__ = "defne.ertugrul22@imperial.ac.uk"
__license__ = "MIT"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "constants",
    "heat_transfer",
    "mass_transfer",
    "pump",
    "utils",
]

# Configure a library-level NullHandler so that users control log output.
logging.getLogger(__name__).addHandler(logging.NullHandler())
