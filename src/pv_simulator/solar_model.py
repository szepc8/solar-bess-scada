import pandas as pd
import pvlib

from config import PVConfig


class SolarModel:

    def __init__(self, config: PVConfig):
        self.config = config

        self.location = pvlib.location.Location(
            latitude=config.latitude,
            longitude=config.longitude,
            tz=config.timezone,
            altitude=config.altitude_m,
            name="Brasov PV System"
        )

    def calculate_irradiance(self, date: str):

        times = pd.date_range(
            start=f"{date} 00:00",
            periods=288,
            freq="5min",
            tz=self.config.timezone
        )

        solar_position = self.location.get_solarposition(times)

        clearsky = self.location.get_clearsky(times)

        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=self.config.tilt_deg,
            surface_azimuth=self.config.orientation_deg,
            solar_zenith=solar_position["apparent_zenith"],
            solar_azimuth=solar_position["azimuth"],
            dni=clearsky["dni"],
            ghi=clearsky["ghi"],
            dhi=clearsky["dhi"]
        )

        return pd.DataFrame({
            "irradiance": poa["poa_global"],
            "solar_elevation": solar_position["apparent_elevation"]
        })


if __name__ == "__main__":

    config = PVConfig()

    solar = SolarModel(config)

    data = solar.calculate_irradiance("2026-06-21")

    print(data.head(10))

    print(
        "\nMaximum irradiance:",
        round(data["irradiance"].max(), 2),
        "W/m²"
    )