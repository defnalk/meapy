# Changelog

All notable changes to meapy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- `constants.PlantGeometry.COLUMN_CROSS_SECTION_M2` is now computed with
  `math.pi` instead of the truncated literal `3.14159`, eliminating a
  ~8e-9 m² error that propagated into every default-geometry K_OGa
  calculation.

### Changed
- `constants.PlantGeometry.SAMPLING_HEIGHTS_M`, `ExperimentLabels.LABELS`,
  and `ExperimentLabels.COOLING_WATER_FLOWRATES_KG_H` are now immutable
  (`tuple` and `types.MappingProxyType`), preventing accidental
  cross-notebook mutation of shared class-level state. Read API unchanged.
- `heat_transfer.efficiency` now emits a `logger.warning` when the
  computed thermal efficiency exceeds unity, surfacing the
  measurement-inconsistency case the docstring already described
  (instrumentation drift, swapped streams, heat gain from surroundings).

### Performance
- `utils.rolling_mean` rewritten with the cumulative-sum trick:
  O(n·window) Python loop → O(n) vectorised. Measured speedups (Apple
  M-series, Python 3.13, NumPy 2.x, window=60, best-of-5):
  10k samples 27.2 ms → 0.078 ms (~349×); 100k 222 ms → 0.89 ms (~250×);
  1M 2.22 s → 11.7 ms (~190×). Behaviour bit-identical, all 19 existing
  unit tests pass.

### Added
- `benchmarks/bench_rolling_mean.py` — reproducible micro-benchmark with
  cProfile dump for `utils.rolling_mean`. Establishes a baseline for
  detecting future perf regressions.

### Deprecated
- `mass_transfer.ntu_og(m_slope=...)` — the parameter has never been
  honoured (the function always returned the dilute-limit
  `ln(Y_b / Y_t)`). Non-zero values now emit `DeprecationWarning`; the
  parameter will be removed in v0.2.0 in favour of a dedicated
  Colburn-equation entry point that takes the absorption factor
  explicitly. See [#5](https://github.com/defnalk/meapy/issues/5) and
  [PR #11](https://github.com/defnalk/meapy/pull/11).

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
