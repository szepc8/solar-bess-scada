import time

from common.influx_writer import InfluxWriter
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import datetime
from zoneinfo import ZoneInfo

from pv_simulator.config import PVConfig
from pv_simulator.pv_generation import PVGeneration


class RealtimePVSimulator:

    def __init__(self):

        self.config = PVConfig()

        self.generation = PVGeneration(self.config)

        self.timezone = ZoneInfo(
            self.config.timezone
        )

        self.interval = (
            self.config.simulation_interval_seconds
        )

        self.influx_writer = InfluxWriter()

        self.cached_date = None
        self.cached_data = None

    def get_current_measurement(self):

        now = datetime.now(self.timezone)

        current_date = now.date().isoformat()

        # Recalculate the daily profile only
        # when the simulation date changes.
        if current_date != self.cached_date:

            self.cached_data = (
                self.generation.simulate_day(
                    current_date
                )
            )

            self.cached_date = current_date

        # The daily profile has a 5-minute resolution.
        # Select the corresponding time interval.
        timestamp = now.replace(
            minute=(now.minute // 5) * 5,
            second=0,
            microsecond=0
        )

        measurement = self.cached_data.loc[
            timestamp
        ]

        return {
            "timestamp": now.isoformat(),
            "irradiance_wm2": round(
                float(measurement["irradiance"]), 2
            ),
            "ambient_temperature_c": round(
                float(measurement["ambient_temperature"]), 2
            ),
            "panel_temperature_c": round(
                float(measurement["panel_temperature"]), 2
            ),
            "dc_power_kw": round(
                float(measurement["dc_power"]), 3
            ),
            "ac_power_kw": round(
                float(measurement["ac_power"]), 3
            )
        }

    def run(self):

        print("\n=== FRONIUS PRIMO 4.0-1 SIMULATOR ===")
        print("Location: Brasov, Romania")
        print("PV Capacity: 4 kWp")
        print("Telemetry Interval: 5 seconds")
        print("------------------------------------")

        try:
            while True:

                measurement = (
                    self.get_current_measurement()
                )

                print(measurement)

                self.influx_writer.write_pv_measurement(
                    measurement
                )

                print("Telemetry sent to InfluxDB")

                time.sleep(self.interval)

        except KeyboardInterrupt:

            print("\nSimulator stopped.")

        finally:
            self.influx_writer.close()

if __name__ == "__main__":

    simulator = RealtimePVSimulator()

    simulator.run()