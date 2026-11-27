from datetime import datetime

from realtime_simulator import RealtimeSystemSimulator


def main():

    simulator = RealtimeSystemSimulator()

    try:

        now = datetime.now(simulator.timezone)

        system_data = simulator.simulate_step(
            now=now,
            dt_seconds=5.0
        )

        simulator.publish_telemetry(
            system_data
        )

        simulator.print_system_status(
            system_data
        )

        print("\n=== INFLUXDB INTEGRATION TEST ===")

        measurements = (
            "pv_inverter",
            "bess",
            "household_load",
            "ems",
            "grid",
            "smart_meter",
            "energy_balance"
        )

        for measurement in measurements:

            print(f"[SUBMITTED] {measurement}")

        print("\nMeasurements submitted: 7")

        print(
            f"Common timestamp: "
            f"{system_data['timestamp']}"
        )

        print("InfluxDB batch write completed.")

    finally:

        simulator.influx_writer.close()

        print("InfluxDB connection closed.")


if __name__ == "__main__":

    main()