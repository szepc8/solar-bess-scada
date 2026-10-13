import matplotlib.pyplot as plt

from config import PVConfig
from pv_generation import PVGeneration
from weather_model import WeatherModel


def main():

    config = PVConfig()

    date = "2026-06-21"

    # Clear sky simulation
    clear_sky = PVGeneration(config)

    clear_sky.weather_model = WeatherModel(
        min_temperature=25.0,
        max_temperature=25.0,
        cloudiness=0.0,
        seed=42
    )

    clear_data = clear_sky.simulate_day(date)

    # Cloudy simulation
    cloudy = PVGeneration(config)

    cloudy.weather_model = WeatherModel(
        min_temperature=15.0,
        max_temperature=28.0,
        cloudiness=0.3,
        seed=42
    )

    cloudy_data = cloudy.simulate_day(date)

    # Plot
    plt.figure(figsize=(12, 6))

    plt.plot(
        clear_data.index,
        clear_data["ac_power"],
        label="Clear Sky",
        linewidth=2
    )

    plt.plot(
        cloudy_data.index,
        cloudy_data["ac_power"],
        label="Cloudy Weather",
        linewidth=2
    )

    plt.title(
        "PV Production - Brasov - 21 June 2026"
    )

    plt.xlabel("Time")
    plt.ylabel("AC Power (kW)")

    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.show()

    print("\n--- DAILY ENERGY COMPARISON ---")

    print(
        f"Clear Sky: "
        f"{clear_data['energy_kwh'].sum():.2f} kWh"
    )

    print(
        f"Cloudy Weather: "
        f"{cloudy_data['energy_kwh'].sum():.2f} kWh"
    )


if __name__ == "__main__":
    main()