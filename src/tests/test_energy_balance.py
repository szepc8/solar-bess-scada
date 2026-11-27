import pytest

from ems.energy_balance import (
    EnergyBalanceConfig,
    EnergyBalanceValidator
)


@pytest.fixture
def validator():
    return EnergyBalanceValidator()


# ---------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------

def test_default_configuration():
    config = EnergyBalanceConfig()

    assert config.tolerance_kw == pytest.approx(0.001)


def test_custom_configuration():
    validator = EnergyBalanceValidator(
        EnergyBalanceConfig(tolerance_kw=0.01)
    )

    assert validator.config.tolerance_kw == pytest.approx(0.01)


def test_zero_tolerance():
    validator = EnergyBalanceValidator(
        EnergyBalanceConfig(tolerance_kw=0.0)
    )

    balanced = validator.validate(
        pv_power_kw=2.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    unbalanced = validator.validate(
        pv_power_kw=2.001,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    assert balanced["is_balanced"] is True
    assert unbalanced["is_balanced"] is False


@pytest.mark.parametrize(
    "tolerance",
    [
        -0.001,
        float("nan"),
        float("inf"),
        float("-inf")
    ]
)
def test_invalid_tolerance(tolerance):
    with pytest.raises(ValueError):
        EnergyBalanceValidator(
            EnergyBalanceConfig(tolerance_kw=tolerance)
        )


# ---------------------------------------------------------
# Balanced operating scenarios
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "pv, load, bess, grid",
    [
        pytest.param(
            0.0, 0.0, 0.0, 0.0,
            id="system_idle"
        ),
        pytest.param(
            2.0, 2.0, 0.0, 0.0,
            id="direct_pv_consumption"
        ),
        pytest.param(
            4.0, 1.0, -3.0, 0.0,
            id="battery_charging"
        ),
        pytest.param(
            0.0, 2.0, 2.0, 0.0,
            id="battery_discharging"
        ),
        pytest.param(
            0.0, 2.0, 0.0, 2.0,
            id="grid_import"
        ),
        pytest.param(
            4.0, 1.0, 0.0, -3.0,
            id="grid_export"
        ),
        pytest.param(
            1.0, 3.0, 2.0, 0.0,
            id="pv_and_battery_supply"
        ),
        pytest.param(
            1.0, 3.0, 0.0, 2.0,
            id="pv_and_grid_supply"
        ),
        pytest.param(
            0.0, 6.0, 5.0, 1.0,
            id="battery_and_grid_supply"
        ),
        pytest.param(
            4.0, 1.0, -2.0, -1.0,
            id="charging_and_exporting"
        ),
    ]
)
def test_balanced_scenarios(
    validator,
    pv,
    load,
    bess,
    grid
):
    result = validator.validate(
        pv_power_kw=pv,
        load_power_kw=load,
        bess_power_kw=bess,
        grid_power_kw=grid
    )

    assert result["is_balanced"] is True
    assert result["status"] == "BALANCED"

    assert result["balance_error_kw"] == pytest.approx(
        0.0,
        abs=1e-12
    )

    assert result["supply_power_kw"] == pytest.approx(
        result["demand_power_kw"]
    )


# ---------------------------------------------------------
# Supply and demand calculations
# ---------------------------------------------------------

def test_supply_power_calculation(validator):
    result = validator.validate(
        pv_power_kw=2.0,
        load_power_kw=6.0,
        bess_power_kw=3.0,
        grid_power_kw=1.0
    )

    assert result["supply_power_kw"] == pytest.approx(6.0)
    assert result["demand_power_kw"] == pytest.approx(6.0)


def test_demand_power_calculation(validator):
    result = validator.validate(
        pv_power_kw=5.0,
        load_power_kw=1.0,
        bess_power_kw=-3.0,
        grid_power_kw=-1.0
    )

    assert result["supply_power_kw"] == pytest.approx(5.0)
    assert result["demand_power_kw"] == pytest.approx(5.0)


# ---------------------------------------------------------
# Unbalanced operating scenarios
# ---------------------------------------------------------

def test_positive_balance_error(validator):
    result = validator.validate(
        pv_power_kw=3.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    assert result["balance_error_kw"] == pytest.approx(1.0)
    assert result["is_balanced"] is False
    assert result["status"] == "UNBALANCED"


def test_negative_balance_error(validator):
    result = validator.validate(
        pv_power_kw=1.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    assert result["balance_error_kw"] == pytest.approx(-1.0)
    assert result["is_balanced"] is False
    assert result["status"] == "UNBALANCED"


# ---------------------------------------------------------
# Tolerance and boundary tests
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "error_kw, expected_balanced",
    [
        pytest.param(
            0.0005, True,
            id="positive_inside_tolerance"
        ),
        pytest.param(
            -0.0005, True,
            id="negative_inside_tolerance"
        ),
        pytest.param(
            0.001, True,
            id="positive_exact_boundary"
        ),
        pytest.param(
            -0.001, True,
            id="negative_exact_boundary"
        ),
        pytest.param(
            0.001001, False,
            id="positive_outside_boundary"
        ),
        pytest.param(
            -0.001001, False,
            id="negative_outside_boundary"
        ),
        pytest.param(
            0.002, False,
            id="positive_outside_tolerance"
        ),
        pytest.param(
            -0.002, False,
            id="negative_outside_tolerance"
        ),
    ]
)
def test_tolerance_boundaries(
    validator,
    error_kw,
    expected_balanced
):
    result = validator.validate(
        pv_power_kw=max(error_kw, 0.0),
        load_power_kw=max(-error_kw, 0.0),
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    assert result["balance_error_kw"] == pytest.approx(
        error_kw,
        abs=1e-12
    )

    assert result["is_balanced"] is expected_balanced

    expected_status = (
        "BALANCED"
        if expected_balanced
        else "UNBALANCED"
    )

    assert result["status"] == expected_status


def test_custom_tolerance():
    validator = EnergyBalanceValidator(
        EnergyBalanceConfig(tolerance_kw=0.01)
    )

    result = validator.validate(
        pv_power_kw=2.005,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    assert result["balance_error_kw"] == pytest.approx(0.005)
    assert result["is_balanced"] is True
    assert result["status"] == "BALANCED"


def test_floating_point_rounding(validator):
    result = validator.validate(
        pv_power_kw=0.1,
        load_power_kw=0.3,
        bess_power_kw=0.2,
        grid_power_kw=0.0
    )

    assert result["balance_error_kw"] == pytest.approx(
        0.0,
        abs=1e-12
    )

    assert result["is_balanced"] is True
    assert result["status"] == "BALANCED"


def test_sub_watt_grid_normalization_residual(validator):
    result = validator.validate(
        pv_power_kw=2.239,
        load_power_kw=1.250194,
        bess_power_kw=-0.989,
        grid_power_kw=0.0
    )

    assert result["balance_error_kw"] == pytest.approx(
        -0.000194,
        abs=1e-12
    )

    assert result["is_balanced"] is True
    assert result["status"] == "BALANCED"


# ---------------------------------------------------------
# Input validation
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "pv, load, bess, grid",
    [
        (-1.0, 1.0, 0.0, 0.0),
        (1.0, -1.0, 0.0, 0.0),

        (float("nan"), 1.0, 0.0, 0.0),
        (1.0, float("nan"), 0.0, 0.0),
        (1.0, 1.0, float("nan"), 0.0),
        (1.0, 1.0, 0.0, float("nan")),

        (float("inf"), 1.0, 0.0, 0.0),
        (1.0, float("inf"), 0.0, 0.0),
        (1.0, 1.0, float("inf"), 0.0),
        (1.0, 1.0, 0.0, float("inf")),

        (float("-inf"), 1.0, 0.0, 0.0),
        (1.0, float("-inf"), 0.0, 0.0),
        (1.0, 1.0, float("-inf"), 0.0),
        (1.0, 1.0, 0.0, float("-inf")),
    ]
)
def test_invalid_power_inputs(
    validator,
    pv,
    load,
    bess,
    grid
):
    with pytest.raises(ValueError):
        validator.validate(
            pv_power_kw=pv,
            load_power_kw=load,
            bess_power_kw=bess,
            grid_power_kw=grid
        )


# ---------------------------------------------------------
# Telemetry tests
# ---------------------------------------------------------

def test_telemetry_fields(validator):
    result = validator.validate(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=-2.0,
        grid_power_kw=-1.0
    )

    expected_fields = {
        "pv_power_kw",
        "load_power_kw",
        "bess_power_kw",
        "grid_power_kw",
        "supply_power_kw",
        "demand_power_kw",
        "balance_error_kw",
        "is_balanced",
        "status"
    }

    assert set(result.keys()) == expected_fields


def test_telemetry_preserves_input_values(validator):
    result = validator.validate(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=-2.0,
        grid_power_kw=-1.0
    )

    assert result["pv_power_kw"] == pytest.approx(4.0)
    assert result["load_power_kw"] == pytest.approx(1.0)
    assert result["bess_power_kw"] == pytest.approx(-2.0)
    assert result["grid_power_kw"] == pytest.approx(-1.0)


def test_validator_is_stateless(validator):
    first = validator.validate(
        pv_power_kw=3.0,
        load_power_kw=1.0,
        bess_power_kw=0.0,
        grid_power_kw=0.0
    )

    second = validator.validate(
        pv_power_kw=3.0,
        load_power_kw=1.0,
        bess_power_kw=-2.0,
        grid_power_kw=0.0
    )

    assert first["is_balanced"] is False
    assert second["is_balanced"] is True

    assert first["status"] == "UNBALANCED"
    assert second["status"] == "BALANCED"