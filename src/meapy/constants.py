"""Physical constants and plant-specific parameters for MEA carbon capture systems.

This module centralises all hard-coded values used throughout meapy, following the
principle that magic numbers belong in one auditable place. Values are sourced from
DOW MEA technical data (2003), the Imperial College pilot-plant design documentation
(Hale, 2025), and the Engineering Toolbox.

Typical usage example::

    from meapy.constants import MEAProperties, PlantGeometry, AlarmLimits

    cp = MEAProperties.CP_15_PCT_AT_25C
    area = PlantGeometry.COLUMN_CROSS_SECTION_M2
"""

from __future__ import annotations

__all__ = [
    "MEAProperties",
    "PlantGeometry",
    "AlarmLimits",
    "HeatExchangerParams",
    "PhysicalConstants",
    "ExperimentLabels",
]


class PhysicalConstants:
    """Universal physical constants.

    Attributes:
        R_UNIVERSAL: Universal gas constant in J/(mol·K).
        STANDARD_TEMP_K: Standard temperature (0 °C) in kelvin.
        ATMOSPHERIC_PRESSURE_PA: Standard atmospheric pressure in Pa.
    """

    R_UNIVERSAL: float = 8.314  # J/(mol·K)
    STANDARD_TEMP_K: float = 273.15  # K
    ATMOSPHERIC_PRESSURE_PA: float = 101_325.0  # Pa


class MEAProperties:
    """Thermophysical properties of a 15 % (w/w) MEA aqueous solution.

    All values are taken from Dow Chemical MEA product data (2003) and are
    valid at or near ambient conditions unless otherwise stated.

    Attributes:
        MASS_FRACTION: Mass fraction of MEA in the solvent (dimensionless).
        CP_15_PCT_AT_25C: Specific heat capacity at 25 °C in J/(kg·K).
        CP_15_PCT_AT_40C: Specific heat capacity at 40 °C in J/(kg·K).
        CP_15_PCT_AT_60C: Specific heat capacity at 60 °C in J/(kg·K).
        DENSITY_KG_M3: Approximate density at 25 °C in kg/m³.
        VISCOSITY_PA_S: Dynamic viscosity at 25 °C in Pa·s.
        MW_MEA: Molar mass of monoethanolamine in g/mol.
        MW_CO2: Molar mass of CO₂ in g/mol.
    """

    MASS_FRACTION: float = 0.15
    CP_15_PCT_AT_25C: float = 3940.0  # J/(kg·K)   — DOW MEA datasheet
    CP_15_PCT_AT_40C: float = 3980.0  # J/(kg·K)
    CP_15_PCT_AT_60C: float = 4020.0  # J/(kg·K)
    DENSITY_KG_M3: float = 1_008.0   # kg/m³
    VISCOSITY_PA_S: float = 1.6e-3   # Pa·s
    MW_MEA: float = 61.08            # g/mol
    MW_CO2: float = 44.01            # g/mol


class PlantGeometry:
    """Geometric parameters of the Imperial College carbon-capture pilot plant.

    Attributes:
        COLUMN_HEIGHT_M: Total packed height of absorber E101 in metres.
        COLUMN_DIAMETER_M: Internal diameter of absorber/stripper columns in metres.
        COLUMN_CROSS_SECTION_M2: Cross-sectional area of absorber in m².
        SAMPLING_HEIGHTS_M: Heights (from base) of the six gas-sampling ports in metres.
        C100_PLATE_AREA_M2: Effective heat-transfer area of intercooler C100 in m².
        C200_PLATE_AREA_M2: Effective heat-transfer area of trim-cooler C200 in m².
        PACKING_TYPE: Descriptive name of the structured packing used.
    """

    COLUMN_HEIGHT_M: float = 6.2       # m
    COLUMN_DIAMETER_M: float = 0.1     # m  (100 mm ID)
    COLUMN_CROSS_SECTION_M2: float = 3.14159 * (0.1 / 2) ** 2  # π r²  ≈ 7.854e-3 m²
    SAMPLING_HEIGHTS_M: list[float] = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]  # ports 1–6
    C100_PLATE_AREA_M2: float = 0.30   # m²  (manufacturer spec)
    C200_PLATE_AREA_M2: float = 0.25   # m²
    PACKING_TYPE: str = "Sulzer MellapakPlus 252.Y"


class AlarmLimits:
    """Alarm and safety thresholds for the Imperial College pilot plant.

    All threshold values are taken from the plant P&ID and the commissioning
    documentation (Hale, 2025).

    Attributes:
        LT101_LOW_LEVEL_PCT: Low-level alarm for stripper E100 level transmitter LT101 (%).
        LT101_LOW_SHUTDOWN_PCT: Low-level shutdown threshold for LT101 (%).
        FT103_HIGH_FLOW_KG_H: High-flowrate alarm at transmitter FT103 (kg/h).
        FT104_HIGH_FLOW_KG_H: High-flowrate alarm at transmitter FT104 (kg/h).
        PUMP_SPEED_MIN_PCT: Minimum allowable pump speed for J100 (%).
        PUMP_SPEED_MAX_DESIGN_PCT: Design maximum pump speed for J100 (%).
    """

    LT101_LOW_LEVEL_PCT: float = 10.0   # %  — low-level alarm
    LT101_LOW_SHUTDOWN_PCT: float = 5.0  # %  — trip setpoint
    FT103_HIGH_FLOW_KG_H: float = 1_000.0   # kg/h
    FT104_HIGH_FLOW_KG_H: float = 1_000.0   # kg/h
    PUMP_SPEED_MIN_PCT: float = 0.0
    PUMP_SPEED_MAX_DESIGN_PCT: float = 100.0


class HeatExchangerParams:
    """Default/reference parameters for heat exchangers C100 and C200.

    Attributes:
        U_LITERATURE_MIN_KW: Minimum literature value for U in kW/(m²·K).
        U_LITERATURE_MAX_KW: Maximum literature value for U in kW/(m²·K).
        FLOW_UNIT_CONVERSION: Conversion factor from kg/h to kg/s.
    """

    U_LITERATURE_MIN_KW: float = 1.0   # kW/(m²·K)  — Engineering Toolbox (2003)
    U_LITERATURE_MAX_KW: float = 4.0   # kW/(m²·K)
    FLOW_UNIT_CONVERSION: float = 1.0 / 3_600.0   # kg/h → kg/s


class ExperimentLabels:
    """Canonical labels used for the five pilot-plant experiments.

    Attributes:
        LABELS: Ordered list of experiment identifiers A–E.
        COOLING_WATER_FLOWRATES_KG_H: Average cooling water flowrate at FT201 per
            experiment in kg/h, as reported in Table 5.2.1 of the main report.
    """

    LABELS: list[str] = ["A", "B", "C", "D", "E"]
    COOLING_WATER_FLOWRATES_KG_H: dict[str, float] = {
        "A": 722.0,
        "B": 719.0,
        "C": 716.0,
        "D": 541.0,
        "E": 1615.0,
    }
