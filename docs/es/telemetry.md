# 📊 Catálogo de variables de telemetría

> Este archivo se genera desde `msfs_gateway/telemetry.py`; no lo edites
> manualmente.
> Actualización: `python -m msfs_gateway.docsgen --write`.

El registro es la única fuente de verdad: los perfiles de panel vinculan los
instrumentos a estas claves, y el gateway lee las SimVar y envía comandos.

## Cómo leer la tabla

- **Clave** — el nombre de la variable en la trama de telemetría y en los
  `bindings` del perfil.
- **Tipo** — `number`, `bool` o `string`; `bool` llega en JSON como
  `true/false`, los números como `float`.
- **Lectura** — la SimVar de la que el gateway toma el valor (para `custom.*` no
  hay fuente: los lee el puente WASM según la descripción del perfil).
- **Comando** — el evento SimConnect usado para cambiar la variable; un guion
  significa «solo lectura».

## Variables por grupo

### Eléctrico y alimentación

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `power.batteryMaster` | bool | — | ELECTRICAL MASTER BATTERY | TOGGLE_MASTER_BATTERY | Interruptor principal de batería |
| `power.avionicsMaster` | bool | — | AVIONICS MASTER SWITCH | TOGGLE_AVIONICS_MASTER | Alimentación de aviónica |
| `power.busVolts` | number | V | ELECTRICAL MAIN BUS VOLTAGE | — | Tensión del bus principal |

### Motor

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `engine.rpm` | number | RPM | GENERAL ENG RPM:1 | — | RPM del motor |
| `engine.fuelFlowGph` | number | GPH | ENG FUEL FLOW GPH:1 | — | Consumo de combustible por hora |
| `engine.torquePct` | number | % | TURB ENG MAX TORQUE PERCENT:1 | — | Par del motor turbohélice |
| `engine.ittC` | number | °C | TURB ENG ITT:1 | — | Temperatura ITT |
| `engine.propRpm` | number | RPM | PROP RPM:1 | — | RPM de la hélice |
| `engine.n1Pct` | number | % | TURB ENG N1:1 | — | N1 del motor n.º 1 |
| `engine.n1Pct2` | number | % | TURB ENG N1:2 | — | N1 del motor n.º 2 |

### Actitud espacial

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `attitude.pitchDeg` | number | ° | PLANE PITCH DEGREES | — | Cabeceo |
| `attitude.bankDeg` | number | ° | PLANE BANK DEGREES | — | Banqueo |

### Altitud

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `altitude.indicatedFt` | number | FT | INDICATED ALTITUDE | — | Altitud indicada |

### Velocidad

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `speed.iasKt` | number | KT | AIRSPEED INDICATED | — | Velocidad indicada |

### VSI

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `verticalSpeed.fpm` | number | FPM | VERTICAL SPEED | — | Velocidad vertical |

### Rumbo

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `heading.magneticDeg` | number | ° | PLANE HEADING DEGREES MAGNETIC | — | Rumbo magnético |

### Flaps de ala

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `flaps.percent` | number | % | TRAILING EDGE FLAPS LEFT PERCENT | — | Posición de los flaps |

### Combustible

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `fuel.leftGal` | number | GAL | FUEL LEFT QUANTITY | — | Combustible del depósito izquierdo |
| `fuel.rightGal` | number | GAL | FUEL RIGHT QUANTITY | — | Combustible del depósito derecho |
| `fuel.totalGal` | number | GAL | — | — | Combustible total |

### Piloto automático

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `autopilot.headingBugDeg` | number | ° | AUTOPILOT HEADING LOCK DIR | HEADING_BUG_SET | Rumbo objetivo (bug de rumbo) |
| `autopilot.master` | bool | — | AUTOPILOT MASTER | AP_MASTER | Piloto automático conectado |
| `autopilot.approachHold` | bool | — | AUTOPILOT APPROACH HOLD | AP_APR_HOLD | Modo APR — comando de conexión |
| `autopilot.approach` | bool | — | AUTOPILOT APPROACH HOLD | — | Modo APR activo |

### Estado de la aeronave

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `aircraft.onGround` | bool | — | SIM ON GROUND | — | Aeronave en tierra |
| `aircraft.radioAltitudeFt` | number | FT | RADIO HEIGHT | — | Altitud por radio sobre la pista |
| `aircraft.title` | string | — | TITLE | — | Título de la aeronave en el simulador |

### Rodaje

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `groundSpeed.kt` | number | KT | GPS GROUND SPEED | — | Velocidad respecto al suelo |

### Navegación (ILS)

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `nav.localizer` | number | dots | NAV CDI:1 | — | Desviación del localizador |
| `nav.glideSlope` | number | ° | NAV GLIDE SLOPE ERROR | — | Desviación de la senda de planeo |
| `nav.locFlag` | bool | — | HSI CDI NEEDLE VALID | — | Localizador capturado |
| `nav.gsFlag` | bool | — | HSI GSI NEEDLE VALID | — | Senda de planeo capturada |

### Controles

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `controls.throttlePct` | number | % | GENERAL ENG THROTTLE LEVER POSITION:1 | THROTTLE_SET | Posición de la palanca de gases (comando del asistente) |
| `controls.rudder` | number | % | RUDDER POSITION | RUDDER_SET | Timón (comando del asistente) |

### Frenos

| Clave | Tipo | Unidad | Lectura (SimVar) | Comando | Descripción |
| --- | --- | --- | --- | --- | --- |
| `brakes.parking` | bool | — | BRAKE PARKING POSITION | PARKING_BRAKES | Freno de estacionamiento |

## Variables con comandos

Estas claves se pueden cambiar mediante `POST /api/sim/command` y el `command`
de WebSocket. El valor se convierte al tipo de la variable; para los eventos con
parámetro se escala (por ejemplo, porcentaje → 0..16383).

| Clave | Evento | Parámetro | Escala |
| --- | --- | --- | --- |
| `power.batteryMaster` | `TOGGLE_MASTER_BATTERY` | no | 1.0 |
| `power.avionicsMaster` | `TOGGLE_AVIONICS_MASTER` | no | 1.0 |
| `autopilot.headingBugDeg` | `HEADING_BUG_SET` | sí | 1.0 |
| `autopilot.master` | `AP_MASTER` | no | 1.0 |
| `autopilot.approachHold` | `AP_APR_HOLD` | no | 1.0 |
| `controls.throttlePct` | `THROTTLE_SET` | sí | 163.83 |
| `controls.rudder` | `RUDDER_SET` | sí | 163.83 |
| `brakes.parking` | `PARKING_BRAKES` | no | 1.0 |

## Variables personalizadas `custom.*`

Un perfil puede declarar sus propias LVAR/RPN en el bloque `variables`; la clave
debe empezar por un segmento en minúsculas (normalmente `custom.`) y no debe
colisionar con las variables integradas. Dicha clave aparece en la trama como una
variable ordinaria.

Tipos admitidos: bool, number, string; fuentes: lvar, rpn. Formato de clave:
`^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$`.

Ejemplo:

```json
{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",
  "name": "APU_BLEED", "initial": false }
```

Los detalles están en
[profile-schema.md](profile-schema.md#6-variables-personalizadas-lvar--rpn).
