import time

from datetime import datetime
from zoneinfo import ZoneInfo

from common.influx_writer import InfluxWriter

from pv_simulator.config import PVConfig
from pv_simulator.pv_generation import PVGeneration

from bess_simulators.bess_simulator import BESSimulator

from load_simulators.load_simulator import LoadSimulator

from ems.ems_controller import EMSController
from ems.energy_balance import EnergyBalanceValidator

from grid_simulators.grid_simulator import GridSimulator
from grid_simulators.smart_meter_simulator import (
    SmartMeterSimulator
)


class RealtimeSystemSimulator:
    """
    Real-time Solar BESS SCADA system simulator.

    Components:
        - Fronius PV Simulator
        - AlphaESS BESS Simulator
        - Household Load Simulator
        - EMS Controller
        - Grid Simulator
        - Smart Meter Simulator
        - Energy Balance Validator
    """

    def __init__(self):

        # PV configuration
        self.config = PVConfig()

        self.generation = PVGeneration(self.config)

        self.timezone = ZoneInfo(
            self.config.timezone
        )

        self.interval = (
            self.config.simulation_interval_seconds
        )

        # Energy system components
        self.bess = BESSimulator(initial_soc=50.0)

        self.load = LoadSimulator()

        self.ems = EMSController()

        self.grid = GridSimulator()

        self.smart_meter = SmartMeterSimulator()

        self.balance_validator = EnergyBalanceValidator()

        # InfluxDB connection
        self.influx_writer = InfluxWriter()

        # PV daily profile cache
        self.cached_date = None
        self.cached_data = None

        # Simulation counters
        self.step_count = 0
        self.unbalanced_count = 0

    def get_current_measurement(
        self,
        now: datetime
    ) -> dict:

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

        # Select the corresponding 5-minute interval.
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

    def get_bess_measurement(
        self,
        requested_power_kw: float,
        dt_seconds: float,
        now: datetime
    ) -> dict:

        telemetry = self.bess.step(
            requested_power_kw=requested_power_kw,
            dt_seconds=dt_seconds
        )

        telemetry["timestamp"] = now.isoformat()

        return telemetry

    def simulate_step(
        self,
        now: datetime,
        dt_seconds: float
    ) -> dict:
        """
        Execute one complete energy system simulation step.
        """

        timestamp = now.isoformat()

        # 1. PV generation
        pv_data = self.get_current_measurement(now)

        pv_power_kw = pv_data["ac_power_kw"]

        # 2. Household consumption
        load_data = self.load.step(
            timestamp=now,
            dt_seconds=dt_seconds
        )

        load_power_kw = load_data["power_kw"]

        # 3. EMS battery setpoint
        ems_data = self.ems.calculate_setpoint(
            pv_power_kw=pv_power_kw,
            load_power_kw=load_power_kw
        )

        ems_data["timestamp"] = timestamp

        requested_bess_power_kw = (
            ems_data["requested_bess_power_kw"]
        )

        # 4. Actual battery response
        bess_data = self.get_bess_measurement(
            requested_power_kw=requested_bess_power_kw,
            dt_seconds=dt_seconds,
            now=now
        )

        actual_bess_power_kw = bess_data["power_kw"]

        # 5. Grid import/export
        grid_data = self.grid.step(
            pv_power_kw=pv_power_kw,
            load_power_kw=load_power_kw,
            bess_power_kw=actual_bess_power_kw,
            dt_seconds=dt_seconds
        )

        grid_data["timestamp"] = timestamp

        # 6. Smart meter measurements
        meter_data = self.smart_meter.measure(
            grid_telemetry=grid_data,
            timestamp=now
        )

        # 7. Power balance validation
        balance_data = self.balance_validator.validate(
            pv_power_kw=pv_power_kw,
            load_power_kw=load_power_kw,
            bess_power_kw=actual_bess_power_kw,
            grid_power_kw=meter_data["power_kw"]
        )

        balance_data["timestamp"] = timestamp

        # 8. Update simulation counters
        self.step_count += 1

        if not balance_data["is_balanced"]:
            self.unbalanced_count += 1

        # 9. Return complete system telemetry
        return {
            "timestamp": timestamp,
            "dt_seconds": dt_seconds,
            "pv": pv_data,
            "load": load_data,
            "ems": ems_data,
            "bess": bess_data,
            "grid": grid_data,
            "smart_meter": meter_data,
            "balance": balance_data
        }

    def publish_telemetry(self, system_data: dict) -> None:
        """
        Publish all seven system measurements
        using a single InfluxDB write request.
        """

        self.influx_writer.write_system_measurement(
            system_data
        )

    def print_system_status(
        self,
        system_data: dict
    ) -> None:

        pv = system_data["pv"]
        load = system_data["load"]
        ems = system_data["ems"]
        bess = system_data["bess"]
        grid = system_data["grid"]
        meter = system_data["smart_meter"]
        balance = system_data["balance"]

        print("\n" + "-" * 70)

        print(
            f"Timestamp: {system_data['timestamp']}"
        )

        print(
            f"Step: {self.step_count} | "
            f"dt: {system_data['dt_seconds']:.3f} s"
        )

        print("-" * 70)

        print(
            f"PV generation:       "
            f"{pv['ac_power_kw']:>9.3f} kW"
        )

        print(
            f"Household load:      "
            f"{load['power_kw']:>9.3f} kW"
        )

        print(
            f"BESS requested:      "
            f"{ems['requested_bess_power_kw']:>9.3f} kW"
        )

        print(
            f"BESS actual:         "
            f"{bess['power_kw']:>9.3f} kW"
        )

        print(
            f"BESS SOC:            "
            f"{bess['soc']:>9.2f} %"
        )

        print(
            f"Grid power:          "
            f"{grid['power_kw']:>9.3f} kW"
        )

        print("-" * 70)

        print(f"EMS mode:            {ems['mode']}")

        print(f"BESS mode:           {bess['mode']}")

        print(f"Grid mode:           {grid['mode']}")

        print("-" * 70)

        print(
            f"Grid voltage:        "
            f"{meter['voltage_v']:>9.2f} V"
        )

        print(
            f"Grid current:        "
            f"{meter['current_a']:>9.3f} A"
        )

        print(
            f"Grid frequency:      "
            f"{meter['frequency_hz']:>9.2f} Hz"
        )

        print("-" * 70)

        print(
            f"Load energy:         "
            f"{load['energy_consumed_kwh']:>9.6f} kWh"
        )

        print(
            f"Imported energy:     "
            f"{grid['energy_imported_kwh']:>9.6f} kWh"
        )

        print(
            f"Exported energy:     "
            f"{grid['energy_exported_kwh']:>9.6f} kWh"
        )

        print("-" * 70)

        print(
            f"Supply power:        "
            f"{balance['supply_power_kw']:>9.3f} kW"
        )

        print(
            f"Demand power:        "
            f"{balance['demand_power_kw']:>9.3f} kW"
        )

        print(
            f"Balance error:       "
            f"{balance['balance_error_kw']:>9.6f} kW"
        )

        print(f"Balance status:      {balance['status']}")

        print(
            f"Unbalanced steps:    "
            f"{self.unbalanced_count}/{self.step_count}"
        )

        print("-" * 70)

        print("All 7 system measurements sent to InfluxDB")

    def run(self):

        print("\n=== SOLAR BESS SCADA SYSTEM SIMULATOR ===")

        print("Location: Brasov, Romania")
        print("PV: Fronius Primo 4.0-1")
        print("BESS: AlphaESS Simulator")
        print("EMS: Maximum Self-Consumption")
        print("Grid: Bidirectional")
        print("Smart Meter: Single-phase")

        print(
            f"Telemetry Interval: {self.interval} seconds"
        )

        print("-" * 70)

        previous_step = time.monotonic()

        try:

            # Allow one real interval to elapse before
            # accumulating the first energy measurement.
            time.sleep(self.interval)

            while True:

                current_step = time.monotonic()

                dt_seconds = current_step - previous_step

                previous_step = current_step

                now = datetime.now(self.timezone)

                system_data = self.simulate_step(
                    now=now,
                    dt_seconds=dt_seconds
                )

                self.publish_telemetry(system_data)

                self.print_system_status(system_data)

                time.sleep(self.interval)

        except KeyboardInterrupt:

            print("\nSimulator stopped.")

        finally:

            self.influx_writer.close()

            print("\n=== SIMULATION SUMMARY ===")

            print(f"Total steps: {self.step_count}")

            print(
                f"Unbalanced steps: "
                f"{self.unbalanced_count}"
            )

            print(
                f"Household consumption: "
                f"{self.load.energy_consumed_kwh:.6f} kWh"
            )

            print(
                f"Grid imported energy: "
                f"{self.grid.energy_imported_kwh:.6f} kWh"
            )

            print(
                f"Grid exported energy: "
                f"{self.grid.energy_exported_kwh:.6f} kWh"
            )

            print("InfluxDB connection closed.")


if __name__ == "__main__":

    simulator = RealtimeSystemSimulator()

    simulator.run()