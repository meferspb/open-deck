# 📄 JSON-Schema für Flugzeugprofile

Ein Profil ist eine einzelne Datei `profiles/{id}.json`, die eine
Instrumententafel deklarativ beschreibt. Der Host validiert sie streng
(`msfs_gateway/profiles.py`), und der Client rendert sie „on the fly".

Alle Größen und Koordinaten sind **Panel-Bruchteile (0..1)**, keine Pixel: Ein
Profil funktioniert auf einem Smartphone und auf einem großen Tablet.

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

## 1. Felder der obersten Ebene

| Feld | Typ | Erforderlich | Beschreibung |
| --- | --- | --- | --- |
| `schemaVersion` | int | ja | immer `1` |
| `id` | slug | ja | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `name` | string | ja | Name für die UI |
| `icao` | string | nein | 2–4-stelliger Code (z. B. `C172`) |
| `revision` | int ≥ 1 | nein | Profilversion |
| `description` | string | nein | Erläuterung |
| `sim.match` | object | nein | Regeln zur automatischen Flugzeugerkennung |
| `panel` | object | ja | Hintergrund, Raster, Beschriftung |
| `widgets` | array 1..64 | ja | Instrumente |
| `variables` | array 0..64 | nein | benutzerdefinierte LVAR/RPN (siehe §6) |

`sim.match.title` ist ein Glob über den Flugzeugnamen im Simulator (ohne
Groß-/Kleinschreibung), zum Beispiel erfasst `"Cessna Skyhawk*"` jede Lackierung
und Namensvariante. `sim.match.atcModel` ist ein Glob über das ATC-Modell
(`C172`), der verwendet wird, wenn der Name nicht gepasst hat. Der Client
übernimmt das Profil automatisch, sobald das Gateway `TITLE` und `ATC MODEL`
über SimConnect liest; eine manuelle Auswahl aus der Liste bleibt wirksam, bis
im Simulator ein anderes Flugzeug geladen wird.

---

## 2. `panel`

| Feld | Typ | Beschreibung |
| --- | --- | --- |
| `background` | Farbe `#RGB(A)` / `#RRGGBB(AA)` | Panel-Hintergrund |
| `gridSize` | int | Rasterschritt des Hintergrunds in „Einheiten" (optional) |
| `footer` | string | Beschriftung am unteren Rand des Panels |

---

## 3. `widgets[]` — allgemeiner Aufbau

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

| Feld | Zweck |
| --- | --- |
| `id` | eindeutiger Widget-Slug |
| `type` | Typ aus der folgenden Tabelle |
| `label` | Aria-Label / Beschriftung |
| `bindings` | Bindungen an kanonische Telemetrie-Schlüssel |
| `command` | für Steuerinstrumente — wie die Variable geändert wird |
| `options` | typabhängige Einstellungen (Skalen, Labels, Farbtöne) |
| `layout` | Geometrie (siehe §4) |

### `bindings`

Die Schlüssel stammen aus dem kanonischen Register `msfs_gateway/telemetry.py`
(flach, mit Punkten): `power.batteryMaster`, `attitude.pitchDeg`, `engine.rpm`,
`speed.iasKt`, `autopilot.headingBugDeg` usw. Der Server weist unbekannte
Schlüssel während der Validierung zurück. Die vollständige Liste mit Typen und
Einheiten steht in [telemetry.md](telemetry.md); Beschreibungen der
Instrumententypen und Optionen in [widgets.md](widgets.md).

---

## 4. `layout` — Formfaktor-Adaptivität

```json
"layout": {
  "base":       { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "phone":      { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 },
  "tablet-sm":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "tablet-lg":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 }
}
```

- `base` ist erforderlich; `phone` / `tablet-sm` / `tablet-lg` sind optionale
  **Überschreibungen**, die über `base` gelegt werden (Sie können nur die
  abweichenden Felder angeben).
- `x`, `y` — obere linke Ecke; `w`, `h` — Breite/Höhe. Alles in 0..1-Bruchteilen,
  `w,h > 0`, und das Rechteck darf die Panel-Grenzen nicht überschreiten.
- Die Werte `x,y,w,h` können auch „zusätzlich" sein — der Client leitet die
  Textgröße aus den Abmessungen des Instruments über die CSS-Variablen `--w`/
  `--h` ab.

---

## 5. Instrumententypen

| `type` | Was es tut | `bindings` (erforderliche Rollen) | `command` | Wichtige `options` |
| --- | --- | --- | --- | --- |
| `attitude` | Künstlicher Horizont (Canvas) | `pitch`, `bank` | — | — |
| `gauge.radial` | Rundskala mit Nadel | `value` | — | `min`, `max`, `redline`, `unit`, `decimals`, `majorTicks`, `minorTicks`, `zones[]` |
| `readout` | Digitalanzeige | `value` | — | `caption`, `unit`, `decimals`, `alarm.{below,above}` |
| `switch.toggle` | Kippschalter | `state` | `{key, action: set|toggle}` | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | Drehschalter (Wischen/Mausrad/Pfeile) | `value` | `{key, action: set}` | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | Warnleuchte | `active` | — | `caption`, `tone: ok|warn|danger`, `invert` |
| `vsi` | Variometer (Canvas) | `value` | — | `limit` (standardmäßig 2000 FPM) |
| `altimeter` | Dreizeiger-Höhenmesser | `value` | — | — |
| `heading` | Kursanzeiger mit Kompassrose und „Bug" | `heading` (optional `bug`) | — | — |

### `options` nach Typ

- **`gauge.radial`**: `min`/`max` — Skalenbereich; `redline` — ein roter Bogen von
  `redline` bis `max`; `zones` — ein Array von `{from, to, tone}` für farbige
  Sektoren (`ok`/`warn`/`danger`); `majorTicks`/`minorTicks` — Teilstriche;
  `decimals` — Stellen im numerischen Wert; `unit` — Einheitenbeschriftung.
- **`readout`**: `caption` — Überschrift; `unit` — Einheit; `decimals`;
  `alarm` — Hervorhebungsschwellen `{below, above}`.
- **`switch.toggle`**: `caption`, `onLabel`/`offLabel` — Zustandstexte;
  `command.action = "toggle"` — Umschalten ohne expliziten Wert senden.
- **`knob.rotary`**: `min`/`max`/`step`/`wrap` — Bereich und Schritt; `unit`,
  `decimals` — Anzeige; `wrap = true` — den Bereich umlaufen lassen (zum
  Beispiel 0–359°).
- **`annunciator`**: `tone` — Lampenfarbe; `invert = true` — bei einem falschen
  Wert leuchten (eine „BUS OFF"-Anzeige bei fehlender Stromversorgung).
- **`vsi`**: `limit` — Skalengrenze in Fuß/min (standardmäßig 2000); die Nadel
  geht auf ±90°, wenn die Grenze erreicht ist.
- **`heading`**: Die optionale Bindung `bug` zeichnet den Zielkurs
  (`autopilot.headingBugDeg`) als separaten Zeiger.
- **`attitude`**: keine Optionen; die Beschriftung stammt aus dem `label` des
  Instruments.
- Unbekannte Optionen werden nicht zurückgewiesen (aus Kompatibilitätsgründen),
  aber auch nicht vom Client verwendet — prüfen Sie mit [widgets.md](widgets.md).

### `command`

```json
"command": { "key": "power.batteryMaster", "action": "set" }
```

`key` muss eine **beschreibbare** Variable sein (eine mit einem `sim_event`).
`action`: `set` — den Wert aus `value` setzen; `toggle` — ihn umschalten.

---

## 6. Benutzerdefinierte Variablen (LVAR und RPN)

Standard-SimVars decken die Cessna 172 und die meisten einfachen Flugzeuge ab,
aber PMDG, Fenix, FlyByWire und iniBuilds halten ihren Zustand in eigenen
Variablen. Ein Profil kann sie im Block `variables` deklarieren, und Widgets
können die resultierenden Schlüssel (`custom.*`) wie gewöhnliche referenzieren.

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

| Feld | Beschreibung |
| --- | --- |
| `key` | Schlüssel der Form `custom.fuelLbs` (erstes Segment kleingeschrieben, dann camelCase); darf nicht mit einer eingebauten Variable kollidieren |
| `kind` | `number` / `bool` / `string` |
| `source` | `lvar` — eine LVAR über die WASM-Bridge lesen; `rpn` — mit einem RPN-Skript berechnen |
| `name` | LVAR-Name (für `source: lvar`), bis zu 127 UTF-8-Byte |
| `expression` | RPN-Skript (für `source: rpn`); die Antwort wird in eine Zahl/ein Flag geparst |
| `initial` | Anfangswert für den Mock-Modus (ohne MSFS) |
| `label`, `unit` | Beschriftungen für den Editor |

Widget-Bindungen werden gegen **eingebaute + deklarierte** Schlüssel validiert:

```json
{ "id": "fuel", "type": "readout", "bindings": { "value": "custom.fuelLbs" } }
```

So funktioniert es:

- im **Mock-Modus** setzt der Provider `initial` ein — das Panel erwacht ohne
  MSFS zum Leben;
- in einem **echten Flug** werden die Werte von `WasmBridge` (`read_specs`) über
  das MobiFlight/SimBridge-WASM-Modul gelesen; der Bus pollt sie höchstens
  4-mal pro Sekunde und cacht sie zwischen Frames;
- wenn die Bridge nicht verbunden ist, fehlen die Schlüssel einfach im Frame —
  die Instrumente zeigen „--" (das Einsetzen von 0.0 wäre eine Lüge).

Beispielprofil: [`profiles/demo-lvar-panel.json`](../../profiles/demo-lvar-panel.json).

---

## 7. Vollständiges Beispiel (Cessna 172S)

Siehe [`profiles/cessna-172-skyhawk.json`](../../profiles/cessna-172-skyhawk.json) —
11 Instrumente: Künstlicher Horizont, Geschwindigkeit/Höhe/Kurve (Digitalanzeige),
Drehzahlmesser und Kraftstoff (Skala), Batterie-/Avionikschalter, BUS-OFF-Lampe,
Landeklappen, Heading-Bug-Steller (Drehschalter). Das zweite Beispiel ist
`profiles/piper-pa28-archer-ii.json` (nur `layout.base`, testet das
Fallback-Layout).

---

## 8. Rückwärtskompatibilität mit dem v0-Format

Das ursprüngliche Format aus der Spezifikation (`bindings[]` mit Pixel-
`position` und `sim_var`) wird über den Adapter `msfs_gateway/legacy.py`
unterstützt: Es wird beim Laden in das interne Format übersetzt, und
Koordinaten werden von Pixeln in Panel-Bruchteile umgerechnet (die
Standard-Leinwand ist 1280×800 oder stammt aus `layout.canvas`/
`target_aspect_ratio`). Das Speichern über `PUT /api/profiles/{id}` schreibt das
interne Format.
