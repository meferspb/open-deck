# Open Deck for MSFS — Dienstbeschreibung

Dieses Dokument beschreibt, was das Gateway tut, woraus es besteht, wie Clients
mit ihm interagieren und wie man die Passwortanmeldung aktiviert. Es richtet
sich an Piloten, die das Panel „für sich selbst" einrichten, und an Entwickler,
die den internen Aufbau verstehen müssen.

- Version: 0.1.0
- Host-Plattform: Windows 10/11
- Clients: Browser (PC, Smartphone, Tablet), Android 8+
- Lizenz: [GNU AGPL-3.0](../../LICENSE) + zusätzliche Bedingungen Abschnitt 7

## 1. Zweck

Open Deck for MSFS verwandelt ein Smartphone oder Tablet in eine
Instrumententafel für Microsoft Flight Simulator 2020/2024. Das Gateway läuft
auf demselben Computer wie der Simulator, liest Telemetrie über SimConnect,
stellt sie im lokalen Netzwerk bereit und akzeptiert Befehle (Schalter,
Drehschalter, Tasten). Panels werden durch JSON-Profile pro Flugzeug beschrieben
und direkt im Browser bearbeitet.

Wesentliche Eigenschaften:

- **Offline**: kein externes CDN, keine externen Schriftarten, keine externe API
  und keine externe Telemetrie. Alles funktioniert in einem isolierten Netzwerk
  und auf einem Rechner ohne Internet.
- **Ein Port**: statische Dateien, REST und WebSocket auf einem einzigen
  TCP-Port (standardmäßig 8760) — eine einzige Firewall-Regel genügt.
- **Keine Abhängigkeiten**: der Host ist Python 3.11+ und die
  Standardbibliothek; der Client sind reine ES-Module; Android ist Kotlin ohne
  AndroidX.
- **Optionales Passwort**: Der Zugriff auf die API und die Telemetrie kann mit
  einem Passwort von mindestens 6 Zeichen geschlossen werden, mit Sitzungen,
  QR-Anmeldung und Schutz gegen Brute-Force.

## 2. Betriebsmodell

```
┌──────────────────┐   SimConnect / WASM    ┌─────────────────────────────┐
│  MSFS 2020/2024  │◄──────────────────────►│ Open Deck for MSFS (Windows)│
│  aircraft, LVAR  │   SimVar, TITLE, ATC   │                             │
└──────────────────┘   Client Data Area     │  ┌───────────────────────┐  │
                                             │  │ SimProvider           │  │
┌──────────────────┐        HTTP/WS          │  │  auto / mock / simconn│  │
│  PC browser      │◄───────────────────────►│  └──────────┬────────────┘  │
│  panel, editor   │   8760, static + API    │             │               │
└──────────────────┘                         │  ┌──────────▼────────────┐  │
┌──────────────────┐        HTTP/WS          │  │ Hub: telemetry 30 Hz  │  │
│  Phone/tablet    │◄───────────────────────►│  │ commands, sessions    │  │
└──────────────────┘                         │  └──────────┬────────────┘  │
┌──────────────────┐   HTTP (WebView)        │             │               │
│  Android client  │◄───────────────────────►│  Profiles, integrity,     │
└──────────────────┘   UDP beacon 8761       │  authentication, APK      │
                                             └─────────────────────────────┘
```

Datenfluss:

1. Der Telemetrie-Provider (`simconnect`, `mock` oder `auto`) liest die
   Variablenwerte einmal pro Tick.
2. Der Bus (`Hub`) stellt einen Frame zusammen, fügt Dienstfelder hinzu und
   sendet ihn mit der konfigurierten Rate an alle WebSocket-Clients (30 Hz
   standardmäßig, maximal 60).
3. Der Client zeichnet Instrumente; Befehle gehen zurück an den Bus, werden
   validiert und vom Provider angewendet.
4. Wenn sich das Flugzeug ändert, wählt das Gateway ein passendes Profil nach
   Name/ATC-Modell und benachrichtigt die Clients darüber.

## 3. Komponenten

| Komponente | Dateien | Verantwortlichkeit |
| --- | --- | --- |
| Einstiegspunkt | `msfs_gateway/app.py` | Dependency-Assembly, Lebenszyklus, Banner, Modi `--set-password` / `--build-apk` |
| Einstellungen | `msfs_gateway/settings.py` | CLI-Argumente, Pfade, Standardwerte |
| HTTP/WebSocket | `msfs_gateway/http_api.py`, `websocket.py` | Statische Dateien, REST, RFC-6455-Handshake und -Frames, Authentifizierung |
| Bus | `msfs_gateway/hub.py` | Telemetrie-Frame, Abonnements, Befehle, Befehlsbegrenzung, Flugzeug-Autoerkennung |
| Provider | `msfs_gateway/sim/` | `mock`, `simconnect`, Client Data Area, LVAR/RPN-WASM-Bridge |
| Profile | `msfs_gateway/profiles.py` | Lesen/Validierung/atomares Speichern von JSON-Profilen |
| Telemetrie | `msfs_gateway/telemetry.py` | Variablenkatalog, Typen, Wertumwandlung |
| Authentifizierung | `msfs_gateway/auth.py` | PBKDF2-Hash, Sitzungen, QR-Token, Versuchsbegrenzung |
| Autoerkennung | `msfs_gateway/discovery.py` | UDP-Beacon mit Name, Version und Passwort-Flag |
| Integrität | `msfs_gateway/integrity.py` | SHA-256 der kritischen UI-Dateien |
| QR | `msfs_gateway/qr.py` | Integrierter QR-Generator (SVG), ohne Abhängigkeiten |
| APK-Build | `msfs_gateway/android_build.py` | Einstellungen, JDK-/SDK-/Gradle-Suche, Gradle-Start, APK-Bereitstellung |
| Assistent | `msfs_gateway/assist.py` | Roll- (Geschwindigkeit/Kurs) und Lande-Regelungen (APR, Retard, TOGA) |
| Dokumentationsgenerator | `msfs_gateway/docsgen.py` | `docs/telemetry.md` und `docs/widgets.md` aus Code-Registern |
| Web-Client | `web/` | Panel, Editor, Anmeldung, Assistent, APK-Build-Seite |
| Android | `android/` | WebView-Shell, UDP-Erkennung, Integritätsprüfung, Anmelde-Cookie |
| Build und Prüfungen | `scripts/`, `packaging/` | Installer, `check.ps1`, QR-Verifikation |

## 4. Telemetrie

### 4.1. Frame

Ein Frame ist ein JSON-Objekt, das über WebSocket unmittelbar nach der
Verbindung und dann mit der Rate des Gateways eintrifft:

```json
{
  "type": "telemetry",
  "seq": 421,
  "ts": 1793541762842,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  },
  "values": {
    "attitude.pitchDeg": 2.4,
    "attitude.bankDeg": -6.1,
    "speed.iasKt": 108.2,
    "altitude.indicatedFt": 4520.0,
    "heading.magneticDeg": 274.0,
    "verticalSpeed.fpm": 120.0,
    "engine.rpm": 2380.0,
    "power.batteryMaster": true,
    "custom.lvar.apuBleed": 0.0
  }
}
```

`seq` wächst monoton, `ts` ist Unix-Millisekunden. Der Client erkennt verlorene
Frames anhand von `seq` und zeichnet einfach weiter (für Zeiger ist das
unerheblich).

### 4.2. Variablen

Der vollständige Katalog mit Typen, Einheiten, SimVars und Ereignissen steht in
[telemetry.md](telemetry.md). Unten sind nur die Kategorien aufgeführt.

Der Variablenkatalog ist die einzige Quelle der Wahrheit (`telemetry.py`). Jeder
Eintrag hat einen Typ (`number`, `bool`, `string`), ein Flag „Befehle
akzeptiert" und eine Beschreibung. Der Client kann den Katalog über
`GET /api/telemetry/variables` abrufen.

Kategorien:

- Lage, Höhe, Geschwindigkeit, Kurs, VSI;
- Triebwerk (RPM, Manifold/Drehmoment, N1, ITT, Kraftstoff);
- Elektrik, Landeklappen, Autopilot;
- `custom.<...>` — LVAR/RPN aus dem aktiven Profil.

### 4.3. Provider

| Provider | Verwendung | Eigenschaften |
| --- | --- | --- |
| `simconnect` | echter Flug | `ctypes` + `SimConnect.dll`; String-Datums `TITLE`, `ATC MODEL`; Client Data Area für LVAR/RPN. Wenn die Standard-`SimConnect.cfg` nicht funktioniert, versucht das Gateway selbst TCP `127.0.0.1:19999` (der MSFS-2020/2024-Port) über eine temporäre Konfiguration |
| `mock` | Demo, Entwicklung, Tests | Prozedurales Flugmodell, anfängliche LVAR-Werte aus dem Profil |
| `auto` | standardmäßig | Versucht, SimConnect zu verbinden, und fällt bei Fehlschlag auf Mock zurück |

Wenn das WASM-Modul nicht installiert ist, fehlen die `custom.*`-Schlüssel
einfach, und das Panel zeigt „--" — der Rest der Telemetrie funktioniert weiter.
Nach zwei aufeinanderfolgenden Timeouts pausiert der Circuit Breaker von Client
Data das Polling für 30 Sekunden, damit der Telemetrie-Broadcast-Thread nicht
blockiert wird.

### 4.4. Zustellung und Ausfallsicherheit

- Jeder WebSocket-Client hat seine eigene Warteschlange (8 Frames) und seinen
  eigenen Sender-Thread: Ein langsames Tablet bremst die anderen nicht, und alte
  Frames werden verworfen.
- Die Wiederverbindung des Clients verwendet exponentiellen Backoff; wenn länger
  als 45 Sekunden keine Nachrichten eintreffen, betrachtet der Client die
  Verbindung als „halb-offen" und verbindet neu.
- Eine Sitzung kann während des Flugs ablaufen — der Client prüft den Status
  einmal pro Minute und leitet auf die Anmeldeseite weiter.

## 5. Flugzeugprofile

Ein Profil ist eine JSON-Datei in `profiles/`. Das ausführliche Schema steht in
[`profile-schema.md`](profile-schema.md). Kurz gefasst:

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk",
  "icao": "C172",
  "revision": 3,
  "sim": { "match": { "title": "*Cessna*172*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S" },
  "widgets": [
    {
      "id": "attitude",
      "type": "attitude",
      "label": "Attitude indicator",
      "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
      "layout": {
        "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
        "phone": { "x": 0.03, "y": 0.015, "w": 0.94, "h": 0.3 }
      }
    }
  ]
}
```

- `sim.match` — Vorlagen (Glob) für Flugzeugtitel und ATC-Modell; das Gateway
  wechselt das Profil selbst.
- `layout` — Koordinaten in Panel-Bruchteilen (0..1); `base` und die
  Überschreibungen `phone`, `tablet-sm`, `tablet-lg`.
- `revision` — wächst bei jedem Speichern aus dem Editor.
- Das Speichern ist atomar: temporäre Datei → `fsync` → `os.replace`.

## 6. Clients

### 6.1. Web-Panel

- Drei Formfaktoren mit automatischer Auswahl nach Bildschirmbreite; die
  manuelle Wahl wird gespeichert.
- Instrumente: Künstlicher Horizont, Rundskalen, Digitalanzeigen, Schalter,
  Drehschalter, VSI, Höhenmesser, Kursanzeiger; Animation über
  `requestAnimationFrame`.
- Komfort: Helligkeit 100/72/45 % (`B`), Kiosk-Modus (`F`, Beenden mit `Esc`).
- Die Smartphone-Schaltfläche zeigt einen QR-Code für die schnelle Anmeldung.

### 6.2. Editor

`/editor.html`: Drag-and-drop, Größenänderung, 1-%-Raster, Rückgängig/Wiederholen,
Kopieren von Layouts zwischen Formfaktoren, Speichern auf dem Host.

### 6.3. Android

WebView-Shell: findet den Host über den UDP-Beacon oder akzeptiert eine manuelle
Adresse, prüft die UI-Integrität und öffnet das Panel. Wenn auf dem Gateway ein
Passwort aktiviert ist, zeigt die WebView die Anmeldeseite; die Sitzung wird in
einem WebView-Cookie gespeichert und übersteht einen Neustart der App.
Passwortgeschützte Hosts sind mit einem Schloss markiert.

### 6.4. Anmeldeseite

`/login.html` ist die einzige ohne Anmeldung verfügbare Seite (zusammen mit
ihrem Styling). Sie zeigt ein Passwortfeld, Fehler, den Autoren-Supportblock und
eine Schaltfläche „Abmelden", falls bereits eine Sitzung aktiv ist. Das Passwort
wird nur an das eigene Gateway gesendet, über HTTP im lokalen Netzwerk (siehe
Abschnitt „Sicherheit").

## 7. Netzwerk und Verbindung

| Was | Port | Protokoll |
| --- | --- | --- |
| Statische Dateien, REST, WebSocket | 8760 (konfigurierbar über `--port`) | TCP/HTTP + WS |
| Autoerkennung | 8761 | UDP-Broadcast |

- Das Gateway lauscht auf `0.0.0.0` und gibt beim Start alle seine Adressen aus.
- Android findet den Host über den Beacon: PC-Name, Version, Profilanzahl,
  Passwort-Flag.
- Der QR-Code auf dem Panel enthält die Adresse und ein einmaliges Token: Das
  Smartphone meldet sich mit einem einzigen Scan an, ohne Passworteingabe (das
  Token lebt 10 Minuten und wird einmal verwendet).
- Manuelle Adresseingabe: `192.168.1.10`, `192.168.1.10:8760` oder eine
  vollständige URL.

## 8. Passwortauthentifizierung

### 8.1. Aktivierung

Eine der folgenden Möglichkeiten:

```powershell
# 1. Passwort dauerhaft in config/auth.json speichern
OpenDeck.exe --set-password
#    oder ohne Abfrage:
OpenDeck.exe --set-password "my-password"

# 2. Passwort nur für diesen Lauf übergeben (nicht auf die Festplatte geschrieben)
OpenDeck.exe --password "my-password"

# 3. Umgebungsvariable
$env:OPEN_DECK_PASSWORD = "my-password"
```

In der installierten App gibt es dafür eine Verknüpfung „Passwort festlegen" im
Startmenü. Die Datei `config/auth.json` speichert **nur den PBKDF2-Hash**
(zufälliges Salt, 210.000 Iterationen); löschen Sie die Datei, und die Anmeldung
ist wieder frei. Das Flag `--no-auth` ignoriert die Datei und das Passwort (nur
vertrauenswürdiges Netzwerk).

Das Passwort aus `--password` wird nicht auf die Festplatte geschrieben, ist aber
in der Prozessliste sichtbar (`Get-Process` / Task-Manager). Für den dauerhaften
Einsatz bevorzugen Sie `--set-password`: Es wird beim Start einmal im Speicher
gehasht.

Die Mindestlänge des Passworts beträgt **6 Zeichen**; Grenzen: höchstens 256
Zeichen, keine Steuerzeichen, keine führenden oder abschließenden Leerzeichen.

### 8.2. Wie die Anmeldung funktioniert

1. Der Client öffnet `/login.html` und gibt das Passwort ein.
2. `POST /api/auth/login` prüft den PBKDF2-Hash; bei Erfolg wird eine Sitzung
   erstellt (32 Zufallsbytes, 12 Stunden TTL, bei Aktivität verlängert).
3. Der Server setzt das Cookie `open_deck_session` mit `HttpOnly`,
   `SameSite=Lax` — JavaScript kann es nicht sehen, und der Browser sendet es
   automatisch.
4. Für native Clients gibt die JSON-Antwort ein `token` zurück; es kann als
   `Authorization: Bearer <token>` oder als `?token=` für WebSocket übergeben
   werden.
5. `POST /api/auth/logout` widerruft die Sitzung und löscht das Cookie.

Nur die folgenden Pfade sind öffentlich zugänglich:

| Pfad | Warum |
| --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | die Anmeldeseite und ihr Styling |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | die Anmeldung selbst |
| `/api/health` | „Ist das das Gateway?"-Prüfung und das Passwort-Flag |
| `/api/integrity` | UI-Integritätsprüfung (Lizenzbedingung) |
| `/api/donation` | Autoren-Supportblock (Lizenzbedingung) |
| `/license` | Lizenztext |

Alles andere — Profile, Telemetrie, Befehle, Android-Einstellungen, APK-Build,
QR, `WS /ws` — erfordert eine Sitzung. Seiten ohne Sitzung antworten mit einer
Weiterleitung auf `/login.html?next=…`.

### 8.3. Schutz gegen Brute-Force

- 5 fehlgeschlagene Versuche von einer IP innerhalb von 60 Sekunden → für 60
  Sekunden gesperrt (Antwort `429` mit `Retry-After`).
- Der Hash-Vergleich verwendet `hmac.compare_digest` (konstante Zeit).
- Fehlgeschlagene Versuche werden mit der Adresse, aber ohne das Passwort
  protokolliert.

### 8.4. QR-Anmeldung vom Smartphone

Die Schaltfläche „Smartphone" auf dem Panel fordert `POST /api/pair` an (eine
Sitzung ist erforderlich). Das Gateway stellt ein einmaliges Token für 10
Minuten aus; der QR-Code kodiert
`http://<address>:<port>/?pair=<token>`. Das Smartphone öffnet den Link, das
Gateway tauscht das Token gegen eine reguläre Sitzung, setzt das Cookie und
leitet auf `/` weiter. Das Pairing-Token selbst ist keine Sitzung: Als Cookie
oder Bearer-Token liefert es `401`, sodass der Link nach dem Austausch nicht
wiederverwendet werden kann. Eine erneute Verwendung des Tokens wird
abgewiesen.

## 9. Lande- und Roll-Assistent

Die Seite `/assist.html` und die API `/api/assist*` fügen zwei Hilfsregelungen
hinzu. Dies ist **kein zertifizierter Autopilot**: Der Pilot steuert den Flug
und kann den Assistenten jederzeit deaktivieren.

### 9.1. Rollen

- Nur am Boden aktiviert, bei gelöster Parkbremse und Geschwindigkeit unter
  35 kt.
- Hält die Zielgeschwindigkeit über Grund (3–25 kt) mit einem PI-Schubregler und
  den Kurs mit einem P-Seitenruderregler; der Pilot ändert den Kurs mit den
  Tasten ±1°/±5°.
- „STOP": Schub 0, Seitenruder 0, Parkbremse.
- Wird automatisch deaktiviert, wenn das Flugzeug abhebt, die Parkbremse
  angezogen wird oder die Geschwindigkeit 35 kt überschreitet.

### 9.2. Landen

- ARM: aktiviert `AP_MASTER` und `AP_APR_HOLD` (ILS-Anflug). Erfordert eine
  Geschwindigkeit von mindestens 40 kt und das Flugzeug in der Luft.
- Bei 60–15 ft Funkhöhe reduziert der Assistent den Schub linear von 45 % auf 0.
- Bei der Landung: Schub 0, Autopilot aus; nach dem Abbremsen unter 5 kt —
  „Rollout abgeschlossen".
- TOGA: Vollschub, AP und APR aus (Durchstarten).
- Der Assistent berührt das Höhenruder nicht: Anflug und Abfangen bleiben beim
  Autopiloten/Piloten.

Zustand und Sollwerte: `GET /api/assist`; Aktionen — `POST /api/assist/taxi`
(`engage`, `disengage`, `stop`, `speed`, `heading`) und
`POST /api/assist/landing` (`arm`, `disarm`, `toga`). Alle Anfragen erfordern
eine Sitzung.

## 10. API

Basis-URL: `http://<host>:<port>`. Alle Antworten sind JSON; Fehler haben die
Form `{"error": "…", "code": "…"}`.

| Methode | Pfad | Zugriff | Beschreibung |
| --- | --- | --- | --- |
| GET | `/api/health` | öffentlich | Status, Version, Rate, Passwort-Flag |
| GET | `/api/auth/status` | öffentlich | `{required, authenticated}` |
| POST | `/api/auth/login` | öffentlich | `{password}` → Sitzung + Cookie |
| POST | `/api/auth/logout` | öffentlich | Aktuelle Sitzung widerrufen |
| POST | `/api/pair` | Sitzung erforderlich | Einmaliges QR-Token |
| GET | `/api/profiles` | Sitzung erforderlich | Profilliste |
| GET | `/api/profiles/{id}` | Sitzung erforderlich | Vollständiges Profil |
| PUT | `/api/profiles/{id}` | Sitzung erforderlich | Profil speichern (id im Body = id in der URL) |
| GET | `/api/telemetry` | Sitzung erforderlich | Neuester Frame |
| GET | `/api/telemetry/variables` | Sitzung erforderlich | Variablenkatalog |
| POST | `/api/sim/command` | Sitzung erforderlich | `{key, value}` → Bestätigung |
| POST | `/api/sim/aircraft` | Sitzung erforderlich | `{profileId}` — manuelle Flugzeugauswahl |
| GET | `/api/integrity` | öffentlich | Ergebnis der SHA-256-Prüfung |
| GET | `/api/donation` | öffentlich | Autoren-Supportdaten |
| GET | `/api/connect` | Sitzung erforderlich | Gateway-Adressen für QR/Hinweise |
| GET | `/api/qr.svg?text=…` | Sitzung erforderlich | SVG mit einem QR-Code |
| GET/PUT | `/api/android/settings` | Sitzung erforderlich | APK-Build-Einstellungen |
| GET/POST | `/api/android/build` | Sitzung erforderlich | Start/Status des APK-Builds |
| GET | `/api/android/apk` | Sitzung erforderlich | Die APK herunterladen |
| GET | `/api/assist` | Sitzung erforderlich | Assistent-Zustand und Telemetrie |
| POST | `/api/assist/taxi` | Sitzung erforderlich | Steuerung des Roll-Assistenten |
| POST | `/api/assist/landing` | Sitzung erforderlich | ARM / DISARM / TOGA |
| WS | `/ws` | Sitzung erforderlich | Telemetrie und Befehle |

Anmelde- und Anfragebeispiel:

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"my-password"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

Befehl:

```json
{"type": "command", "id": "c17", "key": "power.batteryMaster", "value": true}
```

Antwort: `{"type": "ack", "id": "c17", "ok": true, "value": true}` oder
`ok:false` mit einem Fehlercode. Befehle sind auf ~20 pro Sekunde pro Client
begrenzt.

## 11. Installation und Start

### 11.1. Windows-Installer

`OpenDeck-Setup-<version>.exe` — Installation pro Benutzer ohne
Administratorrechte, Python nicht erforderlich. Verknüpfungen werden erstellt
für: Start des Gateways, das Panel im Browser, die APK-Build-Seite, „Passwort
festlegen" und die Deinstallation.

### 11.2. Aus dem Quellcode

```powershell
python -m msfs_gateway --sim auto          # echter Flug
python -m msfs_gateway --sim mock          # Demo ohne Simulator
python -m msfs_gateway --password "secret123"
```

| Parameter | Standard | Zweck |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8760` | Adresse und Port |
| `--allow-host NAME` | — | zusätzlicher DNS-Name für Host (falls das Panel über den Namen geöffnet wird) |
| `--sim` | `auto` | `auto`, `mock`, `simconnect` |
| `--telemetry-hz` | `30` | Frame-Rate, 1..60 |
| `--simconnect-dll` | automatische Erkennung | Pfad zu `SimConnect.dll` |
| `--simconnect-host` | `127.0.0.1` | SimConnect-Adresse (entfernter Simulator) |
| `--simconnect-port` | `19999` | SimConnect-TCP-Port |
| `--profile-dir` | `profiles/` | Profilverzeichnis |
| `--password` | — | Passwort für diesen Lauf |
| `--set-password [PWD]` | — | Hash speichern und beenden |
| `--auth-file` | `config/auth.json` | Hash-Datei |
| `--web-dir` / `--profile-dir` | `web/` / `profiles/` | Verzeichnisse für Statik und Profile |
| `--donation-config` | `config/donation.json` | Autoren-Supportdaten |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--discovery-port` / `--discovery-interval` | `8761` / `3` | UDP-Beacon: Port und Periode |
| `--no-auth` | — | Passwort ignorieren |
| `--no-wasm` | — | kein LVAR/RPN |
| `--no-discovery` | — | kein UDP-Beacon |
| `--build-apk [CONFIG]` | — | die APK bauen und beenden |

### 11.3. Android-APK

Die Installation enthält die Android-Quellen; die fertige APK wird nach
`android/dist/OpenDeck-Android-<version>.apk` gebaut. Die Seite `/android.html`
(Anmeldung erforderlich) ermöglicht das Ändern von Name, Package-ID, Version und
standardmäßiger Gateway-Adresse sowie den Build der APK direkt vor Ort. JDK 17,
Android SDK und Gradle 8.x sind erforderlich; in der Release-Distribution ist
die APK bereits beigefügt.

## 12. Diagnose

| Symptom | Was zu prüfen ist |
| --- | --- |
| Das Panel öffnet sich nicht vom Smartphone | dasselbe WLAN, die Adresse aus dem Banner, Windows-Firewall (Port 8760), `--host 0.0.0.0` |
| „Passwortanmeldung erforderlich" | ein Passwort ist gesetzt; geben Sie es auf `/login.html` ein; das QR-Token lebt 10 Minuten |
| „Falsches Passwort" | Tastaturlayout/Groß-/Kleinschreibung; zurücksetzen: `config/auth.json` löschen oder `--no-auth` verwenden |
| Instrumente zeigen „--" | kein SimConnect/WASM, Mock ausgewählt, Flugzeug hat kein Profil, der Simulator ist noch im Hauptmenü |
| Das Profil wechselt nicht | `sim.match` passt nicht zu Name/Modell; manuell auswählen |
| Der APK-Build startet nicht | JDK/SDK/Gradle nicht gefunden; geben Sie die Pfade auf `/android.html` an |
| „Integrität verletzt" | kritische Dateien wurden geändert; `python -m msfs_gateway.integrity --write` |
| `SimConnect_Open … 0x80004005` | das Gateway versucht selbst TCP `127.0.0.1:19999`; wenn das nicht geholfen hat — prüfen Sie `%APPDATA%\Microsoft Flight Simulator\SimConnect.cfg` (sie überschreibt die Einstellungen) und ob ein Flug geladen ist; für einen entfernten Simulator setzen Sie `--simconnect-host/--simconnect-port` |

Logs: die Gateway-Konsole (`--log-level DEBUG`), der „Netzwerk"-Tab des Browsers
und `adb logcat` für Android (Tag `OpenDeckDiscovery`).

## 13. Sicherheit

- Das Passwort schützt die API und die Telemetrie vor einem „WLAN-Nachbarn",
  aber **der Verkehr läuft über HTTP ohne TLS**. In einem vertrauenswürdigen
  Heimnetz ist das akzeptabel; für Gastnetzwerke verwenden Sie ein separates
  VLAN oder einen Reverse-Proxy mit TLS.
- Das Sitzungs-Cookie ist `HttpOnly` + `SameSite=Lax`; das CSRF-Risiko ist
  verringert. URL-Token werden nur für WebSocket (`?token=`) und das einmalige
  QR (`?pair=`) verwendet. Das QR-Token wird nur über `/?pair=` akzeptiert und
  ist keine Sitzung.
- `Origin`-Prüfung für Browser-POST/PUT und WebSocket: Eine Anfrage mit fremdem
  `Origin` erhält `403`; Clients ohne `Origin` sind erlaubt.
- `Host`-Prüfung gegen lokale Namen/IPs: Ein unbekannter Host erhält `403`
  (Schutz gegen DNS-Rebinding).
- Anmeldeversuche sind auf 5 pro Minute pro Adresse begrenzt.
- CORS ist absichtlich deaktiviert: Eine Drittseite kann API-Antworten nicht
  lesen.
- Wenn kein Passwort gesetzt ist, warnt das Gateway ausdrücklich in der Konsole,
  dass Panel und Befehle für alle im lokalen Netzwerk verfügbar sind.
- Der UDP-Beacon ist unsigniert: Jeder Host im Netzwerk kann sich als Gateway
  ausgeben. Setzen Sie das Gateway nicht dem Internet aus.
- Android: Allowlist für WebView-Navigation, Zugriff auf `file:`/`content:` ist
  verboten, gemischte Inhalte sind verboten.

## 14. Einschränkungen

- Ein Live-Lauf von SimConnect/WASM erfordert eine installierte MSFS; im
  Repository wird die Logik durch Emulation verifiziert.
- Die APK ist mit einem Debug-Schlüssel signiert; die Release-Signierung ist noch
  nicht automatisiert.
- Kein mDNS: nur der UDP-Beacon.
- Ein aktives Gateway pro Port; Profile sind Dateien, ohne Datenbank.

## 15. Glossar

| Begriff | Bedeutung |
| --- | --- |
| **Gateway** | Der Prozess auf dem PC mit dem Simulator: liest Telemetrie und stellt sie Clients bereit |
| **Host** | Der Rechner, auf dem das Gateway läuft (im Android-Client — der erkannte PC) |
| **Profil** | Eine JSON-Datei mit Instrumenten und Layouts für ein bestimmtes Flugzeug |
| **Instrument / Widget** | Ein Panel-Element: Künstlicher Horizont, Skala, Schalter usw. |
| **Formfaktor** | Eine Bildschirmklasse: `phone`, `tablet-sm`, `tablet-lg` |
| **Flugzeug** | Ein bestimmtes Flugzeug im Simulator; das Profil wird über `TITLE`/`ATC MODEL` ausgewählt |
| **Telemetrie** | Der Strom von SimVar- und `custom.*`-Werten in einem JSON-Frame |
| **Frame** | Eine einzelne `telemetry`-Nachricht mit `seq`, `ts`, `sim`, `values` |
| **LVAR** | Eine lokale Flugzeugvariable (PMDG, Fenix, FBW usw.) |
| **RPN** | Umgekehrte polnische Notation — ein Skript zur Berechnung eines Werts in MSFS |
| **WASM-Bridge** | LVAR/RPN-Austausch über die Client Data Area des MobiFlight/SimBridge-Moduls |
| **Client Data Area** | Eine benannte SimConnect-Area zum Austausch von Datenblöcken |
| **AP / APR / AT** | Autopilot / ILS-Anflugsmodus / Autothrottle |
| **Retard** | Sanfte Schubrücknahme während des Abfangens (Lande-Assistent) |
| **TOGA** | Take Off / Go Around: Vollschub und Durchstarten |
| **Pairing** | Anmeldung vom Smartphone über ein einmaliges QR-Token |
| **Sitzung** | Eine aktive Anmeldung: ein Token in Cookie/Bearer, TTL 12 Stunden |
| **Integrität** | Vergleich des SHA-256 kritischer UI-Dateien mit dem Manifest |
| **Air-gapped** | Ein Netzwerk ohne Internetzugang; alle Ressourcen sind lokal |

## 16. Feedback und Support

- **Autor:** Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck).
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).
- Fehler und Vorschläge — über die GitHub-Issue-Vorlagen (siehe `.github/`).
- Schwachstellen — privat, gemäß [security.md](security.md).
- Einrichtungsfragen — Discussions (falls aktiviert) oder ein Issue mit der
  Vorlage „Bug".
- Lizenz und der verpflichtende Autoren-Supportblock — [LICENSE](../../LICENSE).

## 17. Lizenz

[GNU Affero General Public License v3.0](../../LICENSE) und
[zusätzliche Bedingungen Abschnitt 7](../../COPYING.ADDITIONAL): Der Quellcode
ist offen, Änderungen werden unter AGPL vertrieben; der Autoren-Supportblock und
die Integritätsprüfung sind verpflichtend und können nicht entfernt werden.
