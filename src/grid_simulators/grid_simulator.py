from enum import Enum
import math


class GridMode(str, Enum):

    IDLE = "IDLE"
    IMPORTING = "IMPORTING"
    EXPORTING = "EXPORTING"


class GridSimulator:
    """
    Simulates bidirectional grid power flow.

    Positive grid power = import from grid.
    Negative grid power = export to grid.

    Power: kW
    Energy: kWh
    """

    def __init__(self, zero_tolerance_kw: float = 0.001):

        if (
                not math.isfinite(zero_tolerance_kw)
                or zero_tolerance_kw < 0
        ):
            raise ValueError(
                "Zero tolerance must be finite and non-negative"
            )

        self.zero_tolerance_kw = zero_tolerance_kw

        self.power_kw = 0.0

        self.energy_imported_kwh = 0.0
        self.energy_exported_kwh = 0.0

        self.mode = GridMode.IDLE

    @staticmethod
    def calculate_grid_power(
        pv_power_kw: float,
        load_power_kw: float,
        bess_power_kw: float
    ) -> float:

        if not all(math.isfinite(value) for value in (
            pv_power_kw,
            load_power_kw,
            bess_power_kw
        )):
            raise ValueError("Power values must be finite")

        if pv_power_kw < 0:
            raise ValueError("PV power cannot be negative")

        if load_power_kw < 0:
            raise ValueError("Load power cannot be negative")

        return (
            load_power_kw
            - pv_power_kw
            - bess_power_kw
        )

    def step(
        self,
        pv_power_kw: float,
        load_power_kw: float,
        bess_power_kw: float,
        dt_seconds: float
    ) -> dict:

        if not math.isfinite(dt_seconds) or dt_seconds <= 0:
            raise ValueError("Time step must be finite and positive")

        self.power_kw = self.calculate_grid_power(
            pv_power_kw=pv_power_kw,
            load_power_kw=load_power_kw,
            bess_power_kw=bess_power_kw
        )

        if abs(self.power_kw) < self.zero_tolerance_kw:
            self.power_kw = 0.0

        dt_hours = dt_seconds / 3600.0

        import_power_kw = max(self.power_kw, 0.0)

        export_power_kw = max(-self.power_kw, 0.0)

        self.energy_imported_kwh += (
            import_power_kw * dt_hours
        )

        self.energy_exported_kwh += (
            export_power_kw * dt_hours
        )

        if self.power_kw > 0:

            self.mode = GridMode.IMPORTING

        elif self.power_kw < 0:

            self.mode = GridMode.EXPORTING

        else:

            self.mode = GridMode.IDLE

        return {
            "power_kw": self.power_kw,
            "import_power_kw": import_power_kw,
            "export_power_kw": export_power_kw,
            "energy_imported_kwh": self.energy_imported_kwh,
            "energy_exported_kwh": self.energy_exported_kwh,
            "mode": self.mode.value
        }

    def reset(self) -> None:

        self.power_kw = 0.0

        self.energy_imported_kwh = 0.0
        self.energy_exported_kwh = 0.0

        self.mode = GridMode.IDLE