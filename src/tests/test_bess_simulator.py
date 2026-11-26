import pytest

from src.bess_simulators.bess_simulator import (
    BESSimulator,
    BESSConfig,
    BESSMode,
)


def test_initial_state():
    bess = BESSimulator()

    assert bess.soc == 50.0
    assert bess.soh == 100.0
    assert bess.power_kw == 0.0
    assert bess.mode == BESSMode.IDLE


def test_discharge():
    bess = BESSimulator()

    result = bess.step(2.0, 3600)

    assert result["soc"] == pytest.approx(28.95, abs=0.01)
    assert result["power_kw"] == 2.0
    assert result["mode"] == "DISCHARGING"
    assert result["energy_discharged_kwh"] == 2.0


def test_charge():
    bess = BESSimulator()

    result = bess.step(-2.0, 3600)

    assert result["soc"] == 69.0
    assert result["power_kw"] == -2.0
    assert result["mode"] == "CHARGING"
    assert result["energy_charged_kwh"] == 2.0


def test_idle():
    bess = BESSimulator()

    result = bess.step(0.0, 3600)

    assert result["soc"] == 50.0
    assert result["power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_max_discharge_power():
    bess = BESSimulator()

    result = bess.step(10.0, 60)

    assert result["power_kw"] == 5.0


def test_max_charge_power():
    bess = BESSimulator()

    result = bess.step(-10.0, 60)

    assert result["power_kw"] == -5.0


def test_min_soc_protection():
    bess = BESSimulator(initial_soc=11.0)

    result = bess.step(5.0, 3600)

    assert result["soc"] == 10.0
    assert result["power_kw"] == pytest.approx(0.095)
    assert result["mode"] == "DISCHARGING"


def test_max_soc_protection():
    bess = BESSimulator(initial_soc=94.0)

    result = bess.step(-5.0, 3600)

    assert result["soc"] == 95.0
    assert result["power_kw"] == pytest.approx(-0.105, abs=0.001)
    assert result["mode"] == "CHARGING"


def test_invalid_initial_soc():
    with pytest.raises(ValueError):
        BESSimulator(initial_soc=5.0)


def test_invalid_timestep():
    bess = BESSimulator()

    with pytest.raises(ValueError):
        bess.step(2.0, 0)


def test_energy_accumulation():
    bess = BESSimulator()

    bess.step(1.0, 3600)
    result = bess.step(1.0, 3600)

    assert result["energy_discharged_kwh"] == 2.0
    assert result["soc"] == pytest.approx(28.95, abs=0.01)