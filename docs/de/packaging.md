# Installer für Windows

Eine einzige Datei `OpenDeck-Setup-<Version>.exe`: Doppelklick → „Weiter" →
fertig. Administratorrechte sind nicht nötig, Python und Internet nicht
erforderlich.

## Was bei der Installation geschieht

| | |
|---|---|
| Verzeichnis | `%LOCALAPPDATA%\OpenDeck` (im Benutzerprofil, ohne UAC) |
| Inhalt | `OpenDeck.exe` — Gateway mit eingebettetem Python 3.13 und Standardbibliothek |
| | `web/` — Web-Client (Panel und Editor), `profiles/` — Flugzeugprofile |
| | `config/donation.json` — Autorendaten, `integrity/` — Integritätsmanifest |
| | `android/` — Android-Quellen und nach dem Build die fertige APK (`android/dist/OpenDeck-Android-<Version>.apk`), `config/android-build.json` — Einstellungen für den APK-Build |
| | `docs/` — vollständige Dokumentation (Dienst, Protokoll, Variablen, Instrumente, Profil-Schema) |
| Verknüpfungen | Desktop, Startmenü (Start, Panel im Browser, Android-APK-Build, „Passwort festlegen", Deinstallation) |
| Deinstallation | „Programme und Funktionen" oder die Verknüpfung „Deinstallieren" |

Die Daten liegen neben der `.exe`, daher können Profile und Autorendaten ohne
Neuinstallation bearbeitet werden (nach der Änderung geschützter Dateien muss
das Manifest neu gebaut werden, siehe Root-README).

## Build (auf der Entwicklermaschine, Internet wird einmal benötigt)

Anforderungen:

- Python 3.11+ und PyInstaller: `python -m pip install pyinstaller`
- NSIS 3.x: `makensis.exe` in `PATH`, oder `NSIS_HOME`, oder `-NsisPath`

```powershell
# aus dem Repository-Stammverzeichnis
pwsh -File scripts/build-installer.ps1 -Version 0.1.0 -NsisPath "C:\Program Files (x86)\NSIS"
```

Das Skript Schritt für Schritt: baut das Integritätsmanifest neu → führt die
Tests aus → baut `build/pyinstaller/dist/OpenDeck` (PyInstaller, onedir) → legt
`web/`, `profiles/`, `config/`, `integrity/` daneben → prüft, dass die `.exe`
startet (`--help`) → kompiliert den Installer nach
`dist/OpenDeck-Setup-<Version>.exe`.

Flags: `-SkipTests`, `-NsisPath <Ordner>`, `-Version 0.2.0`.

Das Skript prüft außerdem, dass der Installer gebaut wurde, und gibt den
endgültigen Pfad und die Größe aus. Die vollständige Schrittliste steht am
Anfang der Datei `scripts/build-installer.ps1`.

Passwortanmeldung: Die Verknüpfung „Passwort festlegen" startet
`OpenDeck.exe --set-password` und fragt das Passwort in der Konsole ab; der Hash
wird in `config/auth.json` neben der `.exe` gespeichert. Das Löschen der Datei
öffnet den Zugriff wieder ohne Anmeldung.

## Vor der Veröffentlichung

1. `config/donation.json` prüfen: Autor Viktor Krasnikov, Donat-Link —
   `https://taps.uz/open_deck_fs`.
2. Das Manifest neu bauen: `python -m msfs_gateway.integrity --write`
   (das Build-Skript erledigt das selbst, aber eine Prüfung schadet nicht).
3. Den Installer auf einer sauberen Maschine testen: Installation ohne
   Administratorrechte, Start, Zugriff auf das Panel vom Smartphone im selben
   Netzwerk, Deinstallation.

## Stille Installation / Bereitstellung

```bat
OpenDeck-Setup-0.1.0.exe /S /D=C:\Tools\OpenDeck
Uninstall.exe /S
```

`/D=` muss zuletzt und ohne Anführungszeichen stehen (NSIS-Einschränkung).

## Einschränkungen

- Der Installer ist nicht signiert: SmartScreen kann „unbekannter Herausgeber"
  warnen — „Weitere Informationen" → „Trotzdem ausführen". Für ein Release ist
  ein Code-Signaturzertifikat (EV/OV) erforderlich.
- Es wird keine Firewall-Regel hinzugefügt (dafür wären Administratorrechte
  nötig). Beim ersten Start fragt Windows nach dem Netzzugriff — für private
  Netzwerke erlauben, sonst können sich Clients nicht verbinden.
- Installation pro Benutzer: Die App ist nur für den aktuellen Benutzer
  sichtbar.
- Registry/Verknüpfungen werden in `HKCU` erstellt — auf Maschinen mit strengen
  Richtlinien (AppLocker, Schreibverbot im Profil) kann die Installation
  blockiert werden; verwenden Sie dann die portable Variante: Entpacken Sie das
  Verzeichnis `build/pyinstaller/dist/OpenDeck` und starten Sie die `.exe` von
  dort.
