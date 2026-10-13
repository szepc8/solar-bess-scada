from dataclasses import dataclass


@dataclass(frozen=True)
class PVConfig:

    # PV panels
    panel_count: int = 10
    panel_power_wp: float = 400.0

    # Installation geometry
    orientation_deg: float = 180.0
    tilt_deg: float = 35.0

    # Inverter
    inverter_model: str = "Fronius Primo 4.0-1"
    inverter_capacity_kw: float = 4.0
    inverter_efficiency: float = 0.97

    # PV temperature model
    temperature_coefficient: float = -0.0035
    reference_temperature: float = 25.0

    # Simulation
    max_irradiance: float = 1000.0
    simulation_interval_seconds: int = 5

    # Geographic location
    latitude: float = 45.658
    longitude: float = 25.601
    altitude_m: float = 600.0
    timezone: str = "Europe/Bucharest"

    @property
    def installed_capacity_kw(self) -> float:
        return self.panel_count * self.panel_power_wp / 1000.0