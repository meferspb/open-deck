# Participar en el desarrollo

¡Gracias por querer ayudar! El proyecto es pequeño y deliberadamente simple:
Python sin dependencias, vanilla JS sin empaquetador, Android con SDK/Kotlin
puro.

## Inicio rápido para desarrolladores

```powershell
# 1. Clonar el repositorio
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# 2. Arrancar el gateway en modo demostración (no se necesita MSFS)
python -m msfs_gateway --sim mock

# 3. Abrir http://127.0.0.1:8760/
```

Requisitos: **Python 3.11+**. Para las pruebas del cliente — **Node.js 20+**.
Para compilar el APK de Android — **JDK 17**, **Android SDK** y **Gradle 8.x**.

## Comprobaciones antes de un PR

```powershell
pwsh -File scripts/check.ps1
```

El script ejecuta:

- `ruff check` y `ruff format --check` para Python;
- `python -m unittest discover -s tests` (250 pruebas);
- `node --test "tests/web/*.test.mjs"` (29 pruebas), si Node.js está instalado.

Instalar las herramientas del linter: `python -m pip install ruff`.

## Estilo de código

- **Python**: PEP 8, formato `ruff format`, longitud de línea 100. Solo la
  biblioteca estándar — no añadimos nuevas dependencias.
- **JS**: módulos ES, sin frameworks ni CDN externos. Comprobación de sintaxis —
  `node --check`, pruebas — `node --test`.
- **Kotlin**: solo Android SDK y Kotlin stdlib, sin AndroidX ni bibliotecas de
  terceros.
- Los comentarios y la documentación — en español; los nombres en el código — en
  inglés.
- Todas las cadenas de usuario deben funcionar **sin conexión**: ni fuentes,
  imágenes ni API externas.

## Qué se puede mejorar

Véanse [`README_ES.md`](../../README_ES.md#hoja-de-ruta) y
[`architecture.md`](architecture.md). Buenas direcciones:

- nuevos perfiles de aeronaves (`profiles/*.json`) — bienvenidos;
- nuevos tipos de instrumento (`web/js/widgets/`, registro `registry.js`) y su
  registro en `msfs_gateway/profiles.py` (`WIDGET_TYPES`,
  `REQUIRED_BINDINGS`);
- pruebas: lógica pura (geometría de instrumentos, perfiles, protocolo) — en
  primer lugar;
- documentación: las discrepancias entre el código y `docs/` se consideran un
  bug.

## Perfiles de aeronaves

1. Copia un perfil existente de `profiles/` y cambia `id`, `name`, `sim.match`.
2. Comprueba la validación:
   `python -c "from msfs_gateway.profiles import ProfileStore; ..."` — o
   simplemente arranca el gateway: los perfiles rotos se omiten con una
   advertencia.
3. Toma los enlaces de `GET /api/telemetry/variables` (el editor los muestra en
   una lista).
4. Adjunta en el PR una descripción del addon con el que lo probaste.

## Commits y PR

- Commits atómicos, mensaje en imperativo: `add A320 profile`, `fix QR mask`.
- En el PR — qué se ha cambiado, por qué y cómo se ha comprobado
  (pruebas/capturas).
- Para cambios de interfaz, adjunta una captura en `docs/screenshots/`.

## Licencia de la contribución

Al enviar un PR, aceptas que tu contribución se distribuye bajo la licencia del
proyecto ([LICENSE](../../LICENSE)). No elimines ni sustituyas el bloque de apoyo
al autor ni la comprobación de integridad — es una condición de la licencia.
