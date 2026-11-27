from datetime import datetime
from zoneinfo import ZoneInfo

from grid_simulators.grid_simulator import GridSimulator

from grid_simulators.smart_meter_simulator import (
    SmartMeterSimulator
)


def main():

    grid = GridSimulator()

    meter = SmartMeterSimulator()

    timezone = ZoneInfo("Europe/Bucharest")

    scenarios = [
        ("Nighttime", 0.0, 0.3, 0.3),
        ("Solar charging", 3.5, 1.0, -2.5),
        ("Battery full", 3.5, 1.0, 0.0),
        ("Battery empty", 0.0, 2.0, 0.0),
        ("High consumption", 0.0, 6.0, 5.0),
        ("Direct PV", 2.0, 2.0, 0.0),
        ("Partial charging", 4.0, 1.0, -2.0),
    ]

    print("Grid and Smart Meter Simulator")

    print("-" * 100)

    print(
        f"{'Scenario':<20}"
        f"{'PV kW':>10}"
        f"{'Load kW':>10}"
        f"{'BESS kW':>10}"
        f"{'Grid kW':>10}"
        f"{'Current A':>12}"
        f"{'Mode':>15}"
    )

    print("-" * 100)

    for name, pv, load, bess in scenarios:

        grid_data = grid.step(
            pv_power_kw=pv,
            load_power_kw=load,
            bess_power_kw=bess,
            dt_seconds=5.0
        )

        meter_data = meter.measure(
            grid_telemetry=grid_data,
            timestamp=datetime.now(timezone)
        )

        print(
            f"{name:<20}"
            f"{pv:>10.3f}"
            f"{load:>10.3f}"
            f"{bess:>10.3f}"
            f"{grid_data['power_kw']:>10.3f}"
            f"{meter_data['current_a']:>12.3f}"
            f"{meter_data['mode']:>15}"
        )

    print("-" * 100)

    print(
        f"Total imported energy: "
        f"{grid.energy_imported_kwh:.6f} kWh"
    )

    print(
        f"Total exported energy: "
        f"{grid.energy_exported_kwh:.6f} kWh"
    )

    print("Simulation completed successfully.")


if __name__ == "__main__":
    main()