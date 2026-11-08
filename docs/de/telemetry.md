# 📊 Telemetrie-Variablenkatalog

> Diese Datei wird aus `msfs_gateway/telemetry.py` generiert; bearbeiten Sie sie
> nicht manuell. Aktualisieren: `python -m msfs_gateway.docsgen --write`.

Das Register ist die einzige Quelle der Wahrheit: Panel-Profile binden
Instrumente an diese Schlüssel, und das Gateway liest SimVars und sendet
Befehle.

## Wie die Tabelle zu lesen ist

- **Schlüssel** — der Variablenname im Telemetrie-Frame und in den `bindings`
  des Profils.
- **Typ** — `number`, `bool` oder `string`; `bool` kommt im JSON als
  `true/false` an, Zahlen als `float`.
- **Lesen** — die SimVar, aus der das Gateway den Wert entnimmt (für `custom.*`
  gibt es keine Quelle: Sie werden von der WASM-Bridge gemäß der
  Profilbeschreibung gelesen).
- **Befehl** — das SimConnect-Ereignis, mit dem die Variable geändert wird; ein
  Strich bedeutet „nur lesen".

## Variablen nach Gruppe

### Elektrik und Stromversorgung

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `power.batteryMaster` | bool | — | ELECTRICAL MASTER BATTERY | TOGGLE_MASTER_BATTERY | Hauptschalter der Batterie |
| `power.avionicsMaster` | bool | — | AVIONICS MASTER SWITCH | TOGGLE_AVIONICS_MASTER | Avionik-Stromversorgung |
| `power.busVolts` | number | V | ELECTRICAL MAIN BUS VOLTAGE | — | Spannung des Hauptbusses |

### Triebwerk

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `engine.rpm` | number | RPM | GENERAL ENG RPM:1 | — | Triebwerksdrehzahl |
| `engine.fuelFlowGph` | number | GPH | ENG FUEL FLOW GPH:1 | — | Kraftstoffverbrauch pro Stunde |
| `engine.torquePct` | number | % | TURB ENG MAX TORQUE PERCENT:1 | — | Drehmoment des Turboprop-Triebwerks |
| `engine.ittC` | number | °C | TURB ENG ITT:1 | — | ITT-Temperatur |
| `engine.propRpm` | number | RPM | PROP RPM:1 | — | Propellerdrehzahl |
| `engine.n1Pct` | number | % | TURB ENG N1:1 | — | N1 von Triebwerk #1 |
| `engine.n1Pct2` | number | % | TURB ENG N1:2 | — | N1 von Triebwerk #2 |

### Räumliche Lage

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `attitude.pitchDeg` | number | ° | PLANE PITCH DEGREES | — | Nickwinkel |
| `attitude.bankDeg` | number | ° | PLANE BANK DEGREES | — | Rollwinkel |

### Höhe

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `altitude.indicatedFt` | number | FT | INDICATED ALTITUDE | — | Angezeigte Höhe |

### Geschwindigkeit

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `speed.iasKt` | number | KT | AIRSPEED INDICATED | — | Angezeigte Fluggeschwindigkeit |

### VSI

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `verticalSpeed.fpm` | number | FPM | VERTICAL SPEED | — | Vertikalgeschwindigkeit |

### Kurs

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `heading.magneticDeg` | number | ° | PLANE HEADING DEGREES MAGNETIC | — | Magnetischer Kurs |

### Landeklappen

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `flaps.percent` | number | % | TRAILING EDGE FLAPS LEFT PERCENT | — | Klappenstellung |

### Kraftstoff

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `fuel.leftGal` | number | GAL | FUEL LEFT QUANTITY | — | Kraftstoff im linken Tank |
| `fuel.rightGal` | number | GAL | FUEL RIGHT QUANTITY | — | Kraftstoff im rechten Tank |
| `fuel.totalGal` | number | GAL | — | — | Gesamter Kraftstoff |

### Autopilot

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `autopilot.headingBugDeg` | number | ° | AUTOPILOT HEADING LOCK DIR | HEADING_BUG_SET | Zielkurs (Heading Bug) |
| `autopilot.master` | bool | — | AUTOPILOT MASTER | AP_MASTER | Autopilot aktiviert |
| `autopilot.approachHold` | bool | — | AUTOPILOT APPROACH HOLD | AP_APR_HOLD | APR-Modus — Aktivierungsbefehl |
| `autopilot.approach` | bool | — | AUTOPILOT APPROACH HOLD | — | APR-Modus aktiv |

### Flugzeugzustand

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `aircraft.onGround` | bool | — | SIM ON GROUND | — | Flugzeug am Boden |
| `aircraft.radioAltitudeFt` | number | FT | RADIO HEIGHT | — | Funkhöhe über der Landebahn |
| `aircraft.title` | string | — | TITLE | — | Flugzeugbezeichnung im Simulator |

### Rollen

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `groundSpeed.kt` | number | KT | GPS GROUND SPEED | — | Geschwindigkeit über Grund |

### Navigation (ILS)

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `nav.localizer` | number | dots | NAV CDI:1 | — | Localizer-Abweichung |
| `nav.glideSlope` | number | ° | NAV GLIDE SLOPE ERROR | — | Glideslope-Abweichung |
| `nav.locFlag` | bool | — | HSI CDI NEEDLE VALID | — | Localizer erfasst |
| `nav.gsFlag` | bool | — | HSI GSI NEEDLE VALID | — | Glideslope erfasst |

### Steuerung

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `controls.throttlePct` | number | % | GENERAL ENG THROTTLE LEVER POSITION:1 | THROTTLE_SET | Stellung des Schubhebels (Assistent-Befehl) |
| `controls.rudder` | number | % | RUDDER POSITION | RUDDER_SET | Seitenruder (Assistent-Befehl) |

### Bremsen

| Schlüssel | Typ | Einheit | Lesen (SimVar) | Befehl | Beschreibung |
| --- | --- | --- | --- | --- | --- |
| `brakes.parking` | bool | — | BRAKE PARKING POSITION | PARKING_BRAKES | Parkbremse |

## Variablen mit Befehlen

Diese Schlüssel können über `POST /api/sim/command` und den WebSocket-Befehl
`command` geändert werden. Der Wert wird in den Variablentyp umgewandelt; bei
Ereignissen mit Parameter wird er skaliert (zum Beispiel Prozent → 0..16383).

| Schlüssel | Ereignis | Parameter | Skalierung |
| --- | --- | --- | --- |
| `power.batteryMaster` | `TOGGLE_MASTER_BATTERY` | nein | 1.0 |
| `power.avionicsMaster` | `TOGGLE_AVIONICS_MASTER` | nein | 1.0 |
| `autopilot.headingBugDeg` | `HEADING_BUG_SET` | ja | 1.0 |
| `autopilot.master` | `AP_MASTER` | nein | 1.0 |
| `autopilot.approachHold` | `AP_APR_HOLD` | nein | 1.0 |
| `controls.throttlePct` | `THROTTLE_SET` | ja | 163.83 |
| `controls.rudder` | `RUDDER_SET` | ja | 163.83 |
| `brakes.parking` | `PARKING_BRAKES` | nein | 1.0 |

## Benutzerdefinierte Variablen `custom.*`

Ein Profil kann im Block `variables` eigene LVAR/RPN deklarieren; der Schlüssel
muss mit einem kleingeschriebenen Segment beginnen (üblicherweise `custom.`) und
darf nicht mit eingebauten Variablen kollidieren. Ein solcher Schlüssel erscheint
im Frame als gewöhnliche Variable.

Zulässige Arten: bool, number, string; Quellen: lvar, rpn. Schlüsselformat: `^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$`.

Beispiel:

```json
{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",
  "name": "APU_BLEED", "initial": false }
```

Details stehen in [profile-schema.md](profile-schema.md#6-benutzerdefinierte-variablen-lvar-und-rpn).
