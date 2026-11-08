# 💰 Comparación de costes de servicios: conectados frente a locales

Este documento responde a la pregunta «cuánto costará esto» para las tres áreas
del proyecto:

1. **Área LLM/IA** — modelos para el agente (DeepSeek Harness + `dsh-shift-router`)
   que enrutan las peticiones entre una cadena barata (Fast) y una inteligente
   (Smart).
2. **Área de integración con el simulador** — puentes SimConnect / WASM,
   navegación, aeronaves.
3. **Infraestructura del gateway** — servidor, entornos de ejecución,
   herramientas.

Todos los precios son **reales, a finales de octubre de 2026**. Los servicios
conectados (en la nube) se facturan por suscripción/volumen; las alternativas
locales son gratuitas pero requieren instalación y mantenimiento propios. Antes
de pagar, consulta la página de precios actual del proveedor.

---

## 1. Agente LLM / IA (para dsh-shift-router)

El router divide la carga en **Fast** (barata, rápida) y **Smart** (tareas más
costosas y complejas). Los precios de la API de DeepSeek son por **1 millón de
tokens**.

| Servicio / modelo | Papel en shift-router | Precio de entrada (fallo de caché) | Precio de entrada (acierto de caché) | Precio de salida | Instalación local |
| --- | --- | --- | --- | --- | --- |
| **DeepSeek `deepseek-flash`** (V4.1-Flash) | Cadena Fast | $0.15 fuera de hora punta / $0.30 en hora punta | $0.003 fuera de hora punta / $0.006 en hora punta | $0.60 fuera de hora punta / $1.20 en hora punta | ❌ nube |
| **DeepSeek `deepseek-v4-pro`** (V4-Pro) | Cadena Smart | $0.66 fuera de hora punta / $1.32 en hora punta | $0.022 fuera de hora punta / $0.044 en hora punta | $1.98 fuera de hora punta / $3.96 en hora punta | ❌ nube |
| DeepSeek **Search** (búsqueda web) | herramientas del agente | $0.75 por 1.000 peticiones | — | — | ❌ nube |
| DeepSeek **Fetch** (lectura de URL) | herramientas del agente | $0.75 por 1.000 peticiones | — | — | ❌ nube |
| **Ollama** + pesos abiertos (Llama / Qwen / DeepSeek-R1-Distill) | Fast/Smart local | gratis | gratis | gratis | ✅ **sí, local** |
| **vLLM / llama.cpp** (inferencia autoalojada) | Fast/Smart local | gratis | gratis | gratis | ✅ **sí, local** |

> **Notas.**
> - Fuera de hora punta = la mitad de la tarifa punta. Hora punta: lunes a
>   viernes de 01:00 a 04:00 y de 06:00 a 10:00 UTC. Todas las demás horas
>   (incluidos los fines de semana) son fuera de hora punta.
> - Según DeepSeek, las llamadas a Search/Fetch a través de DeepSeek Harness
>   fueron gratuitas hasta las 00:00 del 1 de noviembre de 2026 (hora de
>   Pekín); a partir de esa fecha — $0.75/1.000.
> - Los modelos locales son gratuitos en términos monetarios, pero «cuestan»
>   una GPU, electricidad y tiempo de configuración. Para un despliegue
>   air-gapped esta es la única vía.
> - Fuente de precios de DeepSeek: [api-docs.deepseek.com/quick_start/pricing](https://api-docs.deepseek.com/quick_start/pricing)

---

## 2. Puente del simulador (SimConnect / WASM / variables)

| Servicio / herramienta | Tipo | Precio | Instalación local | Comentario |
| --- | --- | --- | --- | --- |
| **SimConnect SDK** (MSFS 2020/2024) | API nativa | gratis (incluida en el SDK) | ✅ sí | SimVar estándar; suficiente para el MVP |
| **MobiFlight WASM Module** | puente WASM para LVAR/HVAR | gratis (código abierto, donativos) | ✅ sí | Amplía el acceso a variables personalizadas de aeronaves complejas |
| **SimBridge** (FlyByWire) | gateway WASM | gratis (código abierto) | ✅ sí | Funciona con aeronaves FBW/personalizadas |
| **FSUIPC7** | puente universal | ~€30 pago único (registro) | ✅ sí | De pago, pero autocontenido y sin suscripción |

> **Resumen del área:** el MVP se construye íntegramente sobre un stack gratuito
> (SimConnect + MobiFlight/SimBridge). FSUIPC7 es un puente opcional de pago.

---

## 3. Navegación, cartas, planificación de vuelo

| Servicio | Tipo | Precio | Instalación local | Comentario |
| --- | --- | --- | --- | --- |
| **Navigraph Unlimited** | suscripción | **€10.86/mes** o **€97.97/año** | parcialmente (Hub local, datos por suscripción) | Cartas Jeppesen, ciclos AIRAC, Moving Map |
| **SimBrief** | planificador en la nube | gratis | ❌ (nube) | Planes de vuelo, combustible, briefing |
| **Little Navmap** | herramienta de escritorio | gratis (código abierto) | ✅ sí | Planificación + mapa móvil, sin cartas Jeppesen |
| **ChartFox** | catálogo de cartas | gratis | parcialmente | Cartas oficiales por país, sin mapa móvil |
| **EFB integrado de MSFS 2024** | parte del simulador | incluido en el precio del juego | ✅ sí (localmente) | Cartas dentro del juego, cobertura limitada |

> **Fuente:** [aerosimnews.com — Navigraph 2026 (precios, alternativas)](https://www.aerosimnews.com/de/navigraph-vergleich-2026-preise-alternativen/)

---

## 4. El propio simulador y aeronaves de nivel de estudio

| Producto | Tipo | Precio (aproximado) | Instalación local |
| --- | --- | --- | --- |
| **MSFS 2020 / 2024 — Standard** | juego | ~$69.99 | ✅ sí |
| **MSFS — Deluxe / Premium Deluxe** | juego | ~$89.99 / ~$119.99 | ✅ sí |
| **FlyByWire A32NX** | aeronave | gratis (código abierto) | ✅ sí |
| **PMDG 737 / Fenix A320 / iniBuilds** | aeronave | ~$50–$70 por aeronave | ✅ sí (a través de la tienda/instalador) |

> Los precios de las aeronaves dependen de la edición y de las rebajas; consulta
> la tienda.

---

## 5. Infraestructura del gateway y de los clientes (nuestro proyecto)

| Componente | Precio | Instalación local |
| --- | --- | --- |
| Python 3.13 (gateway, stdlib, sin dependencias de pip) | gratis | ✅ sí |
| Node.js 22 (pruebas del cliente) | gratis | ✅ sí |
| Servidor HTTP + WebSocket integrado (stdlib) | gratis | ✅ sí |
| Cliente web (JS vanilla, sin CDN) | gratis | ✅ sí |
| `dsh-shift-router` (npm, MIT) | gratis | ✅ sí |

---

## Tabla resumen «de barato a caro»

| Solución | Formato | Coste anual (1 usuario) |
| --- | --- | --- |
| Nuestro gateway + Python/Node + Mobiflight/SimBridge + Little Navmap | local | **€0** |
| + FSUIPC7 (pago único) | local | ~€30 (pago único) |
| + MSFS Standard | juego | ~$69.99 (pago único) |
| + Navigraph Unlimited | suscripción | €97.97/año |
| API de DeepSeek (Fast+Smart a través de shift-router) | por volumen | desde unos pocos $/mes con uso activo |
| LLM totalmente local (Ollama + pesos abiertos) | local | €0 (se requiere una GPU) |

---

## Conclusiones para un despliegue air-gapped

- **Todo lo necesario para el MVP está disponible localmente y gratis**: el
  gateway, SimConnect, MobiFlight/SimBridge, el cliente web, Little Navmap.
- **Los elementos de pago son solo opcionales**: Navigraph (comodidad IFR),
  FSUIPC7 (puente ampliado), aeronaves de nivel de estudio, el propio juego.
- **El área LLM en una red aislada requiere un modelo local** (Ollama/vLLM): las
  API en la nube de DeepSeek no están disponibles sin internet. `dsh-shift-router`
  enruta entonces entre dos modelos locales en lugar de Fast/Smart en la nube.
