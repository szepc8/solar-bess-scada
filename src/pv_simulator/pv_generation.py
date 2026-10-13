import pandas as pd
from weather_model import WeatherModel

from config import PVConfig
from solar_model import SolarModel
from simulator import PVSimulator


class PVGeneration:

    def __init__(self, config: PVConfig):

        self.config = config

        self.solar_model = SolarModel(config)

        self.pv_simulator = PVSimulator(config)

        self.weather_model = WeatherModel(
            min_temperature=15.0,
            max_temperature=28.0,
            cloudiness=0.3,
            seed=42
        )

    def simulate_day(
        self,
        date: str,
        ambient_temperature: float = 25.0
    ) -> pd.DataFrame:

        solar_data = self.solar_model.calculate_irradiance(date)

        solar_data = self.weather_model.generate_weather(
            solar_data
        )

        results = []

        for timestamp, row in solar_data.iterrows():

            irradiance = row["irradiance"]

            ambient_temperature = row["ambient_temperature"]

            panel_temperature = (
                self.pv_simulator.calculate_panel_temperature(
                    irradiance,
                    ambient_temperature
                )
            )

            dc_power = (
                self.pv_simulator.calculate_dc_power(
                    irradiance,
                    panel_temperature
                )
            )

            ac_power = (
                self.pv_simulator.calculate_ac_power(
                    dc_power
                )
            )

            results.append({
                "timestamp": timestamp,
                "irradiance": irradiance,
                "ambient_temperature": ambient_temperature,
                "panel_temperature": panel_temperature,
                "dc_power": dc_power,
                "ac_power": ac_power
            })

        df = pd.DataFrame(results)

        df.set_index("timestamp", inplace=True)

        # Energy calculation: 5-minute intervals
        interval_hours = 5.0 / 60.0

        df["energy_kwh"] = (
            df["ac_power"] * interval_hours
        )

        df["daily_energy_kwh"] = (
            df["energy_kwh"].cumsum()
        )

        return df


if __name__ == "__main__":

    config = PVConfig()

    generation = PVGeneration(config)

    data = generation.simulate_day(
        date="2026-06-21",
        ambient_temperature=25.0
    )

    print(data.head(10))

    print("\n--- PV SIMULATION RESULTS ---")

    print(
        "Maximum DC Power:",
        round(data["dc_power"].max(), 2),
        "kW"
    )

    print(
        "Maximum AC Power:",
        round(data["ac_power"].max(), 2),
        "kW"
    )

    print(
        "Daily Energy:",
        round(data["energy_kwh"].sum(), 2),
        "kWh"
    )