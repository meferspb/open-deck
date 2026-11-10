# ✈️ Open Deck for MSFS

**Languages:** [English](README.md) · [Русский](README_RU.md) · [Deutsch](README_DE.md) · [中文](README_ZH.md) · [Español](README_ES.md) · [日本語](README_JA.md)


<img src="docs/pic1.jpg" alt="Open Deck for MSFS" width="220" />

**Paneles de instrumentos de MSFS 2020/2024 en tu teléfono y tableta — por la red
local, sin internet.**

Un gateway de Windows lee la telemetría de Microsoft Flight Simulator a través de
SimConnect (incluidos LVAR/RPN mediante un módulo WASM) y la sirve a clientes web
y a una aplicación Android por HTTP + WebSocket. Los paneles se describen
mediante perfiles JSON de aeronaves y se renderizan para tres factores de forma.

El proyecto es totalmente autocontenido: **ni CDN, ni fuente, ni servicio
externos** — todo funciona en una red aislada y en una máquina sin acceso a
internet.

| | |
| --- | --- |
| Versión | 0.1.0 |
| Pruebas | 252 Python + 41 Node.js |
| Plataforma del host | Windows 10/11 (Python 3.11+ o instalador) |
| Clientes | navegador (cualquiera moderno), Android 8+ |
| Autor | Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) |
| Donat | [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) |
| Licencia | [GNU AGPL-3.0](LICENSE) — software libre con un bloque obligatorio de apoyo al autor (Sección 7) |

## Capturas de pantalla

| Teléfono | Tableta grande |
| --- | --- |
| ![Panel en un teléfono](docs/screenshots/phone.png) | ![Panel en una tableta](docs/screenshots/tablet-lg.png) |

| Six-pack clásico de la C172 | Editor de paneles |
| --- | --- |
| ![Six-pack](docs/screenshots/sixpack-phone.png) | ![Editor](docs/screenshots/editor.png) |

![Inicio de sesión por contraseña desde un teléfono](docs/screenshots/login.png)

![Asistente de aterrizaje y rodaje](docs/screenshots/assist.png)

## Características

### Gateway

- **Un solo puerto** para archivos estáticos, REST y WebSocket — basta una única
  regla de firewall; solo la biblioteca estándar de Python, sin
  `pip install`.
- **Fuente de telemetría intercambiable**:
  - `simconnect` — SimConnect nativo a través de `ctypes`;
  - `mock` — un «vuelo» procedimental sin el simulador (demostración y pruebas);
  - `auto` — SimConnect, con retroceso a mock en caso de fallo.
- **Autodetección de aeronave**: el perfil declara `sim.match.title` y
  `atcModel`, el gateway lee `TITLE`/`ATC MODEL` y cambia el panel
  automáticamente.
- **LVAR/RPN a través de WASM** (MobiFlight/SimBridge): Client Data Area, un canal
  síncrono con tiempos de espera, escrituras LVAR mediante RPN.
- **Autodescubrimiento del host** mediante baliza UDP (para clientes nativos), un
  servidor HTTP integrado, API JSON y validación estricta de perfiles y comandos.

### Perfiles e instrumentos

- **6 perfiles**: Cessna 172S, Cessna 172 Classic Six-Pack, Daher TBM 930,
  Airbus A320, Piper PA-28-181, demostración LVAR.
- **Instrumentos**: indicador de actitud, escalas circulares, lecturas digitales,
  interruptores de palanca, selector rotativo (gestos/rueda), luces anunciadoras,
  VSI, altímetro de tres agujas, indicador de rumbo con «bug».
- Diseño en fracciones del panel + anulaciones `layout.phone`,
  `layout.tablet-sm`, `layout.tablet-lg`; esquema y validación —
  [`docs/es/profile-schema.md`](docs/es/profile-schema.md).

### Clientes

- **Cliente web** en módulos ES vanilla: animación fluida (rAF), suavizado,
  gestos, widgets de comando, reconexión.
- **Tres factores de forma** con selección automática por ancho de pantalla.
- **Comodidad en cabina**: brillo del panel 100/72/45 % (tecla `B`) y modo kiosco
  sin interfaz (`F`, salir con `Esc`).
- **Conexión del teléfono por QR**: la página del panel muestra un código QR para
  la dirección del host y una lista de direcciones de red.
- **Cliente Android**: panel WebView, descubrimiento del host por UDP,
  comprobación de integridad, pantalla de conexión con entrada manual de
  dirección.

### Seguridad

- **Inicio de sesión por contraseña** (al menos 6 caracteres): hash PBKDF2,
  sesiones en una cookie `HttpOnly`, tokens Bearer para clientes nativos,
  limitación de intentos, inicio de sesión QR desde un teléfono sin introducir
  contraseña. Un token QR de un solo uso es válido solo a través de `/?pair=` y
  no se acepta como sesión normal.
- **Protección de mismo origen y Host**: las peticiones POST/PUT del navegador y
  WebSocket con un `Origin` ajeno, así como las peticiones con un `Host`
  desconocido, se rechazan (`403`). Esto cierra CSRF, el secuestro de WebSocket
  entre sitios y el DNS rebinding; los clientes sin `Origin` (Android, curl)
  funcionan como antes.
- Solo la página de inicio de sesión, las comprobaciones de salud/integridad y el
  bloque de apoyo al autor son de acceso público — todo lo demás (perfiles,
  telemetría, comandos, compilación del APK) está cerrado.

### Asistente de aterrizaje y rodaje

- **Rodaje**: mantener una velocidad objetivo (3–25 kt) y un rumbo — el gateway
  calcula acelerador y timón; «STOP» da acelerador cero y el freno de
  estacionamiento.
- **Aterrizaje**: ARM activa AP y APR; a 60–15 ft el asistente reduce suavemente
  el acelerador, y al tocar tierra desconecta el piloto automático; TOGA — motor
  y al aire.
- Página `/assist.html` (el botón «Asistente» en la cabecera del panel); también
  funciona en un teléfono. El asistente es un bucle auxiliar; el piloto sigue
  teniendo el control del vuelo.

### Herramientas

- **Editor de paneles** `/editor.html`: arrastrar y soltar, redimensionar, ajuste
  a rejilla del 1 %, deshacer/rehacer (`Ctrl+Z` / `Ctrl+Y`), copia de diseños
  entre factores de forma, guardado del perfil en el host.
- **Compilador de APK de Android** directamente en la distribución: la página
  `/android.html` cambia el nombre de la aplicación, el id del paquete, la
  versión y la dirección del gateway, compila el APK y lo ofrece para descarga;
  también hay una CLI `--build-apk`.
- **Instalador de Windows** (NSIS, por usuario, sin derechos de administrador) con
  un APK listo y las fuentes de Android dentro.

### Licencia e integridad

- El bloque de apoyo al autor **no se puede eliminar**; el SHA-256 de los archivos
  críticos se verifica al arrancar el host y en el navegador, y si no coincide se
  bloquea la interfaz.

## Instalación (Windows, sin Python)

Descarga `OpenDeck-Setup-<version>.exe` de las releases, ejecútalo y pulsa
«Siguiente» — no se necesitan derechos de administrador, ni Python, ni internet.
La instalación va a `%LOCALAPPDATA%\OpenDeck`, y se crean accesos directos y una
entrada en «Programas y características».

1. Inicia **Open Deck for MSFS** — se abre una consola con las direcciones del
   panel.
2. Permite a la aplicación el acceso a la red privada en el aviso del firewall.
3. Abre el panel en este PC o introduce la dirección impresa en tu teléfono, o
   escanea el QR del panel (el botón del teléfono).

Detalles de compilación del instalador —
[`docs/es/packaging.md`](docs/es/packaging.md).

## Inicio de sesión por contraseña

El inicio de sesión se activa de una de las siguientes formas:

```powershell
# guarda la contraseña (hash PBKDF2) en config/auth.json
OpenDeck.exe --set-password            # solicita la contraseña en la consola
OpenDeck.exe --set-password "my-password"

# o solo para esta ejecución
OpenDeck.exe --password "my-password"
```

Contraseña mínima **6 caracteres**. El archivo `config/auth.json` almacena solo el
hash; elimínalo para permitir de nuevo el acceso sin contraseña. En el menú
Inicio, el instalador crea un acceso directo «Establecer contraseña». Detalles —
en la [descripción del servicio](docs/es/service.md#8-autenticación-con-contraseña).

Clientes conectados:

- navegador — página `/login.html`, luego el panel (cookie durante 12 horas);
- teléfono — escanea el QR del panel: un token de un solo uso inicia sesión sin
  contraseña (válido 10 minutos);
- Android — el panel muestra la pantalla de inicio de sesión por sí mismo; la
  sesión se guarda en la WebView.

## Ejecución desde el código fuente

**Se requiere Python 3.11+**; Node.js — solo para las pruebas del cliente.

```powershell
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# modo demostración sin el simulador: http://127.0.0.1:8760/
python -m msfs_gateway --sim mock

# vuelo real: SimConnect, con retroceso a mock en caso de fallo
python -m msfs_gateway --sim auto

# ruta DLL explícita y 60 Hz
python -m msfs_gateway --sim simconnect --simconnect-dll C:\SDK\SimConnect.dll --telemetry-hz 60
```

Parámetros útiles:

| Parámetro | Predeterminado | Propósito |
| --- | --- | --- |
| `--host` | `0.0.0.0` | dirección de escucha |
| `--allow-host NAME` | — | nombre DNS adicional para la cabecera Host (repetible) |
| `--port` | `8760` | puerto HTTP y WebSocket |
| `--sim` | `auto` | `auto` / `mock` / `simconnect` |
| `--telemetry-hz` | `30` | frecuencia de difusión, 1..60 Hz |
| `--simconnect-host` / `--simconnect-port` | `127.0.0.1` / `19999` | dirección de SimConnect (incluido un simulador remoto) |
| `--profile-dir` | `profiles/` | directorio de perfiles JSON |
| `--password` / `--set-password` | — | contraseña para la ejecución / guardar el hash y salir |
| `--auth-file` / `--no-auth` | `config/auth.json` | archivo del hash / desactivar inicio de sesión |
| `--no-wasm` | — | desactivar el puente WASM |
| `--no-discovery` | — | desactivar el autodescubrimiento UDP |
| `--build-apk [CONFIG]` | — | compilar el APK de Android y salir |

## APK de Android desde la distribución

La aplicación instalada contiene las fuentes de Android (`android/`); el APK
listo se compila en `android/dist/OpenDeck-Android-<version>.apk`, y el menú
Inicio tiene «Compilar APK de Android» (`http://127.0.0.1:8760/android.html`).

En la página se configuran el nombre de la aplicación, el id del paquete, la
versión y la dirección predeterminada del gateway; el botón «Compilar APK»
ejecuta `gradle assembleDebug` en el mismo ordenador. Se requieren **JDK 17**,
**Android SDK** y **Gradle 8.x** (las rutas se pueden especificar en la página o
definir mediante `JAVA_HOME` / `ANDROID_HOME` / `gradle` en `PATH`). En la
distribución de publicación el APK listo ya está en `android/dist`.

```powershell
OpenDeck.exe --build-apk                        # ajustes de config/android-build.json
OpenDeck.exe --build-apk C:\path\settings.json
```

## Documentación

El índice completo está en [docs/es/README.md](docs/es/README.md). Documentos
principales:

- [Descripción del servicio: propósito, API, autenticación, asistente, operación](docs/es/service.md)
- [Arquitectura y responsabilidades](docs/es/architecture.md)
- [Protocolo de red: REST, WebSocket, inicio de sesión, QR, autodescubrimiento](docs/es/protocol.md)
- [Catálogo de variables de telemetría](docs/es/telemetry.md) *(generado desde el código)*
- [Catálogo de instrumentos y opciones](docs/es/widgets.md) *(generado desde el código)*
- [Esquema del perfil de aeronave](docs/es/profile-schema.md)
- [Cliente Android: compilación, inicio de sesión, depuración](docs/es/android.md)
- [Compilación del instalador](docs/es/packaging.md)
- [Coste de servicios conectados frente a equivalentes locales](docs/es/pricing.md)
- [Historial de cambios](docs/es/changelog.md)

## Estructura del repositorio

```
msfs_gateway/            # gateway de Python (stdlib)
  sim/                   # proveedores: mock, simconnect, client_data, wasm_bridge
  qr.py                  # generador de QR integrado (SVG)
  assist.py              # asistente de aterrizaje y rodaje
  android_build.py       # compilación del APK desde la distribución
  http_api.py, hub.py, profiles.py, integrity.py, discovery.py, websocket.py
web/                     # cliente web y editor (JS vanilla, sin paso de compilación)
profiles/                # perfiles JSON de aeronaves
android/                 # cliente Android (Kotlin, sin AndroidX)
packaging/               # PyInstaller + NSIS: instalador de Windows
scripts/                 # build-installer.ps1, check.ps1, verify_qr.py
tests/                   # unittest (Python) y node:test (JS)
docs/                    # arquitectura, protocolo, esquema, capturas
config/                  # datos del autor, ajustes de compilación del APK
integrity/               # manifiesto SHA-256 de archivos críticos
```

## Pruebas

```powershell
python -m unittest discover -s tests        # 252 pruebas
node --test "tests/web/*.test.mjs"          # 29 pruebas
python -m ruff check msfs_gateway tests scripts
```

Ejecuta todas las comprobaciones de una vez:

```powershell
pwsh -File scripts/check.ps1
```

Cubierto: telemetría y perfiles, WebSocket (RFC 6455), bus y comandos, proveedor
mock, WASM/Client Data, QR (estructura + matriz de referencia), compilador de APK,
integridad, geometría de instrumentos y diseños.

## Desarrollo

Véase [`docs/es/contributing.md`](docs/es/contributing.md): estilo, pruebas, cómo
añadir un perfil o un instrumento. Cuestiones de seguridad —
[`docs/es/security.md`](docs/es/security.md).

## Hoja de ruta

1. **Ejecución en vivo del puente WASM** con MSFS + MobiFlight/SimBridge (la
   lógica y la emulación están cubiertas por pruebas).
2. **Firma de publicación del APK**: keystore/alias en los ajustes del
   compilador.
3. **mDNS (Bonjour)** como alternativa a la baliza UDP.
4. **Editor**: guías de alineación, selección múltiple.
5. **Android**: renderizado nativo con Compose, servicio en primer plano para el
   modo kiosco.
6. **Grabación/reproducción de telemetría** para demostraciones y perfilado.

## Seguridad

El proyecto está diseñado para una **red local de confianza**: HTTP sin TLS y sin
autenticación, y una baliza UDP sin firmar. No expongas el gateway a internet.
Más — [`docs/es/security.md`](docs/es/security.md).

## Soporte / Donat

- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
- **Autor:** Viktor Krasnikov
- **Repositorio:** [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)

## Licencia

El proyecto se distribuye bajo la **GNU Affero General Public License v3.0
(AGPL-3.0)** con condiciones adicionales de conformidad con la **Sección 7**.

* Eres libre de usar, estudiar, modificar y distribuir este código siempre que se
  conserve la misma licencia (AGPL-3.0) y el código fuente de cualquier
  modificación esté disponible (incluido el uso en un servidor / a través de una
  red según la Sección 13).
* **Condición obligatoria (Sección 7(b) y Sección 5(d)):** En todas las
  bifurcaciones, compilaciones y versiones modificadas está **estrictamente
  prohibido** eliminar, ocultar o alterar la mención del autor original
  (**Viktor Krasnikov**, [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck))
  y los enlaces activos a la página de apoyo (donativo) del desarrollador en la
  interfaz de usuario y la documentación del programa:
  [Donat — https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

El texto legal detallado de las condiciones adicionales se proporciona en el
archivo [COPYING.ADDITIONAL](./COPYING.ADDITIONAL). El texto completo de la
licencia base está en el archivo [LICENSE](./LICENSE).
