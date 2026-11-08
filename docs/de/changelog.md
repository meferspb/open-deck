# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
Versionen — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Geändert

- Vollständiges Rebranding auf **Open Deck for MSFS**: Produktname, Web-Oberflächen,
  Android-App (`com.opendeck.msfs`), ausführbare Dateien, Installer,
  Dokumentation und Flugzeugprofile.
- Logo und App-Symbole aus `docs/pic1.jpg` generiert; Dateien
  `web/img/open-deck-mark.jpg`, `web/favicon.ico`, Android-Drawables und
  `packaging/windows/open-deck.ico`.

### Hinzugefügt

- **Donat**-Link — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) — im Web-Panel,
  Editor, Anmeldebildschirm, Assistenten, Android-Interface, README und Dokumentation.
- Autor **Viktor Krasnikov** und Repository
  [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) angegeben.

### Behoben

- SimConnect: Reihenfolge der Felder von `SIMCONNECT_RECV_SIMOBJECT_DATA` an
  `SimConnect.h` angeglichen (`dwFlags`/`dwEntryNumber`/`dwOutOf`/`dwDefineCount`) — ohne
  dies wurde die Live-Telemetrie numerischer Werte nicht aktualisiert.
- SimConnect: Befehle werden im Dispatch-Thread ausgeführt; Event-IDs
  werden bei der Wiederverbindung zurückgesetzt; fehlgeschlagene `AddToDataDefinition` verschieben
  nicht mehr die Indizes der übrigen Datums.
- WASM/Client Data: Sicherung nach Timeouts und LVAR-Block ≤ 56 Elemente,
  damit ein fehlendes WASM-Modul den Telemetriestream nicht blockiert.
- Das QR-Token wird nicht mehr als reguläre Sitzung akzeptiert und verlängert die TTL nicht.
- `Origin`-Prüfung für Browser-POST/PUT und WebSocket sowie
  `Host`-Prüfung gegen lokale Namen/IPs hinzugefügt (schließt DNS-Rebinding); für
  den Zugriff über den eigenen DNS-Namen wurde `--allow-host` ergänzt.
- Open Redirect in `login.js` über einen Backslash in `next` geschlossen.
- Fehler im Anfrage-Body hinterlassen die Keep-Alive-Verbindung nicht mehr in einem
  desynchronisierten Zustand; ein Limit gleichzeitiger Verbindungen wurde hinzugefügt.
- Die Token `pair`/`token` werden im Anfrage-Log redigiert.
- Assistent: Fehlende Höhe/Geschwindigkeit/Kurs werden nicht durch Null ersetzt; AP
  wird zurückgerollt, wenn APR nicht aktiviert wurde; bei Verbindungsverlust werden die Regelkreise deaktiviert;
  `stop` meldet einen Fehler, wenn Befehle nicht gesendet wurden.
- Telemetrie: Eingebaute SimVars, die in der SimConnect-Definition fehlen oder
  veraltet sind, werden als `null` geliefert (die UI zeigt `--`).
- SimVar-Genauigkeit: `TURB ENG MAX TORQUE PERCENT:1` (aktuelles Drehmoment in % des
  Maximums) und `RADIO HEIGHT` statt Höhe über Grund.
- Der QR-Dialog erzeugt das einmalige Token beim Öffnen und bei Ablauf der TTL neu.
- Der Editor leert die Historie beim Profilwechsel und warnt vor nicht gespeicherten
  Änderungen.
- Android-Builder: Allowlist für `extraGradleArgs`, Typprüfung, Verbot von
  drive-relative `outputDir`, sicheres `appName`.
- Android: Eine vollständige URL mit Port wird bei manueller Eingabe wieder akzeptiert.
- SimConnect: Die Wiederverbindung übersteht `OSError` der temporären Konfiguration;
  das Stoppen der Threads ist robuster geworden.
- Der Autoerkennungs-Beacon wird bei Überlauf ohne Profilliste gesendet,
  statt vollständig übersprungen zu werden.
- Das Wachstum der In-Memory-Limiter wurde begrenzt; REST-Befehle erhielten ein Rate-Limit pro IP.
- Bei deaktiviertem Passwort warnt die Konsole vor offenem Zugriff im LAN.

## [0.1.0] — 2026-11-01

Erste öffentliche Veröffentlichung.

### Hinzugefügt

- **Lande- und Roll-Assistent**: Halten von Geschwindigkeit/Kurs am Boden,
  ARM/DISARM/TOGA für den ILS-Anflug, automatisches Retard bei 60–15 Fuß,
  Abkoppeln des AP bei der Landung; Seite `/assist.html` und API `/api/assist*`.
- **Passwortanmeldung** (ab 6 Zeichen): PBKDF2-Hash in `config/auth.json`,
  Sitzungen in einem `HttpOnly`-Cookie für 12 Stunden, Bearer-Token, einmalige
  QR-Anmeldung vom Smartphone, Versuchslimit und Schutz gegen Brute-Force.
- Gateway in Python (nur stdlib): HTTP + WebSocket (RFC 6455) auf einem Port,
  UDP-Autoerkennung, Flugzeugprofile mit JSON-Schema und Validierung.
- Telemetrie-Provider: `simconnect` (ctypes, String-Datums `TITLE` und
  `ATC MODEL`), `mock` und automatischer Rückfall `auto`.
- WASM-Bridge für LVAR/RPN über SimConnect Client Data Area (MobiFlight/SimBridge):
  Anfragekanal, Timeouts, Wiederverbindung, LVAR-Schreibzugriff über RPN.
- Web-Client ohne Frameworks: Künstlicher Horizont, Rundskalen, Anzeigen, Kippschalter,
  Drehschalter, Variometer, Höhenmesser, Kursanzeiger; drei Formfaktoren.
- Panel-Editor: Drag-and-drop, Rückgängig/Wiederholen, Raster, Kopieren des Layouts
  zwischen Formfaktoren, Speichern auf dem Host.
- Automatische Flugzeugerkennung nach Name und ATC-Modell; die manuelle Auswahl bleibt
  bestehen, bis das Flugzeug im Simulator gewechselt wird.
- Schnelle Smartphone-Verbindung: QR-Code (eigener stdlib-Generator) und
  Liste der Netzwerkadressen.
- Android-Client: WebView-Panel, UDP-Erkennung, Integritätsprüfung.
- Android-APK-Builder in der Distribution: App-Einstellungen (Name, Package-ID,
  Version, Gateway-Adresse), Build über die Webseite `/android.html` und CLI
  `--build-apk`.
- Windows-Installer (NSIS, per-user, ohne Administratorrechte), fertige APK und
  Android-Quellen im Paket.
- Komfort im Cockpit: Panel-Helligkeit in drei Stufen, Kiosk-Modus.
- Profile: Cessna 172S, Cessna 172 Six-Pack, Daher TBM 930, Airbus A320,
  Piper PA-28, LVAR-Demo.

### Behoben

- Ein langsamer oder hängender Client stoppt die Telemetrieauslieferung nicht mehr:
  Jede Verbindung hat ihre eigene Warteschlange (8 Frames) und einen Sender-Thread; alte
  Frames werden verworfen, statt den Bus zu blockieren.
- WebSocket wird mit Code 1002 bei Protokollverletzung geschlossen (unmarkierte,
  fragmentierte und zu große Steuerframes).
- Das Stoppen des Gateways wartet nicht auf einen hängenden Client: Der Close-Frame wird mit
  Timeout gesendet, der Socket in jedem Fall geschlossen.
- POST/PUT lesen den Anfrage-Body immer vollständig aus — die Keep-Alive-Verbindung
  bricht nach dem Start eines APK-Builds nicht mehr.
- APK-Builder: Der Timeout-Wächter greift auch dann, wenn Gradle hängt und nichts
  ausgibt; im App-Namen sind Steuerzeichen verboten.
- Android: Eine Race Condition bei schnellem Neustart der Hostsuche schaltet den neuen
  UDP-Empfänger nicht mehr ab.
- Editor: Bei einem Speicherfehler wird die Revision zurückgerollt; ein zweiter Klick
  startet kein paralleles Speichern.
- Statik: Ein Pfad mit NUL-Byte liefert 404 statt einer Exception, HEAD dupliziert
  nicht den Body, Verbindungsabbrüche durch den Client verschmutzen das Log nicht mit Tracebacks.

- SimConnect: Wenn die Benutzer-`SimConnect.cfg` auf einen
  nicht existierenden Kanal zeigt (häufige Ursache für den Fehler `0x80004005`), wiederholt das Gateway
  die Verbindung automatisch über TCP `127.0.0.1:19999` — den Port,
  auf dem MSFS 2020/2024 lauscht; Adresse und Port werden über
  `--simconnect-host` / `--simconnect-port` konfiguriert.

### Dokumentation

- Vollständiger Dokumentationsindex `docs/README.md`; Entwicklerhandbuch
  `docs/development.md` (Code-Karte, Hinzufügen von Variable/Instrument/Profil/
  Provider/Seite, Tests, Release).
- Die Kataloge `docs/telemetry.md` und `docs/widgets.md` werden aus dem Code
  generiert (`python -m msfs_gateway.docsgen --write`); Test und CI prüfen die Aktualität
  und relative Links.
- `docs/protocol.md` vollständig neu geschrieben: Zugriff, Passwort und QR, alle Endpunkte,
  WebSocket, Assistent, APK-Build, Fehlercodes und Beispiele.
- `docs/architecture.md`, `docs/service.md` (Glossar, Support),
  `docs/profile-schema.md`, README, `android/README.md`,
  `packaging/windows/README.md` aktualisiert; die Dokumentation ist Teil des Installers.

### Sicherheit

- SHA-256-Prüfung kritischer UI-Dateien beim Start und im Browser.
- CSP `default-src 'self'`, Verbot externer Ressourcen, Navigations-Allowlist in
  der Android-WebView.
