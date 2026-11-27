import pytest

from ems.ems_controller import EMSConfig, EMSController


@pytest.fixture
def ems():
    return EMSController()


def test_default_configuration():
    config = EMSConfig()

    assert config.deadband_kw == pytest.approx(0.01)


def test_nighttime_discharge(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=0.0,
        load_power_kw=0.3
    )

    assert result["requested_bess_power_kw"] == pytest.approx(0.3)
    assert result["mode"] == "DISCHARGING"


def test_solar_surplus_charging(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=3.5,
        load_power_kw=1.0
    )

    assert result["requested_bess_power_kw"] == pytest.approx(-2.5)
    assert result["mode"] == "CHARGING"


def test_pv_deficit_discharge(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=0.5,
        load_power_kw=1.5
    )

    assert result["requested_bess_power_kw"] == pytest.approx(1.0)
    assert result["mode"] == "DISCHARGING"


def test_balanced_power(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=2.0,
        load_power_kw=2.0
    )

    assert result["requested_bess_power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_zero_production_and_consumption(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=0.0,
        load_power_kw=0.0
    )

    assert result["requested_bess_power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_positive_deadband(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=2.0,
        load_power_kw=2.005
    )

    assert result["requested_bess_power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_negative_deadband(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=2.005,
        load_power_kw=2.0
    )

    assert result["requested_bess_power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_outside_deadband(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=2.0,
        load_power_kw=2.02
    )

    assert result["requested_bess_power_kw"] == pytest.approx(0.02)
    assert result["mode"] == "DISCHARGING"


def test_custom_deadband():
    ems = EMSController(
        config=EMSConfig(deadband_kw=0.1)
    )

    result = ems.calculate_setpoint(
        pv_power_kw=2.0,
        load_power_kw=2.05
    )

    assert result["requested_bess_power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_high_load_request_not_limited(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=0.0,
        load_power_kw=6.0
    )

    assert result["requested_bess_power_kw"] == pytest.approx(6.0)
    assert result["mode"] == "DISCHARGING"


def test_high_surplus_request_not_limited(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=7.0,
        load_power_kw=1.0
    )

    assert result["requested_bess_power_kw"] == pytest.approx(-6.0)
    assert result["mode"] == "CHARGING"


def test_telemetry_fields(ems):
    result = ems.calculate_setpoint(
        pv_power_kw=3.0,
        load_power_kw=1.0
    )

    assert result["pv_power_kw"] == pytest.approx(3.0)
    assert result["load_power_kw"] == pytest.approx(1.0)
    assert result["net_power_kw"] == pytest.approx(-2.0)
    assert result["requested_bess_power_kw"] == pytest.approx(-2.0)
    assert result["mode"] == "CHARGING"


@pytest.mark.parametrize(
    "pv_power, load_power",
    [
        (-1.0, 1.0),
        (1.0, -1.0),
        (float("nan"), 1.0),
        (1.0, float("nan")),
        (float("inf"), 1.0),
        (1.0, float("inf")),
    ]
)
def test_invalid_power_inputs(ems, pv_power, load_power):
    with pytest.raises(ValueError):
        ems.calculate_setpoint(
            pv_power_kw=pv_power,
            load_power_kw=load_power
        )


@pytest.mark.parametrize(
    "deadband",
    [
        -0.01,
        float("nan"),
        float("inf"),
    ]
)
def test_invalid_deadband(deadband):
    with pytest.raises(ValueError):
        EMSController(
            config=EMSConfig(deadband_kw=deadband)
        )