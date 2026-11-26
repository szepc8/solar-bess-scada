from dataclasses import dataclass
from enum import Enum


class BESSMode(str, Enum):
    IDLE = "IDLE"
    CHARGING = "CHARGING"
    DISCHARGING = "DISCHARGING"
    FAULT = "FAULT"


@dataclass
class BESSConfig:
    capacity_kwh: float = 10.0
    nominal_voltage_v: float = 51.2

    max_charge_power_kw: float = 5.0
    max_discharge_power_kw: float = 5.0

    min_soc: float = 10.0
    max_soc: float = 95.0

    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95


class BESSimulator:

    def __init__(
        self,
        config: BESSConfig | None = None,
        initial_soc: float = 50.0,
    ):
        self.config = config or BESSConfig()

        if not self.config.min_soc <= initial_soc <= self.config.max_soc:
            raise ValueError("Initial SOC outside allowed limits")

        self.soc = initial_soc
        self.soh = 100.0

        self.power_kw = 0.0
        self.mode = BESSMode.IDLE

        self.temperature_c = 25.0

        self.energy_charged_kwh = 0.0
        self.energy_discharged_kwh = 0.0

    def step(self, requested_power_kw: float, dt_seconds: float) -> dict:
        """
        Simulate BESS operation for one time step.

        Positive power = discharge.
        Negative power = charge.
        """

        if dt_seconds <= 0:
            raise ValueError("dt_seconds must be positive")

        cfg = self.config
        dt_hours = dt_seconds / 3600.0

        power = max(
            -cfg.max_charge_power_kw,
            min(requested_power_kw, cfg.max_discharge_power_kw),
        )

        if power > 0:
            available_energy = (
                (self.soc - cfg.min_soc)
                / 100.0
                * cfg.capacity_kwh
            )

            max_energy_output = (
                available_energy * cfg.discharge_efficiency
            )

            requested_energy = power * dt_hours

            actual_energy = min(
                requested_energy,
                max_energy_output,
            )

            self.soc -= (
                actual_energy
                / cfg.discharge_efficiency
                / cfg.capacity_kwh
                * 100.0
            )

            self.energy_discharged_kwh += actual_energy

            self.power_kw = actual_energy / dt_hours

            self.mode = (
                BESSMode.DISCHARGING
                if self.power_kw > 0
                else BESSMode.IDLE
            )

        elif power < 0:
            available_capacity = (
                (cfg.max_soc - self.soc)
                / 100.0
                * cfg.capacity_kwh
            )

            max_energy_input = (
                available_capacity / cfg.charge_efficiency
            )

            requested_energy = abs(power) * dt_hours

            actual_energy = min(
                requested_energy,
                max_energy_input,
            )

            self.soc += (
                actual_energy
                * cfg.charge_efficiency
                / cfg.capacity_kwh
                * 100.0
            )

            self.energy_charged_kwh += actual_energy

            self.power_kw = -actual_energy / dt_hours

            self.mode = (
                BESSMode.CHARGING
                if self.power_kw < 0
                else BESSMode.IDLE
            )

        else:
            self.power_kw = 0.0
            self.mode = BESSMode.IDLE

        self.soc = max(
            cfg.min_soc,
            min(self.soc, cfg.max_soc),
        )

        current_a = (
            self.power_kw * 1000.0
            / cfg.nominal_voltage_v
        )

        return {
            "soc": round(self.soc, 2),
            "soh": self.soh,
            "power_kw": round(self.power_kw, 3),
            "voltage_v": cfg.nominal_voltage_v,
            "current_a": round(current_a, 2),
            "temperature_c": self.temperature_c,
            "mode": self.mode.value,
            "energy_charged_kwh": round(
                self.energy_charged_kwh, 3
            ),
            "energy_discharged_kwh": round(
                self.energy_discharged_kwh, 3
            ),
        }