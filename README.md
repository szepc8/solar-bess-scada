# Solar BESS SCADA

A practical Python + Docker + InfluxDB + Grafana learning project that simulates a residential photovoltaic (PV) installation and, in future sessions, an AlphaESS battery energy storage system (BESS), smart meter, Modbus communications, and SCADA logic.

> **Status:** Session 1 PV simulator implemented and manually validated. This repository currently produces **simulated** telemetry; it does **not** read from or control the real installation.

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

The BESS reference is an **AlphaESS S5 with 9.12 kWh storage** and EPS capability. Battery modeling is planned for Session 2.

## Development environment

- Windows, PyCharm Community Edition, Python 3.13
- WSL2 + Docker Compose
- InfluxDB 2.7 (container `solar-influxdb`, host port `127.0.0.1:8086`)
- Grafana 11.6.0 (container `solar-grafana`, host port `127.0.0.1:3000`)
- Git, with one branch per development session

Session 0 configured and tested InfluxDB and Grafana. Preserve the working Docker Compose configuration.

## Repository structure

The following is the intended layout; in the working project, **tests were observed under `src/tests/`**. Commands below use that location. You may later move them to top-level `tests/` and adjust commands accordingly.

```text
solar-bess-scada/
├── .env                       # local credentials; NEVER commit
├── .gitignore
├── README.md
├── requirements.txt
├── docker/                    # existing Compose configuration from Session 0
├── grafana/
│   └── dashboards/
│       └── fronius-pv.json   # export manually before final commit
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
    │   ├── plot_generation.py
    │   └── realtime_simulator.py
    └── tests/
        └── test_pv_simulator.py
```

## Session 1 — PV simulator: step-by-step

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

**Export the dashboard** from Grafana as JSON and save it to `grafana/dashboards/fronius-pv.json`. Inspect the export before committing. The export is a **pending repository task** until saved.

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

The test module was reported working. **Confirm the exact number of passing tests in the terminal** before finalizing the session.

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
- [x] Pytest module reported running (verify full test summary)
- [ ] Export Grafana dashboard JSON into Git repository
- [ ] Commit Session 1 branch and confirm clean working tree

## Known limitations / planned improvements

- Current telemetry is **simulated**, not live Fronius or AlphaESS data.
- Clear-sky modeling and synthetic clouds are not real weather observations.
- Panel NOCT and constant inverter efficiency are assumptions.
- The current profile is sampled every 5 minutes; 5-second telemetry repeats values.
- Ambient-temperature curve is a synthetic approximation.
- Inverter standby power, MPPT behavior, clipping detail, cable/soiling/shading losses, and device faults are not yet modeled.
- No physical EPS wiring or grid-meter topology has been verified.
- Unit tests currently cover the PV mathematics, not the end-to-end InfluxDB/Grafana pipeline.
- Time-zone transitions and exact integration boundaries deserve dedicated tests.

## Next session — AlphaESS S5 BESS simulator

Proposed branch: `session-02-bess-simulator`.

Implement a 9.12 kWh battery model with state of charge (SOC), charge/discharge power, efficiency, SOC bounds, energy balance, and later EPS/backup behavior. Confirm the actual AlphaESS S5 limits and battery specifications before claiming device-specific fidelity.

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

Keep this root README as the project overview and running session summary. For future sessions, consider detailed notes in `docs/sessions/session-XX-<topic>.md`, linked from here. Do not mark unverified tasks as complete.
