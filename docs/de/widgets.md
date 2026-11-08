# 🧩 Instrumentenkatalog

> Diese Datei wird aus `msfs_gateway/profiles.py` (Typen und erforderliche
> Bindungen) und dem Web-Client (Optionen) generiert. Aktualisieren:
> `python -m msfs_gateway.docsgen --write`.

Jedes Instrument ist ein Element des Arrays `widgets[]` im Profil. Das
vollständige Profil-Schema steht in [profile-schema.md](profile-schema.md).

## Allgemeiner Aufbau

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

- `id` — ein eindeutiger Slug (`[a-z0-9][a-z0-9-]`), verwendet im Editor
  und zum Binden von Ereignissen.
- `layout` — Koordinaten in Panel-Bruchteilen; `base` ist erforderlich, `phone`,
  `tablet-sm`, `tablet-lg` sind optional.
- `options` — ein optionales Objekt, das vom Typ abhängt.
- `command` — erforderlich für einen Kippschalter und einen Drehschalter (siehe
  unten).

## Instrumententypen

| Typ | Instrument | Erforderliche Bindungen | `command` | Wichtigste Optionen |
| --- | --- | --- | --- | --- |
| `attitude` | Künstlicher Horizont | `pitch`, `bank` | — | — |
| `gauge.radial` | Rundskala | `value` | — | `min`*, `max`*, `redline`, `zones`, `majorTicks`, `minorTicks`, `decimals`, `unit` |
| `readout` | Digitalanzeige | `value` | — | `unit`, `decimals`, `caption`, `alarm` |
| `switch.toggle` | Kippschalter | `state` | erforderlich | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | Drehschalter / Encoder | `value` | erforderlich | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | Warnleuchten | `active` | — | `caption`, `tone`, `invert` |
| `vsi` | Variometer | `value` | — | `limit` |
| `altimeter` | Höhenmesser | `value` | — | — |
| `heading` | Kursanzeiger | `heading` | — | — |

`*` neben einer Option bedeutet, dass sie erforderlich ist. Die übrigen
Optionen haben sinnvolle Standardwerte und dienen der Konfiguration des
Erscheinungsbilds.

## Typbeschreibungen

### `attitude` — Künstlicher Horizont

Künstlicher Horizont: Nick- und Rollwinkel über `pitch`/`bank`, eine Rollskala
und eine Nullmarke. Es gibt keine zusätzlichen Optionen.

Minimales Beispiel:

```json
{ "id": "attitude", "type": "attitude", "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `gauge.radial` — Rundskala

Rundes Zeigerinstrument: der `value` innerhalb des Bereichs `min..max`,
Teilstriche, eine rote Zone, eine Beschriftung und Einheiten.

| Option | Bedeutung | Erforderlich |
| --- | --- | --- |
| `min` | Skalenminimum | ja |
| `max` | Skalenmaximum | ja |
| `redline` | rote Zone (innerhalb des Bereichs min..max) | nein |
| `zones` | zusätzliche farbige Zonen | nein |
| `majorTicks` | Anzahl der Hauptteilstriche | nein |
| `minorTicks` | Anzahl der Nebenteilstriche | nein |
| `decimals` | Nachkommastellen | nein |
| `unit` | Einheitenbeschriftung | nein |

Minimales Beispiel:

```json
{ "id": "speed", "type": "gauge.radial", "bindings": { "value": "speed.iasKt" }, "options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `readout` — Digitalanzeige

Digitalanzeige: formatiert `value` mit der angegebenen Stellenzahl, Einheiten
und einer Beschriftung; sie kann einen Alarmschwellenwert hervorheben.

| Option | Bedeutung | Erforderlich |
| --- | --- | --- |
| `unit` | Einheiten | nein |
| `decimals` | Nachkommastellen | nein |
| `caption` | Beschriftung über dem Wert | nein |
| `alarm` | Schwelle für Alarmhervorhebung | nein |

Minimales Beispiel:

```json
{ "id": "alt", "type": "readout", "bindings": { "value": "altitude.indicatedFt" }, "options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `switch.toggle` — Kippschalter

Kippschalter: zeigt einen booleschen `state` und sendet den Befehl
`command.key`; die Aktion `set` sendet den entgegengesetzten Wert, und `toggle`
sendet ein Umschalt-Ereignis.

| Option | Bedeutung | Erforderlich |
| --- | --- | --- |
| `caption` | Beschriftung des Schalters | nein |
| `onLabel` | Text für den Ein-Zustand | nein |
| `offLabel` | Text für den Aus-Zustand | nein |

Minimales Beispiel:

```json
{ "id": "battery", "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" }, "command": { "key": "power.batteryMaster", "action": "set" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `knob.rotary` — Drehschalter / Encoder

Drehschalter/Encoder: Drehung und Wischgesten ändern `value` um `step` innerhalb
des Bereichs `min..max` und senden einen Befehl mit dem neuen Wert.

| Option | Bedeutung | Erforderlich |
| --- | --- | --- |
| `min` | Minimum | nein |
| `max` | Maximum | nein |
| `step` | Änderungsschritt | nein |
| `wrap` | Wert umlaufen lassen | nein |
| `unit` | Einheiten | nein |
| `decimals` | Nachkommastellen | nein |
| `caption` | Beschriftung | nein |

Minimales Beispiel:

```json
{ "id": "hdg", "type": "knob.rotary", "bindings": { "value": "autopilot.headingBugDeg" }, "command": { "key": "autopilot.headingBugDeg", "action": "set" }, "options": { "min": 0, "max": 359, "step": 1, "wrap": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `annunciator` — Warnleuchten

Warnleuchten: Leuchten auf, wenn `active` wahr ist; Beschriftung, Farbton und
Invertierung werden über Optionen konfiguriert.

| Option | Bedeutung | Erforderlich |
| --- | --- | --- |
| `caption` | Beschriftung der Leuchte | nein |
| `tone` | Glühfarbe/Farbton | nein |
| `invert` | Logik invertieren | nein |

Minimales Beispiel:

```json
{ "id": "bus", "type": "annunciator", "bindings": { "active": "power.busVolts" }, "options": { "caption": "BUS OFF", "invert": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `vsi` — Variometer

Variometer: eine Vertikalgeschwindigkeitsnadel, wobei die Skala durch `limit`
begrenzt wird, mit Beschriftungen in fpm.

| Option | Bedeutung | Erforderlich |
| --- | --- | --- |
| `limit` | Skalengrenze, fpm | nein |

Minimales Beispiel:

```json
{ "id": "vsi", "type": "vsi", "bindings": { "value": "verticalSpeed.fpm" }, "options": { "limit": 2000 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `altimeter` — Höhenmesser

Ein Dreizeiger-Höhenmesser (Hunderter-/Tausender-/Zehntausender-Fuß) auf Basis
von `value`.

Minimales Beispiel:

```json
{ "id": "altimeter", "type": "altimeter", "bindings": { "value": "altitude.indicatedFt" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `heading` — Kursanzeiger

Ein Kursanzeiger mit drehbarer Kompassrose und einem „Bug"; der Wert ist der
magnetische Kurs in Grad.

Minimales Beispiel:

```json
{ "id": "heading", "type": "heading", "bindings": { "heading": "heading.magneticDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

## Befehle von Kippschalter und Drehschalter

Der Block `command` beschreibt, was an das Gateway gesendet werden soll:

| Feld | Bedeutung |
| --- | --- |
| `key` | eine Variable mit dem Flag „Befehle akzeptiert" (siehe Telemetrie-Katalog) |
| `action` | `set` — einen neuen Wert senden; `toggle` — ein Umschalt-Ereignis |
| `value` | für `set`: `true/false`/Zahl; standardmäßig der entgegengesetzte Wert des aktuellen Werts |

Beispiel für einen Kippschalter:

```json
{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" } }
```

## Validierung

- Der Typ muss in der obigen Liste enthalten sein; der Editor speichert keinen
  unbekannten Typ.
- Die erforderlichen `bindings`-Rollen müssen auf vorhandene Telemetrie-
  Schlüssel verweisen.
- `layout.base` und die Überschreibungen müssen Rechtecke innerhalb von `0..1`
  sein (siehe Profil-Schema).
