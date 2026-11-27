from dataclasses import dataclass
from datetime import datetime
import math


@dataclass
class SmartMeterConfig:

    voltage_v: float = 230.0
    frequency_hz: float = 50.0
    power_factor: float = 1.0


class SmartMeterSimulator:
    """
    Simulates a single-phase bidirectional smart meter.

    Positive active power = grid import.
    Negative active power = grid export.

    Current is reported as a non-negative RMS magnitude.
    """

    def __init__(
        self,
        config: SmartMeterConfig | None = None
    ):

        self.config = (
            config if config is not None
            else SmartMeterConfig()
        )

        self._validate_config()

    def _validate_config(self) -> None:

        if not all(math.isfinite(value) for value in (
            self.config.voltage_v,
            self.config.frequency_hz,
            self.config.power_factor
        )):
            raise ValueError("Configuration values must be finite")

        if self.config.voltage_v <= 0:
            raise ValueError("Voltage must be positive")

        if self.config.frequency_hz <= 0:
            raise ValueError("Frequency must be positive")

        if not 0 < self.config.power_factor <= 1:
            raise ValueError(
                "Power factor must be greater than 0 and at most 1"
            )

    def measure(
        self,
        grid_telemetry: dict,
        timestamp: datetime
    ) -> dict:

        power_kw = grid_telemetry["power_kw"]

        energy_imported_kwh = (
            grid_telemetry["energy_imported_kwh"]
        )

        energy_exported_kwh = (
            grid_telemetry["energy_exported_kwh"]
        )

        if not all(math.isfinite(value) for value in (
            power_kw,
            energy_imported_kwh,
            energy_exported_kwh
        )):
            raise ValueError("Meter values must be finite")

        if energy_imported_kwh < 0 or energy_exported_kwh < 0:
            raise ValueError("Energy counters cannot be negative")

        current_a = (
            abs(power_kw) * 1000.0
            / (
                self.config.voltage_v
                * self.config.power_factor
            )
        )

        apparent_power_kva = (
            abs(power_kw)
            / self.config.power_factor
        )

        return {
            "timestamp": timestamp.isoformat(),
            "power_kw": power_kw,
            "voltage_v": self.config.voltage_v,
            "current_a": current_a,
            "frequency_hz": self.config.frequency_hz,
            "power_factor": self.config.power_factor,
            "apparent_power_kva": apparent_power_kva,
            "energy_imported_kwh": energy_imported_kwh,
            "energy_exported_kwh": energy_exported_kwh,
            "mode": grid_telemetry["mode"]
        }