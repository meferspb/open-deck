# 🛠️ Development and Internal Design

A document for those who change the code: what lives where, how to add a
variable, instrument, profile, provider, or page, and how to test and release.
User documentation is in [service.md](service.md), and the protocol in
[protocol.md](protocol.md).

## 1. Requirements

- Windows 10/11 (the gateway uses `ctypes` for SimConnect; the rest is
  cross-platform).
- Python **3.11+**; there are no third-party dependencies — only the standard
  library.
- Node.js **20+** — for web client tests (the client itself does not require a
  build).
- JDK 17 + Android SDK + Gradle 8.x — only for building the APK.
- PyInstaller and NSIS — only for the installer.

## 2. Code map

```
msfs_gateway/
  app.py            dependency assembly, lifecycle, CLI modes
  settings.py       CLI arguments, paths, defaults
  telemetry.py      variable registry (keys, types, SimVars, events)
  hub.py            bus: frame, subscriptions, commands, aircraft autodetection
  http_api.py       HTTP: static files, REST, WebSocket upgrade, authorization
  websocket.py      RFC 6455: frames, ping/pong, close, send queue
  auth.py           password, PBKDF2, sessions, QR tokens, attempt limiting
  assist.py         taxi and landing assists (10 Hz)
  profiles.py       validation, storage, atomic profile saving
  legacy.py         adapter for the old v0 profile format
  integrity.py      SHA-256 manifest of critical files
  discovery.py      autodiscovery UDP beacon
  qr.py             QR generator (SVG) on stdlib
  android_build.py  settings, tool lookup, Gradle launch
  docsgen.py        generation of docs/telemetry.md and docs/widgets.md
  sim/              providers: mock, simconnect, client_data, wasm_bridge
web/                panel, editor, login, assist (vanilla ES modules)
profiles/           aircraft JSON profiles
android/            Kotlin client (WebView + UDP discovery)
packaging/windows/  PyInstaller + NSIS
scripts/            build-installer.ps1, check.ps1, verify_qr.py
tests/              unittest (Python) and node:test (JS)
docs/               this and other documentation
```

## 3. How to add a telemetry variable

1. Open `msfs_gateway/telemetry.py`, add a `Variable(...)` to
   `_VARIABLES`: key, type, label, `sim_var`/`sim_unit`, and, if needed,
   `sim_event`, `sim_event_param`, `sim_event_scale`.
2. Verify the SimVar name against the MSFS SDK documentation (case and units
   matter).
3. Update the catalog: `python -m msfs_gateway.docsgen --write`.
4. Run `python -m unittest tests.test_telemetry` and the full suite.
5. If the variable is a control — make sure the event actually changes
   state (`bool` comparison uses the current value).

## 4. How to add an instrument

1. Create `web/js/widgets/my-widget.js`: a class with `update(state)` and
   `destroy()` (see `base.js` and neighboring instruments). Rendering — canvas
   or DOM.
2. Register the type in `web/js/widgets/registry.js`.
3. Add the type to `WIDGET_TYPES`, the required roles to `REQUIRED_BINDINGS`,
   and, if needed, option checks in `msfs_gateway/profiles.py`.
4. Describe the instrument in `msfs_gateway/docsgen.py` (`WIDGET_ORDER`,
   `WIDGET_TITLES`, `WIDGET_DESCRIPTIONS`, `WIDGET_OPTIONS`, example) and
   run `python -m msfs_gateway.docsgen --write`.
5. Check it on all three form factors (phone/small/large tablet) and in the
   editor; add a geometry test in `tests/web/`.

## 5. How to add an aircraft profile

1. Copy a similar profile from `profiles/`, change `id`, `name`, `icao`,
   `sim.match` (glob over `TITLE`/`ATC MODEL`).
2. Check validation: `python -m unittest tests.test_profiles`.
3. Build the `base` layouts + differences for the form factors; make sure the
   rectangles do not go beyond `0..1`.
4. Check in the editor `/editor.html` and on a real aircraft (if MSFS is
   available).
5. Add the profile to the README (list) and to the CHANGELOG.

## 6. How to add a telemetry provider

1. Subclass `SimProvider` (`sim/base.py`) and implement `start`, `stop`,
   `read`, `apply_command`, `connected`; if needed —
   `select_aircraft`, `aircraft_title`, `atc_model`.
2. Register the choice in `sim/__init__.py:create_sim()` and add the value
   to `SIM_CHOICES` (`settings.py`).
3. Thread safety: `read()` and `apply_command()` may be called from different
   threads — use a lock.
4. Add tests with a fake transport (see `tests/test_mock_sim.py`).

## 7. How to add an endpoint

1. Handle the path in `_handle_api_get/post/put` (`http_api.py`).
2. Decide whether it is public or session-protected: public — only in
   `PUBLIC_API_PATHS`; everything else is closed automatically.
3. Respond through `_send_json`/`ApiError`; errors carry a machine-readable
   `code`.
4. Document the endpoint in `docs/protocol.md` (table + example) and in
   `docs/service.md` (API section).
5. Add a test in `tests/` (unit + HTTP integration if needed).

## 8. How to add a page

1. Put the HTML in `web/`, JS in `web/js/`, styles in `web/css/`.
2. The page is **closed** by default (except `/login.html` and its files);
   without a session the server returns `302` to login.
3. Add the link to the panel header (`web/index.html`), then rebuild the
   manifest: `python -m msfs_gateway.integrity --write`.
4. Check on a phone (`?device=phone`) and in kiosk mode.

## 9. Tests and checks

```powershell
pwsh -File scripts/check.ps1       # ruff + format + 250 Python + 35 JS
python -m unittest discover -s tests
node --test "tests/web/*.test.mjs"
python -m msfs_gateway.docsgen --check
python -m msfs_gateway.integrity
```

Test strategy:

- **Pure logic** (validation, profiles, QR, assist controllers,
  authentication) — unit tests without network or MSFS.
- **HTTP/WebSocket** — start `GatewayApplication.start_background()` on
  `127.0.0.1:0` and use `http.client`/raw sockets.
- **SimConnect/WASM** — a fake DLL/transport; a live flight is verified manually.
- **Web** — `node:test` for pure functions (layout, `isConnectionStale`).

## 10. Documentation

- `docs/telemetry.md` and `docs/widgets.md` are **generated** from the code;
  manual edits will be overwritten. Change `docsgen.py` and run `--write`.
- The other documents are manual; when behavior changes, update
  `service.md`, `protocol.md`, `profile-schema.md`, and `CHANGELOG.md`.
- Up-to-date checking is built into `scripts/check.ps1` (docsgen --check).
- Index — [docs/README.md](README.md).

## 11. Build and release

1. Update the version (`msfs_gateway/__init__.py`, `config/android-build.json`,
   `packaging/windows/README.md`).
2. `python -m msfs_gateway.integrity --write` (if critical files changed).
3. `pwsh -File scripts/build-installer.ps1 -Version <x.y.z> -NsisPath <NSIS>`.
4. Check installation/uninstallation and `--set-password` on a clean machine.
5. Build the APK (`android/gradle assembleDebug`) and put it in `android/dist`.
6. Update `CHANGELOG.md`, commit, and tag `v<x.y.z>`.

## 12. Conventions

- Python: stdlib only, `ruff format` formatting, line length 100.
- JS: ES modules, no CDN or build step; `node --check` and `node:test`.
- Kotlin: SDK and stdlib only, no AndroidX.
- Comments and documentation — in English; identifiers — in English.
- Do not add external dependencies unless absolutely necessary: the project is
  designed for air-gapped installation.
