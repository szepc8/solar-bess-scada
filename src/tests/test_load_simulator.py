from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from load_simulators.load_simulator import (
    LoadConfig,
    LoadSimulator
)


TIMEZONE = ZoneInfo("Europe/Bucharest")


def make_timestamp(hour: int, minute: int = 0) -> datetime:
    return datetime(
        2026, 11, 26,
        hour, minute,
        tzinfo=TIMEZONE
    )


def test_initial_state():

    simulator = LoadSimulator()

    assert simulator.power_kw == 0.0
    assert simulator.energy_consumed_kwh == 0.0


def test_nighttime_load():

    simulator = LoadSimulator()

    power = simulator.get_base_power(
        make_timestamp(2)
    )

    assert power == pytest.approx(0.30)


def test_morning_peak():

    simulator = LoadSimulator()

    power = simulator.get_base_power(
        make_timestamp(7)
    )

    assert power == pytest.approx(1.50)


def test_evening_peak():

    simulator = LoadSimulator()

    power = simulator.get_base_power(
        make_timestamp(19)
    )

    assert power == pytest.approx(2.00)


def test_no_random_variation():

    config = LoadConfig(variation=0.0)

    simulator = LoadSimulator(config)

    power = simulator.calculate_power(
        make_timestamp(19)
    )

    assert power == pytest.approx(2.0)


def test_random_variation_limits():

    config = LoadConfig(variation=0.15)

    simulator = LoadSimulator(config)

    timestamp = make_timestamp(19)

    for _ in range(1000):

        power = simulator.calculate_power(timestamp)

        assert 1.70 <= power <= 2.30


def test_minimum_power_limit():

    config = LoadConfig(
        min_power_kw=0.50,
        variation=0.0
    )

    simulator = LoadSimulator(config)

    power = simulator.calculate_power(
        make_timestamp(2)
    )

    assert power == pytest.approx(0.50)


def test_maximum_power_limit():

    config = LoadConfig(
        max_power_kw=1.0,
        variation=0.0
    )

    simulator = LoadSimulator(config)

    power = simulator.calculate_power(
        make_timestamp(19)
    )

    assert power == pytest.approx(1.0)


def test_energy_accumulation():

    config = LoadConfig(variation=0.0)

    simulator = LoadSimulator(config)

    timestamp = make_timestamp(19)

    for i in range(12):

        simulator.step(
            timestamp=timestamp + timedelta(seconds=5 * i),
            dt_seconds=5.0
        )

    expected_energy = 2.0 * 60 / 3600

    assert simulator.energy_consumed_kwh == pytest.approx(
        expected_energy
    )


def test_invalid_timestep():

    simulator = LoadSimulator()

    for dt in (0, -5, float("nan"), float("inf")):

        with pytest.raises(ValueError):

            simulator.step(
                timestamp=make_timestamp(12),
                dt_seconds=dt
            )


def test_invalid_configuration():

    invalid_configs = [
        LoadConfig(min_power_kw=-1.0),
        LoadConfig(max_power_kw=0.0),
        LoadConfig(min_power_kw=3.0, max_power_kw=2.0),
        LoadConfig(variation=-0.1),
        LoadConfig(variation=1.5),
        LoadConfig(variation=float("nan")),
        LoadConfig(max_power_kw=float("inf")),
    ]

    for config in invalid_configs:

        with pytest.raises(ValueError):
            LoadSimulator(config)


def test_reproducible_random_sequence():

    simulator_1 = LoadSimulator(
        LoadConfig(random_seed=42)
    )

    simulator_2 = LoadSimulator(
        LoadConfig(random_seed=42)
    )

    timestamp = make_timestamp(19)

    for _ in range(100):

        power_1 = simulator_1.calculate_power(timestamp)
        power_2 = simulator_2.calculate_power(timestamp)

        assert power_1 == power_2


def test_reset():

    simulator = LoadSimulator()

    timestamp = make_timestamp(19)

    first_measurement = simulator.step(
        timestamp=timestamp,
        dt_seconds=5.0
    )

    simulator.reset()

    assert simulator.power_kw == 0.0
    assert simulator.energy_consumed_kwh == 0.0

    second_measurement = simulator.step(
        timestamp=timestamp,
        dt_seconds=5.0
    )

    assert first_measurement == second_measurement


def test_profile_boundaries():

    simulator = LoadSimulator()

    expected_profile = [
        (0, 0.30),
        (6, 1.50),
        (9, 0.60),
        (12, 1.20),
        (14, 0.70),
        (17, 2.00),
        (21, 0.90),
        (23, 0.40),
    ]

    for hour, expected_power in expected_profile:

        power = simulator.get_base_power(
            make_timestamp(hour)
        )

        assert power == pytest.approx(expected_power)


def test_daily_energy_consumption():

    config = LoadConfig(variation=0.0)

    simulator = LoadSimulator(config)

    start_time = make_timestamp(0)

    dt_seconds = 300.0

    for i in range(288):

        timestamp = start_time + timedelta(
            seconds=i * dt_seconds
        )

        simulator.step(
            timestamp=timestamp,
            dt_seconds=dt_seconds
        )

    assert simulator.energy_consumed_kwh == pytest.approx(
        22.8
    )