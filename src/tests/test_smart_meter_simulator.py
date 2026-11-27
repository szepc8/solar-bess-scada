from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from grid_simulators.smart_meter_simulator import (
    SmartMeterConfig,
    SmartMeterSimulator
)


@pytest.fixture
def meter():
    return SmartMeterSimulator()


@pytest.fixture
def timestamp():
    return datetime(
        2026, 11, 26, 12, 0, 0,
        tzinfo=ZoneInfo("Europe/Bucharest")
    )


def create_grid_telemetry(
    power_kw=0.0,
    imported_kwh=0.0,
    exported_kwh=0.0
):
    if power_kw > 0:
        mode = "IMPORTING"
    elif power_kw < 0:
        mode = "EXPORTING"
    else:
        mode = "IDLE"

    return {
        "power_kw": power_kw,
        "import_power_kw": max(power_kw, 0.0),
        "export_power_kw": max(-power_kw, 0.0),
        "energy_imported_kwh": imported_kwh,
        "energy_exported_kwh": exported_kwh,
        "mode": mode
    }


def test_default_configuration():
    config = SmartMeterConfig()

    assert config.voltage_v == 230.0
    assert config.frequency_hz == 50.0
    assert config.power_factor == 1.0


def test_idle_measurement(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    assert result["power_kw"] == 0.0
    assert result["current_a"] == 0.0
    assert result["apparent_power_kva"] == 0.0
    assert result["mode"] == "IDLE"


def test_import_power(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(power_kw=2.0),
        timestamp
    )

    assert result["power_kw"] == pytest.approx(2.0)
    assert result["mode"] == "IMPORTING"


def test_export_power(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(power_kw=-3.0),
        timestamp
    )

    assert result["power_kw"] == pytest.approx(-3.0)
    assert result["mode"] == "EXPORTING"


def test_nominal_voltage(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    assert result["voltage_v"] == 230.0


def test_nominal_frequency(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    assert result["frequency_hz"] == 50.0


def test_default_power_factor(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    assert result["power_factor"] == 1.0


def test_import_current(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(power_kw=2.3),
        timestamp
    )

    assert result["current_a"] == pytest.approx(10.0)


def test_export_current(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(power_kw=-2.3),
        timestamp
    )

    assert result["current_a"] == pytest.approx(10.0)


def test_current_direction_independent(meter, timestamp):
    imported = meter.measure(
        create_grid_telemetry(power_kw=2.3),
        timestamp
    )

    exported = meter.measure(
        create_grid_telemetry(power_kw=-2.3),
        timestamp
    )

    assert imported["current_a"] == pytest.approx(
        exported["current_a"]
    )


def test_apparent_power_import(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(power_kw=2.5),
        timestamp
    )

    assert result["apparent_power_kva"] == pytest.approx(2.5)


def test_apparent_power_export(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(power_kw=-2.5),
        timestamp
    )

    assert result["apparent_power_kva"] == pytest.approx(2.5)


def test_custom_voltage(timestamp):
    meter = SmartMeterSimulator(
        SmartMeterConfig(voltage_v=240.0)
    )

    result = meter.measure(
        create_grid_telemetry(power_kw=2.4),
        timestamp
    )

    assert result["voltage_v"] == 240.0
    assert result["current_a"] == pytest.approx(10.0)


def test_custom_frequency(timestamp):
    meter = SmartMeterSimulator(
        SmartMeterConfig(frequency_hz=49.9)
    )

    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    assert result["frequency_hz"] == pytest.approx(49.9)


def test_non_unity_power_factor(timestamp):
    meter = SmartMeterSimulator(
        SmartMeterConfig(power_factor=0.8)
    )

    result = meter.measure(
        create_grid_telemetry(power_kw=1.84),
        timestamp
    )

    assert result["power_factor"] == pytest.approx(0.8)
    assert result["current_a"] == pytest.approx(10.0)
    assert result["apparent_power_kva"] == pytest.approx(2.3)


def test_imported_energy(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(
            power_kw=1.0,
            imported_kwh=12.5
        ),
        timestamp
    )

    assert result["energy_imported_kwh"] == pytest.approx(12.5)


def test_exported_energy(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(
            power_kw=-1.0,
            exported_kwh=5.5
        ),
        timestamp
    )

    assert result["energy_exported_kwh"] == pytest.approx(5.5)


def test_energy_counters_not_duplicated(meter, timestamp):
    telemetry = create_grid_telemetry(
        power_kw=2.0,
        imported_kwh=10.0,
        exported_kwh=4.0
    )

    for _ in range(10):
        result = meter.measure(
            telemetry,
            timestamp
        )

    assert result["energy_imported_kwh"] == pytest.approx(10.0)
    assert result["energy_exported_kwh"] == pytest.approx(4.0)


def test_timestamp_preserved(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    assert result["timestamp"] == timestamp.isoformat()


def test_telemetry_fields(meter, timestamp):
    result = meter.measure(
        create_grid_telemetry(),
        timestamp
    )

    expected_fields = {
        "timestamp",
        "power_kw",
        "voltage_v",
        "current_a",
        "frequency_hz",
        "power_factor",
        "apparent_power_kva",
        "energy_imported_kwh",
        "energy_exported_kwh",
        "mode"
    }

    assert set(result.keys()) == expected_fields


@pytest.mark.parametrize(
    "voltage",
    [
        0.0,
        -230.0,
        float("nan"),
        float("inf")
    ]
)
def test_invalid_voltage(voltage):
    with pytest.raises(ValueError):
        SmartMeterSimulator(
            SmartMeterConfig(voltage_v=voltage)
        )


@pytest.mark.parametrize(
    "frequency",
    [
        0.0,
        -50.0,
        float("nan"),
        float("inf")
    ]
)
def test_invalid_frequency(frequency):
    with pytest.raises(ValueError):
        SmartMeterSimulator(
            SmartMeterConfig(frequency_hz=frequency)
        )


@pytest.mark.parametrize(
    "power_factor",
    [
        0.0,
        -0.5,
        1.1,
        float("nan"),
        float("inf")
    ]
)
def test_invalid_power_factor(power_factor):
    with pytest.raises(ValueError):
        SmartMeterSimulator(
            SmartMeterConfig(power_factor=power_factor)
        )


@pytest.mark.parametrize(
    "power",
    [
        float("nan"),
        float("inf"),
        float("-inf")
    ]
)
def test_invalid_power(meter, timestamp, power):
    with pytest.raises(ValueError):
        meter.measure(
            create_grid_telemetry(power_kw=power),
            timestamp
        )


@pytest.mark.parametrize(
    "imported, exported",
    [
        (-1.0, 0.0),
        (0.0, -1.0),
        (float("nan"), 0.0),
        (0.0, float("nan")),
        (float("inf"), 0.0),
        (0.0, float("inf"))
    ]
)
def test_invalid_energy_counters(
    meter,
    timestamp,
    imported,
    exported
):
    with pytest.raises(ValueError):
        meter.measure(
            create_grid_telemetry(
                imported_kwh=imported,
                exported_kwh=exported
            ),
            timestamp
        )