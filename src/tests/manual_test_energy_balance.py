from datetime import datetime
from zoneinfo import ZoneInfo

from bess_simulators.bess_simulator import BESSimulator

from ems.ems_controller import EMSController

from ems.energy_balance import EnergyBalanceValidator

from grid_simulators.grid_simulator import GridSimulator

from grid_simulators.smart_meter_simulator import (
    SmartMeterSimulator
)


def main():

    ems = EMSController()

    validator = EnergyBalanceValidator()

    timezone = ZoneInfo("Europe/Bucharest")

    scenarios = [
        ("Nighttime",       0.0, 0.3, 50.0),
        ("Morning",         0.5, 1.5, 50.0),
        ("Solar surplus",   3.5, 1.0, 50.0),
        ("Battery full",    3.5, 1.0, 95.0),
        ("Battery empty",   0.0, 2.0, 10.0),
        ("High load",       0.0, 6.0, 50.0),
        ("Direct PV",       2.0, 2.0, 50.0),
        ("Evening",         0.2, 2.0, 50.0),
        ("Charge limit",    7.0, 1.0, 50.0),
        ("Near max SOC",    4.0, 0.5, 94.99),
        ("Near min SOC",    0.0, 3.0, 10.01),
    ]

    print("Integrated EMS Energy Balance Validation")

    print("-" * 115)

    print(
        f"{'Scenario':<18}"
        f"{'PV kW':>9}"
        f"{'Load kW':>9}"
        f"{'Req kW':>9}"
        f"{'BESS kW':>10}"
        f"{'Grid kW':>10}"
        f"{'SOC %':>9}"
        f"{'Error kW':>12}"
        f"{'Status':>14}"
    )

    print("-" * 115)

    passed = 0

    for name, pv, load, initial_soc in scenarios:

        # Independent battery and grid for each scenario
        bess = BESSimulator(
            initial_soc=initial_soc
        )

        grid = GridSimulator()

        meter = SmartMeterSimulator()

        timestamp = datetime.now(timezone)

        dt_seconds = 5.0

        # 1. Calculate EMS setpoint
        ems_data = ems.calculate_setpoint(
            pv_power_kw=pv,
            load_power_kw=load
        )

        requested_power = (
            ems_data["requested_bess_power_kw"]
        )

        # 2. Execute battery simulation
        bess_data = bess.step(
            requested_power_kw=requested_power,
            dt_seconds=dt_seconds
        )

        actual_bess_power = bess_data["power_kw"]

        # 3. Calculate actual grid power
        grid_data = grid.step(
            pv_power_kw=pv,
            load_power_kw=load,
            bess_power_kw=actual_bess_power,
            dt_seconds=dt_seconds
        )

        # 4. Read smart meter
        meter_data = meter.measure(
            grid_telemetry=grid_data,
            timestamp=timestamp
        )

        # 5. Validate system power balance
        balance = validator.validate(
            pv_power_kw=pv,
            load_power_kw=load,
            bess_power_kw=actual_bess_power,
            grid_power_kw=meter_data["power_kw"]
        )

        if balance["is_balanced"]:
            passed += 1

        print(
            f"{name:<18}"
            f"{pv:>9.3f}"
            f"{load:>9.3f}"
            f"{requested_power:>9.3f}"
            f"{actual_bess_power:>10.3f}"
            f"{meter_data['power_kw']:>10.3f}"
            f"{bess_data['soc']:>9.3f}"
            f"{balance['balance_error_kw']:>12.6f}"
            f"{balance['status']:>14}"
        )

    print("-" * 115)

    print(
        f"Balanced scenarios: {passed}/{len(scenarios)}"
    )

    assert passed == len(scenarios), (
        "One or more power balance scenarios failed"
    )

    # Negative control: intentionally inconsistent power
    invalid_balance = validator.validate(
        pv_power_kw=3.0,
        load_power_kw=1.0,
        bess_power_kw=-1.0,
        grid_power_kw=0.0
    )

    assert not invalid_balance["is_balanced"]

    print(
        "Negative control: "
        f"{invalid_balance['status']}"
    )

    print("Energy balance validation completed.")


if __name__ == "__main__":
    main()