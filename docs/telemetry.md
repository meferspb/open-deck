# 📊 Telemetry Variable Catalog

> This file is generated from `msfs_gateway/telemetry.py`; do not edit it manually.
> Update: `python -m msfs_gateway.docsgen --write`.

The registry is the single source of truth: panel profiles bind instruments to
these keys, and the gateway reads SimVars and sends commands.

## How to read the table

- **Key** — the variable name in the telemetry frame and in the profile's
  `bindings`.
- **Type** — `number`, `bool`, or `string`; `bool` arrives in JSON as
  `true/false`, numbers as `float`.
- **Read** — the SimVar from which the gateway takes the value (for `custom.*`
  there is no source: they are read by the WASM bridge according to the profile
  description).
- **Command** — the SimConnect event used to change the variable;
  a dash means "read-only".

## Variables by group

### Electrical and power

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `power.batteryMaster` | bool | — | ELECTRICAL MASTER BATTERY | TOGGLE_MASTER_BATTERY | Battery master switch |
| `power.avionicsMaster` | bool | — | AVIONICS MASTER SWITCH | TOGGLE_AVIONICS_MASTER | Avionics power |
| `power.busVolts` | number | V | ELECTRICAL MAIN BUS VOLTAGE | — | Main bus voltage |

### Engine

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `engine.rpm` | number | RPM | GENERAL ENG RPM:1 | — | Engine RPM |
| `engine.fuelFlowGph` | number | GPH | ENG FUEL FLOW GPH:1 | — | Fuel flow per hour |
| `engine.torquePct` | number | % | TURB ENG MAX TORQUE PERCENT:1 | — | Turboprop engine torque |
| `engine.ittC` | number | °C | TURB ENG ITT:1 | — | ITT temperature |
| `engine.propRpm` | number | RPM | PROP RPM:1 | — | Propeller RPM |
| `engine.n1Pct` | number | % | TURB ENG N1:1 | — | Engine #1 N1 |
| `engine.n1Pct2` | number | % | TURB ENG N1:2 | — | Engine #2 N1 |

### Spatial attitude

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `attitude.pitchDeg` | number | ° | PLANE PITCH DEGREES | — | Pitch |
| `attitude.bankDeg` | number | ° | PLANE BANK DEGREES | — | Bank |

### Altitude

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `altitude.indicatedFt` | number | FT | INDICATED ALTITUDE | — | Indicated altitude |

### Speed

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `speed.iasKt` | number | KT | AIRSPEED INDICATED | — | Indicated airspeed |

### VSI

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `verticalSpeed.fpm` | number | FPM | VERTICAL SPEED | — | Vertical speed |

### Heading

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `heading.magneticDeg` | number | ° | PLANE HEADING DEGREES MAGNETIC | — | Magnetic heading |

### Wing flaps

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `flaps.percent` | number | % | TRAILING EDGE FLAPS LEFT PERCENT | — | Flap position |

### Fuel

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `fuel.leftGal` | number | GAL | FUEL LEFT QUANTITY | — | Left tank fuel |
| `fuel.rightGal` | number | GAL | FUEL RIGHT QUANTITY | — | Right tank fuel |
| `fuel.totalGal` | number | GAL | — | — | Total fuel |

### Autopilot

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `autopilot.headingBugDeg` | number | ° | AUTOPILOT HEADING LOCK DIR | HEADING_BUG_SET | Target heading (heading bug) |
| `autopilot.master` | bool | — | AUTOPILOT MASTER | AP_MASTER | Autopilot engaged |
| `autopilot.approachHold` | bool | — | AUTOPILOT APPROACH HOLD | AP_APR_HOLD | APR mode — engage command |
| `autopilot.approach` | bool | — | AUTOPILOT APPROACH HOLD | — | APR mode active |

### Aircraft state

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `aircraft.onGround` | bool | — | SIM ON GROUND | — | Aircraft on the ground |
| `aircraft.radioAltitudeFt` | number | FT | RADIO HEIGHT | — | Radio altitude above the runway |
| `aircraft.title` | string | — | TITLE | — | Aircraft title in the simulator |

### Taxi

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `groundSpeed.kt` | number | KT | GPS GROUND SPEED | — | Ground speed |

### Navigation (ILS)

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `nav.localizer` | number | dots | NAV CDI:1 | — | Localizer deviation |
| `nav.glideSlope` | number | ° | NAV GLIDE SLOPE ERROR | — | Glideslope deviation |
| `nav.locFlag` | bool | — | HSI CDI NEEDLE VALID | — | Localizer captured |
| `nav.gsFlag` | bool | — | HSI GSI NEEDLE VALID | — | Glideslope captured |
| `nav.gpsDrivesNav1` | bool | — | GPS DRIVES NAV1 | TOGGLE_GPS_DRIVES_NAV1 | GPS drives NAV1 (false = NAV radio) |

### Controls

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `controls.throttlePct` | number | % | GENERAL ENG THROTTLE LEVER POSITION:1 | THROTTLE_SET | Throttle lever position (assist command) |
| `controls.rudder` | number | % | RUDDER POSITION | RUDDER_SET | Rudder (assist command) |

### Brakes

| Key | Type | Unit | Read (SimVar) | Command | Description |
| --- | --- | --- | --- | --- | --- |
| `brakes.parking` | bool | — | BRAKE PARKING POSITION | PARKING_BRAKES | Parking brake |

## Variables with commands

These keys can be changed through `POST /api/sim/command` and the WebSocket
`command`. The value is coerced to the variable type; for events with a
parameter it is scaled (for example, percent → 0..16383).

| Key | Event | Parameter | Scale |
| --- | --- | --- | --- |
| `power.batteryMaster` | `TOGGLE_MASTER_BATTERY` | no | 1.0 |
| `power.avionicsMaster` | `TOGGLE_AVIONICS_MASTER` | no | 1.0 |
| `autopilot.headingBugDeg` | `HEADING_BUG_SET` | yes | 1.0 |
| `autopilot.master` | `AP_MASTER` | no | 1.0 |
| `autopilot.approachHold` | `AP_APR_HOLD` | no | 1.0 |
| `nav.gpsDrivesNav1` | `TOGGLE_GPS_DRIVES_NAV1` | no | 1.0 |
| `controls.throttlePct` | `THROTTLE_SET` | yes | 163.83 |
| `controls.rudder` | `RUDDER_SET` | yes | 163.83 |
| `brakes.parking` | `PARKING_BRAKES` | no | 1.0 |

## Custom variables `custom.*`

A profile can declare its own LVAR/RPN in the `variables` block; the key must
start with a lowercase segment (usually `custom.`) and must not collide with
built-in variables. Such a key appears in the frame as an ordinary variable.

Allowed kinds: bool, number, string; sources: lvar, rpn. Key format: `^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$`.

Example:

```json
{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",
  "name": "APU_BLEED", "initial": false }
```

Details are in [profile-schema.md](profile-schema.md#6-custom-variables-lvar--rpn).
