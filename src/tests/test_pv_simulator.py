import pytest

from pv_simulator.config import PVConfig
from pv_simulator.simulator import PVSimulator


@pytest.fixture
def simulator():
    config = PVConfig()
    return PVSimulator(config)


def test_installed_capacity():
    config = PVConfig()

    assert config.installed_capacity_kw == 4.0


def test_zero_irradiance(simulator):
    dc_power = simulator.calculate_dc_power(
        irradiance=0,
        panel_temperature=25
    )

    assert dc_power == 0


def test_stc_conditions(simulator):
    dc_power = simulator.calculate_dc_power(
        irradiance=1000,
        panel_temperature=25
    )

    assert dc_power == pytest.approx(4.0)


def test_temperature_losses(simulator):
    dc_power = simulator.calculate_dc_power(
        irradiance=1000,
        panel_temperature=45
    )

    assert dc_power < 4.0


def test_inverter_efficiency(simulator):
    ac_power = simulator.calculate_ac_power(
        dc_power=3.0
    )

    assert ac_power == pytest.approx(2.91)


def test_inverter_power_limit(simulator):
    ac_power = simulator.calculate_ac_power(
        dc_power=5.0
    )

    assert ac_power <= 4.0


def test_panel_temperature(simulator):
    temperature = simulator.calculate_panel_temperature(
        irradiance=800,
        ambient_temperature=20
    )

    assert temperature == pytest.approx(45.0)