import pytest

from grid_simulators.grid_simulator import GridSimulator


@pytest.fixture
def grid():
    return GridSimulator()


def test_initial_state(grid):
    assert grid.power_kw == 0.0
    assert grid.energy_imported_kwh == 0.0
    assert grid.energy_exported_kwh == 0.0
    assert grid.mode == "IDLE"


def test_grid_power_calculation(grid):
    power = grid.calculate_grid_power(
        pv_power_kw=1.0,
        load_power_kw=2.5,
        bess_power_kw=0.5
    )

    assert power == pytest.approx(1.0)


def test_grid_import(grid):
    result = grid.step(
        pv_power_kw=0.5,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == pytest.approx(1.5)
    assert result["import_power_kw"] == pytest.approx(1.5)
    assert result["export_power_kw"] == 0.0
    assert result["mode"] == "IMPORTING"


def test_grid_export(grid):
    result = grid.step(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=0.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == pytest.approx(-3.0)
    assert result["import_power_kw"] == 0.0
    assert result["export_power_kw"] == pytest.approx(3.0)
    assert result["mode"] == "EXPORTING"


def test_grid_idle(grid):
    result = grid.step(
        pv_power_kw=2.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == 0.0
    assert result["import_power_kw"] == 0.0
    assert result["export_power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_battery_supplies_household(grid):
    result = grid.step(
        pv_power_kw=0.0,
        load_power_kw=2.0,
        bess_power_kw=2.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_pv_surplus_charges_battery(grid):
    result = grid.step(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=-3.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == 0.0
    assert result["mode"] == "IDLE"


def test_battery_empty_grid_takeover(grid):
    result = grid.step(
        pv_power_kw=0.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == pytest.approx(2.0)
    assert result["mode"] == "IMPORTING"


def test_battery_full_grid_export(grid):
    result = grid.step(
        pv_power_kw=3.5,
        load_power_kw=1.0,
        bess_power_kw=0.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == pytest.approx(-2.5)
    assert result["mode"] == "EXPORTING"


def test_battery_discharge_limit(grid):
    result = grid.step(
        pv_power_kw=0.0,
        load_power_kw=6.0,
        bess_power_kw=5.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == pytest.approx(1.0)
    assert result["mode"] == "IMPORTING"


def test_battery_charge_limit(grid):
    result = grid.step(
        pv_power_kw=7.0,
        load_power_kw=1.0,
        bess_power_kw=-5.0,
        dt_seconds=5.0
    )

    assert result["power_kw"] == pytest.approx(-1.0)
    assert result["mode"] == "EXPORTING"


def test_imported_energy(grid):
    result = grid.step(
        pv_power_kw=0.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=3600.0
    )

    assert result["energy_imported_kwh"] == pytest.approx(2.0)
    assert result["energy_exported_kwh"] == 0.0


def test_exported_energy(grid):
    result = grid.step(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=0.0,
        dt_seconds=3600.0
    )

    assert result["energy_imported_kwh"] == 0.0
    assert result["energy_exported_kwh"] == pytest.approx(3.0)


def test_energy_accumulation(grid):
    for _ in range(12):
        result = grid.step(
            pv_power_kw=0.0,
            load_power_kw=2.0,
            bess_power_kw=0.0,
            dt_seconds=300.0
        )

    assert result["energy_imported_kwh"] == pytest.approx(2.0)
    assert result["energy_exported_kwh"] == 0.0


def test_bidirectional_energy_accumulation(grid):
    # Import 2 kW for 30 minutes.
    grid.step(
        pv_power_kw=0.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=1800.0
    )

    # Export 3 kW for 30 minutes.
    result = grid.step(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=0.0,
        dt_seconds=1800.0
    )

    assert result["energy_imported_kwh"] == pytest.approx(1.0)
    assert result["energy_exported_kwh"] == pytest.approx(1.5)
    assert result["mode"] == "EXPORTING"


def test_idle_preserves_energy_counters(grid):
    grid.step(
        pv_power_kw=0.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=3600.0
    )

    result = grid.step(
        pv_power_kw=2.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=3600.0
    )

    assert result["energy_imported_kwh"] == pytest.approx(2.0)
    assert result["energy_exported_kwh"] == 0.0
    assert result["mode"] == "IDLE"


def test_reset(grid):
    grid.step(
        pv_power_kw=0.0,
        load_power_kw=2.0,
        bess_power_kw=0.0,
        dt_seconds=3600.0
    )

    grid.step(
        pv_power_kw=4.0,
        load_power_kw=1.0,
        bess_power_kw=0.0,
        dt_seconds=3600.0
    )

    grid.reset()

    assert grid.power_kw == 0.0
    assert grid.energy_imported_kwh == 0.0
    assert grid.energy_exported_kwh == 0.0
    assert grid.mode == "IDLE"


@pytest.mark.parametrize(
    "pv_power, load_power, bess_power",
    [
        (-1.0, 1.0, 0.0),
        (1.0, -1.0, 0.0),
        (float("nan"), 1.0, 0.0),
        (1.0, float("nan"), 0.0),
        (1.0, 1.0, float("nan")),
        (float("inf"), 1.0, 0.0),
        (1.0, float("inf"), 0.0),
        (1.0, 1.0, float("inf")),
    ]
)
def test_invalid_power_inputs(
    grid,
    pv_power,
    load_power,
    bess_power
):
    with pytest.raises(ValueError):
        grid.step(
            pv_power_kw=pv_power,
            load_power_kw=load_power,
            bess_power_kw=bess_power,
            dt_seconds=5.0
        )


@pytest.mark.parametrize(
    "dt_seconds",
    [
        0.0,
        -5.0,
        float("nan"),
        float("inf"),
    ]
)
def test_invalid_timestep(grid, dt_seconds):
    with pytest.raises(ValueError):
        grid.step(
            pv_power_kw=1.0,
            load_power_kw=2.0,
            bess_power_kw=0.0,
            dt_seconds=dt_seconds
        )