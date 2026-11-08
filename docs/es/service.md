# Open Deck for MSFS — descripción del servicio

Este documento describe qué hace el gateway, de qué consta, cómo interactúan los
clientes con él y cómo activar el inicio de sesión por contraseña. Está pensado
para pilotos que configuran el panel «para sí mismos» y para desarrolladores que
necesitan entender el diseño interno.

- Versión: 0.1.0
- Plataforma del host: Windows 10/11
- Clientes: navegador (PC, teléfono, tableta), Android 8+
- Licencia: [GNU AGPL-3.0](../../LICENSE) + condiciones adicionales Sección 7

## 1. Propósito

Open Deck for MSFS convierte un teléfono o una tableta en un panel de
instrumentos para Microsoft Flight Simulator 2020/2024. El gateway se ejecuta en
el mismo ordenador que el simulador, lee la telemetría a través de SimConnect, la
sirve por la red local y acepta comandos (interruptores, selectores rotativos,
botones). Los paneles se describen mediante perfiles JSON de aeronaves y se
editan directamente en el navegador.

Propiedades clave:

- **Sin conexión**: ni CDN, ni fuente, ni API, ni telemetría externas. Todo
  funciona en una red aislada y en una máquina sin acceso a internet.
- **Un solo puerto**: archivos estáticos, REST y WebSocket en un único puerto TCP
  (8760 por defecto) — basta una sola regla de firewall.
- **Sin dependencias**: el host es Python 3.11+ y la biblioteca estándar; el
  cliente son módulos ES vanilla; Android es Kotlin sin AndroidX.
- **Contraseña opcional**: el acceso a la API y a la telemetría puede cerrarse
  con una contraseña de al menos 6 caracteres, con sesiones, inicio de sesión por
  QR y protección contra fuerza bruta.

## 2. Modelo de funcionamiento

```
┌──────────────────┐   SimConnect / WASM    ┌─────────────────────────────┐
│  MSFS 2020/2024  │◄──────────────────────►│ Open Deck for MSFS (Windows)│
│  aircraft, LVAR  │   SimVar, TITLE, ATC   │                             │
└──────────────────┘   Client Data Area     │  ┌───────────────────────┐  │
                                             │  │ SimProvider           │  │
┌──────────────────┐        HTTP/WS          │  │  auto / mock / simconn│  │
│  PC browser      │◄───────────────────────►│  └──────────┬────────────┘  │
│  panel, editor   │   8760, static + API    │             │               │
└──────────────────┘                         │  ┌──────────▼────────────┐  │
┌──────────────────┐        HTTP/WS          │  │ Hub: telemetry 30 Hz  │  │
│  Phone/tablet    │◄───────────────────────►│  │ commands, sessions    │  │
└──────────────────┘                         │  └──────────┬────────────┘  │
┌──────────────────┐   HTTP (WebView)        │             │               │
│  Android client  │◄───────────────────────►│  Profiles, integrity,     │
└──────────────────┘   UDP beacon 8761       │  authentication, APK      │
                                             └─────────────────────────────┘
```

Flujo de datos:

1. El proveedor de telemetría (`simconnect`, `mock` o `auto`) lee los valores de
   las variables una vez por tick.
2. El bus (`Hub`) ensambla una trama, añade los campos de servicio y la difunde
   a todos los clientes WebSocket a la frecuencia configurada (30 Hz por defecto,
   60 como máximo).
3. El cliente dibuja los instrumentos; los comandos vuelven al bus, se validan y
   los aplica el proveedor.
4. Cuando cambia la aeronave, el gateway selecciona un perfil coincidente por
   nombre/modelo ATC y notifica a los clientes.

## 3. Componentes

| Componente | Archivos | Responsabilidad |
| --- | --- | --- |
| Punto de entrada | `msfs_gateway/app.py` | Ensamblado de dependencias, ciclo de vida, banner, modos `--set-password` / `--build-apk` |
| Configuración | `msfs_gateway/settings.py` | Argumentos CLI, rutas, valores predeterminados |
| HTTP/WebSocket | `msfs_gateway/http_api.py`, `websocket.py` | Archivos estáticos, REST, handshake y tramas RFC 6455, autenticación |
| Bus | `msfs_gateway/hub.py` | Trama de telemetría, suscripciones, comandos, limitación de comandos, autodetección de aeronave |
| Proveedores | `msfs_gateway/sim/` | `mock`, `simconnect`, Client Data Area, puente WASM LVAR/RPN |
| Perfiles | `msfs_gateway/profiles.py` | Lectura/validación/guardado atómico de perfiles JSON |
| Telemetría | `msfs_gateway/telemetry.py` | Catálogo de variables, tipos, conversión de valores |
| Autenticación | `msfs_gateway/auth.py` | Hash PBKDF2, sesiones, tokens QR, limitación de intentos |
| Autodescubrimiento | `msfs_gateway/discovery.py` | Baliza UDP con nombre, versión e indicador de contraseña |
| Integridad | `msfs_gateway/integrity.py` | SHA-256 de los archivos críticos de la interfaz |
| QR | `msfs_gateway/qr.py` | Generador de QR integrado (SVG), sin dependencias |
| Compilación del APK | `msfs_gateway/android_build.py` | Ajustes, búsqueda de JDK/SDK/Gradle, lanzamiento de Gradle, entrega del APK |
| Asistente | `msfs_gateway/assist.py` | Bucles de rodaje (velocidad/rumbo) y aterrizaje (APR, retard, TOGA) |
| Generador de documentación | `msfs_gateway/docsgen.py` | `docs/telemetry.md` y `docs/widgets.md` desde los registros del código |
| Cliente web | `web/` | Panel, editor, inicio de sesión, asistente, página de compilación del APK |
| Android | `android/` | Contenedor WebView, descubrimiento UDP, comprobación de integridad, cookie de sesión |
| Compilación y comprobaciones | `scripts/`, `packaging/` | Instalador, `check.ps1`, verificación de QR |

## 4. Telemetría

### 4.1. Trama

Una trama es un objeto JSON que llega por WebSocket inmediatamente después de la
conexión y luego a la frecuencia del gateway:

```json
{
  "type": "telemetry",
  "seq": 421,
  "ts": 1793541762842,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  },
  "values": {
    "attitude.pitchDeg": 2.4,
    "attitude.bankDeg": -6.1,
    "speed.iasKt": 108.2,
    "altitude.indicatedFt": 4520.0,
    "heading.magneticDeg": 274.0,
    "verticalSpeed.fpm": 120.0,
    "engine.rpm": 2380.0,
    "power.batteryMaster": true,
    "custom.lvar.apuBleed": 0.0
  }
}
```

`seq` crece de forma monotónica, `ts` es la hora Unix en milisegundos. El cliente
detecta las tramas perdidas por `seq` y simplemente sigue dibujando (esto no
importa para las agujas).

### 4.2. Variables

El catálogo completo con tipos, unidades, SimVar y eventos está en
[telemetry.md](telemetry.md). A continuación solo se enumeran las categorías.

El catálogo de variables es la única fuente de verdad (`telemetry.py`). Cada
entrada tiene un tipo (`number`, `bool`, `string`), un indicador de «acepta
comandos» y una descripción. El cliente puede obtener el catálogo mediante
`GET /api/telemetry/variables`.

Categorías:

- actitud, altitud, velocidad, rumbo, VSI;
- motor (RPM, colector/par, N1, ITT, combustible);
- eléctrico, flaps, piloto automático;
- `custom.<...>` — LVAR/RPN del perfil activo.

### 4.3. Proveedores

| Proveedor | Cuándo se usa | Características |
| --- | --- | --- |
| `simconnect` | vuelo real | `ctypes` + `SimConnect.dll`; datos de cadena `TITLE`, `ATC MODEL`; Client Data Area para LVAR/RPN. Si el `SimConnect.cfg` estándar no funciona, el propio gateway prueba TCP `127.0.0.1:19999` (el puerto de MSFS 2020/2024) a través de una configuración temporal |
| `mock` | demostración, desarrollo, pruebas | Modelo de vuelo procedimental, valores LVAR iniciales del perfil |
| `auto` | predeterminado | Intenta conectar SimConnect y retrocede a mock en caso de fallo |

Si el módulo WASM no está instalado, las claves `custom.*` simplemente no
aparecen y el panel muestra «--» — el resto de la telemetría sigue funcionando.
Tras dos tiempos de espera consecutivos, el cortacircuitos de Client Data pausa
las consultas durante 30 segundos para no bloquear el hilo de difusión de
telemetría.

### 4.4. Entrega y resiliencia

- Cada cliente WebSocket tiene su propia cola (8 tramas) y su hilo emisor: una
  tableta lenta no ralentiza a los demás, y las tramas antiguas se descartan.
- La reconexión del cliente usa retroceso exponencial; si no llegan mensajes
  durante más de 45 segundos, el cliente considera la conexión «semiabierta» y
  se reconecta.
- Una sesión puede caducar durante el vuelo — el cliente comprueba el estado una
  vez por minuto y redirige a la página de inicio de sesión.

## 5. Perfiles de aeronaves

Un perfil es un archivo JSON en `profiles/`. El esquema detallado está en
[`profile-schema.md`](profile-schema.md). En resumen:

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk",
  "icao": "C172",
  "revision": 3,
  "sim": { "match": { "title": "*Cessna*172*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S" },
  "widgets": [
    {
      "id": "attitude",
      "type": "attitude",
      "label": "Attitude indicator",
      "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
      "layout": {
        "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
        "phone": { "x": 0.03, "y": 0.015, "w": 0.94, "h": 0.3 }
      }
    }
  ]
}
```

- `sim.match` — plantillas (glob) para el título de la aeronave y el modelo ATC;
  el gateway cambia el perfil por sí mismo.
- `layout` — coordenadas en fracciones del panel (0..1); `base` y las anulaciones
  `phone`, `tablet-sm`, `tablet-lg`.
- `revision` — crece con cada guardado desde el editor.
- El guardado es atómico: archivo temporal → `fsync` → `os.replace`.

## 6. Clientes

### 6.1. Panel web

- Tres factores de forma con selección automática por ancho de pantalla; la
  elección manual se recuerda.
- Instrumentos: indicador de actitud, escalas circulares, lecturas,
  interruptores, selector rotativo, VSI, altímetro, indicador de rumbo;
  animación mediante `requestAnimationFrame`.
- Comodidad: brillo 100/72/45 % (`B`), modo kiosco (`F`, salir con `Esc`).
- El botón del teléfono muestra un código QR para un inicio de sesión rápido.

### 6.2. Editor

`/editor.html`: arrastrar y soltar, redimensionar, rejilla del 1 %,
deshacer/rehacer, copia de diseños entre factores de forma, guardado en el host.

### 6.3. Android

Contenedor WebView: encuentra el host mediante la baliza UDP o acepta una
dirección manual, comprueba la integridad de la interfaz y abre el panel. Si hay
una contraseña activada en el gateway, la WebView muestra la página de inicio de
sesión; la sesión se guarda en una cookie de la WebView y sobrevive al reinicio
de la aplicación. Los hosts protegidos con contraseña se marcan con un candado.

### 6.4. Página de inicio de sesión

`/login.html` es la única página disponible sin iniciar sesión (junto con sus
estilos). Muestra un campo de contraseña, errores, el bloque de apoyo al autor y
un botón «Cerrar sesión» si ya hay una sesión activa. La contraseña se envía solo
a su propio gateway, por HTTP en la red local (véase la sección «Seguridad»).

## 7. Red y conexión

| Qué | Puerto | Protocolo |
| --- | --- | --- |
| Archivos estáticos, REST, WebSocket | 8760 (configurable con `--port`) | TCP/HTTP + WS |
| Autodescubrimiento | 8761 | Difusión UDP |

- El gateway escucha en `0.0.0.0` e imprime todas sus direcciones al arrancar.
- Android encuentra el host mediante la baliza: nombre del PC, versión, número de
  perfiles, indicador de contraseña.
- El código QR del panel contiene la dirección y un token de un solo uso: el
  teléfono inicia sesión con un solo escaneo, sin introducir una contraseña (el
  token vive 10 minutos y se usa una vez).
- Introducción manual de la dirección: `192.168.1.10`, `192.168.1.10:8760` o una
  URL completa.

## 8. Autenticación con contraseña

### 8.1. Cómo activarla

Cualquiera de las siguientes formas:

```powershell
# 1. Guardar la contraseña en config/auth.json (de forma persistente)
OpenDeck.exe --set-password
#    o sin solicitud interactiva:
OpenDeck.exe --set-password "my-password"

# 2. Pasar la contraseña solo para esta ejecución (no se escribe en disco)
OpenDeck.exe --password "my-password"

# 3. Variable de entorno
$env:OPEN_DECK_PASSWORD = "my-password"
```

En la aplicación instalada hay un acceso directo «Establecer contraseña» en el
menú Inicio para esto. El archivo `config/auth.json` almacena **solo el hash
PBKDF2** (sal aleatoria, 210.000 iteraciones); elimina el archivo y el inicio de
sesión vuelve a ser libre. La opción `--no-auth` ignora el archivo y la
contraseña (solo para redes de confianza).

La contraseña de `--password` no se escribe en disco pero es visible en la lista
de procesos (`Get-Process` / Administrador de tareas). Para un uso permanente,
prefiere `--set-password`: se convierte en hash una vez en memoria al arrancar.

La longitud mínima de la contraseña es **6 caracteres**; límites: no más de 256
caracteres, sin caracteres de control, sin espacios al principio ni al final.

### 8.2. Cómo funciona el inicio de sesión

1. El cliente abre `/login.html` e introduce la contraseña.
2. `POST /api/auth/login` verifica el hash PBKDF2; si tiene éxito se crea una
   sesión (32 bytes aleatorios, TTL de 12 horas, ampliado con la actividad).
3. El servidor establece la cookie `open_deck_session` con `HttpOnly`,
   `SameSite=Lax` — JavaScript no puede verla, y el navegador la envía
   automáticamente.
4. Para los clientes nativos, la respuesta JSON devuelve un `token`; puede
   pasarse como `Authorization: Bearer <token>` o como `?token=` para WebSocket.
5. `POST /api/auth/logout` revoca la sesión y borra la cookie.

Solo son de acceso público:

| Ruta | Por qué |
| --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | la página de inicio de sesión y sus estilos |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | el propio inicio de sesión |
| `/api/health` | comprobación «¿es este el gateway?» e indicador de contraseña |
| `/api/integrity` | comprobación de integridad de la interfaz (condición de licencia) |
| `/api/donation` | bloque de apoyo al autor (condición de licencia) |
| `/license` | texto de la licencia |

Todo lo demás — perfiles, telemetría, comandos, ajustes de Android, compilación
del APK, QR, `WS /ws` — requiere una sesión. Las páginas sin sesión responden con
una redirección a `/login.html?next=…`.

### 8.3. Protección contra fuerza bruta

- 5 intentos fallidos desde una IP en 60 segundos → bloqueo durante 60 segundos
  (respuesta `429` con `Retry-After`).
- La comparación de hashes usa `hmac.compare_digest` (tiempo constante).
- Los intentos fallidos se registran con la dirección pero sin la contraseña.

### 8.4. Inicio de sesión por QR desde un teléfono

El botón «teléfono» del panel solicita `POST /api/pair` (se requiere una sesión).
El gateway emite un token de un solo uso para 10 minutos; el QR codifica
`http://<address>:<port>/?pair=<token>`. El teléfono abre el enlace, el gateway
canjea el token por una sesión normal, establece la cookie y redirige a `/`. El
token de emparejamiento en sí no es una sesión: como cookie o token Bearer
devuelve `401`, por lo que el enlace no puede reutilizarse tras el canje.
Reutilizar el token se rechaza.

## 9. Asistente de aterrizaje y rodaje

La página `/assist.html` y la API `/api/assist*` añaden dos bucles auxiliares.
Esto **no es un piloto automático certificado**: el piloto controla el vuelo y
puede desactivar el asistente en cualquier momento.

### 9.1. Rodaje

- Se activa solo en tierra, con el freno de estacionamiento liberado y una
  velocidad inferior a 35 kt.
- Mantiene la velocidad respecto al suelo objetivo (3–25 kt) con un controlador
  PI de acelerador y el rumbo con un controlador P de timón; el piloto cambia el
  rumbo con los botones ±1°/±5°.
- «STOP»: acelerador 0, timón 0, freno de estacionamiento.
- Se desactiva automáticamente si la aeronave despega, se acciona el freno de
  estacionamiento o la velocidad supera 35 kt.

### 9.2. Aterrizaje

- ARM: activa `AP_MASTER` y `AP_APR_HOLD` (aproximación ILS). Requiere una
  velocidad de al menos 40 kt y la aeronave en el aire.
- A 60–15 ft de altitud por radio, el asistente reduce linealmente el acelerador
  del 45 % al 0.
- Al tocar tierra: acelerador 0, piloto automático desconectado; tras reducir por
  debajo de 5 kt — «rodaje posterior completado».
- TOGA: acelerador a tope, AP y APR desconectados (motor y al aire).
- El asistente no toca el elevador: la aproximación y el flare siguen en manos
  del piloto automático/piloto.

Estado y consignas: `GET /api/assist`; acciones — `POST /api/assist/taxi`
(`engage`, `disengage`, `stop`, `speed`, `heading`) y
`POST /api/assist/landing` (`arm`, `disarm`, `toga`). Todas las peticiones
requieren una sesión.

## 10. API

URL base: `http://<host>:<port>`. Todas las respuestas son JSON; los errores
tienen la forma `{"error": "…", "code": "…"}`.

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/health` | público | Estado, versión, frecuencia, indicador de contraseña |
| GET | `/api/auth/status` | público | `{required, authenticated}` |
| POST | `/api/auth/login` | público | `{password}` → sesión + cookie |
| POST | `/api/auth/logout` | público | Revocar la sesión actual |
| POST | `/api/pair` | sesión requerida | Token QR de un solo uso |
| GET | `/api/profiles` | sesión requerida | Lista de perfiles |
| GET | `/api/profiles/{id}` | sesión requerida | Perfil completo |
| PUT | `/api/profiles/{id}` | sesión requerida | Guardar un perfil (id del cuerpo = id de la URL) |
| GET | `/api/telemetry` | sesión requerida | Última trama |
| GET | `/api/telemetry/variables` | sesión requerida | Catálogo de variables |
| POST | `/api/sim/command` | sesión requerida | `{key, value}` → confirmación |
| POST | `/api/sim/aircraft` | sesión requerida | `{profileId}` — selección manual de aeronave |
| GET | `/api/integrity` | público | Resultado de la comprobación SHA-256 |
| GET | `/api/donation` | público | Datos de apoyo al autor |
| GET | `/api/connect` | sesión requerida | Direcciones del gateway para QR/ayudas |
| GET | `/api/qr.svg?text=…` | sesión requerida | SVG con un código QR |
| GET/PUT | `/api/android/settings` | sesión requerida | Ajustes de compilación del APK |
| GET/POST | `/api/android/build` | sesión requerida | Inicio/estado de la compilación del APK |
| GET | `/api/android/apk` | sesión requerida | Descargar el APK |
| GET | `/api/assist` | sesión requerida | Estado del asistente y telemetría |
| POST | `/api/assist/taxi` | sesión requerida | Control del asistente de rodaje |
| POST | `/api/assist/landing` | sesión requerida | ARM / DISARM / TOGA |
| WS | `/ws` | sesión requerida | Telemetría y comandos |

Ejemplo de inicio de sesión y petición:

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"my-password"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

Comando:

```json
{"type": "command", "id": "c17", "key": "power.batteryMaster", "value": true}
```

Respuesta: `{"type": "ack", "id": "c17", "ok": true, "value": true}` o
`ok:false` con un código de error. Los comandos están limitados a ~20 por segundo
por cliente.

## 11. Instalación y arranque

### 11.1. Instalador de Windows

`OpenDeck-Setup-<version>.exe` — instalación por usuario sin derechos de
administrador, no requiere Python. Se crean accesos directos para: iniciar el
gateway, el panel en el navegador, la página de compilación del APK, «Establecer
contraseña» y la desinstalación.

### 11.2. Desde el código fuente

```powershell
python -m msfs_gateway --sim auto          # vuelo real
python -m msfs_gateway --sim mock          # demostración sin el simulador
python -m msfs_gateway --password "secret123"
```

| Parámetro | Predeterminado | Propósito |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8760` | dirección y puerto |
| `--allow-host NAME` | — | nombre DNS adicional para Host (si el panel se abre por nombre) |
| `--sim` | `auto` | `auto`, `mock`, `simconnect` |
| `--telemetry-hz` | `30` | frecuencia de tramas, 1..60 |
| `--simconnect-dll` | detección automática | ruta a `SimConnect.dll` |
| `--simconnect-host` | `127.0.0.1` | dirección de SimConnect (simulador remoto) |
| `--simconnect-port` | `19999` | puerto TCP de SimConnect |
| `--profile-dir` | `profiles/` | directorio de perfiles |
| `--password` | — | contraseña para esta ejecución |
| `--set-password [PWD]` | — | guardar el hash y salir |
| `--auth-file` | `config/auth.json` | archivo del hash |
| `--web-dir` / `--profile-dir` | `web/` / `profiles/` | directorios estático y de perfiles |
| `--donation-config` | `config/donation.json` | datos de apoyo al autor |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--discovery-port` / `--discovery-interval` | `8761` / `3` | baliza UDP: puerto y periodo |
| `--no-auth` | — | ignorar la contraseña |
| `--no-wasm` | — | sin LVAR/RPN |
| `--no-discovery` | — | sin baliza UDP |
| `--build-apk [CONFIG]` | — | compilar el APK y salir |

### 11.3. APK de Android

La instalación contiene las fuentes de Android; el APK listo se compila en
`android/dist/OpenDeck-Android-<version>.apk`. La página `/android.html` (requiere
inicio de sesión) permite cambiar el nombre, el id del paquete, la versión y la
dirección predeterminada del gateway y compilar el APK en el acto. Se requieren
JDK 17, Android SDK y Gradle 8.x; en la distribución de publicación el APK ya
está adjunto.

## 12. Diagnóstico

| Síntoma | Qué comprobar |
| --- | --- |
| El panel no se abre desde el teléfono | la misma Wi-Fi, la dirección del banner, el firewall de Windows (puerto 8760), `--host 0.0.0.0` |
| «Se requiere inicio de sesión por contraseña» | hay una contraseña establecida; introdúcela en `/login.html`; el token QR vive 10 minutos |
| «Contraseña incorrecta» | distribución del teclado/mayúsculas; restablecer: eliminar `config/auth.json` o usar `--no-auth` |
| Los instrumentos muestran «--» | sin SimConnect/WASM, mock seleccionado, la aeronave no tiene perfil, el simulador sigue en el menú principal |
| El perfil no cambia | `sim.match` no coincide con el nombre/modelo; selecciónalo manualmente |
| La compilación del APK no se inicia | no se encuentra JDK/SDK/Gradle; especifica las rutas en `/android.html` |
| «Integridad violada» | se modificaron archivos críticos; `python -m msfs_gateway.integrity --write` |
| `SimConnect_Open … 0x80004005` | el propio gateway prueba TCP `127.0.0.1:19999`; si eso no ayudó — comprueba `%APPDATA%\Microsoft Flight Simulator\SimConnect.cfg` (sobrescribe los ajustes) y que haya un vuelo cargado; para un simulador remoto configura `--simconnect-host/--simconnect-port` |

Registros: la consola del gateway (`--log-level DEBUG`), la pestaña «Red» del
navegador y `adb logcat` para Android (etiqueta `OpenDeckDiscovery`).

## 13. Seguridad

- La contraseña protege la API y la telemetría de un «vecino de Wi-Fi», pero
  **el tráfico va por HTTP sin TLS**. En una red doméstica de confianza esto es
  aceptable; para redes de invitados, usa una VLAN separada o un proxy inverso
  con TLS.
- La cookie de sesión es `HttpOnly` + `SameSite=Lax`; el riesgo de CSRF se
  reduce. Los tokens de URL se usan solo para WebSocket (`?token=`) y el QR de un
  solo uso (`?pair=`). El token QR se acepta solo a través de `/?pair=` y no es
  una sesión.
- Comprobación de `Origin` para POST/PUT del navegador y WebSocket: una petición
  con un `Origin` ajeno recibe `403`; los clientes sin `Origin` se permiten.
- Comprobación de `Host` contra nombres/IP locales: un Host desconocido recibe
  `403` (protección contra DNS rebinding).
- Los intentos de inicio de sesión están limitados a 5 por minuto por dirección.
- CORS está desactivado intencionadamente: una página de terceros no puede leer
  las respuestas de la API.
- Si no hay contraseña establecida, el gateway advierte explícitamente en la
  consola de que el panel y los comandos están disponibles para todos en la red
  local.
- La baliza UDP no está firmada: cualquier host de la red puede hacerse pasar por
  el gateway. No expongas el gateway a internet.
- Android: lista de permitidos de navegación en WebView, acceso a
  `file:`/`content:` prohibido, contenido mixto prohibido.

## 14. Limitaciones

- Una ejecución real de SimConnect/WASM requiere MSFS instalado; en el
  repositorio la lógica se verifica mediante emulación.
- El APK está firmado con una clave de depuración; la firma de publicación aún no
  está automatizada.
- Sin mDNS: solo la baliza UDP.
- Un gateway activo por puerto; los perfiles son archivos, sin base de datos.

## 15. Glosario

| Término | Significado |
| --- | --- |
| **Gateway** | El proceso en el PC con el simulador: lee la telemetría y la sirve a los clientes |
| **Host** | La máquina donde se ejecuta el gateway (en el cliente Android — el PC descubierto) |
| **Perfil** | Un archivo JSON con instrumentos y diseños para una aeronave concreta |
| **Instrumento / widget** | Un elemento del panel: indicador de actitud, escala, interruptor, etc. |
| **Factor de forma** | Una clase de pantalla: `phone`, `tablet-sm`, `tablet-lg` |
| **Aeronave** | Una aeronave concreta en el simulador; el perfil se selecciona por `TITLE`/`ATC MODEL` |
| **Telemetría** | El flujo de valores SimVar y `custom.*` en una trama JSON |
| **Trama** | Un único mensaje `telemetry` con `seq`, `ts`, `sim`, `values` |
| **LVAR** | Una variable local de la aeronave (PMDG, Fenix, FBW, etc.) |
| **RPN** | Notación polaca inversa — un script para calcular un valor en MSFS |
| **Puente WASM** | Intercambio LVAR/RPN a través del Client Data Area del módulo MobiFlight/SimBridge |
| **Client Data Area** | Un área SimConnect con nombre para intercambiar bloques de datos |
| **AP / APR / AT** | Piloto automático / modo de aproximación ILS / autothrottle |
| **Retard** | Reducción suave del acelerador durante el flare (asistente de aterrizaje) |
| **TOGA** | Take Off / Go Around: acelerador a tope y motor y al aire |
| **Emparejamiento** | Inicio de sesión desde un teléfono mediante un token QR de un solo uso |
| **Sesión** | Un inicio de sesión activo: un token en cookie/Bearer, TTL de 12 horas |
| **Integridad** | Comparación del SHA-256 de los archivos críticos de la interfaz con el manifiesto |
| **Air-gapped** | Una red sin acceso a internet; todos los recursos son locales |

## 16. Comentarios y soporte

- **Autor:** Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck).
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).
- Errores y sugerencias — a través de las plantillas de issue de GitHub (véase
  `.github/`).
- Vulnerabilidades — de forma privada, según [security.md](security.md).
- Preguntas de configuración — Discussions (si está activado) o un issue con la
  plantilla «Bug».
- Licencia y bloque obligatorio de apoyo al autor — [LICENSE](../../LICENSE).

## 17. Licencia

[GNU Affero General Public License v3.0](../../LICENSE) y
[condiciones adicionales Sección 7](../../COPYING.ADDITIONAL): el código fuente
es abierto, las modificaciones se distribuyen bajo AGPL; el bloque de apoyo al
autor y la comprobación de integridad son obligatorios y no pueden eliminarse.
