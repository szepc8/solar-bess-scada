import os

from dotenv import load_dotenv

from influxdb_client import (
    InfluxDBClient,
    Point,
    WritePrecision
)

from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxWriter:
    """
    InfluxDB telemetry writer for the Solar BESS SCADA system.

    Supports:
        - Individual PV measurements
        - Individual BESS measurements
        - Complete system batch measurements
    """

    def __init__(self):

        load_dotenv()

        self.url = os.getenv("INFLUXDB_URL")
        self.token = os.getenv("INFLUXDB_TOKEN")
        self.org = os.getenv("INFLUXDB_ORG")
        self.bucket = os.getenv("INFLUXDB_BUCKET")

        required = {
            "INFLUXDB_URL": self.url,
            "INFLUXDB_TOKEN": self.token,
            "INFLUXDB_ORG": self.org,
            "INFLUXDB_BUCKET": self.bucket,
        }

        missing = [
            key for key, value in required.items()
            if not value
        ]

        if missing:
            raise ValueError(
                f"Missing environment variables: {missing}"
            )

        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )

        self.write_api = self.client.write_api(
            write_options=SYNCHRONOUS
        )

    # =====================================================
    # COMMON POINT BUILDER
    # =====================================================

    def _create_point(
        self,
        measurement: str,
        device: str,
        telemetry: dict,
        float_fields: tuple,
        string_fields: tuple = (),
        boolean_fields: tuple = ()
    ) -> Point:

        point = (
            Point(measurement)
            .tag("device", device)
            .tag("location", "brasov")
            .time(
                telemetry["timestamp"],
                WritePrecision.NS
            )
        )

        for field in float_fields:

            point.field(
                field,
                float(telemetry[field])
            )

        for field in string_fields:

            point.field(
                field,
                str(telemetry[field])
            )

        for field in boolean_fields:

            point.field(
                field,
                bool(telemetry[field])
            )

        return point

    # =====================================================
    # PV INVERTER
    # =====================================================

    def _build_pv_point(self, telemetry: dict) -> Point:

        return self._create_point(
            measurement="pv_inverter",
            device="fronius_primo_4_0_1",
            telemetry=telemetry,
            float_fields=(
                "irradiance_wm2",
                "ambient_temperature_c",
                "panel_temperature_c",
                "dc_power_kw",
                "ac_power_kw"
            )
        )

    # =====================================================
    # ALPHAESS BESS
    # =====================================================

    def _build_bess_point(self, telemetry: dict) -> Point:

        return self._create_point(
            measurement="bess",
            device="alphaess_simulator",
            telemetry=telemetry,
            float_fields=(
                "soc",
                "soh",
                "power_kw",
                "voltage_v",
                "current_a",
                "temperature_c",
                "energy_charged_kwh",
                "energy_discharged_kwh"
            ),
            string_fields=(
                "mode",
            )
        )

    # =====================================================
    # HOUSEHOLD LOAD
    # =====================================================

    def _build_load_point(self, telemetry: dict) -> Point:

        return self._create_point(
            measurement="household_load",
            device="household_simulator",
            telemetry=telemetry,
            float_fields=(
                "power_kw",
                "energy_consumed_kwh"
            )
        )

    # =====================================================
    # EMS CONTROLLER
    # =====================================================

    def _build_ems_point(self, telemetry: dict) -> Point:

        return self._create_point(
            measurement="ems",
            device="ems_controller",
            telemetry=telemetry,
            float_fields=(
                "pv_power_kw",
                "load_power_kw",
                "net_power_kw",
                "requested_bess_power_kw"
            ),
            string_fields=(
                "mode",
            )
        )

    # =====================================================
    # GRID SIMULATOR
    # =====================================================

    def _build_grid_point(self, telemetry: dict) -> Point:

        return self._create_point(
            measurement="grid",
            device="grid_simulator",
            telemetry=telemetry,
            float_fields=(
                "power_kw",
                "import_power_kw",
                "export_power_kw",
                "energy_imported_kwh",
                "energy_exported_kwh"
            ),
            string_fields=(
                "mode",
            )
        )

    # =====================================================
    # SMART METER
    # =====================================================

    def _build_smart_meter_point(
        self,
        telemetry: dict
    ) -> Point:

        return self._create_point(
            measurement="smart_meter",
            device="smart_meter_simulator",
            telemetry=telemetry,
            float_fields=(
                "power_kw",
                "voltage_v",
                "current_a",
                "frequency_hz",
                "power_factor",
                "apparent_power_kva",
                "energy_imported_kwh",
                "energy_exported_kwh"
            ),
            string_fields=(
                "mode",
            )
        )

    # =====================================================
    # ENERGY BALANCE
    # =====================================================

    def _build_energy_balance_point(
        self,
        telemetry: dict
    ) -> Point:

        return self._create_point(
            measurement="energy_balance",
            device="energy_balance_validator",
            telemetry=telemetry,
            float_fields=(
                "pv_power_kw",
                "load_power_kw",
                "bess_power_kw",
                "grid_power_kw",
                "supply_power_kw",
                "demand_power_kw",
                "balance_error_kw"
            ),
            string_fields=(
                "status",
            ),
            boolean_fields=(
                "is_balanced",
            )
        )

    # =====================================================
    # INDIVIDUAL WRITES - BACKWARD COMPATIBILITY
    # =====================================================

    def write_pv_measurement(self, telemetry: dict):

        point = self._build_pv_point(telemetry)

        self.write_api.write(
            bucket=self.bucket,
            org=self.org,
            record=point
        )

    def write_bess_measurement(self, telemetry: dict):

        point = self._build_bess_point(telemetry)

        self.write_api.write(
            bucket=self.bucket,
            org=self.org,
            record=point
        )

    # =====================================================
    # COMPLETE SYSTEM BATCH WRITE
    # =====================================================

    def write_system_measurement(self, system_data: dict):
        """
        Publish all seven system measurements using
        a single synchronous InfluxDB write request.
        """

        timestamp = system_data["timestamp"]

        components = (
            "pv",
            "bess",
            "load",
            "ems",
            "grid",
            "smart_meter",
            "balance"
        )

        # Verify that all components share the same timestamp.
        for component in components:

            if system_data[component]["timestamp"] != timestamp:

                raise ValueError(
                    f"Timestamp mismatch: {component}"
                )

        points = [
            self._build_pv_point(
                system_data["pv"]
            ),
            self._build_bess_point(
                system_data["bess"]
            ),
            self._build_load_point(
                system_data["load"]
            ),
            self._build_ems_point(
                system_data["ems"]
            ),
            self._build_grid_point(
                system_data["grid"]
            ),
            self._build_smart_meter_point(
                system_data["smart_meter"]
            ),
            self._build_energy_balance_point(
                system_data["balance"]
            )
        ]

        self.write_api.write(
            bucket=self.bucket,
            org=self.org,
            record=points
        )

    # =====================================================
    # RESOURCE CLEANUP
    # =====================================================

    def close(self):

        self.client.close()