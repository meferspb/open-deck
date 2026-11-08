# 📱 Open Deck for MSFS — cliente Android

Aplicación Android nativa (Kotlin, sin bibliotecas de terceros) que convierte un
teléfono o una tableta en un panel de instrumentos de MSFS:

- **autodescubrimiento** del host de Windows mediante una baliza UDP (puerto
  8761) y entrada manual de IP;
- **renderizado del panel** — la WebView carga el cliente web desde el host, por
  lo que la versión Android recibe automáticamente todos los perfiles,
  instrumentos, el editor y las actualizaciones de la interfaz;
- **tres factores de forma** seleccionados por el tamaño de pantalla
  (`smallestScreenWidthDp`): phone / tablet-sm / tablet-lg;
- **comprobación de integridad** antes de mostrar el panel (condición de licencia
  sobre la protección del bloque de apoyo al autor);
- **inicio de sesión por contraseña**: si el gateway tiene una contraseña
  activada, la WebView muestra la página de inicio de sesión; la sesión se guarda
  en una cookie de la WebView y sobrevive al reinicio de la aplicación; los hosts
  con contraseña se marcan con un candado 🔒;
- **modo kiosco**: inmersivo a pantalla completa, la pantalla no se apaga, rotación
  sin recargar el panel;
- **bloque de apoyo al autor** en la pantalla de conexión (los datos llegan del
  host);
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

## Requisitos de compilación

| Componente | Versión |
| --- | --- |
| JDK | 17+ |
| Android SDK | platform 35, build-tools 35.x |
| Gradle | 8.9+ (el proyecto está compilado para 8.10.2) |
| Android Gradle Plugin | 8.7.3 |
| Kotlin | 2.0.21 |

`minSdk 26` (Android 8.0), `targetSdk 35`.

## Compilación

Verificado en este repositorio: **JDK 17.0.20.1 (Temurin), Gradle 8.10.2,
AGP 8.7.3, Kotlin 2.0.21, Android SDK platform 35 / build-tools 35.0.0**.
`assembleDebug` y `lintDebug` pasan: **0 errores**, 3 advertencias informativas
(cleartext en la red local, overdraw, reglas de backup).

```bash
cd android

# la ruta al SDK se puede definir mediante ANDROID_HOME o local.properties:
#   echo "sdk.dir=/path/to/android-sdk" > local.properties

# opción 1: Android Studio — abrir el directorio android/ y pulsar Run

# opción 2: línea de comandos (Gradle 8.9+)
gradle wrapper --gradle-version 8.10.2   # una vez, crea gradlew
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk

# instalación en el dispositivo
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Tras la compilación, el APK de depuración aparece en
`android/dist/OpenDeck-Android-<versión>.apk` (firma de depuración — para
instalarlo en el propio dispositivo; para publicarlo se necesita una clave de
release).

> **Sobre la compilación air-gapped.** La aplicación no usa bibliotecas de
> terceros: solo Android SDK y Kotlin stdlib. Pero Gradle de todos modos descarga
> AGP y el plugin de Kotlin desde Maven. Si la máquina de compilación está
> aislada, traslada la caché de Gradle (`~/.gradle/caches`) desde una máquina
> donde la compilación ya se haya ejecutado, o compila el APK de antemano y
> distribúyelo como archivo. En la distribución del gateway (`android/` + el APK
> compilado) la compilación está disponible desde la página `/android.html`.

## Cómo funciona

```
MainActivity
├── DiscoveryClient  → UDP 8761, baliza JSON del host (nombre, IP, puerto, perfiles, auth)
├── HostStore        → SharedPreferences: último host
├── HostApi          → GET /api/health, /api/integrity, /api/donation
└── WebView          → http://<host>:<port>/?device=<preset>&frame=0
```

Orden de arranque:

1. La aplicación levanta un receptor UDP y muestra los hosts encontrados (en los
   hosts con contraseña — un candado).
2. El usuario elige un host o introduce la dirección manualmente si la red corta
   el broadcast.
3. Antes de mostrar el panel se ejecuta `GET /api/integrity`: si el host informa
   de una violación de integridad de la interfaz — el panel se bloquea con un
   mensaje.
4. El panel se abre en la WebView. Si el gateway requiere contraseña, la WebView
   muestra `/login.html`; tras iniciar sesión, la cookie se guarda y el panel se
   abre sin volver a introducirla.
5. El botón «Asistente» en la cabecera del panel abre `/assist.html` (aterrizaje
   y rodaje); también funciona en el teléfono.

## Estructura

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
        │   ├── MainActivity.kt     # pantallas, WebView, bloqueo de integridad,
        │   │                       # cookie de sesión, apertura del asistente
        │   ├── DiscoveryClient.kt  # receptor UDP de balizas (generaciones de hilos)
        │   ├── HostApi.kt          # comprobaciones HTTP y datos del donativo
        │   └── HostStore.kt        # último host en SharedPreferences
        └── res/
            ├── layout/activity_main.xml, view_setup.xml
            ├── values/strings.xml, colors.xml, themes.xml
            ├── drawable/…          # open_deck_logo.png, tarjetas, placa de donativo
            └── xml/network_security_config.xml
```

## Depuración

- **No se encuentra el host**: el teléfono y el PC deben estar en la misma
  subred, el firewall del PC debe permitir redes privadas y el puerto 8760; la
  baliza va por UDP 8761. Introduce la dirección manualmente
  (`192.168.1.10:8760`).
- **«Se requiere inicio de sesión»**: hay una contraseña activada en el gateway —
  introdúcela en la página de inicio de sesión; el código QR del panel inicia
  sesión sin contraseña (10 minutos).
- **La comprobación de integridad no pasa**: los archivos de interfaz del host
  han cambiado — reconstruye el manifiesto
  (`python -m msfs_gateway.integrity --write`).
- **Registros**: `adb logcat -s OpenDeckDiscovery OpenDeck`, los registros de la
  WebView — a través de Chrome DevTools (`chrome://inspect`).
- **Instalación del APK**: permite la instalación desde orígenes desconocidos;
  para una compilación de release se necesita una firma propia.

## Seguridad

- HTTP sin TLS: la red es local y de confianza, `usesCleartextTraffic` está
  activado a conciencia; la contraseña protege el inicio de sesión, pero no cifra
  el tráfico.
- WebView: lista de permitidos de navegación, `file:`/`content:` prohibidos,
  contenido mixto prohibido, cookie — solo la sesión `HttpOnly` del gateway.
- Los datos del donativo llegan del host; el bloque no se puede eliminar
  (condición de licencia).

## Limitaciones y siguientes pasos

- El panel lo renderiza el cliente web del host: esto da un 100 % de paridad de
  funciones, pero requiere WebView (presente en cualquier Android 8+).
- El renderizado nativo completo de instrumentos con Compose es un motor aparte;
  el protocolo (`/api/profiles`, `/ws`) ya está listo para él.
- No hay foreground-service: tras un largo periodo en segundo plano, Android
  puede suspender la WebView — para el kiosco, mantén la aplicación en pantalla.
