from datetime import datetime
from zoneinfo import ZoneInfo

from load_simulators.load_simulator import (
    LoadConfig,
    LoadSimulator
)


def main():

    config = LoadConfig(
        variation=0.15,
        random_seed=42
    )

    simulator = LoadSimulator(config)

    timezone = ZoneInfo("Europe/Bucharest")

    test_hours = [2, 7, 10, 13, 15, 19, 22, 23]

    print("Household Load Simulator")
    print("-" * 65)

    print(
        f"{'Time':<10}"
        f"{'Base kW':>12}"
        f"{'Actual kW':>15}"
        f"{'Energy kWh':>18}"
    )

    print("-" * 65)

    for hour in test_hours:

        timestamp = datetime(
            2026, 11, 26,
            hour, 0, 0,
            tzinfo=timezone
        )

        base_power = simulator.get_base_power(timestamp)

        telemetry = simulator.step(
            timestamp=timestamp,
            dt_seconds=5.0
        )

        print(
            f"{timestamp.strftime('%H:%M'):<10}"
            f"{base_power:>12.3f}"
            f"{telemetry['power_kw']:>15.3f}"
            f"{telemetry['energy_consumed_kwh']:>18.6f}"
        )

    print("-" * 65)

    print("Simulation completed successfully.")


if __name__ == "__main__":
    main()