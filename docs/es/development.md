# 🛠️ Desarrollo y diseño interno

Un documento para quienes cambian el código: qué vive dónde, cómo añadir una
variable, un instrumento, un perfil, un proveedor o una página, y cómo probar y
publicar. La documentación de usuario está en [service.md](service.md), y el
protocolo en [protocol.md](protocol.md).

## 1. Requisitos

- Windows 10/11 (el gateway usa `ctypes` para SimConnect; el resto es
  multiplataforma).
- Python **3.11+**; no hay dependencias de terceros — solo la biblioteca
  estándar.
- Node.js **20+** — para las pruebas del cliente web (el cliente en sí no
  requiere compilación).
- JDK 17 + Android SDK + Gradle 8.x — solo para compilar el APK.
- PyInstaller y NSIS — solo para el instalador.

## 2. Mapa del código

```
msfs_gateway/
  app.py            ensamblado de dependencias, ciclo de vida, modos CLI
  settings.py       argumentos CLI, rutas, valores predeterminados
  telemetry.py      registro de variables (claves, tipos, SimVar, eventos)
  hub.py            bus: trama, suscripciones, comandos, autodetección de aeronave
  http_api.py       HTTP: archivos estáticos, REST, actualización a WebSocket, autorización
  websocket.py      RFC 6455: tramas, ping/pong, cierre, cola de envío
  auth.py           contraseña, PBKDF2, sesiones, tokens QR, limitación de intentos
  assist.py         asistentes de rodaje y aterrizaje (10 Hz)
  profiles.py       validación, almacenamiento, guardado atómico de perfiles
  legacy.py         adaptador para el antiguo formato de perfil v0
  integrity.py      manifiesto SHA-256 de archivos críticos
  discovery.py      baliza UDP de autodescubrimiento
  qr.py             generador de QR (SVG) sobre stdlib
  android_build.py  ajustes, búsqueda de herramientas, lanzamiento de Gradle
  docsgen.py        generación de docs/telemetry.md y docs/widgets.md
  sim/              proveedores: mock, simconnect, client_data, wasm_bridge
web/                panel, editor, inicio de sesión, asistente (módulos ES vanilla)
profiles/           perfiles JSON de aeronaves
android/            cliente Kotlin (WebView + descubrimiento UDP)
packaging/windows/  PyInstaller + NSIS
scripts/            build-installer.ps1, check.ps1, verify_qr.py
tests/              unittest (Python) y node:test (JS)
docs/               esta y otras documentaciones
```

## 3. Cómo añadir una variable de telemetría

1. Abre `msfs_gateway/telemetry.py` y añade un `Variable(...)` a `_VARIABLES`:
   clave, tipo, etiqueta, `sim_var`/`sim_unit` y, si es necesario, `sim_event`,
   `sim_event_param`, `sim_event_scale`.
2. Verifica el nombre de la SimVar con la documentación del SDK de MSFS (las
   mayúsculas y las unidades importan).
3. Actualiza el catálogo: `python -m msfs_gateway.docsgen --write`.
4. Ejecuta `python -m unittest tests.test_telemetry` y la suite completa.
5. Si la variable es un control, asegúrate de que el evento cambia realmente el
   estado (la comparación `bool` usa el valor actual).

## 4. Cómo añadir un instrumento

1. Crea `web/js/widgets/my-widget.js`: una clase con `update(state)` y
   `destroy()` (véanse `base.js` y los instrumentos vecinos). El renderizado —
   canvas o DOM.
2. Registra el tipo en `web/js/widgets/registry.js`.
3. Añade el tipo a `WIDGET_TYPES`, los roles obligatorios a
   `REQUIRED_BINDINGS` y, si es necesario, comprobaciones de opciones en
   `msfs_gateway/profiles.py`.
4. Describe el instrumento en `msfs_gateway/docsgen.py` (`WIDGET_ORDER`,
   `WIDGET_TITLES`, `WIDGET_DESCRIPTIONS`, `WIDGET_OPTIONS`, ejemplo) y ejecuta
   `python -m msfs_gateway.docsgen --write`.
5. Compruébalo en los tres factores de forma (teléfono/tableta pequeña/grande) y
   en el editor; añade una prueba de geometría en `tests/web/`.

## 5. Cómo añadir un perfil de aeronave

1. Copia un perfil similar de `profiles/`, cambia `id`, `name`, `icao`,
   `sim.match` (glob sobre `TITLE`/`ATC MODEL`).
2. Comprueba la validación: `python -m unittest tests.test_profiles`.
3. Crea los diseños `base` + las diferencias para los factores de forma;
   asegúrate de que los rectángulos no salgan de `0..1`.
4. Compruébalo en el editor `/editor.html` y en una aeronave real (si MSFS está
   disponible).
5. Añade el perfil al README (lista) y al CHANGELOG.

## 6. Cómo añadir un proveedor de telemetría

1. Hereda de `SimProvider` (`sim/base.py`) e implementa `start`, `stop`, `read`,
   `apply_command`, `connected`; si es necesario — `select_aircraft`,
   `aircraft_title`, `atc_model`.
2. Registra la opción en `sim/__init__.py:create_sim()` y añade el valor a
   `SIM_CHOICES` (`settings.py`).
3. Seguridad entre hilos: `read()` y `apply_command()` pueden llamarse desde
   hilos diferentes — usa un bloqueo.
4. Añade pruebas con un transporte falso (véase `tests/test_mock_sim.py`).

## 7. Cómo añadir un endpoint

1. Gestiona la ruta en `_handle_api_get/post/put` (`http_api.py`).
2. Decide si es público o está protegido por sesión: público — solo en
   `PUBLIC_API_PATHS`; todo lo demás se cierra automáticamente.
3. Responde mediante `_send_json`/`ApiError`; los errores llevan un `code`
   legible por máquina.
4. Documenta el endpoint en `docs/protocol.md` (tabla + ejemplo) y en
   `docs/service.md` (sección API).
5. Añade una prueba en `tests/` (unidad + integración HTTP si es necesario).

## 8. Cómo añadir una página

1. Coloca el HTML en `web/`, el JS en `web/js/` y los estilos en `web/css/`.
2. La página está **cerrada** por defecto (excepto `/login.html` y sus archivos);
   sin sesión, el servidor devuelve `302` al inicio de sesión.
3. Añade el enlace a la cabecera del panel (`web/index.html`) y luego reconstruye
   el manifiesto: `python -m msfs_gateway.integrity --write`.
4. Compruébala en un teléfono (`?device=phone`) y en modo kiosco.

## 9. Pruebas y comprobaciones

```powershell
pwsh -File scripts/check.ps1       # ruff + formato + 252 Python + 41 JS
python -m unittest discover -s tests
node --test "tests/web/*.test.mjs"
python -m msfs_gateway.docsgen --check
python -m msfs_gateway.integrity
```

Estrategia de pruebas:

- **Lógica pura** (validación, perfiles, QR, controladores del asistente,
  autenticación) — pruebas unitarias sin red ni MSFS.
- **HTTP/WebSocket** — inicia `GatewayApplication.start_background()` en
  `127.0.0.1:0` y usa `http.client`/sockets crudos.
- **SimConnect/WASM** — una DLL/transporte falsos; un vuelo real se verifica
  manualmente.
- **Web** — `node:test` para funciones puras (diseño, `isConnectionStale`).

## 10. Documentación

- `docs/telemetry.md` y `docs/widgets.md` se **generan** desde el código; las
  ediciones manuales se sobrescribirán. Cambia `docsgen.py` y ejecuta `--write`.
- Los demás documentos son manuales; cuando cambie el comportamiento, actualiza
  `service.md`, `protocol.md`, `profile-schema.md` y `CHANGELOG.md`.
- La comprobación de actualidad está integrada en `scripts/check.ps1`
  (docsgen --check).
- Índice — [docs/README.md](README.md).

## 11. Compilación y publicación

1. Actualiza la versión (`msfs_gateway/__init__.py`, `config/android-build.json`,
   `packaging/windows/README.md`).
2. `python -m msfs_gateway.integrity --write` (si han cambiado archivos
   críticos).
3. `pwsh -File scripts/build-installer.ps1 -Version <x.y.z> -NsisPath <NSIS>`.
4. Comprueba la instalación/desinstalación y `--set-password` en una máquina
   limpia.
5. Compila el APK (`android/gradle assembleDebug`) y colócalo en
   `android/dist`.
6. Actualiza `CHANGELOG.md`, haz commit y etiqueta `v<x.y.z>`.

## 12. Convenciones

- Python: solo la biblioteca estándar, formato `ruff format`, longitud de línea
  100.
- JS: módulos ES, sin CDN ni paso de compilación; `node --check` y `node:test`.
- Kotlin: solo SDK y biblioteca estándar, sin AndroidX.
- Los comentarios y la documentación — en inglés; los identificadores — en
  inglés.
- No añadas dependencias externas salvo que sea absolutamente necesario: el
  proyecto está diseñado para una instalación air-gapped.
