from ems.ems_controller import EMSController


def main():

    ems = EMSController()

    scenarios = [
        ("Nighttime", 0.0, 0.3),
        ("Morning", 0.5, 1.5),
        ("Solar surplus", 3.5, 0.6),
        ("Balanced", 2.0, 2.0),
        ("Maximum PV", 4.0, 0.7),
        ("Evening", 0.2, 2.0),
        ("High consumption", 0.0, 6.0),
        ("Deadband", 2.0, 2.005),
        ("No production/load", 0.0, 0.0),
    ]

    print("EMS Controller - Maximum Self-Consumption")
    print("-" * 85)

    print(
        f"{'Scenario':<22}"
        f"{'PV kW':>10}"
        f"{'Load kW':>10}"
        f"{'Net kW':>10}"
        f"{'BESS Req kW':>15}"
        f"{'EMS Mode':>18}"
    )

    print("-" * 85)

    for name, pv_power, load_power in scenarios:

        result = ems.calculate_setpoint(
            pv_power_kw=pv_power,
            load_power_kw=load_power
        )

        print(
            f"{name:<22}"
            f"{result['pv_power_kw']:>10.3f}"
            f"{result['load_power_kw']:>10.3f}"
            f"{result['net_power_kw']:>10.3f}"
            f"{result['requested_bess_power_kw']:>15.3f}"
            f"{result['mode']:>18}"
        )

    print("-" * 85)

    print("EMS simulation completed successfully.")


if __name__ == "__main__":
    main()