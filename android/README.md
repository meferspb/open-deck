# 📱 Open Deck for MSFS — Android Client

A native Android app (Kotlin, no third-party libraries) that
turns a phone or tablet into an MSFS instrument panel:

- **auto-discovery** of the Windows host via UDP beacon (port 8761) and manual IP entry;
- **panel rendering** — the WebView loads the web client from the host, so the
  Android version automatically gets all profiles, instruments, the editor, and
  UI updates;
- **three form factors** selected by screen size (`smallestScreenWidthDp`):
  phone / tablet-sm / tablet-lg;
- **integrity check** before showing the panel (a license condition on protecting
  the author support block);
- **password login**: if a password is enabled on the gateway, the WebView shows
  the login page; the session is stored in a WebView cookie and survives an app
  restart; hosts with a password are marked with a lock 🔒;
- **kiosk mode**: full-screen immersive, the screen stays on, rotation without
  reloading the panel;
- **author support block** on the connection screen (the details come from the host);
- **Donation:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

## Build requirements

| Component | Version |
| --- | --- |
| JDK | 17+ |
| Android SDK | platform 35, build-tools 35.x |
| Gradle | 8.9+ (the project is built with 8.10.2) |
| Android Gradle Plugin | 8.7.3 |
| Kotlin | 2.0.21 |

`minSdk 26` (Android 8.0), `targetSdk 35`.

## Building

Verified in this repository: **JDK 17.0.20.1 (Temurin), Gradle 8.10.2,
AGP 8.7.3, Kotlin 2.0.21, Android SDK platform 35 / build-tools 35.0.0**.
`assembleDebug` and `lintDebug` pass: **0 errors**, 3 informational
warnings (cleartext on the local network, overdraw, backup-rules).

```bash
cd android

# the SDK path can be set via ANDROID_HOME or local.properties:
#   echo "sdk.dir=/path/to/android-sdk" > local.properties

# option 1: Android Studio — open the android/ directory and click Run

# option 2: command line (Gradle 8.9+)
gradle wrapper --gradle-version 8.10.2   # once, creates gradlew
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk

# install on a device
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

After building, the debug APK appears in `android/dist/OpenDeck-Android-<version>.apk`
(debug signature — for installing on your own device; publishing requires a
release key).

> **About air-gapped builds.** The app uses no third-party libraries:
> only the Android SDK and Kotlin stdlib. But Gradle still downloads AGP and the
> Kotlin plugin from Maven. If the build machine is isolated, transfer the
> Gradle cache (`~/.gradle/caches`) from a machine where the build has already run, or
> build the APK in advance and distribute it as a file. In the gateway distribution
> (`android/` + the built APK), the build is available from the `/android.html` page.

## How it works

```
MainActivity
├── DiscoveryClient  → UDP 8761, host JSON beacon (name, IP, port, profiles, auth)
├── HostStore        → SharedPreferences: last host
├── HostApi          → GET /api/health, /api/integrity, /api/donation
└── WebView          → http://<host>:<port>/?device=<preset>&frame=0
```

Startup sequence:

1. The app starts a UDP receiver and shows discovered hosts
   (hosts with a password have a lock).
2. The user selects a host or enters the address manually if the network blocks
   broadcast.
3. Before showing the panel, `GET /api/integrity` is performed: if the host reports
   a UI integrity violation, the panel is blocked with a message.
4. The panel opens in the WebView. If the gateway requires a password, the WebView
   shows `/login.html`; after login the cookie is saved and the panel
   opens without re-entering it.
5. The "Assistant" button in the panel header opens `/assist.html` (landing and
   taxi); it also works on a phone.

## Structure

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
        │   ├── MainActivity.kt     # screens, WebView, integrity lock,
        │   │                       # login cookie, opening the assistant
        │   ├── DiscoveryClient.kt  # UDP beacon receiver (thread generations)
        │   ├── HostApi.kt          # HTTP checks and donation details
        │   └── HostStore.kt        # last host in SharedPreferences
        └── res/
            ├── layout/activity_main.xml, view_setup.xml
            ├── values/strings.xml, colors.xml, themes.xml
            ├── drawable/…          # open_deck_logo.png, cards, donation banner
            └── xml/network_security_config.xml
```

## Debugging

- **Host not found**: the phone and PC are on the same subnet, the firewall on the PC
  allows private networks and port 8760; the beacon goes to UDP 8761.
  Enter the address manually (`192.168.1.10:8760`).
- **"Login required"**: a password is enabled on the gateway — enter it on the login
  page; the QR code from the panel logs in without a password (10 minutes).
- **Integrity check fails**: the UI files on the host have been modified —
  rebuild the manifest (`python -m msfs_gateway.integrity --write`).
- **Logs**: `adb logcat -s OpenDeckDiscovery OpenDeck`; WebView logs via Chrome
  DevTools (`chrome://inspect`).
- **Installing the APK**: allow installation from unknown sources; a
  release build needs your own signature.

## Security

- HTTP without TLS: the network is local and trusted, `usesCleartextTraffic` is enabled
  deliberately; the password protects login but does not encrypt traffic.
- WebView: navigation allow-list, `file:`/`content:` disallowed, mixed
  content disallowed, cookies — only the gateway's `HttpOnly` session.
- Donation details come from the host; the block cannot be removed (license condition).

## Limitations and next steps

- The panel renders the host's web client: this gives 100% feature parity but requires
  a WebView (available on any Android 8+).
- A fully native Compose rendering of instruments is a separate engine; the protocol
  (`/api/profiles`, `/ws`) is already ready for it.
- No foreground service: after being backgrounded for a long time, Android may suspend the
  WebView — for kiosk use, keep the app on screen.
