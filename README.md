# meapy

[![CI](https://github.com/defnalk/meapy/actions/workflows/ci.yml/badge.svg)](https://github.com/defnalk/meapy/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen)](https://github.com/defnalk/meapy/actions/workflows/ci.yml)
[![PyPI ready](https://img.shields.io/badge/PyPI-ready-blue?logo=pypi&logoColor=white)](https://github.com/defnalk/meapy)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2A6DB2)](http://mypy-lang.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> A typed, tested Python library for the core calculations needed to commission and evaluate MEA-based post-combustion CO₂ capture pilot plants.

## Why this matters

Monoethanolamine (MEA) absorption is the benchmark technology for post-combustion CO₂ capture and underpins most operational and near-term commercial carbon-capture deployments on power, cement, and waste-to-energy plants. As regulators tighten emissions caps and CCUS projects move from FEED to operation, plant teams need reliable, auditable calculations for absorber performance, heat-exchanger duty, and pump operability — the same numbers that drive solvent inventory, regeneration energy, and OPEX. **meapy** packages those calculations as a small, well-typed scientific Python library so engineers can move from raw transmitter readings to commissioning decisions without rolling bespoke spreadsheets.

## Key features

- ✅ **Heat-exchanger thermal analysis** — `Q = ṁ·cp·ΔT`, counter- and co-current LMTD, `U`, `η`, `ε`, NTU, and a one-call `analyse_exchanger()` wrapper.
- ✅ **Packed-column mass transfer** — `K_OGa` from log-ratio driving force, section-by-section profiling, `NTU_OG`, `H_OG`, absorption factor.
- ✅ **Pump commissioning** — exponential level model + linear flow model, alarm-aware `safe_pump_speed()` with binding-constraint diagnostics.
- ✅ **Curated constants** — MEA thermophysical properties, plant geometry, alarm setpoints, all centralised and cited.
- ✅ **Typed end to end** — `mypy --strict` clean, PEP 561 `py.typed`, Google-style docstrings on every public symbol.
- ✅ **CI matrix** — Python 3.10/3.11/3.12 × Linux/macOS/Windows, ruff + mypy + pytest, coverage gate.

## Validation

A worked validation notebook reproducing published pilot-plant calculations
lives at [`benchmarks/validation.ipynb`](benchmarks/validation.ipynb). It
documents input parameters, computed outputs, literature values, and
percent error for each comparison, with a summary table at the end.

> **Status:** the benchmark notebook is being prepared against an
> open-access pilot-plant reference. Until it lands, the regression
> coverage in `tests/` exercises every public function with hand-checked
> reference values.

## Used for

- 🛠️ **Pump commissioning** — converting startup speed/level/flow data into a defensible maximum safe operating speed and binding-constraint diagnosis (J100).
- 🧪 **Absorber diagnostics** — turning IR-analyser CO₂ vol% readings into a `K_OGa` profile to spot maldistribution and packing under-performance (E101).
- 🌡️ **Heat-exchanger checks** — closing the energy balance on intercoolers and trim coolers (C100/C200), reporting `U`, `η`, `ε`, and unmeasured loss.

## Quickstart

```bash
pip install meapy   # once published; for now: pip install -e .
```

```python
from meapy.heat_transfer import analyse_exchanger

result = analyse_exchanger(
    mea_flow_kg_h=900, cp_mea_j_kg_k=3940,
    t_mea_in_c=85.0,  t_mea_out_c=42.0,
    utility_flow_kg_h=800, cp_utility_j_kg_k=3940,
    t_utility_in_c=30.0,   t_utility_out_c=68.0,
    area_m2=0.30,
)

print(f"U = {result['u_kw_m2_k']:.2f} kW/(m²·K)")
print(f"η = {result['efficiency']:.3f}")
print(f"ε = {result['effectiveness']:.3f}")
```

See `examples/` for end-to-end scripts covering heat-exchanger analysis and
pump commissioning.

## Citing

If you use **meapy** in academic or industrial work, please cite it as:

```bibtex
@software{meapy,
  author  = {Ertugrul, Defne Nihal},
  title   = {meapy: A Python library for MEA carbon-capture pilot-plant analysis},
  year    = {2025},
  version = {0.1.0},
  url     = {https://github.com/defnalk/meapy},
  license = {MIT},
  note    = {DOI to be assigned via Zenodo on first tagged release}
}
```

## Licence

MIT — see [LICENSE](LICENSE).
