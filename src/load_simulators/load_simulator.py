from dataclasses import dataclass
from datetime import datetime
import math
import random


@dataclass
class LoadConfig:
    min_power_kw: float = 0.15
    max_power_kw: float = 6.0
    variation: float = 0.15
    random_seed: int = 42


class LoadSimulator:
    """
    Simulates residential electricity consumption.

    Power is expressed in kW.
    Energy is expressed in kWh.

    Positive power represents household consumption.
    """

    DAILY_PROFILE = (
        (0, 6, 0.30),
        (6, 9, 1.50),
        (9, 12, 0.60),
        (12, 14, 1.20),
        (14, 17, 0.70),
        (17, 21, 2.00),
        (21, 23, 0.90),
        (23, 24, 0.40),
    )

    def __init__(self, config: LoadConfig | None = None):

        self.config = config if config is not None else LoadConfig()

        self._validate_config()

        self._random = random.Random(
            self.config.random_seed
        )

        self.power_kw = 0.0
        self.energy_consumed_kwh = 0.0

    def _validate_config(self) -> None:

        if not all(math.isfinite(value) for value in (
            self.config.min_power_kw,
            self.config.max_power_kw,
            self.config.variation,
        )):
            raise ValueError("Configuration values must be finite")

        if self.config.min_power_kw < 0:
            raise ValueError("Minimum power cannot be negative")

        if self.config.max_power_kw <= 0:
            raise ValueError("Maximum power must be positive")

        if self.config.max_power_kw < self.config.min_power_kw:
            raise ValueError(
                "Maximum power must be greater than or equal to minimum power"
            )

        if not 0 <= self.config.variation <= 1:
            raise ValueError("Variation must be between 0 and 1")

    def get_base_power(self, timestamp: datetime) -> float:
        """
        Return nominal household consumption
        for the supplied local time.
        """

        hour = timestamp.hour

        for start_hour, end_hour, power_kw in self.DAILY_PROFILE:

            if start_hour <= hour < end_hour:
                return power_kw

        raise RuntimeError("No matching household load interval")

    def calculate_power(self, timestamp: datetime) -> float:
        """
        Calculate household power with random variation.
        """

        base_power = self.get_base_power(timestamp)

        variation_factor = self._random.uniform(
            1.0 - self.config.variation,
            1.0 + self.config.variation
        )

        power_kw = base_power * variation_factor

        power_kw = max(
            self.config.min_power_kw,
            power_kw
        )

        power_kw = min(
            self.config.max_power_kw,
            power_kw
        )

        return power_kw

    def step(
        self,
        timestamp: datetime,
        dt_seconds: float
    ) -> dict:
        """
        Advance the simulation by one time interval.
        """

        if not math.isfinite(dt_seconds) or dt_seconds <= 0:
            raise ValueError("Time step must be finite and positive")

        self.power_kw = self.calculate_power(timestamp)

        dt_hours = dt_seconds / 3600.0

        interval_energy_kwh = self.power_kw * dt_hours

        self.energy_consumed_kwh += interval_energy_kwh

        return {
            "timestamp": timestamp.isoformat(),
            "power_kw": self.power_kw,
            "energy_consumed_kwh": self.energy_consumed_kwh
        }

    def reset(self) -> None:
        """
        Reset the simulation state and random sequence.
        """

        self.power_kw = 0.0
        self.energy_consumed_kwh = 0.0

        self._random.seed(self.config.random_seed)