# 🏗️ Arquitectura de Open Deck for MSFS

Este documento describe los componentes, los flujos de datos y las decisiones de
diseño clave. El formato de perfil se describe en
[profile-schema.md](profile-schema.md), y el protocolo de red en
[protocol.md](protocol.md).

---

## 1. Diagrama de alto nivel

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

## 2. Componentes y responsabilidades

### 2.1. `telemetry.py` — registro canónico de variables

La única fuente de verdad sobre las magnitudes: nombre de la clave, tipo,
unidad, enlace a la SimVar (`sim_var`/`sim_unit`) y evento de escritura
(`sim_event`). Los perfiles hacen referencia únicamente a estas claves, de modo
que renombrar una SimVar es una edición en un solo lugar.

```python
Variable("power.batteryMaster", "bool", "Master battery",
         sim_var="ELECTRICAL MASTER BATTERY", sim_unit="bool",
         sim_event="TOGGLE_MASTER_BATTERY")
```

### 2.2. `sim/` — fuentes de telemetría (proveedores)

Interfaz común `SimProvider`:

| Método | Propósito |
| --- | --- |
| `connected` | indica si existe una conexión activa con el simulador |
| `start()` / `stop()` | el hilo en segundo plano del proveedor |
| `read()` | una instantánea de valores `dict[key, value]` |
| `apply_command(key, value)` | aplicar un comando del cliente |
| `select_aircraft(profile_id)` | cambiar la aeronave (solo lo admite mock) |

Implementaciones:

- **`MockSim`** — un vuelo procedimental: el banqueo, el cabeceo, el rumbo, la
  velocidad y la altitud cambian siguiendo sinusoides suaves, y el combustible
  se consume. Necesario para el desarrollo sin MSFS, las demostraciones y las
  pruebas automatizadas.
- **`SimConnectSim`** — SimConnect nativo a través de `ctypes`. Se suscribe a un
  bloque de datos numéricos (`AddToDataDefinition` + `RequestDataOnSimObject`),
  por separado a las cadenas `TITLE`/`ATC MODEL`, almacena en caché los valores
  en `read()` y envía comandos como eventos (`MapClientEventToSimEvent` +
  `TransmitClientEvent`). Las llamadas a SimConnect, incluidos los comandos, se
  realizan en el hilo de despacho (`run_on_dispatch`), porque la API no está
  diseñada para llamadas multihilo. Si el `SimConnect.cfg` del usuario apunta a
  un canal inexistente, la conexión se reintenta por TCP `127.0.0.1:19999` a
  través de una configuración temporal (el puerto de MSFS 2020/2024). Se ha
  verificado la conexión con un MSFS 2020 en vivo; el intercambio numérico en
  vivo, el módulo WASM y el asistente en vuelo son el siguiente paso de
  validación.

La fábrica `create_sim()` selecciona un proveedor según el ajuste `--sim`:

- `mock` → siempre mock;
- `simconnect` → solo SimConnect, sale en caso de error;
- `auto` → SimConnect, con retroceso a mock en caso de fallo (el gateway siempre
  arranca).

### 2.3. `hub.py` — bus de telemetría

- un único hilo «ticker» a la frecuencia `--telemetry-hz` recoge `sim.read()` y
  difunde la trama a todos los clientes WebSocket;
- cada cliente tiene su propia cola (8 tramas) y su hilo emisor: una tableta
  lenta no detiene la entrega a los demás, y las tramas antiguas se descartan;
- **limitación de la frecuencia de comandos** (≤30/s por cliente) — protección
  contra un toque atascado;
- `build_message()` normaliza los valores (redondeo a 3 decimales, el conjunto
  completo de claves) y añade los metadatos `seq`, `ts` y `sim`.

### 2.4. `profiles.py` + `legacy.py` — perfiles de aeronaves

- `validate_profile()` — comprobación estricta de la estructura (tipos de
  instrumento, enlaces, comandos, rectángulos, rangos de las escalas);
- `ProfileStore` — guardado atómico y seguro entre hilos (tmp + `fsync` +
  `os.replace`);
- `legacy.adapt()` — convierte el formato «en píxeles» v0 de la especificación
  al formato interno (coordenadas en fracciones 0..1) para que los paneles
  antiguos se carguen tal cual.

### 2.5. `http_api.py` + `websocket.py` — red

- `ThreadingHTTPServer` sirve los archivos estáticos de `web/` y la API REST y
  realiza la actualización a WebSocket en un solo puerto — una única regla de
  firewall;
- `websocket.py` — una implementación mínima de RFC 6455 (texto, ping/pong,
  cierre) sobre la biblioteca estándar;
- `auth.py` — inicio de sesión por contraseña opcional: hash PBKDF2, sesiones en
  memoria, cookie `HttpOnly`, tokens Bearer, tokens QR de un solo uso,
  limitación de intentos;
- cabeceras de seguridad: CSP `default-src 'self'`, `X-Content-Type-Options`,
  `Referrer-Policy`; archivos estáticos sin caché (desarrollo en vivo);
- `/api/connect` + `qr.py` — conexión rápida desde el teléfono: el host enumera
  sus direcciones de red (primero `192.168.x`, luego `10.x`, `172.16-31.x`), y
  el código QR lo dibuja un generador propio sobre la biblioteca estándar (modo
  byte, EC L, versiones 1–10, todas las máscaras), sin bibliotecas externas ni
  internet.

### 2.5a. `auth.py` — inicio de sesión por contraseña

- La contraseña se almacena solo como hash PBKDF2 (`config/auth.json`), se
  verifica con `hmac.compare_digest`; 5 fallos por minuto desde una dirección →
  bloqueo.
- Las sesiones viven en la memoria del proceso (32 bytes, TTL de 12 horas,
  ampliado con la actividad); el navegador recibe una cookie
  `open_deck_session` (`HttpOnly`, `SameSite=Lax`), y los clientes nativos usan
  Bearer o `?token=` para WebSocket.
- Los tokens QR de un solo uso (`POST /api/pair`, 10 minutos) permiten que un
  teléfono inicie sesión sin introducir una contraseña. Dicho token solo se
  acepta a través de `/?pair=`: `SessionStore.validate` rechaza las sesiones
  `pairing`, por lo que no puede usarse como cookie ni como token Bearer.
- Las peticiones POST/PUT del navegador y las de WebSocket cuyo `Origin` no
  coincide con `Host` se rechazan con `403` (protección contra el secuestro de
  WebSocket entre sitios y CSRF); los clientes sin `Origin` (Android, curl) se
  permiten.
- La cabecera `Host` se comprueba además contra localhost, el nombre de la
  máquina, el FQDN y las IP locales. Esto cierra el DNS rebinding, en el que
  tanto `Origin` como `Host` pertenecen al dominio del atacante.
- Solo el inicio de sesión, `/api/health`, `/api/integrity`, `/api/donation` y
  `/license` son de acceso público; todo lo demás está cerrado.

### 2.5b. `assist.py` — asistentes de aterrizaje y rodaje

- **Rodaje**: un controlador PI de acelerador por velocidad respecto al suelo y
  un controlador P de timón por rumbo; se activa solo en tierra y se desactiva
  al despegar, al frenar o con una velocidad superior a 35 kt; «STOP» da
  acelerador cero y el freno de estacionamiento.
- **Aterrizaje**: ARM activa AP y APR; entre 60 y 15 ft reduce el acelerador de
  forma lineal, y al tocar tierra desconecta el piloto automático; TOGA —
  acelerador a tope. No toca el elevador.
- Un hilo a 10 Hz lee `sim.read()` y envía comandos a través de
  `Hub.apply_assist_command` (sin limitación de frecuencia ni lecturas
  adicionales).
- Es un bucle auxiliar: la decisión final y el control siguen siendo del piloto.

### 2.6. `integrity.py` — protección del bloque de donativos (condición de licencia)

Compara el SHA-256 de cinco archivos críticos (incluidos
`web/js/ui/donation.js`, `web/css/donation.css`, `config/donation.json`) con el
manifiesto `integrity/manifest.json`. El host bloquea el arranque si no
coinciden; el cliente (`web/js/ui/integrity.js`) supervisa además la
visibilidad del bloque en el DOM. Autor — Viktor Krasnikov
([github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)),
Donat — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

### 2.7. `discovery.py` — autodescubrimiento del host (difusión UDP)

Un hilo en segundo plano envía un baliza JSON (nombre del host, versión,
`httpPort`, frecuencia, lista de perfiles) por difusión UDP (`255.255.255.255` +
la difusión dirigida de cada interfaz) cada N segundos. `listen_once()` es el
receptor para los clientes nativos y las pruebas. Los navegadores no admiten
UDP, por lo que el cliente web no lo necesita (ya arranca desde el propio host).

### 2.8. `web/editor.*` — editor visual de paneles

`/editor.html` + `web/js/editor.js` — un editor de arrastrar y soltar: mover y
redimensionar instrumentos, configurar enlaces (listas desplegables del catálogo
`GET /api/telemetry/variables` más `custom.*` declarados en el perfil), opciones
(escalas, unidades, tonos), añadir desde una paleta de tipos y eliminar. El
guardado se realiza con `PUT /api/profiles/{id}`. La vista previa dibuja
instrumentos reales (a través del registro `widgets/registry.js`) con valores de
demostración. Las anulaciones por factor de forma se editan en el factor de
forma activo: si no hay una anulación, la edición va a `layout.base`. Un
historial de ediciones (instantáneas de `widgets` antes de un cambio) permite
deshacer y rehacer arrastres, redimensionados, propiedades, adiciones y
eliminaciones; también hay ajuste a una rejilla del 1 % (Shift lo desactiva
temporalmente) y copia con un botón de la geometría a otros factores de forma.

### 2.8a. Autodetección de aeronave

`SimConnectSim` lee `TITLE` y `ATC MODEL` como datos de cadena separados
(`SIMCONNECT_DATATYPE_STRING256`) y los guarda en `aircraft.title` /
`aircraft.atcModel`. `hub.py` mantiene las reglas `sim.match.title` /
`atcModel` (glob, sin distinguir mayúsculas y minúsculas) y selecciona un perfil
en cada trama si el proveedor no establece uno por sí mismo. El cliente observa
`sim.profileId` en la telemetría y recarga el panel cuando cambia la aeronave;
la selección manual de la lista queda fijada durante 5 segundos para no entrar
en conflicto con una trama que aún no ha llegado.

### 2.8b. `web/js/ui/comfort.js` — brillo y kiosco

El brillo del panel tiene tres niveles (100/72/45 %), se guarda en
`localStorage` y se aplica mediante el atributo `data-brightness` en `<html>`:
el CSS solo atenúa la escena de instrumentos, mientras la interfaz sigue siendo
legible. El modo kiosco oculta el panel superior y la barra de estado, cambia la
escena al modo completo y deja un pequeño botón de salida; `Esc` restaura la
interfaz. Atajos: `B` — brillo, `F` y `Esc` — kiosco.

### 2.9. Puente WASM: LVAR/RPN a través del Client Data Area

Las aeronaves complejas (PMDG, Fenix, FlyByWire, iniBuilds) mantienen su estado
en variables propias. Un perfil las declara en el bloque `variables` (`source:
lvar` o `rpn`), y el puente las lee y escribe a través del **SimConnect Client
Data Area**: el módulo WASM (MobiFlight / SimBridge) publica allí los datos.

```
hub.build_message()
   └─ hub._custom_values(profile_id)        # caché de 0.25 s
        └─ WasmBridge.read_specs(specs)      # wasm_bridge.py
             ├─ read_lvars(names)            # bloque: nombre 128 B + double 8 B
             └─ execute_rpn(script)          # Command → Response
                  └─ ClientDataChannel.read_area / write_area   # client_data.py
                       └─ SimConnectClientDataBackend            # simconnect.py
                            └─ run_on_dispatch(...)  # llamadas en el hilo de SimConnect
```

Capas:

- **`sim/client_data.py`** — el protocolo en forma síncrona: correlación de
  peticiones por `request_id`, tiempos de espera, nuevo registro de un área
  cuando crece su tamaño y reinicio de las peticiones pendientes al
  desconectarse. El transporte está abstraído (`ClientDataBackend`), por lo que
  el protocolo se prueba sin MSFS; `LoopbackClientDataBackend` es una
  implementación en memoria para pruebas y demostraciones.
- **`sim/simconnect.py`** — `SimConnectClientDataBackend`:
  `MapClientDataNameToID`, `AddToClientDataDefinition`, `RequestClientData`,
  `SetClientData`. Todas las llamadas se realizan en el hilo de despacho a
  través de `run_on_dispatch` (SimConnect no está diseñado para llamadas
  multihilo), y las respuestas llegan en
  `SIMCONNECT_RECV_ID_CLIENT_DATA`.
- **`sim/wasm_bridge.py`** — el diseño del bloque LVAR, los comandos RPN y las
  escrituras LVAR mediante `(<value>) (>L:NAME, number)`.

Áreas predeterminadas: `MobiFlight.LVars`, `MobiFlight.Command`,
`MobiFlight.Response`; para otra versión del módulo se sustituyen por constantes
en `wasm_bridge.py`.

Se habilita automáticamente para el proveedor `simconnect` (la opción
`--no-wasm` lo desactiva). Si el módulo WASM no está instalado, las respuestas
no llegan: tras dos tiempos de espera consecutivos, el cortacircuitos de
`ClientDataChannel` deja de consultar temporalmente (30 s), de modo que el flujo
de telemetría no se bloquea en cada trama. Las claves `custom.*` simplemente no
aparecen en la trama: los instrumentos muestran «--» con honestidad, y la
telemetría SimVar sigue funcionando. El bloque LVAR está limitado a 56 elementos
(7616 bytes) para que quepa en `MaxRecvData`/`MaxSendData` = 8192. En modo mock
los valores se toman del `initial` del perfil. Las SimVar integradas que faltan
en la definición aceptada de SimConnect o que están obsoletas se devuelven como
`null` en lugar de `0`: el panel muestra «--», y el asistente no las confunde
con ceros reales.

**Estado de verificación:** el protocolo y la contabilidad de áreas están
cubiertos por pruebas (emulación de MobiFlight mediante un transporte en
memoria), y se han verificado la compilación y el arranque; todavía no se ha
ejecutado un vuelo en vivo con MSFS y el módulo WASM — este es el único paso que
requiere un simulador instalado.

### 2.10. `android_build.py` — compilación del APK de Android desde la distribución

La aplicación instalada contiene las fuentes de Android (`android/`), y tras una
compilación el APK listo está en `android/dist`. La página `/android.html` y la
API `/api/android/*` permiten cambiar el nombre de la aplicación, el id del
paquete, la versión y la dirección predeterminada del gateway, ejecutar
`gradle assembleDebug` y descargar el APK recién generado. La configuración está
en `config/android-build.json`; los mismos valores se pasan a la compilación
como `-P…` y terminan en `BuildConfig`/el manifiesto de Android.

Búsqueda de herramientas: ajustes → `JAVA_HOME` / `ANDROID_HOME` → rutas
habituales. Si el perfil de usuario no es escribible (políticas estrictas,
sandboxes), la caché de Gradle, `TMP` y el almacén de claves de depuración se
redirigen automáticamente al directorio de distribución (`.gradle-home`,
`.tmp`, `.android-home`) — la compilación sigue funcionando. CLI sin navegador:
`OpenDeck.exe --build-apk [config.json]`.

---

## 3. Flujo de datos

### 3.1. Telemetría (push)

```
MockSim/SimConnectSim._loop()
   └─ sim.read()                        # instantánea de valores
        └─ hub.build_message()          # normalización + seq/ts/sim
             └─ hub._broadcast_text()   # JSON a cada cola WebSocket
                  └─ web: handleMessage('telemetry') → store → panel-view → widgets
```

### 3.2. Comando (petición/confirmación)

```
web: toggle-switch.onClick()
   └─ socket.command(key, value)        # {type:'command', id, key, value}
        └─ hub.handle_command()         # validación + límite de frecuencia
             └─ sim.apply_command()     # mock / SimConnect
                  └─ ack {type:'ack', id, ok, value}   (por WebSocket)
                       └─ el cliente espera la confirmación por telemetría
```

### 3.3. Perfil (pull)

```
web: api.listProfiles() → GET /api/profiles
   └─ api.getProfile(id) → GET /api/profiles/{id}
        └─ profiles.load_profile_file() → legacy.adapt_if_needed() → ensure_valid()
             └─ panel-view.mount(profile) → createWidgetInstance() según el tipo
```

### 3.4. Autodescubrimiento (push UDP)

```
DiscoveryBeacon._loop()                      # hilo daemon
   └─ payload() {name, version, httpPort, profiles, auth?, ts}
        └─ sendto(255.255.255.255:8761) + difusiones dirigidas
             └─ Android/cliente nativo: listen_once() → http://<ip>:<port>/
```

---

## 4. Decisiones de diseño clave

| Decisión | Por qué |
| --- | --- |
| Solo la biblioteca estándar de Python | air-gapped: `pip install` no está disponible; ya hay un intérprete instalado |
| Un puerto para HTTP+WS | una sola regla de firewall, diagnóstico más sencillo |
| WebSocket sin biblioteca externa | control sobre el protocolo, sin dependencias |
| El perfil usa coordenadas 0..1, no píxeles | un perfil para todos los factores de forma |
| `layout.base` + anulaciones | teléfono/tableta especifican solo las diferencias |
| Registro canónico de SimVar | desacopla los perfiles de un puente concreto |
| Suavizado en el cliente (Smoother) | animación a 60 fps sobre una red de 20–30 Hz |
| El widget dibuja el canvas según `clientWidth` | escalado HiDPI honesto en la vista previa |
| Proveedor `auto` | el gateway arranca sin MSFS y sin editar la configuración |
| Baliza de autodescubrimiento UDP | Android encuentra el host sin IP manual; los navegadores no la necesitan |

---

## 5. Límites del MVP y siguientes pasos

Lo que **ya existe**: un gateway sobre la biblioteca estándar, WebSocket con
colas por cliente, mock/SimConnect (+ retroceso TCP), puente LVAR/RPN WASM, 9
tipos de instrumento, 3 factores de forma, perfiles con validación y guardado
atómico, un editor con deshacer/rehacer y copia de diseños, autodescubrimiento
UDP, un cliente Android, un compilador de APK en la distribución, un instalador
de Windows, inicio de sesión por contraseña con QR, asistente de aterrizaje y
rodaje, comprobación de integridad, 250 pruebas de Python y 35 de JS.

Siguientes pasos (véase «Hoja de ruta» en el README):

- validación en vuelo real: SimConnect/WASM en una aeronave real, asistente en
  el aire y en tierra;
- firma de publicación del APK (almacén de claves en la configuración del
  compilador);
- mDNS (Bonjour) como alternativa a la baliza UDP;
- rodaje por rutas usando cartas de aeropuerto (por ahora el asistente solo
  mantiene velocidad y rumbo);
- grabación/reproducción de telemetría para demostraciones y perfilado.
