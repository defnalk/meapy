# Changelog

All notable changes to meapy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- `flooding.py` — Leva correlation for packed-column flooding velocity
- `equilibrium.py` — CO₂–MEA VLE using Kent–Eisenberg and NRTL models
- `stripper.py` — Reboiler duty and stripping column analysis
- Pandas `DataFrame` integration for batch experiment processing
- Sphinx documentation hosted on ReadTheDocs

---

## [0.1.0] — 2025-06-01

### Added
- `meapy.constants` — `MEAProperties`, `PlantGeometry`, `AlarmLimits`,
  `HeatExchangerParams`, `ExperimentLabels` with full source citations
- `meapy.heat_transfer` — `stream_duty`, `energy_loss`, `lmtd_counter_current`,
  `lmtd_co_current`, `overall_heat_transfer_coefficient`, `efficiency`,
  `effectiveness`, `ntu`, `heat_capacity_rate`, `analyse_exchanger`
- `meapy.mass_transfer` — `mole_fraction_to_ratio`, `mole_ratio_to_fraction`,
  `koga_from_flux`, `koga_profile`, `composition_profile`, `ntu_og`, `hog`,
  `absorption_factor`
- `meapy.pump` — `ExponentialLevelModel`, `LinearFlowModel`,
  `PumpCommissioningResult`, `fit_exponential_level_model`,
  `fit_linear_flowrate_model`, `safe_pump_speed`, `predict_level`,
  `predict_flowrate`
- `meapy.utils` — `steady_state_mean`, `kg_h_to_mol_s`, `mol_s_to_kg_h`,
  `celsius_to_kelvin`, `kelvin_to_celsius`, `summarise_array`, `rolling_mean`
- Full pytest suite: unit tests for all modules + integration tests for the
  end-to-end pilot-plant workflow; ≥ 90 % coverage enforced by CI
- GitHub Actions CI: lint (ruff) + type-check (mypy) + tests on
  Python 3.10/3.11/3.12 across Ubuntu, macOS, Windows
- `pyproject.toml` with ruff, mypy, pytest, and coverage configuration
- MIT licence, README with API reference and usage examples
- `examples/heat_exchanger_analysis.py` and `examples/pump_commissioning.py`

[Unreleased]: https://github.com/defnalk/meapy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/defnalk/meapy/releases/tag/v0.1.0
