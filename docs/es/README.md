# 📚 Documentación de Open Deck for MSFS

**Languages:** [English](../README.md) · [Русский](../ru/README.md) · [Deutsch](../de/README.md) · [中文](../zh/README.md) · [Español](README.md) · [日本語](../ja/README.md)


<img src="../pic1.jpg" alt="Open Deck for MSFS" width="180" />

Aquí se reúnen todos los documentos del proyecto. Empieza por el README de la
raíz del repositorio: ofrece la visión general y el inicio rápido; este índice te
ayuda a encontrar los detalles.

## Por dónde empezar

| Si eres… | Lee en orden |
| --- | --- |
| un piloto que configura el panel «para sí mismo» | [README](../../README_ES.md) → [service.md](service.md) |
| alguien que quiere entender cómo funciona | [architecture.md](architecture.md) → [protocol.md](protocol.md) |
| alguien que escribe un cliente o una integración | [protocol.md](protocol.md) → [telemetry.md](telemetry.md) |
| alguien que cambia el código | [development.md](development.md) → [architecture.md](architecture.md) |
| alguien que crea un perfil de aeronave | [profile-schema.md](profile-schema.md) → [widgets.md](widgets.md) |
| alguien que compila el instalador/APK | [packaging.md](packaging.md) → [android.md](android.md) |
| alguien que revisa la seguridad | [security.md](security.md) |

## Documentos

| Documento | Qué cubre | Público |
| --- | --- | --- |
| [service.md](service.md) | Descripción completa del servicio: propósito, modelo operativo, telemetría, perfiles, clientes, red, autenticación, asistente, API, instalación, diagnóstico, seguridad, licencia | todos |
| [architecture.md](architecture.md) | Diseño interno: módulos, flujos de datos, puente WASM, decisiones clave y límites del MVP | desarrolladores |
| [protocol.md](protocol.md) | HTTP REST, WebSocket, inicio de sesión por contraseña y QR, autodescubrimiento, códigos de error y ejemplos | integradores |
| [telemetry.md](telemetry.md) | Catálogo de todas las variables: tipos, unidades, SimVar, eventos, `custom.*` — generado desde el código | desarrolladores de clientes y perfiles |
| [widgets.md](widgets.md) | Catálogo de instrumentos: enlaces obligatorios, `command`, opciones, ejemplos JSON — generado desde el código | autores de perfiles |
| [profile-schema.md](profile-schema.md) | Esquema JSON del perfil: campos, diseños, validación, compatibilidad, ejemplo completo | autores de perfiles |
| [development.md](development.md) | Cómo cambiar el código: mapa de módulos, añadir una variable/instrumento/perfil/proveedor/página, pruebas, publicación | colaboradores |
| [pricing.md](pricing.md) | Comparación de «servicios conectados frente a equivalentes locales» para un escenario air-gapped | quienes eligen el stack |
| [android.md](android.md) | Cliente Android: compilación, arquitectura, inicio de sesión, depuración | desarrolladores de Android |
| [packaging.md](packaging.md) | Instalador: contenido, compilación, accesos directos, desinstalación, opciones silenciosas | ingenieros de publicación |
| [contributing.md](contributing.md) | Cómo participar: estilo, pruebas, perfiles, PR | colaboradores |
| [security.md](security.md) | Modelo de amenazas, qué está protegido, cómo informar de una vulnerabilidad | todos |
| [changelog.md](changelog.md) | Historial de versiones | todos |

## Capturas de pantalla

`../screenshots/` — el panel en un teléfono y una tableta, six-pack, editor,
página de inicio de sesión y asistente. Se usan en el README y en la descripción
del servicio.

## Mantener la documentación actualizada

Dos documentos se **generan desde el código** y son comprobados por una prueba:

```powershell
python -m msfs_gateway.docsgen --check   # telemetry.md y widgets.md
python -m msfs_gateway.docsgen --write   # actualizar tras cambiar los registros
```

Si has modificado `telemetry.py`, `profiles.py` o los instrumentos web,
actualiza la documentación y ejecuta `pwsh -File scripts/check.ps1`.

## Cómo escribir documentación

- Escribe en español, en párrafos breves, con ejemplos JSON/comandos.
- Los enlaces son relativos para que funcionen tanto en GitHub como en local.
- No dupliques el esquema: el perfil — en `profile-schema.md`, las variables —
  en `telemetry.md`, los instrumentos — en `widgets.md`, la red — en
  `protocol.md`.
- Si cambias el comportamiento, actualiza el README/la descripción del servicio
  y `CHANGELOG.md`.
