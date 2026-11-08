# 🏗️ Open Deck for MSFS Architecture

This document describes the components, data flows, and key design decisions.
The profile format is covered in [profile-schema.md](profile-schema.md), and the
network protocol in [protocol.md](protocol.md).

---

## 1. High-level diagram

```
┌───────────────────────────── Windows Host (Core Gateway) ─────────────────────────────┐
│                                                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌────────────────────┐   │
│  │  SimProvider  │──▶│      Hub      │──▶│ WebSocket /ws │──▶│  Web client (JS)   │   │
│  │  (mock /      │   │  (broadcast,  │   │               │   │  Android client    │   │
│  │   SimConnect) │   │   commands)   │   ├───────────────┤   └────────────────────┘   │
│  └──────▲────────┘   └──────▲────────┘   │  HTTP /api    │                            │
│         │                   │            │  HTTP / (static)│                          │
│         │ read()            │ profiles   └───────┬───────┘                            │
│         │ apply_command()   │ list/get/save      │                                    │
│  ┌──────┴────────┐   ┌──────┴────────┐          │                                    │
│  │  telemetry.py │   │  profiles.py  │          │  REST + WebSocket on ONE port      │
│  │ (SimVar reg.) │   │  (validation) │          └────────────────────────────────────┘
│  └───────────────┘   └───────────────┘                                               │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ SimConnect API (native, ctypes) — or mock without MSFS
        │
┌───────┴────────┐
│  MSFS 2020/24  │
└────────────────┘
```

---

## 2. Components and responsibilities

### 2.1. `telemetry.py` — canonical variable registry

The single source of truth about quantities: key name, type, unit, SimVar
binding (`sim_var`/`sim_unit`), and write event (`sim_event`). Profiles refer
only to these keys, so renaming a SimVar is a one-place edit.

```python
Variable("power.batteryMaster", "bool", "Master battery",
         sim_var="ELECTRICAL MASTER BATTERY", sim_unit="bool",
         sim_event="TOGGLE_MASTER_BATTERY")
```

### 2.2. `sim/` — telemetry sources (providers)

Common `SimProvider` interface:

| Method | Purpose |
| --- | --- |
| `connected` | whether there is a live connection to the simulator |
| `start()` / `stop()` | the provider's background thread |
| `read()` | a snapshot of values `dict[key, value]` |
| `apply_command(key, value)` | apply a client command |
| `select_aircraft(profile_id)` | switch the aircraft (supported by mock only) |

Implementations:

- **`MockSim`** — a procedural flight: bank/pitch/heading/speed/altitude change
  along smooth sinusoids, fuel is consumed. Needed for development without
  MSFS, demos, and automated tests.
- **`SimConnectSim`** — native SimConnect through `ctypes`. Subscribes to a
  block of numeric datums (`AddToDataDefinition` + `RequestDataOnSimObject`),
  separately to the string `TITLE`/`ATC MODEL`, caches values in `read()`, and
  sends commands as events (`MapClientEventToSimEvent` +
  `TransmitClientEvent`). SimConnect calls, including commands, are made on the
  dispatch thread (`run_on_dispatch`), because the API is not designed for
  multithreaded calls. If the user's `SimConnect.cfg` points to a nonexistent
  channel, the connection is retried over TCP `127.0.0.1:19999` through a
  temporary config (the MSFS 2020/2024 port). Connection to a live MSFS 2020 has
  been verified; live numeric exchange, the WASM module, and the assist in
  flight are the next validation step.

The `create_sim()` factory selects a provider from the `--sim` setting:

- `mock` → always mock;
- `simconnect` → SimConnect only, exit on error;
- `auto` → SimConnect, falling back to mock on failure (the gateway always
  starts).

### 2.3. `hub.py` — telemetry bus

- a single "ticker" thread at the `--telemetry-hz` rate collects `sim.read()`
  and broadcasts the frame to all WebSocket clients;
- each client has its own queue (8 frames) and sender thread: a slow tablet
  does not stop delivery to the others, and old frames are dropped;
- **command rate limiting** (≤30/s per client) — protection against a stuck
  touch;
- `build_message()` normalizes values (round to 3 decimal places, the full set
  of keys), adds `seq`, `ts`, and `sim` metadata.

### 2.4. `profiles.py` + `legacy.py` — aircraft profiles

- `validate_profile()` — strict structure checking (instrument types, bindings,
  commands, rectangles, gauge ranges);
- `ProfileStore` — thread-safe atomic saving (tmp + `fsync` +
  `os.replace`);
- `legacy.adapt()` — converts the "pixel" v0 format from the specification into
  the internal one (coordinates in 0..1 fractions) so old panels load as-is.

### 2.5. `http_api.py` + `websocket.py` — network

- `ThreadingHTTPServer` serves `web/` static files and the REST API and performs
  the WebSocket upgrade on one port — a single firewall rule;
- `websocket.py` — a minimal RFC 6455 implementation (text, ping/pong, close) on
  stdlib;
- `auth.py` — optional password login: PBKDF2 hash, in-memory sessions,
  `HttpOnly` cookie, Bearer tokens, one-time QR tokens, attempt limiting;
- security headers: CSP `default-src 'self'`, `X-Content-Type-Options`,
  `Referrer-Policy`; static files without caching (live development);
- `/api/connect` + `qr.py` — quick phone connection: the host lists its network
  addresses (first `192.168.x`, then `10.x`, `172.16-31.x`), and the QR code is
  drawn by a custom stdlib generator (byte mode, EC L, versions 1–10, all
  masks), without external libraries or the internet.

### 2.5a. `auth.py` — password login

- The password is stored only as a PBKDF2 hash (`config/auth.json`), verified
  with `hmac.compare_digest`; 5 failures per minute from an address → blocking.
- Sessions live in process memory (32 bytes, 12-hour TTL, extended on
  activity); the browser receives an `open_deck_session` cookie (`HttpOnly`,
  `SameSite=Lax`), native clients use Bearer or `?token=` for WebSocket.
- One-time QR tokens (`POST /api/pair`, 10 minutes) let a phone log in without
  entering a password. Such a token is accepted only through `/?pair=`:
  `SessionStore.validate` rejects `pairing` sessions, so it cannot be used as a
  cookie or Bearer token.
- Browser POST/PUT and WebSocket requests whose `Origin` does not match `Host`
  are rejected with `403` (protection against cross-site WebSocket hijacking
  and CSRF); clients without `Origin` (Android, curl) are allowed.
- The `Host` header is additionally checked against localhost, the machine
  name, FQDN, and local IPs. This closes DNS rebinding, where both `Origin`
  and `Host` belong to the attacker's domain.
- Only login, `/api/health`, `/api/integrity`, `/api/donation`, and `/license`
  are publicly accessible; everything else is closed.

### 2.5b. `assist.py` — landing and taxi assists

- **Taxi**: a PI throttle controller by ground speed and a P rudder controller
  by heading; enabled only on the ground, disabled on liftoff/braking/speed
  above 35 kt; "STOP" gives zero throttle and the parking brake.
- **Landing**: ARM enables AP and APR, between 60–15 ft it linearly reduces
  throttle, and on touchdown it disengages AP; TOGA — full throttle. It does
  not touch the elevator.
- A 10 Hz thread reads `sim.read()` and sends commands through
  `Hub.apply_assist_command` (without rate limiting or extra reads).
- This is an auxiliary loop: the final decision and control remain with the
  pilot.

### 2.6. `integrity.py` — donation protection (license condition)

Compares the SHA-256 of five critical files (including `web/js/ui/donation.js`,
`web/css/donation.css`, `config/donation.json`) with the
`integrity/manifest.json` manifest. The host blocks startup on mismatch; the
client (`web/js/ui/integrity.js`) additionally monitors the block's visibility
in the DOM. Author — Viktor Krasnikov ([github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)),
Donat — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

### 2.7. `discovery.py` — host autodiscovery (UDP broadcast)

A background thread sends a JSON beacon (host name, version, `httpPort`,
frequency, profile list) over UDP broadcast (`255.255.255.255` + directed
broadcast of each interface) every N seconds. `listen_once()` is the receiver
for native clients and tests. Browsers do not support UDP, so the web client
does not need it (it already starts from the host itself).

### 2.8. `web/editor.*` — visual panel editor

`/editor.html` + `web/js/editor.js` — a drag-and-drop editor: moving and
resizing instruments, configuring bindings (drop-down lists from the catalog
`GET /api/telemetry/variables` plus `custom.*` declared in the profile), options
(gauges, units, tones), adding from a type palette, and deleting. Saving is done
through `PUT /api/profiles/{id}`. The preview draws real instruments (through the
`widgets/registry.js` registry) with demo values. Form-factor overrides are
edited in the active form factor: if there is no override, the edit goes into
`layout.base`. An edit history (snapshots of `widgets` before a change) provides
undo and redo for dragging, resizing, properties, adding, and deleting; there is
also 1 % grid snapping (Shift temporarily disables it) and one-button copying of
geometry to other form factors.

### 2.8a. Aircraft autodetection

`SimConnectSim` reads `TITLE` and `ATC MODEL` as separate string datums
(`SIMCONNECT_DATATYPE_STRING256`) and stores them in `aircraft.title` /
`aircraft.atcModel`. `hub.py` keeps the `sim.match.title` / `atcModel` rules
(glob, case-insensitive) and selects a profile on every frame if the provider
does not set one itself. The client watches `sim.profileId` in telemetry and
reloads the panel when the aircraft changes; manual selection from the list is
pinned for 5 seconds so it does not conflict with a frame that has not arrived
yet.

### 2.8b. `web/js/ui/comfort.js` — brightness and kiosk

Panel brightness has three levels (100/72/45 %), is stored in `localStorage`, and
is applied via the `data-brightness` attribute on `<html>`: CSS dims only the
instrument scene, while the UI remains readable. Kiosk mode hides the top panel
and status bar, switches the scene to full mode, and leaves a small exit button;
`Esc` restores the UI. Shortcuts: `B` — brightness, `F` and `Esc` — kiosk.

### 2.9. WASM bridge: LVAR/RPN through Client Data Area

Complex aircraft (PMDG, Fenix, FlyByWire, iniBuilds) keep state in their own
variables. A profile declares them in the `variables` block (`source: lvar` or
`rpn`), and the bridge reads/writes them through **SimConnect Client Data Area** —
the WASM module (MobiFlight / SimBridge) publishes data there.

```
hub.build_message()
   └─ hub._custom_values(profile_id)        # 0.25 s cache
        └─ WasmBridge.read_specs(specs)      # wasm_bridge.py
             ├─ read_lvars(names)            # block: name 128 B + double 8 B
             └─ execute_rpn(script)          # Command → Response
                  └─ ClientDataChannel.read_area / write_area   # client_data.py
                       └─ SimConnectClientDataBackend            # simconnect.py
                            └─ run_on_dispatch(...)  # calls on the SimConnect thread
```

Layers:

- **`sim/client_data.py`** — the protocol in synchronous form: request
  correlation by `request_id`, timeouts, re-registration of an area when its
  size grows, and resetting pending requests on disconnect. The transport is
  abstracted (`ClientDataBackend`), so the protocol is tested without MSFS;
  `LoopbackClientDataBackend` is an in-memory implementation for tests and
  demos.
- **`sim/simconnect.py`** — `SimConnectClientDataBackend`: `MapClientDataNameToID`,
  `AddToClientDataDefinition`, `RequestClientData`, `SetClientData`. All calls
  are made on the dispatch thread through `run_on_dispatch` (SimConnect is not
  designed for multithreaded calls), and responses arrive in
  `SIMCONNECT_RECV_ID_CLIENT_DATA`.
- **`sim/wasm_bridge.py`** — the LVAR block layout, RPN commands, and LVAR writes
  through `(<value>) (>L:NAME, number)`.

Default areas: `MobiFlight.LVars`, `MobiFlight.Command`,
`MobiFlight.Response`; for a different module version they are overridden by
constants in `wasm_bridge.py`.

It is enabled automatically for the `simconnect` provider (the `--no-wasm` flag
disables it). If the WASM module is not installed, responses do not arrive:
after two consecutive timeouts the `ClientDataChannel` circuit breaker
temporarily (30 s) stops polling, so the telemetry stream is not blocked on
every frame. The `custom.*` keys are simply absent from the frame — instruments
honestly show "--", and SimVar telemetry keeps working. The LVAR block is
limited to 56 elements (7616 bytes) so it fits within
`MaxRecvData`/`MaxSendData` = 8192. In mock mode values are taken from the
profile's `initial`. Built-in SimVars that are missing from the accepted
SimConnect definition or are outdated are returned as `null` rather than `0`:
the panel shows "--", and the assist does not mistake them for real zeros.

**Verification status:** the protocol and area accounting are covered by tests
(MobiFlight emulation through an in-memory transport), and the build and startup
have been verified; a live flight with MSFS + the WASM module has not been run
yet — this is the only step that requires an installed simulator.

### 2.10. `android_build.py` — building the Android APK from the distribution

The installed app contains the Android sources (`android/`), and after a build
the ready APK is in `android/dist`. The page `/android.html` and the API
`/api/android/*` let you change the app name, package id, version, and default
gateway address, run `gradle assembleDebug`, and download the fresh APK.
Settings are in `config/android-build.json`; the same values are passed into the
build as `-P…` and end up in `BuildConfig`/the Android manifest.

Tool lookup: settings → `JAVA_HOME` / `ANDROID_HOME` → typical paths.
If the user profile is not writable (strict policies, sandboxes), the Gradle
cache, `TMP`, and the debug keystore are automatically redirected to the
distribution directory (`.gradle-home`, `.tmp`, `.android-home`) — the build
keeps working. CLI without a browser: `OpenDeck.exe --build-apk [config.json]`.

---

## 3. Data flow

### 3.1. Telemetry (push)

```
MockSim/SimConnectSim._loop()
   └─ sim.read()                        # snapshot of values
        └─ hub.build_message()          # normalization + seq/ts/sim
             └─ hub._broadcast_text()   # JSON into each WebSocket queue
                  └─ web: handleMessage('telemetry') → store → panel-view → widgets
```

### 3.2. Command (request/ack)

```
web: toggle-switch.onClick()
   └─ socket.command(key, value)        # {type:'command', id, key, value}
        └─ hub.handle_command()         # validation + rate limit
             └─ sim.apply_command()     # mock / SimConnect
                  └─ ack {type:'ack', id, ok, value}   (over WebSocket)
                       └─ client waits for confirmation via telemetry
```

### 3.3. Profile (pull)

```
web: api.listProfiles() → GET /api/profiles
   └─ api.getProfile(id) → GET /api/profiles/{id}
        └─ profiles.load_profile_file() → legacy.adapt_if_needed() → ensure_valid()
             └─ panel-view.mount(profile) → createWidgetInstance() by type
```

### 3.4. Autodiscovery (UDP push)

```
DiscoveryBeacon._loop()                      # daemon thread
   └─ payload() {name, version, httpPort, profiles, auth?, ts}
        └─ sendto(255.255.255.255:8761) + directed broadcasts
             └─ Android/native client: listen_once() → http://<ip>:<port>/
```

---

## 4. Key design decisions

| Decision | Why |
| --- | --- |
| Python stdlib only | air-gapped: `pip install` is unavailable; one interpreter is already installed |
| One port for HTTP+WS | one firewall rule, simpler diagnostics |
| WebSocket without an external library | control over the protocol, no dependencies |
| Profile uses 0..1 coordinates, not pixels | one profile for all form factors |
| `layout.base` + overrides | phone/tablet specify only the differences |
| Canonical SimVar registry | decouples profiles from a specific bridge |
| Client-side smoothing (Smoother) | 60 fps animation over a 20–30 Hz network |
| Widget draws canvas by `clientWidth` | honest HiDPI scaling in the preview |
| `auto` provider | the gateway starts without MSFS and without config edits |
| UDP autodiscovery beacon | Android finds the host without a manual IP; browsers do not need it |

---

## 5. MVP boundaries and next steps

What **already exists**: a stdlib gateway, WebSocket with per-client queues,
mock/SimConnect (+ TCP fallback), LVAR/RPN WASM bridge, 9 instrument types,
3 form factors, profiles with validation and atomic saving, an editor with
undo/redo and layout copying, UDP autodiscovery, an Android client, an APK
builder in the distribution, a Windows installer, password login with QR,
landing and taxi assist, integrity checking, 250 Python and 35 JS tests.

Next steps (see the README "Roadmap"):

- live flight validation: SimConnect/WASM on a real aircraft, assist in the
  air and on the ground;
- release signing of the APK (keystore in the builder settings);
- mDNS (Bonjour) as an alternative to the UDP beacon;
- route taxiing using airport charts (for now the assist holds only
  speed and heading);
- telemetry recording/replay for demos and profiling.
