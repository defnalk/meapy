# meapy

![Tests](https://github.com/defnalk/meapy/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Coverage](https://img.shields.io/badge/coverage-90%25+-brightgreen)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

> **A scientific Python library for analysing post-combustion CO₂ capture processes based on monoethanolamine (MEA) absorption.**

meapy provides a clean, tested, and typed API for the core calculations performed when commissioning and evaluating MEA-based carbon capture pilot plants — heat exchanger thermal analysis, packed-column mass transfer, and pump commissioning — styled after scientific packages like [pvlib](https://pvlib-python.readthedocs.io/) and [scipy](https://scipy.org/).

---

## ✨ Features

| Module | What it does |
|---|---|
| `meapy.heat_transfer` | LMTD · overall heat transfer coefficient *U* · thermal efficiency · NTU-effectiveness for plate heat exchangers |
| `meapy.mass_transfer` | K_OGa profiles · NTU_OG · H_OG · composition profiling along packed absorber columns |
| `meapy.pump` | Exponential & linear regression commissioning models · safe operating speed · alarm-threshold checking |
| `meapy.constants` | Curated MEA thermophysical properties (DOW, 2003) · pilot-plant geometry · alarm setpoints |
| `meapy.utils` | Unit conversions · steady-state detection · descriptive statistics |

- **100 % type-annotated** — full `mypy --strict` compliance
- **Google-style docstrings** on every public function and class
- **≥ 90 % test coverage** across unit and integration suites
- **No magic numbers** — every hard-coded value lives in `constants.py` with a source citation
- **Logging, not print** — configure output with standard `logging`

---

## 🏗 Background

meapy was developed from the Imperial College London MEA carbon-capture pilot-plant analysis (Hale, 2025). The plant operates a 15 % (w/w) MEA solution in a counter-current packed absorber (E101) and stripper (E100), with plate heat exchangers C100 (intercooler) and C200 (trim cooler), and pump J100 driving lean MEA recirculation.

```
        CO₂-lean N₂ out ↑
              ┌───────┐
              │  E101 │ ← Lean MEA in (from C200)
              │ Absorb│
              │  er   │
              └───────┘
        Rich MEA ↓      ↑ CO₂ + N₂ in
              ┌───────┐
              │  C100 │  intercooler (MEA↔MEA)
              └───────┘
              ┌───────┐
              │  C200 │  trim cooler (MEA↔water)
              └───────┘
              ┌───────┐
              │  E100 │  stripper
              │  J100 │  pump
              └───────┘
```

---

## 📦 Installation

**From PyPI** (once published):

```bash
pip install meapy
```

**From source** (recommended for development):

```bash
git clone https://github.com/defnalk/meapy.git
cd meapy
pip install -e ".[dev]"
```

**Requirements:** Python 3.10+, NumPy ≥ 1.24, SciPy ≥ 1.11

---

## 🚀 Quick Start

### Heat Exchanger Analysis (C100 intercooler)

```python
from meapy.heat_transfer import analyse_exchanger
from meapy.constants import MEAProperties

result = analyse_exchanger(
    mea_flow_kg_h=900,
    cp_mea_j_kg_k=MEAProperties.CP_15_PCT_AT_40C,  # 3980 J/(kg·K)
    t_mea_in_c=85.0,
    t_mea_out_c=42.0,
    utility_flow_kg_h=800,
    cp_utility_j_kg_k=MEAProperties.CP_15_PCT_AT_40C,
    t_utility_in_c=30.0,
    t_utility_out_c=68.0,
    area_m2=0.30,
)

print(f"U         = {result['u_kw_m2_k']:.2f} kW/(m²·K)")
print(f"Efficiency = {result['efficiency']:.3f}")
print(f"LMTD      = {result['lmtd_k']:.2f} K")
# U         = 1.74 kW/(m²·K)
# Efficiency = 0.961
# LMTD      = 19.03 K
```

### Pump Commissioning (J100)

```python
import numpy as np
from meapy.pump import (
    fit_exponential_level_model,
    fit_linear_flowrate_model,
    safe_pump_speed,
)

# Data from LT101 and FT103 transmitters
speeds = np.array([10, 20, 30, 40, 50, 53], dtype=float)
levels = np.array([80.1, 65.3, 52.0, 38.7, 24.1, 15.0], dtype=float)
flows  = np.array([177.5, 365.2, 552.8, 740.4, 927.0, 980.1], dtype=float)

level_model = fit_exponential_level_model(speeds, levels)
flow_model  = fit_linear_flowrate_model(speeds, flows)
result      = safe_pump_speed(level_model, flow_model)

print(result)
# ── Pump Commissioning Result ────────────────────────────
#   Safe operating speed  : 53.0 %
#   Predicted MEA level   : 15.1 %
#   Predicted flowrate    : 980.1 kg/h
#   Level alarm at        : 62.8 %
#   Flow alarm at         : 54.2 %
#   Limiting constraint   : flow
```

### Mass Transfer — K_OGa Profile (E101 absorber)

```python
import numpy as np
from meapy.mass_transfer import composition_profile, koga_profile
from meapy.constants import PlantGeometry
from meapy.utils import kg_h_to_mol_s, summarise_array

# Six sampling ports at fixed heights
heights_m   = PlantGeometry.SAMPLING_HEIGHTS_M          # [0.5, 1.5, ..., 5.5] m
co2_vol_pct = [14.0, 11.5, 9.0, 6.0, 3.5, 1.5]        # gas analyser readings

_, y_co2 = composition_profile(heights_m, co2_vol_pct)

inert_flow_mol_s = kg_h_to_mol_s(500.0, 28.014)         # N₂ at 500 kg/h
cross_section_m2 = PlantGeometry.COLUMN_CROSS_SECTION_M2

koga = koga_profile(inert_flow_mol_s, cross_section_m2, heights_m, list(y_co2))
stats = summarise_array(koga[~np.isnan(koga)])

print(f"Mean K_OGa = {stats['mean']:.1f} kmol/(m³·h)")
print(f"Range      = [{stats['min']:.1f}, {stats['max']:.1f}] kmol/(m³·h)")
```

---

## 📖 API Reference

### `meapy.heat_transfer`

| Function | Signature | Returns |
|---|---|---|
| `stream_duty` | `(mass_flow_kg_s, cp_j_kg_k, t_in_c, t_out_c)` | `float` W |
| `energy_loss` | `(q_hot_w, q_cold_w)` | `float` W |
| `lmtd_counter_current` | `(t_hot_in, t_hot_out, t_cold_in, t_cold_out)` | `float` K |
| `lmtd_co_current` | `(t_hot_in, t_hot_out, t_cold_in, t_cold_out)` | `float` K |
| `overall_heat_transfer_coefficient` | `(q_w, lmtd_k, area_m2)` | `float` W/(m²·K) |
| `efficiency` | `(q_cold_w, q_hot_w)` | `float` |
| `effectiveness` | `(q_actual_w, c_hot, c_cold, t_hot_in, t_cold_in)` | `float` |
| `ntu` | `(u_w_m2_k, area_m2, c_min_w_k)` | `float` |
| `analyse_exchanger` | `(**kwargs)` | `dict[str, float]` |

### `meapy.mass_transfer`

| Function | Returns |
|---|---|
| `mole_fraction_to_ratio(y)` | mole ratio Y |
| `mole_ratio_to_fraction(Y)` | mole fraction y |
| `koga_from_flux(...)` | K_OGa in mol/(m³·s) |
| `koga_profile(...)` | `ndarray` in kmol/(m³·h) |
| `composition_profile(...)` | `(heights, y_co2)` ndarrays |
| `ntu_og(y_bottom, y_top)` | dimensionless NTU_OG |
| `hog(koga, flux)` | H_OG in m |
| `absorption_factor(L, G, m)` | dimensionless A |

### `meapy.pump`

| Class / Function | Description |
|---|---|
| `ExponentialLevelModel` | Frozen dataclass: `l0`, `k`, `r_squared`; methods `predict()`, `invert()` |
| `LinearFlowModel` | Frozen dataclass: `slope`, `intercept`, `r_squared`; methods `predict()`, `invert()` |
| `PumpCommissioningResult` | Result dataclass with `safe_speed_pct`, `limiting_constraint`, etc. |
| `fit_exponential_level_model(speeds, levels)` | Fit L = L₀·exp(k·PS) by log-linearisation |
| `fit_linear_flowrate_model(speeds, flows)` | Fit F = slope·PS + intercept by OLS |
| `safe_pump_speed(level_model, flow_model)` | Determine binding constraint and safe speed |

Full API documentation: [meapy.readthedocs.io](https://meapy.readthedocs.io)

---

## 🧪 Running Tests

```bash
# All tests with coverage report
make test

# Unit tests only (fast)
pytest tests/unit/

# Integration tests only
pytest tests/integration/ -m integration

# With verbose output
pytest -v --tb=short
```

---

## 🔧 Development

```bash
# Install in editable mode with all dev extras
make install

# Lint and format
make lint

# Type-check
mypy src/meapy

# Run examples
python examples/heat_exchanger_analysis.py
python examples/pump_commissioning.py
```

---

## 📁 Repository Structure

```
meapy/
├── src/meapy/
│   ├── __init__.py          # Package entry point and version
│   ├── constants.py         # MEA properties, plant geometry, alarm limits
│   ├── heat_transfer.py     # LMTD, U, efficiency, effectiveness
│   ├── mass_transfer.py     # K_OGa, composition profiling, NTU
│   ├── pump.py              # Commissioning models and safe speed
│   └── utils.py             # Unit conversions, steady-state detection
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── unit/
│   │   ├── test_heat_transfer.py
│   │   ├── test_mass_transfer.py
│   │   ├── test_pump.py
│   │   └── test_utils.py
│   └── integration/
│       └── test_workflow.py
├── examples/
│   ├── heat_exchanger_analysis.py
│   └── pump_commissioning.py
├── docs/
├── .github/workflows/ci.yml
├── pyproject.toml
├── Makefile
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 📚 References

- DOW Chemical (2003). *MEA product data and thermophysical properties.*
- Engineering Toolbox (2003). *Overall heat transfer coefficients for plate heat exchangers.*
- Hale, R. (2025). *Imperial College London MEA Carbon Capture Pilot Plant Manual.*
- Treybal, R. E. (1981). *Mass Transfer Operations* (3rd ed.). McGraw-Hill.
- Coulson, J. M., & Richardson, J. F. (2002). *Chemical Engineering Volume 1* (6th ed.). Butterworth-Heinemann.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

```bash
# Fork the repo, create a branch, commit your changes, open a PR
git checkout -b feature/my-improvement
git commit -m "feat: add packed column flooding correlation"
git push origin feature/my-improvement
```

---

## 📄 License

MIT © 2025 Defne Nihal Ertugrul. See [LICENSE](LICENSE) for details.
