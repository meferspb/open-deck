# 🔌 Protocolo de red de Open Deck for MSFS

Toda la comunicación pasa por un único puerto TCP (`8760` por defecto):

- **Archivos estáticos HTTP** — archivos de `web/` (panel, editor, inicio de
  sesión, asistente);
- **API REST** — perfiles, telemetría, comandos, asistente, compilación del APK;
- **WebSocket `/ws`** — flujo de telemetría y confirmaciones de comandos.

## 0. Convenciones

- URL base: `http://<host>:<port>`; todas las rutas son relativas.
- JSON es UTF-8, `Content-Type: application/json; charset=utf-8`.
- Respuestas de la API: `Cache-Control: no-store`; archivos estáticos:
  `no-cache`.
- **CORS está desactivado intencionadamente**: la API está pensada para clientes
  del mismo origen, y una página de terceros no puede leer las respuestas.
- **Protección de mismo origen**: si el navegador envía `Origin`, su host y su
  puerto efectivo deben coincidir con `Host`. De lo contrario, las peticiones
  `POST`/`PUT` y WebSocket reciben `403` `origin_not_allowed`. Los clientes sin
  `Origin` (Android, curl) se permiten.
- **Lista de hosts permitidos**: `Host` debe apuntar a localhost, al nombre de la
  máquina, al FQDN, a una IP local o a un nombre de `--allow-host`; de lo
  contrario `403 host_not_allowed`. Esto protege contra DNS rebinding.
- Límite del cuerpo de la petición — **2 MiB**; `Content-Length` desconocido →
  `411`.
- La contraseña (si está activada) y las sesiones se describen en la sección 2.
- La versión del protocolo en la baliza de autodescubrimiento es `protocol: 1`.

---

## 1. Acceso: público y bajo sesión

Si no hay contraseña configurada, todo está disponible. Si hay una configurada,
solo la página de inicio de sesión, sus archivos y los datos de servicio
requeridos por la licencia están abiertos sin sesión:

| Ruta | Acceso | Propósito |
| --- | --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | público | página de inicio de sesión y estilos |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | público | inicio/cierre de sesión |
| `/api/health` | público | «¿es este el gateway?», versión, indicador de contraseña |
| `/api/integrity` | público | comprobación SHA-256 de la interfaz |
| `/api/donation` | público | bloque de apoyo al autor |
| `/license` | público | texto de la licencia |
| todo lo demás | sesión requerida | perfiles, telemetría, comandos, QR, APK, asistente, `/ws` |

Sin sesión:

- la API responde con `401` y `{"error","code":"unauthorized"}`, además de
  `WWW-Authenticate: Bearer realm="open-deck"`;
- las páginas HTML responden con `302` a `/login.html?next=<path>`;
- el handshake de WebSocket se rechaza con `401` (el navegador mostrará un error
  de conexión).

---

## 2. Autenticación

La contraseña tiene al menos 6 caracteres y se almacena como hash PBKDF2 en
`config/auth.json` (210.000 iteraciones, sal aleatoria). Una sesión son 32 bytes
aleatorios con un TTL de 12 horas, ampliado al acceder.

El token se acepta de tres formas:

| Método | Dónde | Para quién |
| --- | --- | --- |
| Cookie `open_deck_session` | `HttpOnly; SameSite=Lax` | navegador y WebView de Android |
| `Authorization: Bearer <token>` | cabecera | clientes nativos |
| `?token=<token>` | solo `/ws` | WebSocket sin cookie |

### `GET /api/auth/status`

```json
{ "required": true, "authenticated": false }
```

### `POST /api/auth/login`

```json
{ "password": "secret" }
```

Éxito — `200`, cookie y token:

```json
{ "ok": true, "required": true, "token": "<43 characters>", "expiresIn": 43200 }
```

Errores:

| Estado | `code` | Cuándo |
| --- | --- | --- |
| `400` | `missing_password` | falta `password` |
| `401` | `bad_password` | contraseña incorrecta |
| `429` | `rate_limited` | tras 5 fallos desde una dirección; incluye `Retry-After` |

Si no hay contraseña configurada, la respuesta es
`{"ok":true,"required":false}`.

### `POST /api/auth/logout`

Revoca la sesión actual y borra la cookie: `{"ok": true}`.

### `POST /api/pair`

Requiere sesión. Token de un solo uso para iniciar sesión desde un teléfono:

```json
{ "url": "http://192.168.1.10:8760/?pair=…", "token": "…", "expiresIn": 600, "required": true }
```

Al seguir `url` se canjea el token por una sesión normal (cookie) y se redirige
a `/`; reutilizarlo devuelve `/login.html?error=pair`.

---

## 3. API REST

A continuación, `{id}` es un identificador de perfil
(`[a-z0-9][a-z0-9-]{1,63}`).

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "authRequired": true,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  }
}
```

### `GET /api/profiles`

```json
{ "profiles": [
  { "id": "cessna-172-skyhawk", "name": "Cessna 172S Skyhawk", "icao": "C172",
    "revision": 3, "widgetCount": 11 }
] }
```

### `GET /api/profiles/{id}`

El perfil completo (véase [profile-schema.md](profile-schema.md)).
`404 not_found` — no existe el archivo; `422 invalid_profile` — falló la
validación.

### `PUT /api/profiles/{id}`

El cuerpo es un perfil JSON completo; el `id` del cuerpo debe coincidir con la
URL (`400 id_mismatch`). Respuesta `{"ok": true, "profile": {…}}`.

### `GET /api/telemetry`

La última trama (el mismo formato que `telemetry` por WebSocket). `seq` crece;
`values` contiene todas las claves del registro.

### `GET /api/telemetry/variables`

Catálogo de variables:

```json
{ "variables": [
  { "key": "speed.iasKt", "label": "Indicated airspeed", "kind": "number",
    "unit": "KT", "writable": false, "simVar": "AIRSPEED INDICATED", "simEvent": null }
] }
```

El catálogo completo legible por humanos está en [telemetry.md](telemetry.md).

### `GET /api/integrity`

```json
{ "verified": true, "checkedAt": "2026-11-01T…", "manifestPresent": true,
  "files": { "web/index.html": "<sha256>" }, "errors": [] }
```

### `GET /api/donation`

Datos de apoyo al autor de `config/donation.json` (la única fuente es la
configuración del host). Autor — Viktor Krasnikov, Donat —
[`https://taps.uz/open_deck_fs`](https://taps.uz/open_deck_fs).

### `GET /api/connect`

Direcciones para teléfono/tableta:

```json
{
  "host": "FLIGHTSIM-PC",
  "primaryUrl": "http://192.168.1.10:8760/",
  "phoneUrl": "http://192.168.1.10:8760/?device=phone",
  "urls": [
    { "url": "http://192.168.1.10:8760/", "host": "192.168.1.10",
      "private": true, "loopback": false, "linkLocal": false }
  ],
  "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
  "qr": { "scale": 6, "border": 4, "maxTextLength": 512 }
}
```

Orden: `192.168.*`, luego `10.*`, `172.16–31.*`, link-local, loopback.

### `GET /api/qr.svg?text=…&scale=6&border=4`

Un SVG con un código QR (hasta 512 caracteres; generado en el host, sin
bibliotecas). `400 missing_text` — falta `text`; `400` (`code` = `error`) —
`scale`/`border` no son números; `422 qr_too_long` — el texto no cabe en las
versiones de QR admitidas.

### `POST /api/sim/command`

```json
{ "key": "power.batteryMaster", "value": true }
```

Éxito — `200` con
`{"type":"ack","id":…,"key":…,"ok":true,"value":…}`.
Errores: `400` con `code` = `invalid_key`, `not_writable`, `invalid_value`,
`rate_limited` o `sim_error`; `409 sim_rejected` — el simulador lo rechazó.
Para las variables con un evento parametrizado, el valor se escala
(porcentaje → 0..16383).

### `POST /api/sim/aircraft`

```json
{ "profileId": "cessna-172-sixpack" }
```

Respuesta:
`{"ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false}`.
`pinned: true` — el proveedor no puede cambiar de aeronave (SimConnect), por lo
que la selección queda fijada hasta que cambie la aeronave en el simulador.
`404` — no existe ese perfil.

### Asistente

`GET /api/assist` — estado del bucle:

```json
{
  "telemetry": {
    "onGround": true, "radioAltitudeFt": 0, "groundSpeedKt": 12.3,
    "iasKt": 0, "headingDeg": 274, "localizerDeg": 0.0,
    "glideSlopeDeg": 0.0, "locValid": false, "gsValid": false,
    "autopilotMaster": false, "approach": false,
    "throttlePct": 18.4, "rudderPct": -3.2, "parkingBrake": false
  },
  "taxi": { "engaged": true, "targetSpeedKt": 12, "targetHeadingDeg": 274,
            "throttlePct": 18.4, "rudderPct": -3.2, "message": "…" },
  "landing": { "phase": "off", "message": "…", "throttlePct": 0, "active": false },
  "limits": { "taxiSpeedMinKt": 3, "taxiSpeedMaxKt": 25,
              "flareStartFt": 60, "flareIdleFt": 15 }
}
```

`POST /api/assist/taxi`:

| `action` | Campos | Significado |
| --- | --- | --- |
| `engage` | — | activar el mantenimiento de velocidad/rumbo (solo en tierra) |
| `disengage` | — | desactivar |
| `stop` | — | acelerador 0, freno de estacionamiento |
| `speed` | `value` (3…25) | fijar la velocidad de rodaje |
| `heading` | `delta` (±) | girar el rumbo objetivo |

`POST /api/assist/landing`: `action` = `arm` (AP + APR), `disarm`, `toga`.

Respuesta: `{"ok": true|false, "message": "…", "status": {…}}`.
`200` — acción realizada; `409` — rechazada (no está en tierra, velocidad
demasiado baja, sin conexión con MSFS, acción desconocida).

### Compilación del APK de Android

- `GET /api/android/settings` — `{settings, toolchain, apk, prebuiltApk}`.
- `PUT /api/android/settings` — guardar ajustes (nombre, id del paquete,
  versión, dirección del gateway, rutas de herramientas).
  `422 invalid_settings`.
- `GET /api/android/build` — estado del trabajo:
  `{jobId, state, running, log, apk, error}` (`state`:
  `idle|running|success|failed`).
- `POST /api/android/build` — iniciar; `202` con `jobId`, `409 build_running`,
  `422 invalid_settings`.
- `GET /api/android/apk` — descargar el APK
  (`application/vnd.android.package-archive`); si no hay compilación, el APK
  listo de la distribución, de lo contrario `404 apk_missing`.

### Archivos estáticos y páginas de servicio

- `GET /` — panel (`index.html`), `GET /editor.html` — editor,
  `GET /android.html` — compilación del APK, `GET /assist.html` — asistente,
  `GET /login.html` — inicio de sesión.
- `GET /license` — texto de la licencia.
- `HEAD` — solo archivos estáticos; para `/api/*` — `405`.
- `OPTIONS` — `204` sin cabeceras CORS.

---

## 4. WebSocket `/ws`

Handshake — RFC 6455, versión 13. Solo mensajes de texto; los mensajes binarios
se cierran con `1002`.

### 4.1. Autorización

El token se toma de una cookie, de `Authorization: Bearer` o de `?token=` (para
`/ws`). Sin una sesión válida — HTTP `401`, y no se realiza la actualización. Un
token de emparejamiento de un solo uso no es válido aquí: solo se acepta a
través de `/?pair=`. Si `Origin` y `Host` no coinciden — HTTP `403`, y no se
realiza la actualización.

### 4.2. Servidor → cliente

#### `hello` — primer mensaje

```json
{
  "type": "hello",
  "clientId": "a1b2c3d4",
  "server": { "name": "Open Deck for MSFS", "version": "0.1.0",
              "telemetryHz": 30.0, "uptimeSec": 1.2 },
  "profiles": [ … ],
  "state": { /* trama de telemetría completa */ }
}
```

#### `telemetry` — periódicamente (`telemetryHz` veces por segundo)

```json
{
  "type": "telemetry",
  "seq": 1234,
  "ts": 1762340000000,
  "sim": { "provider": "mock", "connected": true,
           "aircraftTitle": "…", "profileId": "…" },
  "values": { "speed.iasKt": 108.0, "altitude.indicatedFt": 4520.0, … }
}
```

- `seq` es monotónico — revela la pérdida de tramas;
- `values` siempre contiene todas las claves del registro. `null` significa «sin
  datos»: SimConnect no aceptó la SimVar o la telemetría está obsoleta. El
  cliente muestra un guion en lugar de sustituir un cero.

#### `aircraft`

```json
{ "type": "aircraft", "profileId": "cessna-172-sixpack", "aircraftTitle": "…" }
```

Llega tras un cambio/autodetección de aeronave para que el cliente cambie de
perfil.

#### `ack`

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong`

Respuesta a `ping`: `{ "type": "pong", "t": <echo>, "ts": <unix ms> }`.

#### `error`

`{ "type": "error", "code": "bad_json"|"unknown_type", "error": "…" }`.

### 4.3. Cliente → servidor

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` es arbitrario; el servidor lo devuelve en el `ack`.

### 4.4. Códigos de `ack`

| `code` | Significado |
| --- | --- |
| `invalid_key` | clave vacía/desconocida |
| `not_writable` | variable de solo lectura |
| `invalid_value` | el valor no se puede convertir al tipo |
| `rate_limited` | más de 30 comandos por segundo desde un cliente WebSocket o una IP para REST |
| `sim_rejected` | el simulador rechazó el comando |
| `sim_error` | error interno del proveedor |

### 4.5. Límites y comportamiento

- Tamaño máximo de mensaje — 256 KiB; si es mayor — `1002`.
- Por cliente — una cola de 8 tramas de telemetría; al desbordarse se descartan
  las más antiguas (un cliente lento no ralentiza a los demás).
- Las tramas de control (ping/pong/close) no se fragmentan y son ≤125 bytes.
- Tiempo de espera de lectura inactiva — 90 s; el cliente envía `ping` cada 20 s.
- Cierre: `1000` — normal, `1002` — violación del protocolo.

### 4.6. Recomendaciones para el cliente

- El estado visual proviene de `telemetry.values`, no de `ack`.
- Reconecta con retroceso exponencial (500 ms → 8 s, con jitter); si no llegan
  mensajes durante 45 s — trata la conexión como «semiabierta» y reconecta.
- No bloquees la interfaz: muestra «esperando», revierte en `ok:false`/tiempo de
  espera.

---

## 5. Inicio de sesión por QR (emparejamiento)

```
Phone (no session)                      Gateway
        │  GET /?pair=<one-time token>   │
        ├───────────────────────────────►│
        │                                │ token check (10 min, once)
        │  302 / + Set-Cookie open_deck_session  │
        │◄───────────────────────────────┤
        │  GET / (with cookie)           │
        └───────────────────────────────►│ panel
```

El código QR lo dibuja el propio gateway (`/api/qr.svg`); el token lo crea
`POST /api/pair` (requiere sesión). De este modo el teléfono inicia sesión sin
introducir una contraseña. El token es de un solo uso y no es una sesión: un
intento de usarlo como cookie o token Bearer devuelve `401`, y su TTL no se
amplía.

---

## 6. Autodescubrimiento (difusión UDP)

El host envía una baliza JSON al puerto UDP `8761` cada 3 segundos (para Android
y clientes nativos; los navegadores no admiten UDP).

```json
{
  "type": "open-deck-msfs",
  "protocol": 1,
  "name": "FLIGHTSIM-PC",
  "version": "0.1.0",
  "httpPort": 8760,
  "telemetryHz": 30.0,
  "profiles": ["cessna-172-skyhawk", "piper-pa28-archer-ii"],
  "auth": true,
  "ts": 1762340000
}
```

| Campo | Descripción |
| --- | --- |
| `type` | siempre `open-deck-msfs` |
| `protocol` | versión del esquema de la baliza |
| `name` | nombre del host |
| `httpPort` | puerto HTTP/WebSocket |
| `telemetryHz` | frecuencia de telemetría |
| `profiles` | perfiles disponibles |
| `auth` | presente solo cuando hay una contraseña activada (`true`) |
| `ts` | hora Unix |

Comprobación manual:

```powershell
python -m msfs_gateway.discovery --listen
```

---

## 7. Errores HTTP

Formato: `{"error": "text", "code": "machine_code"}`.

| Estado | Códigos típicos |
| --- | --- |
| `400` | `bad_request`, `bad_json`, `invalid_value`, `id_mismatch`, `missing_password` |
| `401` | `unauthorized`, `bad_password` |
| `404` | `not_found`, `apk_missing` |
| `409` | `build_running`, `sim_rejected`, rechazos del asistente |
| `411` | `length_required` |
| `413` | `too_large` |
| `422` | `invalid_profile`, `invalid_settings`, `qr_too_long` |
| `429` | `rate_limited` |
| `501` | método HTTP no admitido (stdlib) |

---

## 8. Ejemplos

### Inicio de sesión y solicitud de perfil

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

### Bearer en lugar de cookie

```bash
TOKEN=$(curl -s -H "Content-Type: application/json" \
  -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/telemetry
```

### Comando

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
     -d '{"key":"power.batteryMaster","value":true}' \
     http://127.0.0.1:8760/api/sim/command
```

### WebSocket (Python, sin bibliotecas)

```python
import json, socket, base64, os
sock = socket.create_connection(("127.0.0.1", 8760))
key = base64.b64encode(os.urandom(16)).decode()
sock.sendall((
    "GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Cookie: open_deck_session=<token>\r\n\r\n"
).encode())
# después lee tramas RFC 6455 (véase msfs_gateway/websocket.py)
```

---

## 9. Compatibilidad

- Esquema de perfil — `schemaVersion: 1`; el antiguo formato `v0` lo adapta
  `legacy.py` al leer.
- Baliza — `protocol: 1`; los clientes deben ignorar los nuevos campos
  opcionales (`auth`).
- La API no está versionada en la URL: los cambios incompatibles solo se hacen
  en una nueva versión mayor del gateway.
