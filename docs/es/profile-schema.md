# 📄 Esquema JSON del perfil de aeronave

Un perfil es un único archivo `profiles/{id}.json` que describe un panel de
instrumentos de forma declarativa. El host lo valida estrictamente
(`msfs_gateway/profiles.py`), y el cliente lo renderiza «al vuelo».

Todos los tamaños y coordenadas son **fracciones del panel (0..1)**, no píxeles:
un perfil funciona en un teléfono y en una tableta grande.

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

## 1. Campos de nivel superior

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `schemaVersion` | int | sí | siempre `1` |
| `id` | slug | sí | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `name` | string | sí | nombre para la interfaz |
| `icao` | string | no | código de 2–4 caracteres (p. ej. `C172`) |
| `revision` | int ≥ 1 | no | versión del perfil |
| `description` | string | no | explicación |
| `sim.match` | object | no | reglas de autodetección de aeronave |
| `panel` | object | sí | fondo, rejilla, pie de página |
| `widgets` | array 1..64 | sí | instrumentos |
| `variables` | array 0..64 | no | LVAR/RPN personalizadas (véase §6) |

`sim.match.title` es un glob sobre el nombre de la aeronave en el simulador (sin
distinguir mayúsculas y minúsculas), por ejemplo `"Cessna Skyhawk*"` capturará
cualquier librea y variante de nombre. `sim.match.atcModel` es un glob sobre el
modelo ATC (`C172`), que se usa si el nombre no coincidió. El cliente selecciona
el perfil automáticamente en cuanto el gateway lee `TITLE` y `ATC MODEL` a
través de SimConnect; una selección manual de la lista permanece vigente hasta
que se carga una aeronave diferente en el simulador.

---

## 2. `panel`

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `background` | color `#RGB(A)` / `#RRGGBB(AA)` | fondo del panel |
| `gridSize` | int | paso de la rejilla de fondo en «unidades» (opcional) |
| `footer` | string | leyenda en la parte inferior del panel |

---

## 3. `widgets[]` — estructura común

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

| Campo | Propósito |
| --- | --- |
| `id` | slug único del widget |
| `type` | tipo de la tabla siguiente |
| `label` | etiqueta aria / leyenda |
| `bindings` | enlaces a claves canónicas de telemetría |
| `command` | para instrumentos de control — cómo cambiar la variable |
| `options` | ajustes dependientes del tipo (escalas, etiquetas, tonos) |
| `layout` | geometría (véase §4) |

### `bindings`

Las claves provienen del registro canónico `msfs_gateway/telemetry.py` (planas,
con puntos): `power.batteryMaster`, `attitude.pitchDeg`, `engine.rpm`,
`speed.iasKt`, `autopilot.headingBugDeg`, etc. El servidor rechaza las claves
desconocidas durante la validación. La lista completa con tipos y unidades está
en [telemetry.md](telemetry.md); las descripciones de los tipos de instrumento y
las opciones están en [widgets.md](widgets.md).

---

## 4. `layout` — adaptabilidad por factor de forma

```json
"layout": {
  "base":       { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "phone":      { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 },
  "tablet-sm":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "tablet-lg":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 }
}
```

- `base` es obligatorio; `phone` / `tablet-sm` / `tablet-lg` son **anulaciones**
  opcionales que se combinan sobre `base` (puedes especificar solo los campos
  que difieren).
- `x`, `y` — esquina superior izquierda; `w`, `h` — ancho/alto. Todo en
  fracciones 0..1, `w,h > 0`, y el rectángulo no debe extenderse más allá de los
  límites del panel.
- Los valores `x,y,w,h` también pueden ser «adicionales»: el cliente deriva el
  tamaño del texto a partir de las dimensiones del instrumento mediante las
  variables CSS `--w`/`--h`.

---

## 5. Tipos de instrumento

| `type` | Qué hace | `bindings` (roles obligatorios) | `command` | `options` principales |
| --- | --- | --- | --- | --- |
| `attitude` | indicador de actitud (canvas) | `pitch`, `bank` | — | — |
| `gauge.radial` | escala circular con aguja | `value` | — | `min`, `max`, `redline`, `unit`, `decimals`, `majorTicks`, `minorTicks`, `zones[]` |
| `readout` | lectura digital | `value` | — | `caption`, `unit`, `decimals`, `alarm.{below,above}` |
| `switch.toggle` | interruptor de palanca | `state` | `{key, action: set|toggle}` | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | selector rotativo (gestos/rueda/flechas) | `value` | `{key, action: set}` | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | luz anunciadora | `active` | — | `caption`, `tone: ok|warn|danger`, `invert` |
| `vsi` | VSI (canvas) | `value` | — | `limit` (2000 FPM por defecto) |
| `altimeter` | altímetro de tres agujas | `value` | — | — |
| `heading` | indicador de rumbo con carta de brújula y «bug» | `heading` (`bug` opcional) | — | — |

### `options` por tipo

- **`gauge.radial`**: `min`/`max` — rango de la escala; `redline` — un arco rojo
  desde `redline` hasta `max`; `zones` — un array de `{from, to, tone}` para
  sectores coloreados (`ok`/`warn`/`danger`); `majorTicks`/`minorTicks` — marcas
  de graduación; `decimals` — dígitos del valor numérico; `unit` — etiqueta de
  unidad.
- **`readout`**: `caption` — encabezado; `unit` — unidad; `decimals`; `alarm` —
  umbrales de resaltado `{below, above}`.
- **`switch.toggle`**: `caption`, `onLabel`/`offLabel` — textos de estado;
  `command.action = "toggle"` — enviar un toggle sin un valor explícito.
- **`knob.rotary`**: `min`/`max`/`step`/`wrap` — rango y paso; `unit`,
  `decimals` — visualización; `wrap = true` — recorrer el rango en bucle (por
  ejemplo 0–359°).
- **`annunciator`**: `tone` — color de la lámpara; `invert = true` — encenderse
  con un valor falso (un indicador «BUS OFF» cuando la alimentación está
  apagada).
- **`vsi`**: `limit` — límite de la escala en pies/min (2000 por defecto); la
  aguja llega a ±90° cuando se alcanza el límite.
- **`heading`**: el enlace opcional `bug` dibuja el rumbo objetivo
  (`autopilot.headingBugDeg`) como un puntero separado.
- **`attitude`**: sin opciones; la leyenda proviene del `label` del instrumento.
- Las opciones desconocidas no se rechazan (por compatibilidad), pero el cliente
  tampoco las usa — compruébalo con [widgets.md](widgets.md).

### `command`

```json
"command": { "key": "power.batteryMaster", "action": "set" }
```

`key` debe ser una variable **escribible** (una que tenga `sim_event`).
`action`: `set` — establecer el valor de `value`; `toggle` — alternarlo.

---

## 6. Variables personalizadas: LVAR / RPN

Las SimVar predeterminadas cubren la Cessna 172 y la mayoría de aeronaves
simples, pero PMDG, Fenix, FlyByWire e iniBuilds mantienen su estado en variables
propias. Un perfil puede declararlas en el bloque `variables`, y los widgets
pueden referenciar las claves resultantes (`custom.*`) como las ordinarias.

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

| Campo | Descripción |
| --- | --- |
| `key` | clave con la forma `custom.fuelLbs` (primer segmento en minúsculas, luego camelCase); no debe colisionar con una variable integrada |
| `kind` | `number` / `bool` / `string` |
| `source` | `lvar` — leer una LVAR a través del puente WASM; `rpn` — calcular con un script RPN |
| `name` | nombre de la LVAR (para `source: lvar`), hasta 127 bytes UTF-8 |
| `expression` | script RPN (para `source: rpn`); la respuesta se convierte en número/indicador |
| `initial` | valor inicial para el modo mock (sin MSFS) |
| `label`, `unit` | etiquetas para el editor |

Los enlaces de los widgets se validan contra las claves **integradas +
declaradas**:

```json
{ "id": "fuel", "type": "readout", "bindings": { "value": "custom.fuelLbs" } }
```

Cómo funciona:

- en **modo mock** el proveedor sustituye `initial` — el panel cobra vida sin
  MSFS;
- en **un vuelo real** los valores los lee `WasmBridge` (`read_specs`) a través
  del módulo WASM de MobiFlight/SimBridge; el bus los consulta como máximo 4
  veces por segundo y los almacena en caché entre tramas;
- si el puente no está conectado, las claves simplemente no aparecen en la
  trama — los instrumentos muestran «--» (sustituir 0.0 sería mentir).

Perfil de ejemplo:
[`profiles/demo-lvar-panel.json`](../../profiles/demo-lvar-panel.json).

---

## 7. Ejemplo completo (Cessna 172S)

Véase [`profiles/cessna-172-skyhawk.json`](../../profiles/cessna-172-skyhawk.json) —
11 instrumentos: indicador de actitud, velocidad/altitud/viraje (lectura),
tacómetro y combustible (escala), interruptores de batería/aviónica, lámpara BUS
OFF, flaps, ajuste del bug de rumbo (knob). El segundo ejemplo es
`profiles/piper-pa28-archer-ii.json` (solo `layout.base`, prueba del diseño de
reserva).

---

## 8. Compatibilidad con el formato v0

El formato original de la especificación (`bindings[]` con `position` en píxeles
y `sim_var`) se admite a través del adaptador `msfs_gateway/legacy.py`: se
traduce al formato interno al cargar, y las coordenadas se recalculan de píxeles
a fracciones del panel (el canvas predeterminado es 1280×800 o el indicado por
`layout.canvas`/`target_aspect_ratio`). El guardado mediante
`PUT /api/profiles/{id}` escribe el formato interno.
