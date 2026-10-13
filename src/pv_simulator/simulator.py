from pv_simulator.config import PVConfig


class PVSimulator:

    def __init__(self, config: PVConfig):
        self.config = config

    def calculate_panel_temperature(
        self,
        irradiance: float,
        ambient_temperature: float
    ) -> float:

        # Simplified thermal model
        noct = 45.0

        panel_temperature = (
            ambient_temperature
            + (noct - 20.0) / 800.0 * irradiance
        )

        return panel_temperature

    def calculate_dc_power(
        self,
        irradiance: float,
        panel_temperature: float
    ) -> float:

        temperature_factor = (
            1.0
            + self.config.temperature_coefficient
            * (
                panel_temperature
                - self.config.reference_temperature
            )
        )

        dc_power = (
            self.config.installed_capacity_kw
            * irradiance / 1000.0
            * temperature_factor
        )

        return max(0.0, dc_power)

    def calculate_ac_power(
        self,
        dc_power: float
    ) -> float:

        ac_power = (
            dc_power
            * self.config.inverter_efficiency
        )

        return min(
            max(0.0, ac_power),
            self.config.inverter_capacity_kw
        )