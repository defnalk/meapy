# Changelog

All notable changes to **meapy** will be documented in this file.

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

Initial public release. Establishes the v0.1.x public API surface; any
breaking change to a symbol listed below will require a major-version bump
per SemVer.

### Added — `meapy.constants`

Curated thermophysical constants, plant geometry, and alarm setpoints.
Sourced from Dow MEA technical data (2003) and Imperial College pilot-plant
documentation (Hale, 2025).

- `PhysicalConstants` — universal constants (`R_UNIVERSAL`, `STANDARD_TEMP_K`, `ATMOSPHERIC_PRESSURE_PA`).
- `MEAProperties` — 15 % w/w MEA `cp` at 25/40/60 °C, density, viscosity, MW of MEA and CO₂.
- `PlantGeometry` — column height/diameter/cross-section, sampling-port heights, C100/C200 plate areas.
- `AlarmLimits` — LT101 low-level alarm and shutdown thresholds, FT103/FT104 high-flow alarms, pump speed bounds.
- `HeatExchangerParams` — literature U range, kg/h ↔ kg/s conversion factor.
- `ExperimentLabels` — canonical labels A–E and cooling-water flowrates per experiment.

### Added — `meapy.heat_transfer`

LMTD / NTU-effectiveness analysis for plate heat exchangers.

- `stream_duty(mass_flow_kg_s: float, cp_j_kg_k: float, t_in_c: float, t_out_c: float) -> float`
  Sensible heat duty `Q = ṁ·cp·ΔT` in W; sign encodes hot vs cold.
- `energy_loss(q_hot_w: float, q_cold_w: float) -> float`
  Absolute energy-balance imbalance `|Q_hot + Q_cold|` in W.
- `lmtd_counter_current(t_hot_in_c, t_hot_out_c, t_cold_in_c, t_cold_out_c) -> float`
  Counter-current log mean temperature difference (K).
- `lmtd_co_current(t_hot_in_c, t_hot_out_c, t_cold_in_c, t_cold_out_c) -> float`
  Co-current (parallel-flow) LMTD (K).
- `overall_heat_transfer_coefficient(q_w: float, lmtd_k: float, area_m2: float) -> float`
  `U = Q / (A·ΔT_lm)` in W/(m²·K).
- `heat_capacity_rate(mass_flow_kg_s: float, cp_j_kg_k: float) -> float`
  `C = ṁ·cp` in W/K.
- `efficiency(q_cold_w: float, q_hot_w: float) -> float`
  Thermal efficiency `η = Q_cold / |Q_hot|`.
- `effectiveness(q_actual_w, c_hot_w_k, c_cold_w_k, t_hot_in_c, t_cold_in_c) -> float`
  ε-NTU effectiveness `ε = Q_actual / (C_min·ΔT_max)`.
- `ntu(u_w_m2_k: float, area_m2: float, c_min_w_k: float) -> float`
  Number of Transfer Units `NTU = U·A / C_min`.
- `analyse_exchanger(*, mea_flow_kg_h, cp_mea_j_kg_k, t_mea_in_c, t_mea_out_c, utility_flow_kg_h, cp_utility_j_kg_k, t_utility_in_c, t_utility_out_c, area_m2, flow_direction="counter") -> dict[str, float]`
  End-to-end thermal analysis returning `q_hot_w`, `q_cold_w`, `q_loss_w`, `lmtd_k`, `u_w_m2_k`, `u_kw_m2_k`, `efficiency`, `effectiveness`, `ntu`.

### Added — `meapy.mass_transfer`

Two-film mass-transfer analysis for packed CO₂ absorption columns.

- `mole_fraction_to_ratio(y: float) -> float`
  `Y = y / (1 − y)`.
- `mole_ratio_to_fraction(Y: float) -> float`
  `y = Y / (1 + Y)`.
- `koga_from_flux(inert_gas_flow_mol_s, cross_section_m2, packed_height_m, y_bottom, y_top) -> float`
  Overall volumetric gas-phase mass-transfer coefficient `K_OGa = (V'/(A_c·H))·ln(Y_b/Y_t)` in mol/(m³·s).
- `koga_profile(inert_gas_flow_mol_s, cross_section_m2, sampling_heights_m, y_values) -> NDArray[float64]`
  Section-by-section `K_OGa` profile in kmol/(m³·h); failed sections returned as `NaN`.
- `composition_profile(sampling_heights_m, co2_volume_pct) -> tuple[NDArray, NDArray]`
  Convert IR analyser vol% readings to mole-fraction profile along the column.
- `ntu_og(y_bottom: float, y_top: float, m_slope: float = 0.0) -> float`
  Number of overall gas-phase transfer units `NTU_OG ≈ ln(Y_b/Y_t)` for dilute systems.
- `hog(koga_mol_m3_s: float, inert_gas_flux_mol_m2_s: float) -> float`
  Height of a transfer unit `H_OG = G' / K_OGa` in m.
- `absorption_factor(liquid_flow_mol_s, gas_flow_mol_s, m_slope) -> float`
  Dimensionless absorption factor `A = L / (m·G)`.

### Added — `meapy.pump`

Centrifugal-pump commissioning analysis (J100).

- `ExponentialLevelModel(l0: float, k: float, r_squared: float)` — frozen dataclass for `L = L₀·exp(k·PS)` with `predict(pump_speed_pct) -> float` and `invert(target_level_pct) -> float`.
- `LinearFlowModel(slope: float, intercept: float, r_squared: float)` — frozen dataclass for `F = slope·PS + intercept` with `predict` / `invert`.
- `PumpCommissioningResult` — dataclass containing `safe_speed_pct`, `predicted_level_pct`, `predicted_flow_kg_h`, `level_alarm_speed_pct`, `flow_alarm_speed_pct`, `limiting_constraint`, and `notes`.
- `fit_exponential_level_model(pump_speeds_pct: ArrayLike, mea_levels_pct: ArrayLike) -> ExponentialLevelModel`
  OLS fit on `ln(L)` vs `PS`.
- `fit_linear_flowrate_model(pump_speeds_pct: ArrayLike, flowrates_kg_h: ArrayLike) -> LinearFlowModel`
  OLS fit of flowrate against pump speed.
- `predict_level(model: ExponentialLevelModel, pump_speed_pct: float) -> float`
- `predict_flowrate(model: LinearFlowModel, pump_speed_pct: float) -> float`
- `safe_pump_speed(level_model, flow_model, level_alarm_pct=…, flow_alarm_kg_h=…, speed_min_pct=…, speed_max_pct=…) -> PumpCommissioningResult`
  Determine the maximum safe pump speed as the minimum of the level- and flow-alarm intercepts.

### Added — `meapy.utils`

Shared helpers for unit conversions and steady-state data handling.

- `steady_state_mean(values: Sequence[float], window: int = 3, tol: float = 1.0) -> float`
  Mean of a trailing window when its peak-to-peak variation is within tolerance.
- `kg_h_to_mol_s(flow_kg_h: float, molar_mass_g_mol: float) -> float`
- `mol_s_to_kg_h(flow_mol_s: float, molar_mass_g_mol: float) -> float`
- `celsius_to_kelvin(t_c: float) -> float`
- `kelvin_to_celsius(t_k: float) -> float`
- `summarise_array(arr: ArrayLike) -> dict[str, float]`
  Returns `mean`, `std`, `min`, `max`, `n`.
- `rolling_mean(arr: ArrayLike, window: int) -> NDArray[float64]`
  Equal-weight rolling mean with expanding-window edge handling.

### Added — Tooling and project infrastructure

- Full pytest suite (unit + end-to-end pilot-plant integration), ≥ 90 % coverage gate enforced in CI.
- GitHub Actions matrix: ruff lint + mypy strict + pytest on Python 3.10/3.11/3.12 × Ubuntu/macOS/Windows.
- `pyproject.toml` with ruff, mypy, pytest, and coverage configuration; PEP 561 `py.typed` marker.
- MIT licence.
- `examples/heat_exchanger_analysis.py` and `examples/pump_commissioning.py`.

### Public API stability note

Every symbol exported from a module's `__all__` is part of the v0.1.x public
contract. Internal helpers (leading underscore) may change without notice.

[Unreleased]: https://github.com/defnalk/meapy/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/defnalk/meapy/releases/tag/v0.1.0
