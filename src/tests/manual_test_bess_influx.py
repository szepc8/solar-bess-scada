from datetime import datetime, timezone

from src.bess_simulators.bess_simulator import BESSimulator
from src.common.influx_writer import InfluxWriter


def main():

    bess = BESSimulator()

    writer = InfluxWriter()

    try:
        telemetry = bess.step(
            requested_power_kw=2.0,
            dt_seconds=5.0
        )

        telemetry["timestamp"] = (
            datetime.now(timezone.utc).isoformat()
        )

        writer.write_bess_measurement(telemetry)

        print("BESS telemetry:")
        print(telemetry)

        print("\nBESS telemetry successfully sent to InfluxDB!")

    finally:
        writer.close()


if __name__ == "__main__":
    main()