# Instalador para Windows

Un único archivo `OpenDeck-Setup-<versión>.exe`: doble clic → «Siguiente» →
listo. No se necesitan derechos de administrador, ni Python, ni internet.

## Qué ocurre durante la instalación

| | |
|---|---|
| Directorio | `%LOCALAPPDATA%\OpenDeck` (en el perfil del usuario, sin UAC) |
| Contenido | `OpenDeck.exe` — el gateway con Python 3.13 embebido y la biblioteca estándar |
| | `web/` — cliente web (panel y editor), `profiles/` — perfiles de aeronaves |
| | `config/donation.json` — datos del autor, `integrity/` — manifiesto de integridad |
| | `android/` — fuentes de Android y, tras la compilación, el APK listo (`android/dist/OpenDeck-Android-<versión>.apk`), `config/android-build.json` — ajustes de compilación del APK |
| | `docs/` — documentación completa (servicio, protocolo, variables, instrumentos, esquema de perfil) |
| Accesos directos | escritorio, menú Inicio (inicio, panel en el navegador, compilación del APK de Android, «Establecer contraseña», desinstalación) |
| Desinstalación | «Programas y características» o el acceso directo «Desinstalar» |

Los datos están junto al `.exe`, por lo que los perfiles y los datos se pueden
editar sin reinstalar (tras editar archivos protegidos hay que reconstruir el
manifiesto; véase el [README de la raíz](../../README_ES.md)).

## Compilación (en la máquina del desarrollador, internet solo hace falta una vez)

Requisitos:

- Python 3.11+ y PyInstaller: `python -m pip install pyinstaller`
- NSIS 3.x: `makensis.exe` en `PATH`, o `NSIS_HOME`, o `-NsisPath`

```powershell
# desde la raíz del repositorio
pwsh -File scripts/build-installer.ps1 -Version 0.1.0 -NsisPath "C:\Program Files (x86)\NSIS"
```

El script paso a paso: reconstruye el manifiesto de integridad → ejecuta las
pruebas → compila `build/pyinstaller/dist/OpenDeck` (PyInstaller, onedir) →
coloca junto a él `web/`, `profiles/`, `config/`, `integrity/` → comprueba que el
`.exe` arranca (`--help`) → compila el instalador en
`dist/OpenDeck-Setup-<versión>.exe`.

Opciones: `-SkipTests`, `-NsisPath <carpeta>`, `-Version 0.2.0`.

El script también comprueba que el instalador se haya compilado e imprime la ruta
final y el tamaño. La lista completa de pasos está al principio del archivo
`scripts/build-installer.ps1`.

Inicio de sesión por contraseña: el acceso directo «Establecer contraseña»
ejecuta `OpenDeck.exe --set-password` y solicita la contraseña en la consola; el
hash se guarda en `config/auth.json` junto al `.exe`. Eliminar el archivo vuelve
a permitir el acceso sin inicio de sesión.

## Antes de publicar

1. Comprobar `config/donation.json`: autor Viktor Krasnikov, enlace Donat —
   `https://taps.uz/open_deck_fs`.
2. Reconstruir el manifiesto: `python -m msfs_gateway.integrity --write` (el
   script de compilación lo hace por sí mismo, pero no está de más comprobarlo).
3. Probar el instalador en una máquina limpia: instalación sin administrador,
   arranque, acceso al panel desde un teléfono en la misma red, desinstalación.

## Instalación silenciosa / despliegue

```bat
OpenDeck-Setup-0.1.0.exe /S /D=C:\Tools\OpenDeck
Uninstall.exe /S
```

`/D=` debe ir al final y sin comillas (limitación de NSIS).

## Limitaciones

- El instalador no está firmado: SmartScreen puede advertir «editor desconocido»
  — «Más información» → «Ejecutar de todos modos». Para una publicación se
  necesita un certificado de código (EV/OV).
- No se añade la regla de firewall (se necesitan derechos de administrador). En
  el primer arranque, Windows preguntará por el acceso a la red — permite el
  acceso para redes privadas; de lo contrario, los clientes no podrán conectarse.
- Instalación por usuario: la aplicación solo es visible para el usuario actual.
- El registro y los accesos directos se crean en `HKCU` — en máquinas con
  políticas estrictas (AppLocker, prohibición de escritura en el perfil) la
  instalación puede bloquearse; en ese caso, usa la variante portátil: descomprime
  el directorio `build/pyinstaller/dist/OpenDeck` y ejecuta el `.exe` desde allí.
