import time

from common.influx_writer import InfluxWriter
from datetime import datetime
from zoneinfo import ZoneInfo

from pv_simulator.config import PVConfig
from pv_simulator.pv_generation import PVGeneration
from bess_simulators.bess_simulator import BESSimulator

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

        self.bess = BESSimulator(initial_soc=50.0)

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

    def get_bess_measurement(self, dt_seconds: float) -> dict:

        now = datetime.now(self.timezone)

        hour = now.hour

        if 6 <= hour < 12:
            requested_power = -2.0

        elif 12 <= hour < 18:
            requested_power = 2.0

        else:
            requested_power = 0.0

        telemetry = self.bess.step(
            requested_power_kw=requested_power,
            dt_seconds=dt_seconds
        )

        telemetry["timestamp"] = now.isoformat()

        return telemetry

    def run(self):

        print("\n=== SOLAR PV + ALPHAESS BESS SIMULATOR ===")
        print("Location: Brasov, Romania")
        print("PV: Fronius Primo 4.0-1")
        print("BESS: AlphaESS Simulator")
        print(f"Telemetry Interval: {self.interval} seconds")
        print("----------------------------------------")

        previous_step = time.monotonic()

        try:
            while True:
                current_step = time.monotonic()
                dt_seconds = current_step - previous_step
                previous_step = current_step

                # PV telemetry
                pv_measurement = self.get_current_measurement()

                self.influx_writer.write_pv_measurement(
                    pv_measurement
                )

                # BESS telemetry
                bess_measurement = self.get_bess_measurement(
                    dt_seconds
                )

                self.influx_writer.write_bess_measurement(
                    bess_measurement
                )

                print("\n--- PV ---")
                print(pv_measurement)

                print("--- BESS ---")
                print(bess_measurement)

                print("Telemetry sent to InfluxDB")

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\nSimulator stopped.")

        finally:
            self.influx_writer.close()
if __name__ == "__main__":

    simulator = RealtimePVSimulator()

    simulator.run()