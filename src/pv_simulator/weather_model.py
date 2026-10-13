import numpy as np
import pandas as pd


class WeatherModel:

    def __init__(
        self,
        min_temperature: float = 15.0,
        max_temperature: float = 28.0,
        cloudiness: float = 0.3,
        seed: int = 42
    ):
        self.min_temperature = min_temperature
        self.max_temperature = max_temperature
        self.cloudiness = np.clip(cloudiness, 0.0, 1.0)

        self.rng = np.random.default_rng(seed)

    def generate_weather(
        self,
        solar_data: pd.DataFrame
    ) -> pd.DataFrame:

        df = solar_data.copy()

        hours = (
            df.index.hour
            + df.index.minute / 60.0
        )

        # Minimum temperature around 05:00
        # Maximum temperature around 15:00
        temperature_cycle = (
            1.0
            + np.cos(
                2.0 * np.pi * (hours - 15.0) / 24.0
            )
        ) / 2.0

        df["ambient_temperature"] = (
            self.min_temperature
            + (
                self.max_temperature
                - self.min_temperature
            ) * temperature_cycle
        )

        # Smooth cloud variation
        cloud_noise = self.rng.uniform(
            0.0,
            1.0,
            len(df)
        )

        cloud_factor = pd.Series(
            cloud_noise,
            index=df.index
        ).rolling(
            window=12,
            min_periods=1
        ).mean()

        # Cloud attenuation
        attenuation = (
            1.0
            - self.cloudiness * cloud_factor
        )

        df["cloud_factor"] = attenuation

        df["irradiance_clear_sky"] = df["irradiance"]

        df["irradiance"] = (
            df["irradiance_clear_sky"]
            * df["cloud_factor"]
        )

        return df

