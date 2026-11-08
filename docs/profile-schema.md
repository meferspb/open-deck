# 📄 Aircraft JSON Profile Schema

A profile is a single file `profiles/{id}.json` that describes an instrument
panel declaratively. The host validates it strictly
(`msfs_gateway/profiles.py`), and the client renders it "on the fly".

All sizes and coordinates are **panel fractions (0..1)**, not pixels: one profile
works on a phone and on a large tablet.

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk SP",
  "icao": "C172",
  "revision": 3,
  "description": "…",
  "sim": { "match": { "title": "Cessna Skyhawk*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S · OPEN DECK" },
  "widgets": [ … ]
}
```

---

## 1. Top-level fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `schemaVersion` | int | yes | always `1` |
| `id` | slug | yes | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `name` | string | yes | name for the UI |
| `icao` | string | no | 2–4 character code (e.g. `C172`) |
| `revision` | int ≥ 1 | no | profile version |
| `description` | string | no | explanation |
| `sim.match` | object | no | aircraft autodetection rules |
| `panel` | object | yes | background, grid, caption |
| `widgets` | array 1..64 | yes | instruments |
| `variables` | array 0..64 | no | custom LVAR/RPN (see §6) |

`sim.match.title` is a glob over the aircraft name in the simulator
(case-insensitive), for example `"Cessna Skyhawk*"` will pick up any livery and
name variant. `sim.match.atcModel` is a glob over the ATC model (`C172`), used
if the name did not match. The client picks up the profile automatically as soon
as the gateway reads `TITLE` and `ATC MODEL` through SimConnect; a manual
selection from the list remains in effect until a different aircraft is loaded
in the simulator.

---

## 2. `panel`

| Field | Type | Description |
| --- | --- | --- |
| `background` | color `#RGB(A)` / `#RRGGBB(AA)` | panel background |
| `gridSize` | int | background grid step in "units" (optional) |
| `footer` | string | caption at the bottom of the panel |

---

## 3. `widgets[]` — common structure

```json
{
  "id": "battery-switch",
  "type": "switch.toggle",
  "label": "Battery",
  "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" },
  "options": { "caption": "BATTERY", "onLabel": "ON", "offLabel": "OFF" },
  "layout": {
    "base": { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
    "phone": { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 }
  }
}
```

| Field | Purpose |
| --- | --- |
| `id` | unique widget slug |
| `type` | type from the table below |
| `label` | aria label / caption |
| `bindings` | bindings to canonical telemetry keys |
| `command` | for control instruments — how to change the variable |
| `options` | type-dependent settings (gauges, labels, tones) |
| `layout` | geometry (see §4) |

### `bindings`

Keys come from the canonical registry `msfs_gateway/telemetry.py` (flat, with
dots): `power.batteryMaster`, `attitude.pitchDeg`, `engine.rpm`,
`speed.iasKt`, `autopilot.headingBugDeg`, etc. The server rejects unknown keys
during validation. The full list with types and units is in
[telemetry.md](telemetry.md); descriptions of instrument types and options are
in [widgets.md](widgets.md).

---

## 4. `layout` — form-factor adaptivity

```json
"layout": {
  "base":       { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "phone":      { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 },
  "tablet-sm":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "tablet-lg":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 }
}
```

- `base` is required; `phone` / `tablet-sm` / `tablet-lg` are optional
  **overrides** that are merged on top of `base` (you can specify only the
  fields that differ).
- `x`, `y` — top-left corner; `w`, `h` — width/height. All in 0..1 fractions,
  `w,h > 0`, and the rectangle must not extend beyond the panel bounds.
- The values `x,y,w,h` can also be "additional" — the client derives the text
  size from the instrument's dimensions through the CSS variables `--w`/`--h`.

---

## 5. Instrument types

| `type` | What it does | `bindings` (required roles) | `command` | Key `options` |
| --- | --- | --- | --- | --- |
| `attitude` | attitude indicator (canvas) | `pitch`, `bank` | — | — |
| `gauge.radial` | circular gauge with a needle | `value` | — | `min`, `max`, `redline`, `unit`, `decimals`, `majorTicks`, `minorTicks`, `zones[]` |
| `readout` | digital readout | `value` | — | `caption`, `unit`, `decimals`, `alarm.{below,above}` |
| `switch.toggle` | toggle switch | `state` | `{key, action: set|toggle}` | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | rotary selector (swipe/wheel/arrows) | `value` | `{key, action: set}` | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | annunciator light | `active` | — | `caption`, `tone: ok|warn|danger`, `invert` |
| `vsi` | VSI (canvas) | `value` | — | `limit` (2000 FPM by default) |
| `altimeter` | three-pointer altimeter | `value` | — | — |
| `heading` | heading indicator with a compass card and a "bug" | `heading` (optional `bug`) | — | — |

### `options` by type

- **`gauge.radial`**: `min`/`max` — gauge range; `redline` — a red arc from
  `redline` to `max`; `zones` — an array of `{from, to, tone}` for colored sectors
  (`ok`/`warn`/`danger`); `majorTicks`/`minorTicks` — tick marks; `decimals` —
  digits in the numeric value; `unit` — unit label.
- **`readout`**: `caption` — heading; `unit` — unit; `decimals`; `alarm` —
  highlight thresholds `{below, above}`.
- **`switch.toggle`**: `caption`, `onLabel`/`offLabel` — state texts;
  `command.action = "toggle"` — send a toggle without an explicit value.
- **`knob.rotary`**: `min`/`max`/`step`/`wrap` — range and step; `unit`,
  `decimals` — display; `wrap = true` — loop the range (for example 0–359°).
- **`annunciator`**: `tone` — lamp color; `invert = true` — light up on a false
  value (a "BUS OFF" indicator when power is off).
- **`vsi`**: `limit` — gauge limit in feet/min (2000 by default); the needle
  goes to ±90° when the limit is reached.
- **`heading`**: the optional `bug` binding draws the target heading
  (`autopilot.headingBugDeg`) as a separate pointer.
- **`attitude`**: no options; the caption comes from the instrument's `label`.
- Unknown options are not rejected (for compatibility) but are not used by the
  client either — check with [widgets.md](widgets.md).

### `command`

```json
"command": { "key": "power.batteryMaster", "action": "set" }
```

`key` must be a **writable** variable (one that has a `sim_event`).
`action`: `set` — set the value from `value`; `toggle` — toggle it.

---

## 6. Custom variables: LVAR / RPN

Default SimVars cover the Cessna 172 and most simple aircraft, but PMDG, Fenix,
FlyByWire, and iniBuilds keep state in their own variables. A profile can
declare them in the `variables` block, and widgets can reference the resulting
keys (`custom.*`) like ordinary ones.

```json
"variables": [
  {
    "key": "custom.fuelLbs",
    "kind": "number",
    "source": "lvar",
    "name": "PMDG_FUEL_LBS",
    "label": "Fuel (pounds)",
    "unit": "LBS",
    "initial": 1200
  },
  {
    "key": "custom.apuOn",
    "kind": "bool",
    "source": "lvar",
    "name": "PMDG_APU_ON"
  },
  {
    "key": "custom.cabinAlt",
    "kind": "number",
    "source": "rpn",
    "expression": "(A:CABIN ALTITUDE, feet)"
  }
]
```

| Field | Description |
| --- | --- |
| `key` | key of the form `custom.fuelLbs` (first segment lowercase, then camelCase); must not collide with a built-in variable |
| `kind` | `number` / `bool` / `string` |
| `source` | `lvar` — read an LVAR through the WASM bridge; `rpn` — compute with an RPN script |
| `name` | LVAR name (for `source: lvar`), up to 127 UTF-8 bytes |
| `expression` | RPN script (for `source: rpn`); the response is parsed into a number/flag |
| `initial` | initial value for mock mode (without MSFS) |
| `label`, `unit` | labels for the editor |

Widget bindings are validated against **built-in + declared** keys:

```json
{ "id": "fuel", "type": "readout", "bindings": { "value": "custom.fuelLbs" } }
```

How it works:

- in **mock mode** the provider substitutes `initial` — the panel comes alive
  without MSFS;
- in **a real flight** the values are read by `WasmBridge` (`read_specs`) through
  the MobiFlight/SimBridge WASM module; the bus polls them at most 4 times per
  second and caches them between frames;
- if the bridge is not connected, the keys are simply absent from the frame —
  the instruments show "--" (substituting 0.0 would be a lie).

Example profile: [`profiles/demo-lvar-panel.json`](../profiles/demo-lvar-panel.json).

---

## 7. Complete example (Cessna 172S)

See [`profiles/cessna-172-skyhawk.json`](../profiles/cessna-172-skyhawk.json) —
11 instruments: attitude indicator, speed/altitude/turn (readout), tachometer and
fuel (gauge), battery/avionics switches, BUS OFF lamp, flaps, heading bug setter
(knob). The second example is `profiles/piper-pa28-archer-ii.json` (only
`layout.base`, testing the fallback layout).

---

## 8. Backward compatibility with the v0 format

The original format from the specification (`bindings[]` with pixel `position`
and `sim_var`) is supported through the `msfs_gateway/legacy.py` adapter: it is
translated into the internal format on load, and coordinates are recalculated
from pixels into panel fractions (the default canvas is 1280×800 or from
`layout.canvas`/`target_aspect_ratio`). Saving through `PUT /api/profiles/{id}`
writes the internal format.
