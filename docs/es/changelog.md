# Historial de cambios

Formato: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
versiones — [SemVer](https://semver.org/lang/ru/).

## [Sin publicar]

### Cambiado

- Rebranding completo a **Open Deck for MSFS**: nombre del producto, interfaces
  web, aplicación Android (`com.opendeck.msfs`), archivos ejecutables, instalador,
  documentación y perfiles de aeronaves.
- Logotipo e iconos de la aplicación generados a partir de `docs/pic1.jpg`;
  archivos `web/img/open-deck-mark.jpg`, `web/favicon.ico`, drawable de Android y
  `packaging/windows/open-deck.ico`.

### Añadido

- Enlace **Donat** — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) — en el panel web,
  el editor, la pantalla de inicio de sesión, el asistente, la interfaz Android,
  el README y la documentación.
- Se indican el autor **Viktor Krasnikov** y el repositorio
  [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck).

### Corregido

- SimConnect: el orden de los campos de `SIMCONNECT_RECV_SIMOBJECT_DATA` se ha
  ajustado a `SimConnect.h` (`dwFlags`/`dwEntryNumber`/`dwOutOf`/`dwDefineCount`) —
  sin esto, la telemetría numérica en vivo no se actualizaba.
- SimConnect: los comandos se ejecutan en el hilo de despacho; los event id se
  restablecen al reconectar; los `AddToDataDefinition` fallidos ya no desplazan
  los índices de los demás datos.
- WASM/Client Data: cortacircuitos tras los tiempos de espera y bloque LVAR ≤ 56
  elementos, para que un módulo WASM ausente no bloquee el flujo de telemetría.
- El token QR ya no se acepta como una sesión normal ni amplía el TTL.
- Añadida la comprobación de `Origin` para POST/PUT del navegador y WebSocket, así
  como la comprobación de `Host` contra nombres/IP locales (cierra el DNS
  rebinding); para el acceso por un nombre DNS propio se añadió `--allow-host`.
- Cerrado el open redirect en `login.js` mediante una barra invertida en `next`.
- Los errores del cuerpo de la petición ya no dejan la conexión keep-alive en un
  estado desincronizado; añadido un límite de conexiones simultáneas.
- Los tokens `pair`/`token` se redactan en el registro de peticiones.
- Asistente: la ausencia de altitud/velocidad/rumbo no se sustituye por cero; AP
  se revierte si APR no se activó; al perderse la conexión los bucles se
  desconectan; `stop` informa de un error si los comandos no se enviaron.
- Telemetría: las SimVar integradas que no están en la definición de SimConnect o
  que están obsoletas se devuelven como `null` (la interfaz muestra `--`).
- Precisión de SimVar: `TURB ENG MAX TORQUE PERCENT:1` (par actual en % del
  máximo) y `RADIO HEIGHT` en lugar de la altura sobre el suelo.
- El diálogo QR recrea el token de un solo uso al abrirse y al caducar el TTL.
- El editor limpia el historial al cambiar de perfil y advierte de cambios no
  guardados.
- Compilador de Android: allowlist para `extraGradleArgs`, comprobación de tipos,
  prohibición de `outputDir` relativo a la unidad, `appName` seguro.
- Android: la URL completa con puerto vuelve a aceptarse en la entrada manual.
- SimConnect: la reconexión sobrevive a `OSError` de la configuración temporal; la
  detención de hilos es más robusta.
- La baliza de autodescubrimiento, al desbordarse, se envía sin la lista de
  perfiles en lugar de omitirse por completo.
- Limitado el crecimiento de los limitadores en memoria; los comandos REST
  recibieron rate-limit por IP.
- Con la contraseña desactivada, la consola advierte del acceso abierto en la LAN.

## [0.1.0] — 2026-11-01

Primera publicación pública.

### Añadido

- **Asistente de aterrizaje y rodaje**: mantenimiento de velocidad/rumbo en
  tierra, ARM/DISARM/TOGA para la aproximación ILS, retard automático a 60–15
  pies, desconexión de AP al tocar tierra; página `/assist.html` y API
  `/api/assist*`.
- **Inicio de sesión por contraseña** (desde 6 caracteres): hash PBKDF2 en
  `config/auth.json`, sesiones en cookie `HttpOnly` durante 12 horas, tokens
  Bearer, inicio de sesión QR de un solo uso desde el teléfono, límite de
  intentos y protección contra fuerza bruta.
- Gateway en Python (solo stdlib): HTTP + WebSocket (RFC 6455) en un solo puerto,
  autodescubrimiento UDP, perfiles de aeronaves con esquema JSON y validación.
- Proveedores de telemetría: `simconnect` (ctypes, datos de cadena `TITLE` y
  `ATC MODEL`), `mock` y retroceso automático `auto`.
- Puente WASM LVAR/RPN a través de SimConnect Client Data Area
  (MobiFlight/SimBridge): canal de peticiones, tiempos de espera, reconexión,
  escritura LVAR mediante RPN.
- Cliente web sin frameworks: horizonte artificial, escalas circulares, paneles,
  interruptores de palanca, selector rotativo, variómetro, altímetro, indicador
  de rumbo; tres factores de forma.
- Editor de paneles: arrastrar y soltar, deshacer/rehacer, rejilla, copia del
  diseño entre factores de forma, guardado en el host.
- Autodetección de aeronave por nombre y modelo ATC; la selección manual queda
  fijada hasta que cambie la aeronave en el simulador.
- Conexión rápida del teléfono: código QR (generador propio sobre stdlib) y lista
  de direcciones de red.
- Cliente Android: panel WebView, descubrimiento UDP, comprobación de integridad.
- Compilador de APK de Android en la distribución: ajustes de la aplicación
  (nombre, package id, versión, dirección del gateway), compilación desde la
  página web `/android.html` y CLI `--build-apk`.
- Instalador de Windows (NSIS, por usuario, sin derechos de administrador), APK
  listo y fuentes de Android dentro.
- Comodidad en la cabina: brillo del panel en tres niveles, modo kiosco.
- Perfiles: Cessna 172S, Cessna 172 Six-Pack, Daher TBM 930, Airbus A320,
  Piper PA-28, demostración LVAR.

### Corregido

- Un cliente lento o bloqueado ya no detiene la difusión de telemetría: cada
  conexión tiene su propia cola (8 tramas) y su hilo emisor; las tramas antiguas
  se descartan en lugar de bloquear el bus.
- WebSocket se cierra con el código 1002 ante una violación del protocolo (tramas
  de control sin marcar, fragmentadas y demasiado grandes).
- La detención del gateway no espera a un cliente bloqueado: el close-frame se
  envía con tiempo de espera, y el socket se cierra en cualquier caso.
- POST/PUT siempre leen el cuerpo de la petición — la conexión keep-alive ya no se
  rompe tras iniciar la compilación del APK.
- Compilador de APK: el vigilante de tiempo de espera se activa aunque Gradle se
  bloquee y no imprima nada; en el nombre de la aplicación se prohíben los
  caracteres de control.
- Android: una carrera al reiniciar rápidamente la búsqueda del host ya no apaga
  el nuevo receptor UDP.
- Editor: ante un error de guardado se revierte la revisión, y un segundo clic no
  inicia un guardado paralelo.
- Estáticos: una ruta con un byte NUL da 404 en lugar de una excepción, HEAD no
  duplica el cuerpo, y las desconexiones de clientes no llenan el log de
  tracebacks.

- SimConnect: si el `SimConnect.cfg` del usuario apunta a un canal inexistente
  (causa frecuente del error `0x80004005`), el gateway reintenta automáticamente
  la conexión por TCP `127.0.0.1:19999` — el puerto que escucha MSFS 2020/2024;
  la dirección y el puerto se configuran con `--simconnect-host` /
  `--simconnect-port`.

### Documentación

- Índice completo de documentación `docs/README.md`; guía del desarrollador
  `docs/development.md` (mapa del código, añadir variable/instrumento/perfil/
  proveedor/página, pruebas, publicación).
- Los catálogos `docs/telemetry.md` y `docs/widgets.md` se generan desde el código
  (`python -m msfs_gateway.docsgen --write`); una prueba y CI comprueban su
  actualidad y los enlaces relativos.
- Reescrito por completo `docs/protocol.md`: acceso, contraseña y QR, todos los
  endpoint, WebSocket, asistente, compilación del APK, códigos de error y
  ejemplos.
- Actualizados `docs/architecture.md`, `docs/service.md` (glosario, soporte),
  `docs/profile-schema.md`, README, `android/README.md`,
  `packaging/windows/README.md`; la documentación se incluye en el instalador.

### Seguridad

- Comprobación SHA-256 de los archivos críticos de la interfaz al arrancar y en
  el navegador.
- CSP `default-src 'self'`, prohibición de recursos externos, lista de permitidos
  de navegación en Android WebView.
