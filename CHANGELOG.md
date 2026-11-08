# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
versions — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Changed

- Full rebranding to **Open Deck for MSFS**: product name, web interfaces,
  Android app (`com.opendeck.msfs`), executables, installer,
  documentation, and aircraft profiles.
- Logo and app icons generated from `docs/pic1.jpg`; files
  `web/img/open-deck-mark.jpg`, `web/favicon.ico`, Android drawables, and
  `packaging/windows/open-deck.ico`.

### Added

- **Donation** link — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) — in the web panel,
  editor, login screen, assistant, Android UI, README, and documentation.
- Author **Viktor Krasnikov** and the repository
  [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) are credited.

### Fixed

- SimConnect: the field order of `SIMCONNECT_RECV_SIMOBJECT_DATA` now matches
  `SimConnect.h` (`dwFlags`/`dwEntryNumber`/`dwOutOf`/`dwDefineCount`) — without
  this, live numeric telemetry did not update.
- SimConnect: commands are executed on the dispatch thread; event IDs
  are reset on reconnect; failed `AddToDataDefinition` calls no longer
  shift the indices of the other datums.
- WASM/Client Data: a circuit breaker after timeouts and an LVAR block of ≤ 56 elements,
  so that a missing WASM module does not block the telemetry stream.
- The QR token is no longer accepted as a regular session and does not extend the TTL.
- Added an `Origin` check for browser POST/PUT and WebSocket, as well as
  a `Host` check against local names/IPs (closes DNS rebinding); `--allow-host`
  was added for access via your own DNS name.
- Closed an open redirect in `login.js` via a backslash in `next`.
- Request body errors no longer leave a keep-alive connection in a
  desynchronized state; a limit on concurrent connections was added.
- `pair`/`token` tokens are redacted in the request log.
- Assistant: missing altitude/speed/heading is not substituted with zero; AP
  rolls back if APR did not engage; on loss of connection the modes are turned off;
  `stop` reports an error if commands were not sent.
- Telemetry: built-in SimVars that are absent from the SimConnect definition or
  are deprecated are served as `null` (the UI shows `--`).
- SimVar accuracy: `TURB ENG MAX TORQUE PERCENT:1` (current torque as a % of
  maximum) and `RADIO HEIGHT` instead of height above ground.
- The QR dialog recreates a one-time token on open and when the TTL expires.
- The editor clears history when switching profiles and warns about unsaved
  changes.
- Android builder: allowlist for `extraGradleArgs`, type checks, drive-relative
  `outputDir` disallowed, safe `appName`.
- Android: a full URL with a port is accepted again on manual input.
- SimConnect: reconnection survives an `OSError` from a temporary config;
  thread shutdown is more robust.
- The auto-discovery beacon, when oversized, is sent without the profile list
  instead of being skipped entirely.
- Growth of in-memory limiters is bounded; REST commands now have a per-IP rate limit.
- When the password is disabled, the console warns about open access on the LAN.

## [0.1.0] — 2026-11-01

First public release.

### Added

- **Landing and taxi assistant**: speed/heading hold on the ground,
  ARM/DISARM/TOGA for an ILS approach, automatic retard at 60–15 ft,
  AP disengagement on touchdown; the `/assist.html` page and the `/api/assist*` API.
- **Password login** (6 characters minimum): PBKDF2 hash in `config/auth.json`,
  12-hour sessions in an `HttpOnly` cookie, Bearer tokens, one-time
  QR login from a phone, an attempt limit, and brute-force protection.
- Python gateway (stdlib only): HTTP + WebSocket (RFC 6455) on a single port,
  UDP auto-discovery, aircraft profiles with a JSON schema and validation.
- Telemetry providers: `simconnect` (ctypes, string datums `TITLE` and
  `ATC MODEL`), `mock`, and automatic `auto` fallback.
- WASM LVAR/RPN bridge via SimConnect Client Data Area (MobiFlight/SimBridge):
  request channel, timeouts, reconnection, LVAR writes via RPN.
- Framework-free web client: attitude indicator, circular gauges, annunciators,
  toggle switches, rotary selector, variometer, altimeter, heading indicator;
  three form factors.
- Panel editor: drag-and-drop, undo/redo, grid, copying layouts
  between form factors, saving to the host.
- Aircraft auto-detection by title and ATC model; manual selection sticks
  until the aircraft changes in the simulator.
- Quick phone connection: QR code (own stdlib generator) and
  a list of network addresses.
- Android client: WebView panel, UDP discovery, integrity check.
- Android APK builder in the distribution: app settings (name, package id,
  version, gateway address), building from the `/android.html` web page and the
  `--build-apk` CLI.
- Windows installer (NSIS, per-user, no administrator rights), a ready APK, and
  the Android sources inside.
- Cockpit comfort: three-step panel brightness, kiosk mode.
- Profiles: Cessna 172S, Cessna 172 Six-Pack, Daher TBM 930, Airbus A320,
  Piper PA-28, LVAR demo.

### Fixed

- A slow or hung client no longer stops telemetry broadcast:
  each connection has its own queue (8 frames) and sender thread; old
  frames are dropped instead of blocking the bus.
- WebSocket closes with code 1002 on protocol violation (unmasked,
  fragmented, and oversized control frames).
- Gateway shutdown does not wait for a hung client: the close frame is sent with
  a timeout, and the socket is closed either way.
- POST/PUT always drain the request body — a keep-alive connection no longer
  breaks after starting an APK build.
- APK builder: the timeout watchdog fires even if Gradle hangs and prints
  nothing; control characters are disallowed in the app name.
- Android: a race during a fast restart of host discovery no longer kills the new
  UDP receiver.
- Editor: on a save error the revision rolls back, and a second click does not
  start a parallel save.
- Static files: a path with a NUL byte returns 404 instead of throwing, HEAD does not
  duplicate the body, and client connection drops no longer clutter the log with tracebacks.

- SimConnect: if the user's `SimConnect.cfg` points to a
  nonexistent channel (a common cause of error `0x80004005`), the gateway
  automatically retries connecting over TCP `127.0.0.1:19999` — the port
  that MSFS 2020/2024 listens on; the address and port are configurable via
  `--simconnect-host` / `--simconnect-port`.

### Documentation

- Complete documentation index `docs/README.md`; developer guide
  `docs/development.md` (code map, adding a variable/instrument/profile/
  provider/page, tests, release).
- The `docs/telemetry.md` and `docs/widgets.md` catalogs are generated from code
  (`python -m msfs_gateway.docsgen --write`); a test and CI check up-to-dateness
  and relative links.
- Completely rewritten `docs/protocol.md`: access, password and QR, all endpoints,
  WebSocket, assistant, APK build, error codes, and examples.
- Updated `docs/architecture.md`, `docs/service.md` (glossary, support),
  `docs/profile-schema.md`, README, `android/README.md`,
  `packaging/windows/README.md`; documentation is included in the installer.

### Security

- SHA-256 verification of critical UI files at startup and in the browser.
- CSP `default-src 'self'`, external resources disallowed, navigation allow-list in the
  Android WebView.
