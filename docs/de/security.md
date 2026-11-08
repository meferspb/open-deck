# Sicherheitsrichtlinie

## Bedrohungsmodell

Open Deck for MSFS ist für ein **vertrauenswürdiges lokales Netzwerk** ausgelegt
(Heim-WLAN, isoliertes Segment im Cockpit, air-gapped Rechner). Standardmäßig:

- laufen HTTP und WebSocket **ohne TLS** (das Passwort schützt die Anmeldung,
  verschlüsselt aber nicht den Verkehr);
- ist der UDP-Beacon der Autoerkennung unsigniert — jeder Host im Netzwerk kann
  sich als Gateway ausgeben;
- vertraut der Client den Dateien, die der Host ausliefert (die SHA-256-Prüfung
  schützt nur den Spendenblock und die UI-Integrität, nicht die Authentizität
  des Servers).

**Setzen Sie das Gateway nicht dem Internet aus** und starten Sie es nicht in
Netzwerken mit nicht vertrauenswürdigen Geräten. Für Gastnetzwerke verwenden Sie
ein separates VLAN oder fügen Sie einen eigenen Reverse-Proxy mit
Authentifizierung hinzu.

## Was bereits umgesetzt ist

- **optionale Passwortanmeldung**: PBKDF2-Hash (210.000 Iterationen) in
  `config/auth.json`, Sitzungen mit 12 Stunden TTL, Cookie `HttpOnly`,
  `SameSite=Lax`, Bearer für native Clients, Limit von 5 Versuchen pro Minute,
  einmalige QR-Token für 10 Minuten (nur über `/?pair=` akzeptiert);
- Integritätsprüfung kritischer Dateien (SHA-256) beim Host-Start und im
  Browser. Dies ist eine Barriere gegen versehentliche/absichtliche Änderungen,
  kein kryptografischer Schutz: Das Manifest lässt sich mit `--write` neu
  berechnen;
- CSP `default-src 'self'`, Verbot externer Ressourcen;
- Begrenzung der Anfrage-Body-Größe, Validierung von Profilen und Befehlen;
- CORS deaktiviert: Eine Drittseite kann API-Antworten nicht lesen;
- `Origin`-Prüfung für Browser-POST/PUT und WebSocket: Ein fremder Origin erhält
  `403` (Clients ohne Origin sind erlaubt);
- `Host`-Prüfung gegen eine Liste lokaler Namen und IPs — Schutz gegen
  DNS-Rebinding; ein unbekannter Host erhält `403`;
- ohne Authentifizierung bleiben nur die Anmeldeseite, `/api/health`,
  `/api/integrity` und `/api/donation` (Lizenzanforderungen). Wenn kein Passwort
  gesetzt ist, gibt das Gateway eine Warnung in der Konsole aus;
- Android: Allowlist für WebView-Navigation, nur `http(s)`-Links in den
  Spenden, deaktivierter File-/Content-Zugriff.

## Schwachstelle melden

Bitte **eröffnen Sie kein öffentliches Issue**. Verwenden Sie einen privaten
Kanal:

- GitHub → Security → **Report a vulnerability** (Security Advisories), oder
- eine E-Mail an `security@example.invalid` (ersetzen Sie sie vor der
  Veröffentlichung durch eine echte Adresse).

Geben Sie die Version, Schritte zur Reproduktion und das erwartete/tatsächliche
Verhalten an. Wir antworten innerhalb von 7 Tagen.

## Unterstützte Versionen

| Version | Unterstützung |
| --- | --- |
| 0.1.x | ja |

## Projektunterstützung

- Autor: Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)
- Donat: [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
