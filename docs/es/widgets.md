# 🧩 Catálogo de instrumentos

> Este archivo se genera desde `msfs_gateway/profiles.py` (tipos y enlaces
> obligatorios) y desde el cliente web (opciones). Actualización:
> `python -m msfs_gateway.docsgen --write`.

Cada instrumento es un elemento del array `widgets[]` del perfil. El esquema
completo del perfil está en [profile-schema.md](profile-schema.md).

## Estructura común

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

- `id` — un slug único (`[a-z0-9][a-z0-9-]`), usado en el editor y para vincular
  eventos.
- `layout` — coordenadas en fracciones del panel; `base` es obligatorio, `phone`,
  `tablet-sm` y `tablet-lg` son opcionales.
- `options` — un objeto opcional que depende del tipo.
- `command` — obligatorio para un interruptor de palanca y un selector rotativo
  (véase más abajo).

## Tipos de instrumento

| Tipo | Instrumento | Enlaces obligatorios | `command` | Opciones principales |
| --- | --- | --- | --- | --- |
| `attitude` | Indicador de actitud | `pitch`, `bank` | — | — |
| `gauge.radial` | Escala circular | `value` | — | `min`*, `max`*, `redline`, `zones`, `majorTicks`, `minorTicks`, `decimals`, `unit` |
| `readout` | Lectura digital | `value` | — | `unit`, `decimals`, `caption`, `alarm` |
| `switch.toggle` | Interruptor de palanca | `state` | obligatorio | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | Selector rotativo / encoder | `value` | obligatorio | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | Luces anunciadoras | `active` | — | `caption`, `tone`, `invert` |
| `vsi` | VSI | `value` | — | `limit` |
| `altimeter` | Altímetro | `value` | — | — |
| `heading` | Indicador de rumbo | `heading` | — | — |

`*` junto a una opción significa que es obligatoria. Las demás opciones tienen
valores predeterminados razonables y se usan para configurar la apariencia.

## Descripciones de los tipos

### `attitude` — Indicador de actitud

Indicador de actitud: cabeceo y banqueo mediante `pitch`/`bank`, una escala de
banqueo y una marca de cero. No hay opciones adicionales.

Ejemplo mínimo:

```json
{ "id": "attitude", "type": "attitude", "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `gauge.radial` — Escala circular

Escala circular con aguja: el `value` dentro del rango `min..max`, marcas de
graduación, una zona roja, una leyenda y unidades.

| Opción | Significado | Obligatoria |
| --- | --- | --- |
| `min` | mínimo de la escala | sí |
| `max` | máximo de la escala | sí |
| `redline` | zona roja (dentro del rango min..max) | no |
| `zones` | zonas coloreadas adicionales | no |
| `majorTicks` | número de marcas mayores | no |
| `minorTicks` | número de marcas menores | no |
| `decimals` | dígitos tras el separador decimal | no |
| `unit` | etiqueta de unidad | no |

Ejemplo mínimo:

```json
{ "id": "speed", "type": "gauge.radial", "bindings": { "value": "speed.iasKt" }, "options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `readout` — Lectura digital

Lectura digital: formatea `value` con el número de dígitos indicado, unidades y
una leyenda; puede resaltar un umbral de alarma.

| Opción | Significado | Obligatoria |
| --- | --- | --- |
| `unit` | unidades | no |
| `decimals` | dígitos tras el separador decimal | no |
| `caption` | leyenda sobre el valor | no |
| `alarm` | umbral de resaltado de alarma | no |

Ejemplo mínimo:

```json
{ "id": "alt", "type": "readout", "bindings": { "value": "altitude.indicatedFt" }, "options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `switch.toggle` — Interruptor de palanca

Interruptor de palanca: muestra un `state` booleano y envía el comando
`command.key`; la acción `set` envía el valor opuesto, y `toggle` envía un evento
de alternancia.

| Opción | Significado | Obligatoria |
| --- | --- | --- |
| `caption` | leyenda del interruptor | no |
| `onLabel` | texto para el estado activado | no |
| `offLabel` | texto para el estado desactivado | no |

Ejemplo mínimo:

```json
{ "id": "battery", "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" }, "command": { "key": "power.batteryMaster", "action": "set" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `knob.rotary` — Selector rotativo / encoder

Selector rotativo/encoder: la rotación y los gestos de deslizamiento cambian
`value` en `step` dentro del rango `min..max`, enviando un comando con el nuevo
valor.

| Opción | Significado | Obligatoria |
| --- | --- | --- |
| `min` | mínimo | no |
| `max` | máximo | no |
| `step` | paso de cambio | no |
| `wrap` | recorrer el valor en bucle | no |
| `unit` | unidades | no |
| `decimals` | dígitos tras el separador decimal | no |
| `caption` | leyenda | no |

Ejemplo mínimo:

```json
{ "id": "hdg", "type": "knob.rotary", "bindings": { "value": "autopilot.headingBugDeg" }, "command": { "key": "autopilot.headingBugDeg", "action": "set" }, "options": { "min": 0, "max": 359, "step": 1, "wrap": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `annunciator` — Luces anunciadoras

Luces anunciadoras: se encienden cuando `active` es verdadero; la leyenda, el
tono y la inversión se configuran mediante opciones.

| Opción | Significado | Obligatoria |
| --- | --- | --- |
| `caption` | leyenda de la lámpara | no |
| `tone` | color/tono del brillo | no |
| `invert` | invertir la lógica | no |

Ejemplo mínimo:

```json
{ "id": "bus", "type": "annunciator", "bindings": { "active": "power.busVolts" }, "options": { "caption": "BUS OFF", "invert": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `vsi` — VSI

VSI: una aguja de velocidad vertical, con la escala limitada por `limit`, y
etiquetas en fpm.

| Opción | Significado | Obligatoria |
| --- | --- | --- |
| `limit` | límite de la escala, fpm | no |

Ejemplo mínimo:

```json
{ "id": "vsi", "type": "vsi", "bindings": { "value": "verticalSpeed.fpm" }, "options": { "limit": 2000 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `altimeter` — Altímetro

Un altímetro de tres agujas (centenas/millares/decenas de millar de pies)
basado en el `value`.

Ejemplo mínimo:

```json
{ "id": "altimeter", "type": "altimeter", "bindings": { "value": "altitude.indicatedFt" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `heading` — Indicador de rumbo

Un indicador de rumbo con una carta de brújula giratoria y un «bug»; el valor es
el rumbo magnético en grados.

Ejemplo mínimo:

```json
{ "id": "heading", "type": "heading", "bindings": { "heading": "heading.magneticDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

## Comandos desde un interruptor de palanca y un selector rotativo

El bloque `command` describe qué enviar al gateway:

| Campo | Significado |
| --- | --- |
| `key` | una variable con el indicador «acepta comandos» (véase el catálogo de telemetría) |
| `action` | `set` — enviar un nuevo valor; `toggle` — un evento de alternancia |
| `value` | para `set`: `true/false`/número; por defecto el opuesto del valor actual |

Ejemplo de interruptor de palanca:

```json
{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" } }
```

## Validación

- El tipo debe estar en la lista anterior; el editor no guardará un tipo
  desconocido.
- Los roles obligatorios de `bindings` deben referenciar claves de telemetría
  existentes.
- `layout.base` y las anulaciones deben ser rectángulos dentro de `0..1` (véase
  el esquema del perfil).
