from dataclasses import dataclass
from enum import Enum
import math


class EMSMode(str, Enum):

    IDLE = "IDLE"
    CHARGING = "CHARGING"
    DISCHARGING = "DISCHARGING"


@dataclass
class EMSConfig:

    deadband_kw: float = 0.01


class EMSController:
    """
    Energy Management System controller.

    Strategy:
        Maximum PV self-consumption.

    BESS power convention:
        Positive = discharging
        Negative = charging
        Zero = idle

    Battery protection and physical limits are
    handled by the BESS simulator.
    """

    def __init__(self, config: EMSConfig | None = None):

        self.config = config if config is not None else EMSConfig()

        self._validate_config()

    def _validate_config(self) -> None:

        if not math.isfinite(self.config.deadband_kw):
            raise ValueError("Deadband must be finite")

        if self.config.deadband_kw < 0:
            raise ValueError("Deadband cannot be negative")

    @staticmethod
    def _validate_power(power_kw: float, name: str) -> None:

        if not math.isfinite(power_kw):
            raise ValueError(f"{name} must be finite")

        if power_kw < 0:
            raise ValueError(f"{name} cannot be negative")

    def calculate_setpoint(
        self,
        pv_power_kw: float,
        load_power_kw: float
    ) -> dict:
        """
        Calculate the requested battery power.

        The returned setpoint is not limited by battery
        SOC or maximum battery power.
        """

        self._validate_power(pv_power_kw, "PV power")
        self._validate_power(load_power_kw, "Load power")

        net_power_kw = load_power_kw - pv_power_kw

        if abs(net_power_kw) <= self.config.deadband_kw:

            requested_power_kw = 0.0
            mode = EMSMode.IDLE

        elif net_power_kw > 0:

            requested_power_kw = net_power_kw
            mode = EMSMode.DISCHARGING

        else:

            requested_power_kw = net_power_kw
            mode = EMSMode.CHARGING

        return {
            "pv_power_kw": pv_power_kw,
            "load_power_kw": load_power_kw,
            "net_power_kw": net_power_kw,
            "requested_bess_power_kw": requested_power_kw,
            "mode": mode.value
        }