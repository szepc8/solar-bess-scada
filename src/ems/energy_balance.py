from dataclasses import dataclass
import math


@dataclass
class EnergyBalanceConfig:

    tolerance_kw: float = 0.001


class EnergyBalanceValidator:
    """
    Validates the AC-side power balance.

    PV power:
        Positive = generation

    Load power:
        Positive = consumption

    BESS power:
        Positive = discharging
        Negative = charging

    Grid power:
        Positive = import
        Negative = export
    """

    def __init__(
        self,
        config: EnergyBalanceConfig | None = None
    ):

        self.config = (
            config if config is not None
            else EnergyBalanceConfig()
        )

        if (
            not math.isfinite(self.config.tolerance_kw)
            or self.config.tolerance_kw < 0
        ):
            raise ValueError(
                "Tolerance must be finite and non-negative"
            )

    def validate(
        self,
        pv_power_kw: float,
        load_power_kw: float,
        bess_power_kw: float,
        grid_power_kw: float
    ) -> dict:

        if not all(math.isfinite(value) for value in (
            pv_power_kw,
            load_power_kw,
            bess_power_kw,
            grid_power_kw
        )):
            raise ValueError("Power values must be finite")

        if pv_power_kw < 0 or load_power_kw < 0:
            raise ValueError(
                "PV and load power must be non-negative"
            )

        supply_power_kw = (
            pv_power_kw
            + max(bess_power_kw, 0.0)
            + max(grid_power_kw, 0.0)
        )

        demand_power_kw = (
            load_power_kw
            + max(-bess_power_kw, 0.0)
            + max(-grid_power_kw, 0.0)
        )

        balance_error_kw = (
            supply_power_kw - demand_power_kw
        )

        is_balanced = (
            abs(balance_error_kw)
            <= self.config.tolerance_kw
        )

        return {
            "pv_power_kw": pv_power_kw,
            "load_power_kw": load_power_kw,
            "bess_power_kw": bess_power_kw,
            "grid_power_kw": grid_power_kw,
            "supply_power_kw": supply_power_kw,
            "demand_power_kw": demand_power_kw,
            "balance_error_kw": balance_error_kw,
            "is_balanced": is_balanced,
            "status": (
                "BALANCED"
                if is_balanced
                else "UNBALANCED"
            )
        }