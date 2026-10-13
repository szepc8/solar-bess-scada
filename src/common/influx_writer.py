import os

from dotenv import load_dotenv

from influxdb_client import (
    InfluxDBClient,
    Point,
    WritePrecision
)

from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxWriter:

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

    def write_pv_measurement(self, telemetry: dict):

        point = (
            Point("pv_inverter")
            .tag("device", "fronius_primo_4_0_1")
            .tag("location", "brasov")
            .field(
                "irradiance_wm2",
                float(telemetry["irradiance_wm2"])
            )
            .field(
                "ambient_temperature_c",
                float(telemetry["ambient_temperature_c"])
            )
            .field(
                "panel_temperature_c",
                float(telemetry["panel_temperature_c"])
            )
            .field(
                "dc_power_kw",
                float(telemetry["dc_power_kw"])
            )
            .field(
                "ac_power_kw",
                float(telemetry["ac_power_kw"])
            )
            .time(
                telemetry["timestamp"],
                WritePrecision.NS
            )
        )

        self.write_api.write(
            bucket=self.bucket,
            org=self.org,
            record=point
        )

    def close(self):
        self.client.close()