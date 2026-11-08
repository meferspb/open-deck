# 📱 Open Deck for MSFS — Android-Client

Eine native Android-App (Kotlin, ohne Fremdbibliotheken), die ein Smartphone
oder Tablet in eine MSFS-Instrumententafel verwandelt:

- **Autoerkennung** des Windows-Hosts über UDP-Beacon (Port 8761) und manuelle
  IP-Eingabe;
- **Panel-Rendering** — die WebView lädt den Web-Client vom Host, daher erhält
  die Android-Version automatisch alle Profile, Instrumente, den Editor und
  UI-Updates;
- **drei Formfaktoren** werden nach Bildschirmgröße gewählt
  (`smallestScreenWidthDp`): phone / tablet-sm / tablet-lg;
- **Integritätsprüfung** vor der Anzeige des Panels (Lizenzbedingung zum Schutz
  des Autoren-Supportblocks);
- **Passwortanmeldung**: Wenn auf dem Gateway ein Passwort aktiviert ist, zeigt
  die WebView die Anmeldeseite; die Sitzung wird im WebView-Cookie gespeichert
  und übersteht einen Neustart der App; Hosts mit Passwort sind mit einem
  Schloss markiert 🔒;
- **Kiosk-Modus**: immersives Vollbild, Bildschirm bleibt an, Drehung ohne
  Neuladen des Panels;
- **Autoren-Supportblock** auf dem Verbindungsbildschirm (die Daten kommen vom
  Host);
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

## Build-Anforderungen

| Komponente | Version |
| --- | --- |
| JDK | 17+ |
| Android SDK | platform 35, build-tools 35.x |
| Gradle | 8.9+ (Projekt gebaut mit 8.10.2) |
| Android Gradle Plugin | 8.7.3 |
| Kotlin | 2.0.21 |

`minSdk 26` (Android 8.0), `targetSdk 35`.

## Build

In diesem Repository verifiziert: **JDK 17.0.20.1 (Temurin), Gradle 8.10.2,
AGP 8.7.3, Kotlin 2.0.21, Android SDK platform 35 / build-tools 35.0.0**.
`assembleDebug` und `lintDebug` laufen durch: **0 Fehler**, 3 informative
Warnungen (Cleartext im lokalen Netzwerk, Overdraw, Backup-Rules).

```bash
cd android

# der SDK-Pfad kann über ANDROID_HOME oder local.properties gesetzt werden:
#   echo "sdk.dir=/path/to/android-sdk" > local.properties

# Variante 1: Android Studio — das Verzeichnis android/ öffnen und Run drücken

# Variante 2: Kommandozeile (Gradle 8.9+)
gradle wrapper --gradle-version 8.10.2   # einmalig, erstellt gradlew
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk

# Installation auf dem Gerät
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Nach dem Build erscheint die Debug-APK in
`android/dist/OpenDeck-Android-<Version>.apk` (Debug-Signatur — für die
Installation auf dem eigenen Gerät; für eine Veröffentlichung ist ein
Release-Schlüssel erforderlich).

> **Hinweis zu air-gapped Builds.** Die App verwendet keine
> Fremdbibliotheken: nur Android SDK und Kotlin stdlib. Aber Gradle lädt AGP und
> das Kotlin-Plugin dennoch aus Maven herunter. Wenn die Build-Maschine isoliert
> ist, übertragen Sie den Gradle-Cache (`~/.gradle/caches`) von einer Maschine,
> auf der der Build bereits ausgeführt wurde, oder bauen Sie die APK im Voraus
> und verteilen Sie sie als Datei. In der Gateway-Distribution (`android/` +
> gebaute APK) ist der Build über die Seite `/android.html` verfügbar.

## So funktioniert es

```
MainActivity
├── DiscoveryClient  → UDP 8761, JSON-Beacon des Hosts (Name, IP, Port, Profile, auth)
├── HostStore        → SharedPreferences: letzter Host
├── HostApi          → GET /api/health, /api/integrity, /api/donation
└── WebView          → http://<host>:<port>/?device=<preset>&frame=0
```

Startablauf:

1. Die App startet einen UDP-Empfänger und zeigt die gefundenen Hosts an (bei
   Hosts mit Passwort — ein Schloss).
2. Der Benutzer wählt einen Host aus oder gibt die Adresse manuell ein, wenn das
   Netzwerk Broadcast blockiert.
3. Vor der Anzeige des Panels wird `GET /api/integrity` ausgeführt: Wenn der
   Host eine Verletzung der UI-Integrität meldet, wird das Panel mit einer
   Meldung blockiert.
4. Das Panel öffnet sich in der WebView. Wenn das Gateway ein Passwort
   verlangt, zeigt die WebView `/login.html`; nach der Anmeldung wird das Cookie
   gespeichert, und das Panel öffnet sich ohne erneute Eingabe.
5. Die Schaltfläche „Assistent" in der Panel-Kopfzeile öffnet `/assist.html`
   (Landen und Rollen); sie funktioniert auch auf dem Smartphone.

## Struktur

```
android/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle.properties
├── gradle/wrapper/gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/opendeck/msfs/
        │   ├── MainActivity.kt     # Bildschirme, WebView, Integritätssperre,
        │   │                       # Anmelde-Cookie, Öffnen des Assistenten
        │   ├── DiscoveryClient.kt  # UDP-Empfänger für Beacons (Thread-Generationen)
        │   ├── HostApi.kt          # HTTP-Prüfungen und Spenden-Daten
        │   └── HostStore.kt        # letzter Host in SharedPreferences
        └── res/
            ├── layout/activity_main.xml, view_setup.xml
            ├── values/strings.xml, colors.xml, themes.xml
            ├── drawable/…          # open_deck_logo.png, Karten, Spenden-Plakette
            └── xml/network_security_config.xml
```

## Debugging

- **Host wird nicht gefunden**: Smartphone und PC im selben Subnetz, auf dem PC
  die Firewall für private Netzwerke und Port 8760 erlaubt; der Beacon geht an
  UDP 8761. Geben Sie die Adresse manuell ein (`192.168.1.10:8760`).
- **„Anmeldung erforderlich"**: Auf dem Gateway ist ein Passwort aktiviert —
  geben Sie es auf der Anmeldeseite ein; der QR-Code vom Panel meldet ohne
  Passwort an (10 Minuten).
- **Integritätsprüfung schlägt fehl**: Die UI-Dateien auf dem Host wurden
  geändert — bauen Sie das Manifest neu
  (`python -m msfs_gateway.integrity --write`).
- **Logs**: `adb logcat -s OpenDeckDiscovery OpenDeck`, WebView-Logs — über die
  Chrome DevTools (`chrome://inspect`).
- **APK-Installation**: Erlauben Sie die Installation aus unbekannten Quellen;
  für einen Release-Build ist eine eigene Signatur erforderlich.

## Sicherheit

- HTTP ohne TLS: Das Netzwerk ist lokal und vertrauenswürdig,
  `usesCleartextTraffic` ist bewusst aktiviert; das Passwort schützt die
  Anmeldung, verschlüsselt aber nicht den Verkehr.
- WebView: Navigations-Allowlist, `file:`/`content:` verboten, gemischte Inhalte
  verboten, Cookies — nur die `HttpOnly`-Sitzung des Gateways.
- Die Spenden-Daten kommen vom Host; der Block kann nicht entfernt werden
  (Lizenzbedingung).

## Einschränkungen und nächste Schritte

- Das Panel wird vom Web-Client des Hosts gerendert: Das bietet 100 %
  Funktionsparität, erfordert aber eine WebView (auf jedem Android 8+
  vorhanden).
- Vollständig natives Compose-Rendering der Instrumente — eine separate Engine;
  das Protokoll (`/api/profiles`, `/ws`) ist dafür bereits fertig.
- Kein Vordergrunddienst: Bei längerem Minimieren kann Android die WebView
  anhalten — halten Sie für den Kiosk die App auf dem Bildschirm.
