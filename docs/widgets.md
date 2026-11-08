# 🧩 Instrument Catalog

> This file is generated from `msfs_gateway/profiles.py` (types and required
> bindings) and the web client (options). Update:
> `python -m msfs_gateway.docsgen --write`.

Each instrument is an element of the profile's `widgets[]` array. The full
profile schema is in [profile-schema.md](profile-schema.md).

## Common structure

```json
{
  "id": "attitude-main",
  "type": "attitude",
  "label": "Attitude indicator",
  "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
  "layout": {
    "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
    "phone": { "x": 0.03, "y": 0.02, "w": 0.94, "h": 0.3 }
  },
  "options": { "unit": "FT", "decimals": 0 }
}
```

- `id` — a unique slug (`[a-z0-9][a-z0-9-]`), used in the editor
  and for binding events.
- `layout` — coordinates in panel fractions; `base` is required,
  `phone`, `tablet-sm`, `tablet-lg` are optional.
- `options` — an optional object that depends on the type.
- `command` — required for a toggle switch and a rotary selector (see below).

## Instrument types

| Type | Instrument | Required bindings | `command` | Main options |
| --- | --- | --- | --- | --- |
| `attitude` | Attitude indicator | `pitch`, `bank` | — | — |
| `gauge.radial` | Circular gauge | `value` | — | `min`*, `max`*, `redline`, `zones`, `majorTicks`, `minorTicks`, `decimals`, `unit` |
| `readout` | Digital readout | `value` | — | `unit`, `decimals`, `caption`, `alarm` |
| `switch.toggle` | Toggle switch | `state` | required | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | Rotary selector / encoder | `value` | required | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | Annunciator lights | `active` | — | `caption`, `tone`, `invert` |
| `vsi` | VSI | `value` | — | `limit` |
| `altimeter` | Altimeter | `value` | — | — |
| `heading` | Heading indicator | `heading` | — | — |

`*` next to an option means it is required. The other options have sensible
defaults and are used to configure the appearance.

## Type descriptions

### `attitude` — Attitude indicator

Attitude indicator: pitch and bank via `pitch`/`bank`, a bank scale, and a zero mark. There are no additional options.

Minimal example:

```json
{ "id": "attitude", "type": "attitude", "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `gauge.radial` — Circular gauge

Circular needle gauge: the `value` within the `min..max` range, tick marks, a red zone, a caption, and units.

| Option | Meaning | Required |
| --- | --- | --- |
| `min` | gauge minimum | yes |
| `max` | gauge maximum | yes |
| `redline` | red zone (within the min..max range) | no |
| `zones` | additional colored zones | no |
| `majorTicks` | number of major tick marks | no |
| `minorTicks` | number of minor tick marks | no |
| `decimals` | digits after the decimal point | no |
| `unit` | unit label | no |

Minimal example:

```json
{ "id": "speed", "type": "gauge.radial", "bindings": { "value": "speed.iasKt" }, "options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `readout` — Digital readout

Digital readout: formats `value` with the given number of digits, units, and a caption; it can highlight an alarm threshold.

| Option | Meaning | Required |
| --- | --- | --- |
| `unit` | units | no |
| `decimals` | digits after the decimal point | no |
| `caption` | caption above the value | no |
| `alarm` | alarm highlight threshold | no |

Minimal example:

```json
{ "id": "alt", "type": "readout", "bindings": { "value": "altitude.indicatedFt" }, "options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `switch.toggle` — Toggle switch

Toggle switch: shows a boolean `state` and sends the `command.key` command; the `set` action sends the opposite value, and `toggle` sends a toggle event.

| Option | Meaning | Required |
| --- | --- | --- |
| `caption` | toggle caption | no |
| `onLabel` | text for the on state | no |
| `offLabel` | text for the off state | no |

Minimal example:

```json
{ "id": "battery", "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" }, "command": { "key": "power.batteryMaster", "action": "set" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `knob.rotary` — Rotary selector / encoder

Rotary selector/encoder: rotation and swipes change `value` by `step` within the `min..max` range, sending a command with the new value.

| Option | Meaning | Required |
| --- | --- | --- |
| `min` | minimum | no |
| `max` | maximum | no |
| `step` | change step | no |
| `wrap` | loop the value | no |
| `unit` | units | no |
| `decimals` | digits after the decimal point | no |
| `caption` | caption | no |

Minimal example:

```json
{ "id": "hdg", "type": "knob.rotary", "bindings": { "value": "autopilot.headingBugDeg" }, "command": { "key": "autopilot.headingBugDeg", "action": "set" }, "options": { "min": 0, "max": 359, "step": 1, "wrap": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `annunciator` — Annunciator lights

Annunciator lights: light up when `active` is true; the caption, tone, and inversion are configured through options.

| Option | Meaning | Required |
| --- | --- | --- |
| `caption` | lamp caption | no |
| `tone` | glow color/tone | no |
| `invert` | invert the logic | no |

Minimal example:

```json
{ "id": "bus", "type": "annunciator", "bindings": { "active": "power.busVolts" }, "options": { "caption": "BUS OFF", "invert": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `vsi` — VSI

VSI: a vertical speed needle, with the gauge limited by `limit`, and labels in fpm.

| Option | Meaning | Required |
| --- | --- | --- |
| `limit` | gauge limit, fpm | no |

Minimal example:

```json
{ "id": "vsi", "type": "vsi", "bindings": { "value": "verticalSpeed.fpm" }, "options": { "limit": 2000 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `altimeter` — Altimeter

A three-pointer altimeter (hundreds/thousands/tens of thousands of feet) based on the `value`.

Minimal example:

```json
{ "id": "altimeter", "type": "altimeter", "bindings": { "value": "altitude.indicatedFt" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `heading` — Heading indicator

A heading indicator with a rotating compass card and a "bug"; the value is the magnetic heading in degrees.

Minimal example:

```json
{ "id": "heading", "type": "heading", "bindings": { "heading": "heading.magneticDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

## Commands from a toggle switch and a rotary selector

The `command` block describes what to send to the gateway:

| Field | Meaning |
| --- | --- |
| `key` | a variable with the "commands accepted" flag (see the telemetry catalog) |
| `action` | `set` — send a new value; `toggle` — a toggle event |
| `value` | for `set`: `true/false`/number; by default the opposite of the current value |

Toggle switch example:

```json
{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" } }
```

## Validation

- The type must be in the list above; the editor will not save an unknown type.
- The required `bindings` roles must reference existing telemetry keys.
- `layout.base` and the overrides must be rectangles within `0..1`
  (see the profile schema).
