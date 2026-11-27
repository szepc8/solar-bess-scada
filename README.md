# Solar BESS SCADA

A practical Python + Docker + InfluxDB + Grafana learning project simulating residential PV, battery storage, household demand, EMS dispatch, bidirectional grid power and smart-meter telemetry.

> **Status (2026-11-27):** Sessions 0–2 completed; Session 3 implementation, 203 automated tests and EMS dashboard export confirmed. Final documentation, regression and Git handoff remain. All telemetry is **simulated**; no real installation is read or controlled.

## Real installation reference

```text
10 × 400 Wp PV panels (4 kWp), south-facing, ~35° tilt
                 |
                 v
         Fronius Primo 4.0-1
                 |
                 v
           Main AC board
                 |
         AlphaESS Smart Meter
                 |
           +-----+------+
           |            |
        Loads       AlphaESS S5
                        |
                   +----+----+
                   |         |
              9.12 kWh     EPS backup
               battery
```

This is a **logical overview**, not a verified electrical single-line diagram. Grid connection, meter placement, and EPS circuit wiring must be confirmed before modeling exact power flows or commissioning any hardware.

### PV simulation parameters

| Parameter | Value |
|---|---|
| Location | Brașov, Romania (approx. 45.658° N, 25.601° E; 600 m altitude assumed) |
| Time zone | `Europe/Bucharest` |
| PV array | 10 × 400 Wp = **4 kWp** |
| Orientation | South; surface azimuth **180°** |
| Tilt | **35° assumed** (confirm degrees rather than 35% slope) |
| PV inverter | Fronius Primo 4.0-1 |
| AC inverter rating | 4 kW |
| Simplified inverter efficiency | 97% (constant model assumption) |
| Temperature coefficient | −0.35%/°C |
| Reference cell temperature | 25°C |
| Reference irradiance (STC) | 1,000 W/m²; **not a hard irradiance cap** |
| Simplified NOCT | 45°C (assumed) |
| Telemetry publishing interval | 5 seconds |
| Daily profile calculation resolution | 5 minutes |

The BESS reference is an **AlphaESS S5 with 9.12 kWh storage** and EPS capability. Session 2 uses a **demonstration 10 kWh / 51.2 V** battery model; these are **not verified AlphaESS S5 specifications**. The real-installation reference above remains 9.12 kWh.

## Development environment

- Windows, PyCharm Community Edition, Python 3.13
- WSL2 + Docker Compose
- InfluxDB 2.7 (container `solar-influxdb`, host port `127.0.0.1:8086`)
- Grafana 11.6.0 (container `solar-grafana`, host port `127.0.0.1:3000`)
- Git, with one branch per development session

Session 0 configured and tested InfluxDB and Grafana. Preserve the working Docker Compose configuration.

## Repository structure

Current logical layout through Session 3. The runtime path is confirmed by the supplied Session 3 source; dashboard filenames are the agreed export targets, not independently inspected files.

```text
solar-bess-scada/
├── .env                       # local credentials; NEVER commit
├── .gitignore
├── README.md
├── requirements.txt
├── docker/                    # existing Compose configuration from Session 0
├── grafana/
│   └── dashboards/
│       ├── fronius-pv.json   # Session 1 export (verify filename in checkout)
│       ├── alphaess_bess_dashboard.json
│       └── solar-bess-ems.json
└── src/
    ├── common/
    │   ├── __init__.py
    │   └── influx_writer.py
    ├── pv_simulator/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── simulator.py
    │   ├── solar_model.py
    │   ├── weather_model.py
    │   ├── pv_generation.py
    │   └── plot_generation.py
    ├── bess_simulators/
    │   ├── __init__.py
    │   └── bess_simulator.py
    ├── load_simulators/
    │   ├── __init__.py
    │   └── load_simulator.py
    ├── ems/
    │   ├── __init__.py
    │   ├── ems_controller.py
    │   └── energy_balance.py
    ├── grid_simulators/
    │   ├── __init__.py
    │   ├── grid_simulator.py
    │   └── smart_meter_simulator.py
    ├── realtime_simulator.py
    └── tests/
        ├── test_pv_simulator.py
        ├── test_bess_simulator.py
        ├── manual_test_bess_influx.py
        ├── test_load_simulator.py
        ├── test_ems_controller.py
        ├── test_grid_simulator.py
        ├── test_smart_meter_simulator.py
        ├── test_energy_balance.py
        └── test_ems_integration.py
```

## Session 0 — Infrastructure setup

Docker Compose services `solar-influxdb` and `solar-grafana` were started and the Grafana datasource connection was confirmed successful. Use the existing Compose configuration and local `.env` described below. Verify with `docker ps`; the exact Compose invocation depends on the checkout.

## Session 1 — PV simulator: step-by-step

Historical development instructions; the current runtime command is documented in Session 3.

### Step 1 — Create the session branch

From the repository root:

```bash
git status
git switch -c session-01-pv-simulator
git branch --show-current
```

If the branch already exists, use `git switch session-01-pv-simulator` instead. Check for uncommitted changes before switching.

### Step 2 — Install Python dependencies

Activate the project's Python environment and install:

```bash
python -m pip install pvlib pandas numpy matplotlib influxdb-client python-dotenv pytest
```

Record the actual project dependencies in `requirements.txt` (pin versions when preparing reproducible releases). Python 3.13 is the environment used during development.

### Step 3 — Define the PV configuration

`src/pv_simulator/config.py` contains a `PVConfig` dataclass with:

- 10 panels × 400 Wp; derived `installed_capacity_kw = 4.0`
- orientation 180°, tilt 35°
- Fronius Primo 4.0-1, AC limit 4 kW, efficiency 0.97
- temperature coefficient −0.0035/°C, reference temperature 25°C
- Brașov latitude/longitude, time zone, assumed altitude
- 5-second telemetry interval

Keep configuration separate from calculation and storage code.

### Step 4 — Calculate solar irradiance

`solar_model.py` uses `pvlib.location.Location`, `get_solarposition`, `get_clearsky`, and `pvlib.irradiance.get_total_irradiance` to compute **plane-of-array (POA) irradiance** for south-facing panels tilted 35°.

The daily profile uses 288 points at 5-minute intervals. Test date: **2026-06-21**.

Observed validation:

```text
Midnight POA irradiance: 0 W/m²
Maximum POA irradiance: 1018.42 W/m²
Process finished with exit code 0
```

POA irradiance can exceed 1,000 W/m². The STC value is a reference, not a physical maximum.

### Step 5 — Implement the electrical PV model

`simulator.py` defines `PVSimulator`, independent of Docker, Grafana, or InfluxDB.

Simplified panel-temperature model:

```text
T_panel = T_ambient + (NOCT - 20) / 800 × G_POA
```

DC power model:

```text
P_DC = max(0, P_STC × (G_POA / 1000)
                 × [1 + gamma × (T_panel - 25)])
```

AC power model:

```text
P_AC = min(max(0, P_DC × 0.97), 4.0 kW)
```

These are **simplified engineering models**. The Fronius model name identifies the target installation, not an exact manufacturer efficiency curve or electrical register map.

### Step 6 — Simulate daily energy

`pv_generation.py` combines irradiance, weather, panel temperature, and power. With a 5-minute time step:

```text
E_interval [kWh] = P_AC [kW] × (5 / 60) [h]
E_day [kWh] = sum(E_interval)
```

Initial test: 2026-06-21, clear sky, ambient temperature fixed at 25°C.

Observed results:

| Metric | Clear-sky scenario |
|---|---:|
| Maximum DC power | 3.62 kW |
| Maximum AC power | 3.51 kW |
| Daily energy | 28.57 kWh |

This is a modeled clear-sky estimate, **not measured production or a weather forecast**.

### Step 7 — Add dynamic weather

`weather_model.py` uses NumPy and pandas to synthesize:

- a daily ambient-temperature cycle (example range 15–28°C);
- smoothed random cloud attenuation (`cloudiness=0.3`, `seed=42`);
- adjusted irradiance and therefore DC/AC power.

Observed results for the synthetic weather scenario:

| Metric | Clear sky | Dynamic weather |
|---|---:|---:|
| Maximum DC power | 3.62 kW | 3.18 kW |
| Maximum AC power | 3.51 kW | 3.08 kW |
| Daily energy | 28.57 kWh | 24.60 kWh |

Daily energy decreased **3.97 kWh (~13.9%)**. This difference includes both cloud attenuation **and temperature changes**. The cloud model is illustrative, not actual meteorological data.

### Step 8 — Visualize the daily profile

`plot_generation.py` uses Matplotlib to compare clear-sky and dynamic-weather AC power for 2026-06-21:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pv_simulator.plot_generation
```

For WSL2/Linux:

```bash
PYTHONPATH=src python -m pv_simulator.plot_generation
```

The visual check showed zero night production, morning ramp-up, an afternoon decline, and reduced/fluctuating output in the cloudy scenario.

### Step 9 — Run real-time telemetry

`realtime_simulator.py` uses the `Europe/Bucharest` time zone, caches a daily profile, selects the current **5-minute bucket**, and publishes a measurement every **5 seconds**.

Fields emitted:

| Field | Unit |
|---|---|
| `timestamp` | ISO-8601, offset-aware |
| `irradiance_wm2` | W/m² |
| `ambient_temperature_c` | °C |
| `panel_temperature_c` | °C |
| `dc_power_kw` | kW |
| `ac_power_kw` | kW |

Run with the project root as the working directory:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pv_simulator.realtime_simulator
```

Or on WSL2/Linux:

```bash
PYTHONPATH=src python -m pv_simulator.realtime_simulator
```

**Known limitation:** publishing at 5-second intervals does not mean the underlying PV values are recalculated every 5 seconds. The profile has 5-minute resolution; repeated values within a 5-minute bucket are expected. Timing may drift slightly with `time.sleep(5)`.

### Step 10 — Write telemetry to InfluxDB

`src/common/influx_writer.py` uses `influxdb-client`, `python-dotenv`, and synchronous writes.

Create a local `.env` in the repository root:

```dotenv
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=<your-private-token>
INFLUXDB_ORG=<your-organization>
INFLUXDB_BUCKET=energy
```

Use the actual organization and token configured during Session 0. **Never commit `.env` or share its token.** The observed bucket name was `energy`.

InfluxDB schema:

- Measurement: `pv_inverter`
- Tags: `device=fronius_primo_4_0_1`, `location=brasov`
- Fields: `ac_power_kw`, `dc_power_kw`, `irradiance_wm2`, `ambient_temperature_c`, `panel_temperature_c`
- Timestamp: measurement ISO-8601 time

The console displayed `Telemetry sent to InfluxDB`, and the `pv_inverter` measurement and fields were verified in the InfluxDB Data Explorer.

To verify containers:

```bash
docker ps
```

Open the local InfluxDB UI at `http://localhost:8086`.

### Step 11 — Create the Grafana dashboard

Grafana 11.6.0 is available locally at `http://localhost:3000`.

Use the existing **`Solar-InfluxDB`** data source, query language **Flux**, organization/token from Session 0, and default bucket `energy`. From one Docker container to the other, `http://solar-influxdb:8086` works **only when both containers share a resolvable Docker network**.

Dashboard: **Solar BESS SCADA - Fronius PV**

Five panels, all verified visually:

1. PV AC Power — `ac_power_kw` (kW; suggested Y axis 0–4)
2. PV DC Power — `dc_power_kw` (kW; suggested Y axis 0–4)
3. Solar Irradiance — `irradiance_wm2` (W/m²)
4. PV Panel Temperature — `panel_temperature_c` (°C)
5. Ambient Temperature — `ambient_temperature_c` (°C)

Set dashboard time range to **Last 15 minutes**, refresh to **5s**, and time zone to **Europe/Bucharest**.

Example Flux query for AC power (replace the `_field` value for other panels):

```flux
from(bucket: "energy")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "pv_inverter")
  |> filter(fn: (r) => r._field == "ac_power_kw")
  |> filter(fn: (r) => r.device == "fronius_primo_4_0_1")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
```

**Export the dashboard** from Grafana as JSON and save it to `grafana/dashboards/fronius-pv.json`. Inspect the export before committing. Export and final commit were subsequently confirmed by the user.

### Step 12 — Unit tests

`src/tests/test_pv_simulator.py` contains seven tests for:

1. installed PV capacity = 4 kWp;
2. zero DC power at zero irradiance;
3. STC DC power = 4 kW;
4. power reduction at elevated panel temperature;
5. inverter efficiency (3 kW DC → 2.91 kW AC);
6. AC inverter cap at 4 kW;
7. panel temperature (800 W/m², 20°C ambient → 45°C panel).

Run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest src/tests/ -v
```

Or in WSL2/Linux:

```bash
PYTHONPATH=src python -m pytest src/tests/ -v
```

The user subsequently confirmed all seven tests passed.

#### Import issue resolved

With `src` as PyCharm **Sources Root**, make sure `src/common/__init__.py` and `src/pv_simulator/__init__.py` exist. Use consistent package imports, for example:

```python
from pv_simulator.config import PVConfig
from pv_simulator.simulator import PVSimulator
from common.influx_writer import InfluxWriter
```

Avoid the legacy `from config import PVConfig` inside `simulator.py` when executing as a package. Prefer `python -m pv_simulator.realtime_simulator` with `PYTHONPATH=src` to running a source file by path.

## Security and Git handoff

Recommended `.gitignore` entries:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.idea/
```

Before committing, check the branch and inspect staged files:

```bash
git branch --show-current
git status
git add src/ grafana/dashboards/fronius-pv.json requirements.txt README.md .gitignore
git diff --cached --stat
git diff --cached --check
git commit -m "feat: implement Fronius 4kWp PV simulator and Grafana dashboard"
git status
```

The `git add` command assumes the Grafana JSON export already exists. **Do not execute it unchanged until the export is saved.** Ensure no secrets are staged. Do not mark the session complete until the tests, export, and commit are confirmed.

## Session 1 acceptance checklist

- [x] Model configured for 4 kWp, Fronius Primo 4.0-1, south-facing array
- [x] Brașov solar-position and POA irradiance calculations executed
- [x] DC/AC power and daily energy calculated
- [x] Synthetic cloud and temperature model executed
- [x] Daily production comparison chart reviewed
- [x] 5-second telemetry publishing observed
- [x] InfluxDB writes and measurement verified
- [x] Grafana dashboard with five panels reviewed
- [x] Seven PV tests passed
- [x] Export Grafana dashboard JSON into Git repository (reported)
- [x] Final Session 1 commit reported complete; clean tree not independently checked

## Session 1 limitations / planned improvements (historical)

- Current telemetry is **simulated**, not live Fronius or AlphaESS data.
- Clear-sky modeling and synthetic clouds are not real weather observations.
- Panel NOCT and constant inverter efficiency are assumptions.
- The current profile is sampled every 5 minutes; 5-second telemetry repeats values.
- Ambient-temperature curve is a synthetic approximation.
- Inverter standby power, MPPT behavior, clipping detail, cable/soiling/shading losses, and device faults are not yet modeled.
- No physical EPS wiring or grid-meter topology has been verified.
- Unit tests currently cover the PV mathematics, not the end-to-end InfluxDB/Grafana pipeline.
- Time-zone transitions and exact integration boundaries deserve dedicated tests.

## Session 2 — BESS simulator and Grafana monitoring (2026-10-15)

### Objective and scope

Add a self-contained battery simulator to the existing PV simulation, publish both telemetry streams to the same InfluxDB instance, and monitor the battery in Grafana. **Option A** was selected: a fixed time-of-day charging/discharging profile. PV-surplus-following EMS and grid energy balance are explicitly deferred.

**Branch:** `session-02-alphaess-bess` (reported clean at session start). Do not merge or commit until the final checks below are complete.

### Implementation files

- `src/bess_simulators/__init__.py` — package marker.
- `src/bess_simulators/bess_simulator.py` — `BESSConfig`, `BESSMode`, and `BESSimulator.step()`.
- `src/tests/test_bess_simulator.py` — 11 automated battery-model tests.
- `src/tests/manual_test_bess_influx.py` — manual InfluxDB write smoke test (not a pytest test).
- `src/common/influx_writer.py` — existing PV writer retained; `write_bess_measurement()` added.
- `realtime_simulator.py` — existing PV runtime extended to update and publish BESS telemetry. **Check its path in your checkout:** Session 1 documents `src/pv_simulator/realtime_simulator.py`, while the uploaded runtime was named `realtime_simulator.py` and the Session 2 commands used `src/realtime_simulator.py`. Use the actual location and consistent imports.
- `grafana/dashboards/alphaess_bess_dashboard.json` — intended location of the Grafana export; export completion reported; file validity not independently checked.

### Demonstration battery configuration

| Parameter | Value | Notes |
|---|---:|---|
| Usable model capacity | 10.0 kWh | Demonstration setting, not confirmed S5 capacity |
| Nominal DC voltage | 51.2 V | Held constant in this version |
| Maximum charge / discharge power | 5 / 5 kW | Simulation limits |
| Initial SOC | 50% | Reset at process startup |
| Minimum / maximum SOC | 10% / 95% | Enforced in `step()` |
| Charge / discharge efficiency | 95% / 95% | Constant assumptions |
| SOH | 100% | Constant placeholder |
| Battery temperature | 25°C | Constant placeholder |

**Power sign convention:** positive `power_kw` means discharge; negative means charge; zero means idle. Current is approximated as `power_kw × 1000 / 51.2` and uses the same sign convention. This is a simplified telemetry convention, not a detailed AC/DC converter model.

For `dt_h = dt_seconds / 3600` and capacity `C` in kWh:

- **Discharge:** `SOC_new = SOC_old - (E_out / discharge_efficiency / C) × 100`, where `E_out = P_discharge × dt_h`.
- **Charge:** `SOC_new = SOC_old + (E_in × charge_efficiency / C) × 100`, where `E_in = abs(P_charge) × dt_h`.
- Power is limited to configured maximums, and actual energy is reduced if the next step would cross a SOC bound. Charged/discharged energy counters represent input/output energy at the model boundary and accumulate only while the process runs.

`BESSMode` defines `IDLE`, `CHARGING`, `DISCHARGING`, and `FAULT`. **FAULT detection and protection logic are not implemented** in this version.

### Fixed schedule (Option A — historical, superseded by Session 3 EMS)

The runtime chooses requested BESS power using the local `Europe/Bucharest` clock:

| Local time | Requested power | Mode |
|---|---:|---|
| 00:00–06:00 | 0 kW | IDLE |
| 06:00–12:00 | −2 kW | CHARGING |
| 12:00–18:00 | +2 kW | DISCHARGING |
| 18:00–24:00 | 0 kW | IDLE |

The actual power can drop below the requested magnitude or to zero at SOC boundaries. **The flat −2 kW Battery Power line in the morning is expected**; this controller does not react to PV production, household load, or electricity prices. The model does not calculate grid import/export. If PV produces less than the charging demand, the shortfall is not currently represented in telemetry.

The PV profile is calculated in 5-minute buckets, while PV and BESS telemetry are published about every 5 seconds. The BESS time step uses `time.monotonic()` to account for elapsed time. SOC and counters are in-memory and reset on restart.

### InfluxDB integration

Existing configuration is loaded from the root `.env` by `InfluxWriter`; do not commit credentials. The observed bucket is `energy` and the existing PV measurement remains `pv_inverter`.

New BESS schema:

| Item | Value |
|---|---|
| Measurement | `bess` |
| Tags | `device=alphaess_simulator`, `location=brasov` |
| Numeric fields | `soc`, `soh`, `power_kw`, `voltage_v`, `current_a`, `temperature_c`, `energy_charged_kwh`, `energy_discharged_kwh` |
| String field | `mode` |
| Timestamp | Offset-aware ISO-8601 time supplied by runtime; InfluxDB `WritePrecision.NS` |

The BESS writer uses the existing synchronous `InfluxDBClient` write API and is closed together with the PV writer on shutdown.

**Manual smoke test:**

```powershell
python -m src.tests.manual_test_bess_influx
```

Observed output included `soc=49.97`, `power_kw=2.0`, `mode=DISCHARGING`, `energy_discharged_kwh=0.003` and `BESS telemetry successfully sent to InfluxDB!` after a 5-second discharge step. The charging counter correctly remained zero.

### Run the integrated simulator

Start the existing Docker Compose services as configured in Session 0, then run from the repository root. For the layout with `src/realtime_simulator.py`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python src/realtime_simulator.py
```

If your actual file is `src/pv_simulator/realtime_simulator.py`, use the Session 1 module command (`python -m pv_simulator.realtime_simulator`) and ensure the BESS imports are consistent with `PYTHONPATH=src`. **Do not create a second copy of the runtime just to match this example.** Stop with `Ctrl+C`.

Observed during integration (2026-10-15, local time around 08:52): PV `ac_power_kw=0.891`, BESS `power_kw=-2.0`, `mode=CHARGING`, with SOC increasing `50.30 → 50.33 → 50.36%` over successive ~5-second samples. The runtime printed `Telemetry sent to InfluxDB` each iteration. These are simulated values, not real device readings.

### Grafana — AlphaESS BESS Monitoring

Datasource: `Solar-InfluxDB`, Flux queries, bucket `energy`, measurement `bess`, device `alphaess_simulator`. Nine panels were visually checked:

| Panel | Field | Visualization | Observed example |
|---|---|---|---|
| Battery SOC | `soc` | Gauge | 74.3% |
| Battery Voltage | `voltage_v` | Stat | 51.2 V |
| Battery Operating Mode | `mode` | Stat + value mappings | CHARGING |
| Battery Power | `power_kw` | Time series | −2.0 kW |
| Battery Current | `current_a` | Time series | −39.06 A |
| Battery Temperature | `temperature_c` | Time series | 25.0°C |
| Battery SOH | `soh` | Stat | 100.0% |
| Energy Charged | `energy_charged_kwh` | Stat | 2.559 kWh |
| Energy Discharged | `energy_discharged_kwh` | Stat | 0.000 kWh |

For numeric instantaneous Stat panels, use `last()`; for time-series panels, use `aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)`. Example SOC query:

```flux
from(bucket: "energy")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bess")
  |> filter(fn: (r) => r._field == "soc")
  |> filter(fn: (r) => r.device == "alphaess_simulator")
  |> last()
```

The Operating Mode Stat panel initially displayed `No data` because text fields were excluded by the numeric-field selection. Setting **Fields = All fields** showed both time and mode. The final query removed the time column:

```flux
from(bucket: "energy")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "bess")
  |> filter(fn: (r) => r._field == "mode")
  |> filter(fn: (r) => r.device == "alphaess_simulator")
  |> last()
  |> keep(columns: ["_value"])
```

Use value mappings `IDLE` (gray), `CHARGING` (green), `DISCHARGING` (blue), and `FAULT` (red). The dashboard showed CHARGING correctly. A cosmetic issue remains: **SOH 100% appeared red**; adjust its color threshold so a healthy value is green. Set auto-refresh to 5s if desired.

Export dashboard JSON through Grafana and save it as `grafana/dashboards/alphaess_bess_dashboard.json`; verify its contents and JSON validity before committing. Export completion was subsequently reported.

### Automated tests and verification

Run from the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest src/tests/ -v
```

- Session 1 PV suite: **7 passed**, previously reported.
- Session 2 BESS suite: **11 passed in 0.03s**, reported on 2026-10-15; covers initial state, charging, discharging, idle, power caps, SOC bounds, invalid initial SOC/time step, and accumulated energy.
- **Full 18-test regression run passed**, subsequently confirmed by the user.

### Limitations and future work

- Not an official AlphaESS S5 model, manufacturer register map, or validated hardware control interface. The reference installation has 9.12 kWh, but this demonstrator uses 10 kWh.
- No household load, grid power balance, PV-driven dispatch, tariff optimization, or EMS yet.
- Voltage, SOH, and temperature are fixed; no degradation, thermal response, or fault detection.
- No persistent SOC/counters; restarting resets battery state and energy counters.
- Fixed schedule is for testing only; BESS may request charging even when PV generation is insufficient.
- InfluxDB/Grafana manual checks are not substitutes for automated integration tests.

### Session 2 acceptance checklist

- [x] `session-02-alphaess-bess` branch verified clean at start.
- [x] BESS model implemented and tested (11/11).
- [x] BESS telemetry manually written to InfluxDB.
- [x] PV and BESS real-time publishing observed together.
- [x] Nine BESS Grafana panels visually verified.
- [ ] Correct SOH Stat coloring (cosmetic).
- [x] Dashboard export reported complete; JSON not independently inspected.
- [x] Full test suite: 18/18.
- [x] Session 2 commit and merge into main reported complete.
- [ ] Clean-tree output not independently verified.

### Git handoff (after export and tests)

```powershell
git branch --show-current
git status
python -m pytest src/tests/ -v
python -m json.tool grafana/dashboards/alphaess_bess_dashboard.json > $null
git add README.md src/ grafana/dashboards/alphaess_bess_dashboard.json
git diff --cached --stat
git diff --cached --check
git diff --cached
git commit -m "feat: add AlphaESS BESS simulator and Grafana monitoring"
git status
```

Stage additional changed files only after reviewing them. Never stage `.env`, credentials, or `.venv`. If the JSON export is not yet present, do not execute the `git add` line unchanged.

### Next session handoff

Plan a dedicated EMS session: simulate household demand, calculate PV surplus, dispatch BESS dynamically, and account for grid import/export and SOC limits. Modbus TCP/RTU and SCADA integration remain on the roadmap, with the session ordering to be agreed before creating the next branch.

## Session 3 — Energy Management System (EMS), 2026-11-26–27

**Branch:** `session-03-ems` (agreed branch name; verify locally before committing).

### Step 1 — Initialize the session

From the repository root, with the previous session merged and a clean working tree:

```powershell
git switch main
git status
git switch -c session-03-ems
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest src/tests/ -v
```

The starting baseline was 18 passing tests. Do not recreate the branch if it already exists.

### Steps 2–3 — Household load simulator and tests

`src/load_simulators/load_simulator.py` defines `LoadConfig` and `LoadSimulator`. Default minimum/maximum power: 0.15/6 kW; random variation ±15%, seed 42. The synthetic local-time profile is:

| Local hours | Base power (kW) |
|---|---:|
| 00–06 | 0.30 |
| 06–09 | 1.50 |
| 09–12 | 0.60 |
| 12–14 | 1.20 |
| 14–17 | 0.70 |
| 17–21 | 2.00 |
| 21–23 | 0.90 |
| 23–24 | 0.40 |

Base daily energy is 22.8 kWh on a 24-hour day without variation. `step(timestamp, dt_seconds)` samples the profile, clamps the varied power to configured limits and accumulates `energy_consumed_kwh += power_kw * dt_seconds / 3600`. `reset()` resets state and random seed. Invalid configuration and nonpositive/nonfinite time steps are rejected. The manual eight-sample test accumulated 0.010376 kWh over 40 simulated seconds, not a full day. Fifteen load tests passed; cumulative suite: 33.

### Step 4 — EMS controller

`src/ems/ems_controller.py` defines `EMSConfig`, `EMSMode`, `EMSController.calculate_setpoint(pv_power_kw, load_power_kw)`. The policy maximizes instantaneous PV self-consumption, permits grid export and does not request grid charging. The fixed Session 2 schedule is superseded.

| Quantity | Sign convention |
|---|---|
| PV and household load | Nonnegative |
| BESS | Positive discharge, negative charge |
| Grid | Positive import, negative export |

```text
net_power_kw = load_power_kw - pv_power_kw
requested_bess_power_kw = 0 if abs(net_power_kw) <= 0.01 else net_power_kw
```

The 0.01 kW (10 W) deadband is an engineering assumption. Modes are IDLE, CHARGING and DISCHARGING. The EMS requests power; the BESS enforces its own SOC and power limits. A request can therefore differ from actual battery power. Inputs must be finite and PV/load nonnegative. Twenty-two EMS tests passed.

### Step 5 — Grid and smart meter

`src/grid_simulators/grid_simulator.py` implements `GridSimulator.step(pv_power_kw, load_power_kw, bess_power_kw, dt_seconds)` using actual BESS power:

```text
P_grid = P_load - P_PV - P_BESS
P_import = max(P_grid, 0)
P_export = max(-P_grid, 0)
E_import += P_import * dt_seconds / 3600
E_export += P_export * dt_seconds / 3600
```

Modes: IMPORTING, EXPORTING, IDLE. Import/export counters are independent and resettable. Near-zero grid residual normalization was introduced during realtime integration to suppress rounding artifacts; the exact cutoff should be checked in the current grid source. Twenty-nine grid tests passed.

`smart_meter_simulator.py` defines `SmartMeterConfig` and `SmartMeterSimulator.measure(grid_telemetry, timestamp)`. The ideal single-phase model defaults to 230 V, 50 Hz, PF 1.0. Current is an unsigned magnitude `abs(P_grid)*1000/(V*PF)` A; apparent power is `abs(P_grid)/PF` kVA. The meter copies grid energy counters rather than integrating them again. Forty-two meter tests passed.

Manual grid scenarios included full battery export of 2.5 kW (10.870 A), empty battery import of 2 kW (8.696 A), and high load with battery-limited import of 1 kW (4.348 A). Seven five-second samples accumulated approximately 0.004167 kWh imported and 0.004861 kWh exported.

### Step 6 — Energy balance validator

`src/ems/energy_balance.py` defines `EnergyBalanceConfig(tolerance_kw=0.001)` and `EnergyBalanceValidator.validate(pv_power_kw, load_power_kw, bess_power_kw, grid_power_kw)`.

```text
Supply = PV + max(BESS, 0) + max(Grid, 0)
Demand = Load + max(-BESS, 0) + max(-Grid, 0)
Error = Supply - Demand
is_balanced = abs(Error) <= tolerance_kw
```

Status is BALANCED or UNBALANCED. The default inclusive tolerance is ±1 W, subject to floating-point arithmetic. The validator rejects negative PV/load, nonfinite power and invalid tolerance. It is stateless and returns nine fields (see schema below). Eleven manual operating scenarios were balanced, including near-minimum and near-maximum SOC clipping. Forty-nine validator tests passed.

### Step 7 — Realtime system integration

The confirmed runtime is `src/realtime_simulator.py`, class `RealtimeSystemSimulator`. Its `simulate_step(now, dt_seconds)` orchestrates:

```text
PV profile + household load -> EMS request -> BESS actual response
PV + load + actual BESS -> Grid -> Smart Meter
PV + load + actual BESS + meter grid power -> Energy Balance Validator
All seven telemetry dictionaries -> InfluxWriter -> InfluxDB -> Grafana
```

The runtime caches the PV daily profile, selects the current five-minute bucket, and uses a common offset-aware timestamp for every component. `time.monotonic()` measures elapsed seconds; the first interval elapses before the first energy accumulation. `step_count` and `unbalanced_count` belong to the runtime. `publish_telemetry()` is separate from `simulate_step()`. Ctrl+C closes the writer and prints counters and accumulated energy.

A rounding artifact originally caused tiny grid imports/exports and nonzero current at nominally balanced operation. After normalization, an observed residual of -0.194 W was BALANCED with grid power and current zero. The validator does not itself normalize grid power.

### Step 8 — InfluxDB integration

`src/common/influx_writer.py` now publishes the seven measurements in one synchronous write request via `write_system_measurement(system_data)`. The common timestamp is the point timestamp, not an additional field. Bucket: `energy`; location reference: Brașov.

| Measurement | Fields | Count |
|---|---|---:|
| `pv_inverter` | `irradiance_wm2`, `ambient_temperature_c`, `panel_temperature_c`, `dc_power_kw`, `ac_power_kw` | 5 |
| `bess` | `soc`, `soh`, `power_kw`, `voltage_v`, `current_a`, `temperature_c`, `energy_charged_kwh`, `energy_discharged_kwh`, `mode` | 9 |
| `household_load` | `power_kw`, `energy_consumed_kwh` | 2 |
| `ems` | `pv_power_kw`, `load_power_kw`, `net_power_kw`, `requested_bess_power_kw`, `mode` | 5 |
| `grid` | `power_kw`, `import_power_kw`, `export_power_kw`, `energy_imported_kwh`, `energy_exported_kwh`, `mode` | 6 |
| `smart_meter` | `power_kw`, `voltage_v`, `current_a`, `frequency_hz`, `power_factor`, `apparent_power_kva`, `energy_imported_kwh`, `energy_exported_kwh`, `mode` | 9 |
| `energy_balance` | `pv_power_kw`, `load_power_kw`, `bess_power_kw`, `grid_power_kw`, `supply_power_kw`, `demand_power_kw`, `balance_error_kw`, `is_balanced`, `status` | 9 |
| **Total** | | **45** |

Known device tags: `fronius_primo_4_0_1`, `alphaess_simulator`, `household_simulator`, `ems_controller`, `grid_simulator`, `energy_balance_validator`. Verify the smart-meter device tag in the current writer. All seven measurements and 45 fields were observed at a common timestamp, 2026-11-26T13:44:03.093546+02:00. A two-minute query returned 24 distinct samples for each measurement.

```flux
from(bucket: "energy")
  |> range(start: -2m)
  |> keep(columns: ["_time", "_measurement"])
  |> group(columns: ["_measurement"])
  |> distinct(column: "_time")
  |> map(fn: (r) => ({r with _value: 1}))
  |> count(column: "_value")
  |> rename(columns: {_value: "sample_count"})
  |> group()
  |> sort(columns: ["_measurement"])
```

Mapping to a numeric value avoids the observed Flux error `count: unsupported aggregate column type time`.

### Step 9 — Grafana EMS dashboard

Dashboard: **Solar BESS — Energy Management System**. Datasource `Solar-InfluxDB`, bucket `energy`, last 15 minutes, refresh 5s. Twenty-one panels were visually validated.

| # | Panel | Visualization | Measurement / field |
|---:|---|---|---|
| 1 | PV Power | Stat | pv_inverter / ac_power_kw |
| 2 | Household Load | Stat | household_load / power_kw |
| 3 | BESS Power | Stat | bess / power_kw |
| 4 | Grid Power | Stat | grid / power_kw |
| 5 | Battery SOC | Gauge | bess / soc |
| 6 | System Power | Time series | energy_balance / pv, load, bess, grid power fields |
| 7 | EMS Mode | Stat | ems / mode |
| 8 | BESS Mode | Stat | bess / mode |
| 9 | Grid Mode | Stat | grid / mode |
| 10 | Requested vs. Actual BESS Power | Time series | ems / requested_bess_power_kw; bess / power_kw |
| 11 | Household Energy | Stat | household_load / energy_consumed_kwh |
| 12 | Grid Imported Energy | Stat | grid / energy_imported_kwh |
| 13 | Grid Exported Energy | Stat | grid / energy_exported_kwh |
| 14 | Battery Charged Energy | Stat | bess / energy_charged_kwh |
| 15 | Battery Discharged Energy | Stat | bess / energy_discharged_kwh |
| 16 | Energy Balance Status | Stat | energy_balance / status |
| 17 | Grid Voltage | Stat | smart_meter / voltage_v |
| 18 | Grid Current | Stat | smart_meter / current_a |
| 19 | Grid Frequency | Stat | smart_meter / frequency_hz |
| 20 | Power Factor | Stat | smart_meter / power_factor |
| 21 | Power Balance Error | Time series | energy_balance / balance_error_kw × 1000 |

Use explicit suffix units kW/kWh (3 decimals), SOC (2 decimals), V (1), A and Hz (2). For cumulative energy counters use `last()` rather than summing cumulative readings. For mode/status Stat panels use All fields, Text mode Value, Last not null, solid background and mappings: IDLE gray, CHARGING green, DISCHARGING blue, IMPORTING orange, EXPORTING purple, BALANCED green, UNBALANCED red. Example:

```flux
from(bucket: "energy")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "ems" and r._field == "mode")
  |> filter(fn: (r) => r.device == "ems_controller")
  |> group()
  |> sort(columns: ["_time"])
  |> last()
  |> keep(columns: ["_value"])
```

System Power uses mean aggregation, `createEmpty: true`, minimum interval 10s, max data points 500, no connection across nulls and disconnect threshold 30s. PV yellow, load orange, BESS blue dashed, grid purple dotted. Balance error is displayed in W with three decimals, zero-centered soft range ±1.5 W, thresholds -1 and +1 W (status field is authoritative at boundaries). Voltage thresholds 207/253 V, frequency 49.5/50.5 Hz, PF 0.8/0.95 are dashboard display settings, not physical protection logic.

Observed overnight minimum-SOC protection: SOC 10%, BESS IDLE while EMS requested DISCHARGING, grid IMPORTING, balance BALANCED. Discharged energy was 3.800 kWh, consistent with `(0.50-0.10)*10*0.95`. Later PV reached 1.284 kW against 1.333 kW load, leaving about 0.049 kW import and 0.21 A. These are simulated observations, not real meter data.

### Step 10 — Automated testing

| Test module | Passed |
|---|---:|
| test_pv_simulator.py | 7 |
| test_bess_simulator.py | 11 |
| test_load_simulator.py | 15 |
| test_ems_controller.py | 22 |
| test_grid_simulator.py | 29 |
| test_smart_meter_simulator.py | 42 |
| test_energy_balance.py | 49 |
| test_ems_integration.py | 28 |
| **Total** | **203** |

Reported final integration run: 28 passed in 1.13s; full regression: **203 passed in 1.16s**. Session 3 added 185 tests. Coverage includes input validation, sign conventions, energy counters, SOC limits and recovery, tolerance, synchronized telemetry, fault injection (+500 W meter error), simulation counters and mocked publishing. Integration tests exercise actual `simulate_step()` with controlled PV, deterministic load and mocked InfluxWriter. The 7 kW synthetic PV stress case intentionally exceeds the physical reference inverter rating to test charge limits. Automated tests do not establish live database connectivity or Grafana import correctness.

### Step 11 — Dashboard export

The user confirmed the EMS dashboard export completed. Agreed target: `grafana/dashboards/solar-bess-ems.json`. Export with external sharing enabled for datasource portability. Verify the actual filename and contents locally:

```powershell
python -m json.tool .\grafana\dashboards\solar-bess-ems.json > $null
$dashboard = Get-Content .\grafana\dashboards\solar-bess-ems.json -Raw | ConvertFrom-Json
$dashboard.title
$dashboard.panels.Count
$dashboard.refresh
$dashboard.time
```

Expected: 21 panels, 5s refresh, now-15m to now. The JSON itself was not supplied for independent inspection.

### Step 12 — Documentation and current execution instructions

This consolidated README retains the earlier session details and updates the current runtime path and completion status. Run from the repository root with the Python environment activated, existing Docker services running and `.env` configured:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python src/realtime_simulator.py
```

Linux/WSL alternative: `PYTHONPATH=src python src/realtime_simulator.py`. Stop with Ctrl+C. Open local InfluxDB on port 8086 and Grafana on port 3000. Historical Session 1 module commands above refer to the earlier layout; use the current runtime command for Session 3.

### Steps 13–14 — Final regression and Git handoff (pending)

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest src/tests/ -v
git branch --show-current
git status --short
git add README.md src/ grafana/dashboards/solar-bess-ems.json
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Expect 203 tests. Review staged content for credentials and unrelated changes before committing. Stage other changed files only if appropriate. After successful checks:

```powershell
git commit -m "feat: integrate solar BESS energy management system"
git status
git switch main
git merge --no-ff session-03-ems -m "Merge Session 3: Energy Management System"
python -m pytest src/tests/ -v
git status
```

Only switch branches with a clean working tree; verify the branch name and dashboard path first. Push only if desired and a remote is configured. No commit or merge has been performed by this documentation update.

### Current limitations and roadmap

- Synthetic weather and household demand, constant battery efficiency, voltage, SOH and temperature; no verified manufacturer-specific hardware model.
- No real Modbus TCP/RTU, EPS/islanding, grid outages, tariffs, export limits, or physical control. Grid assumed continuously available.
- In-memory SOC and counters reset at restart; cumulative Grafana values represent the current process run, not lifetime totals.
- PV profile resolution is five minutes; realtime interval is nominally five seconds, with processing overhead. DST and interval-boundary integration need dedicated validation.
- BESS power rounding and grid normalization can leave sub-watt residuals; exact tolerance comparisons may be affected by floating-point cancellation. Grid normalization boundary tests remain open.
- Instantaneous power balance is not an independent cumulative energy conservation audit. Smart-meter electrical model has no noise, harmonics or reactive-power dynamics.
- Future sessions may address persistence, tariffs, real-device read-only Modbus integration, and alarms; agree scope before creating a new branch.

### Session 3 acceptance checklist

- [x] Household load, EMS, grid, smart meter and energy balance implemented.
- [x] Realtime integration and seven synchronized InfluxDB measurements observed.
- [x] Twenty-one Grafana panels reviewed; dashboard export reported complete.
- [x] 203 automated tests passed.
- [x] Consolidated README prepared.
- [ ] Final regression after documentation and export verification.
- [ ] Review staged changes, commit and merge into main; confirm clean tree.

## Documentation convention for every session

**At the end of each session**, update the repository documentation **before the final Git commit**. Record:

- Session objective and branch name.
- Actual hardware/software configuration and assumptions.
- Files created/modified and architecture.
- Commands to install, run, and test.
- Results actually observed (distinguish measured vs simulated vs expected).
- Screenshots/dashboard exports and paths.
- Errors encountered and how they were resolved.
- Known limitations and open tasks.
- Acceptance checklist and next-session handoff.

Keep this single root README as the project overview and running session record. Do not mark unverified tasks as complete.
