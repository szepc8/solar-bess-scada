from datetime import datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

import realtime_simulator

from realtime_simulator import RealtimeSystemSimulator

from bess_simulators.bess_simulator import BESSimulator

from load_simulators.load_simulator import (
    LoadConfig,
    LoadSimulator
)


@pytest.fixture
def timestamp():
    return datetime(
        2026, 11, 27, 12, 0, 0,
        tzinfo=ZoneInfo("Europe/Bucharest")
    )


@pytest.fixture
def simulator(monkeypatch):
    # Prevent any real InfluxDB connection.
    monkeypatch.setattr(
        realtime_simulator,
        "InfluxWriter",
        Mock()
    )

    return RealtimeSystemSimulator()


def configure_scenario(
    simulator,
    monkeypatch,
    pv_power_kw,
    load_power_kw,
    initial_soc=50.0
):
    # Replace the battery with a known initial SOC.
    simulator.bess = BESSimulator(
        initial_soc=initial_soc
    )

    # Keep the real load simulator but use
    # a deterministic, constant load.
    simulator.load = LoadSimulator(
        LoadConfig(
            min_power_kw=load_power_kw,
            max_power_kw=load_power_kw,
            variation=0.0
        )
    )

    # Replace PV generation with controlled telemetry.
    def fixed_pv_measurement(now):
        return {
            "timestamp": now.isoformat(),
            "irradiance_wm2": 0.0,
            "ambient_temperature_c": 20.0,
            "panel_temperature_c": 25.0,
            "dc_power_kw": pv_power_kw / 0.97,
            "ac_power_kw": pv_power_kw
        }

    monkeypatch.setattr(
        simulator,
        "get_current_measurement",
        fixed_pv_measurement
    )


# ---------------------------------------------------------
# Complete system operating scenarios
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "pv, load, soc, requested, actual, grid_power, "
    "ems_mode, bess_mode, grid_mode",
    [
        pytest.param(
            0.0, 0.3, 50.0,
            0.3, 0.3, 0.0,
            "DISCHARGING", "DISCHARGING", "IDLE",
            id="nighttime_battery_supply"
        ),
        pytest.param(
            0.5, 1.5, 50.0,
            1.0, 1.0, 0.0,
            "DISCHARGING", "DISCHARGING", "IDLE",
            id="morning_pv_deficit"
        ),
        pytest.param(
            3.5, 1.0, 50.0,
            -2.5, -2.5, 0.0,
            "CHARGING", "CHARGING", "IDLE",
            id="solar_surplus"
        ),
        pytest.param(
            3.5, 1.0, 95.0,
            -2.5, 0.0, -2.5,
            "CHARGING", "IDLE", "EXPORTING",
            id="battery_full"
        ),
        pytest.param(
            0.0, 2.0, 10.0,
            2.0, 0.0, 2.0,
            "DISCHARGING", "IDLE", "IMPORTING",
            id="battery_empty"
        ),
        pytest.param(
            0.0, 6.0, 50.0,
            6.0, 5.0, 1.0,
            "DISCHARGING", "DISCHARGING", "IMPORTING",
            id="battery_discharge_limit"
        ),
        pytest.param(
            2.0, 2.0, 50.0,
            0.0, 0.0, 0.0,
            "IDLE", "IDLE", "IDLE",
            id="direct_pv_consumption"
        ),
        pytest.param(
            0.2, 2.0, 50.0,
            1.8, 1.8, 0.0,
            "DISCHARGING", "DISCHARGING", "IDLE",
            id="evening_consumption"
        ),
        pytest.param(
            7.0, 1.0, 50.0,
            -6.0, -5.0, -1.0,
            "CHARGING", "CHARGING", "EXPORTING",
            id="battery_charge_limit"
        ),
        pytest.param(
            2.0, 2.005, 50.0,
            0.0, 0.0, 0.005,
            "IDLE", "IDLE", "IMPORTING",
            id="ems_deadband"
        ),
    ]
)
def test_system_operating_scenarios(
    simulator,
    monkeypatch,
    timestamp,
    pv,
    load,
    soc,
    requested,
    actual,
    grid_power,
    ems_mode,
    bess_mode,
    grid_mode
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=pv,
        load_power_kw=load,
        initial_soc=soc
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    assert result["pv"]["ac_power_kw"] == pytest.approx(pv)

    assert result["load"]["power_kw"] == pytest.approx(load)

    assert result["ems"]["requested_bess_power_kw"] == (
        pytest.approx(requested)
    )

    assert result["bess"]["power_kw"] == pytest.approx(actual)

    assert result["grid"]["power_kw"] == pytest.approx(
        grid_power,
        abs=0.001
    )

    assert result["ems"]["mode"] == ems_mode
    assert result["bess"]["mode"] == bess_mode
    assert result["grid"]["mode"] == grid_mode

    assert result["balance"]["is_balanced"] is True
    assert result["balance"]["status"] == "BALANCED"

    assert abs(
        result["balance"]["balance_error_kw"]
    ) <= 0.001


# ---------------------------------------------------------
# Battery SOC behavior
# ---------------------------------------------------------

def test_soc_increases_during_charging(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=3600.0
    )

    assert result["bess"]["soc"] == pytest.approx(69.0)
    assert result["bess"]["power_kw"] == pytest.approx(-2.0)
    assert result["balance"]["is_balanced"] is True


def test_soc_decreases_during_discharging(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=0.0,
        load_power_kw=2.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=3600.0
    )

    assert result["bess"]["soc"] == pytest.approx(
        28.95,
        abs=0.01
    )

    assert result["balance"]["is_balanced"] is True


def test_minimum_soc_protection(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=0.0,
        load_power_kw=3.0,
        initial_soc=10.01
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    assert result["bess"]["soc"] == pytest.approx(10.0)

    assert 0.0 < result["bess"]["power_kw"] < 3.0

    assert result["grid"]["power_kw"] > 0.0

    assert result["balance"]["is_balanced"] is True


def test_maximum_soc_protection(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=4.0,
        load_power_kw=0.5,
        initial_soc=94.99
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    assert result["bess"]["soc"] == pytest.approx(95.0)

    assert -3.5 < result["bess"]["power_kw"] < 0.0

    assert result["grid"]["power_kw"] < 0.0

    assert result["balance"]["is_balanced"] is True


def test_battery_recovery_after_minimum_soc(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0,
        initial_soc=10.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=300.0
    )

    assert result["bess"]["soc"] > 10.0
    assert result["bess"]["mode"] == "CHARGING"
    assert result["grid"]["mode"] == "IDLE"
    assert result["balance"]["is_balanced"] is True


# ---------------------------------------------------------
# Smart meter integration
# ---------------------------------------------------------

def test_smart_meter_grid_power_consistency(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=0.0,
        load_power_kw=2.3,
        initial_soc=10.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    assert result["smart_meter"]["power_kw"] == pytest.approx(
        result["grid"]["power_kw"]
    )

    assert result["smart_meter"]["current_a"] == pytest.approx(
        10.0
    )

    assert result["smart_meter"]["voltage_v"] == 230.0
    assert result["smart_meter"]["frequency_hz"] == 50.0
    assert result["smart_meter"]["mode"] == "IMPORTING"


def test_smart_meter_energy_consistency(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=4.0,
        load_power_kw=1.0,
        initial_soc=95.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=3600.0
    )

    assert result["grid"]["energy_exported_kwh"] == (
        pytest.approx(3.0)
    )

    assert result["smart_meter"]["energy_exported_kwh"] == (
        pytest.approx(3.0)
    )

    assert result["smart_meter"]["energy_imported_kwh"] == 0.0


# ---------------------------------------------------------
# Energy accounting
# ---------------------------------------------------------

def test_household_energy_accounting(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=0.0,
        load_power_kw=2.0,
        initial_soc=10.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=3600.0
    )

    assert result["load"]["energy_consumed_kwh"] == (
        pytest.approx(2.0)
    )

    assert result["grid"]["energy_imported_kwh"] == (
        pytest.approx(2.0)
    )

    assert result["bess"]["energy_discharged_kwh"] == 0.0


def test_pv_energy_distribution(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=4.0,
        load_power_kw=1.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=3600.0
    )

    assert result["load"]["energy_consumed_kwh"] == (
        pytest.approx(1.0)
    )

    assert result["bess"]["energy_charged_kwh"] == (
        pytest.approx(3.0)
    )

    assert result["grid"]["energy_exported_kwh"] == 0.0
    assert result["grid"]["energy_imported_kwh"] == 0.0

    assert result["balance"]["is_balanced"] is True


def test_multiple_step_energy_accumulation(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=0.0,
        load_power_kw=2.0,
        initial_soc=10.0
    )

    for step in range(12):
        result = simulator.simulate_step(
            now=timestamp + timedelta(seconds=300 * step),
            dt_seconds=300.0
        )

    assert result["load"]["energy_consumed_kwh"] == (
        pytest.approx(2.0)
    )

    assert result["grid"]["energy_imported_kwh"] == (
        pytest.approx(2.0)
    )

    assert simulator.step_count == 12
    assert simulator.unbalanced_count == 0


# ---------------------------------------------------------
# Telemetry and timestamp synchronization
# ---------------------------------------------------------

def test_complete_system_telemetry(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    expected_fields = {
        "timestamp",
        "dt_seconds",
        "pv",
        "load",
        "ems",
        "bess",
        "grid",
        "smart_meter",
        "balance"
    }

    assert set(result.keys()) == expected_fields


def test_timestamp_synchronization(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    expected_timestamp = timestamp.isoformat()

    assert result["timestamp"] == expected_timestamp

    for component in (
        "pv",
        "load",
        "ems",
        "bess",
        "grid",
        "smart_meter",
        "balance"
    ):
        assert result[component]["timestamp"] == (
            expected_timestamp
        )


def test_timestep_preserved(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=2.0,
        load_power_kw=1.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.123
    )

    assert result["dt_seconds"] == pytest.approx(5.123)


# ---------------------------------------------------------
# Simulation counters
# ---------------------------------------------------------

def test_initial_simulation_counters(simulator):
    assert simulator.step_count == 0
    assert simulator.unbalanced_count == 0


def test_balanced_step_counter(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    assert simulator.step_count == 1
    assert simulator.unbalanced_count == 0


def test_unbalanced_step_counter(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    # Simulate an incorrect smart meter measurement.
    original_measure = simulator.smart_meter.measure

    def faulty_measure(grid_telemetry, timestamp):
        telemetry = original_measure(
            grid_telemetry=grid_telemetry,
            timestamp=timestamp
        )

        telemetry["power_kw"] += 0.5

        return telemetry

    monkeypatch.setattr(
        simulator.smart_meter,
        "measure",
        faulty_measure
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    assert result["balance"]["is_balanced"] is False
    assert result["balance"]["status"] == "UNBALANCED"

    assert result["balance"]["balance_error_kw"] == (
        pytest.approx(0.5)
    )

    assert simulator.step_count == 1
    assert simulator.unbalanced_count == 1


# ---------------------------------------------------------
# InfluxDB publishing integration
# ---------------------------------------------------------

def test_telemetry_publishing(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    result = simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    simulator.publish_telemetry(result)

    simulator.influx_writer.write_system_measurement \
        .assert_called_once_with(result)


def test_simulation_does_not_publish_automatically(
    simulator,
    monkeypatch,
    timestamp
):
    configure_scenario(
        simulator,
        monkeypatch,
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    simulator.simulate_step(
        now=timestamp,
        dt_seconds=5.0
    )

    simulator.influx_writer.write_system_measurement \
        .assert_not_called()