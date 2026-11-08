# 💰 Service Cost Comparison: Connected vs Local

This document answers the question "how much will this cost" for the three
areas of the project:

1. **LLM/AI area** — models for the agent (DeepSeek Harness + `dsh-shift-router`)
   that route requests between a cheap (Fast) and a smart (Smart) chain.
2. **Simulator integration area** — SimConnect / WASM bridges, navigation,
   aircraft.
3. **Gateway infrastructure** — server, runtimes, tools.

All prices are **real, as of the end of October 2026**. Connected (cloud)
services are billed by subscription/volume; local alternatives are free but
require self-installation and maintenance. Before paying, check the provider's
current pricing page.

---

## 1. LLM / AI agent (for dsh-shift-router)

The router splits the load into **Fast** (cheap, quick) and **Smart**
(more expensive, complex tasks). DeepSeek API prices are per **1 million
tokens**.

| Service / model | Role in shift-router | Input price (cache miss) | Input price (cache hit) | Output price | Local installation |
| --- | --- | --- | --- | --- | --- |
| **DeepSeek `deepseek-flash`** (V4.1-Flash) | Fast chain | $0.15 off-peak / $0.30 peak | $0.003 off-peak / $0.006 peak | $0.60 off-peak / $1.20 peak | ❌ cloud |
| **DeepSeek `deepseek-v4-pro`** (V4-Pro) | Smart chain | $0.66 off-peak / $1.32 peak | $0.022 off-peak / $0.044 peak | $1.98 off-peak / $3.96 peak | ❌ cloud |
| DeepSeek **Search** (web search) | agent tools | $0.75 per 1,000 requests | — | — | ❌ cloud |
| DeepSeek **Fetch** (URL reading) | agent tools | $0.75 per 1,000 requests | — | — | ❌ cloud |
| **Ollama** + open-weights (Llama / Qwen / DeepSeek-R1-Distill) | local Fast/Smart | free | free | free | ✅ **yes, local** |
| **vLLM / llama.cpp** (self-hosted inference) | local Fast/Smart | free | free | free | ✅ **yes, local** |

> **Notes.**
> - Off-peak = half the peak rate. Peak: Mon–Fri 01:00–04:00 and 06:00–10:00 UTC.
>   All other times (including weekends) are off-peak.
> - According to DeepSeek, Search/Fetch calls through DeepSeek Harness were
>   free until 00:00 on November 1, 2026 (Beijing time); from that date —
>   $0.75/1,000.
> - Local models are free in money terms, but they "cost" a GPU, electricity,
>   and setup time. For air-gapped deployment this is the only way.
> - DeepSeek pricing source: [api-docs.deepseek.com/quick_start/pricing](https://api-docs.deepseek.com/quick_start/pricing)

---

## 2. Simulator bridge (SimConnect / WASM / variables)

| Service / tool | Type | Price | Local installation | Comment |
| --- | --- | --- | --- | --- |
| **SimConnect SDK** (MSFS 2020/2024) | native API | free (included in the SDK) | ✅ yes | Standard SimVars; enough for the MVP |
| **MobiFlight WASM Module** | LVAR/HVAR WASM bridge | free (open-source, donations) | ✅ yes | Extends access to custom variables of complex aircraft |
| **SimBridge** (FlyByWire) | WASM gateway | free (open-source) | ✅ yes | Works with FBW/custom aircraft |
| **FSUIPC7** | universal bridge | ~€30 one-time (registration) | ✅ yes | Paid, but self-contained and without a subscription |

> **Area summary:** the MVP is built entirely on a free stack
> (SimConnect + MobiFlight/SimBridge). FSUIPC7 is an optional paid bridge.

---

## 3. Navigation, charts, flight planning

| Service | Type | Price | Local installation | Comment |
| --- | --- | --- | --- | --- |
| **Navigraph Unlimited** | subscription | **€10.86/month** or **€97.97/year** | partially (Hub locally, data by subscription) | Jeppesen charts, AIRAC cycles, Moving Map |
| **SimBrief** | cloud planner | free | ❌ (cloud) | Flight plans, fuel, briefing |
| **Little Navmap** | desktop tool | free (open-source) | ✅ yes | Planning + moving map, without Jeppesen charts |
| **ChartFox** | chart catalog | free | partially | Official charts by country, without a moving map |
| **Built-in EFB MSFS 2024** | part of the simulator | included in the game price | ✅ yes (locally) | Charts right in the game, limited coverage |

> **Source:** [aerosimnews.com — Navigraph 2026 (prices, alternatives)](https://www.aerosimnews.com/de/navigraph-vergleich-2026-preise-alternativen/)

---

## 4. The simulator itself and study-level aircraft

| Product | Type | Price (approximate) | Local installation |
| --- | --- | --- | --- |
| **MSFS 2020 / 2024 — Standard** | game | ~$69.99 | ✅ yes |
| **MSFS — Deluxe / Premium Deluxe** | game | ~$89.99 / ~$119.99 | ✅ yes |
| **FlyByWire A32NX** | aircraft | free (open-source) | ✅ yes |
| **PMDG 737 / Fenix A320 / iniBuilds** | aircraft | ~$50–$70 per aircraft | ✅ yes (through the store/installer) |

> Aircraft prices depend on the edition and sales; check the store.

---

## 5. Gateway and client infrastructure (our project)

| Component | Price | Local installation |
| --- | --- | --- |
| Python 3.13 (gateway, stdlib, no pip dependencies) | free | ✅ yes |
| Node.js 22 (client tests) | free | ✅ yes |
| Built-in HTTP + WebSocket server (stdlib) | free | ✅ yes |
| Web client (vanilla JS, no CDN) | free | ✅ yes |
| `dsh-shift-router` (npm, MIT) | free | ✅ yes |

---

## Summary table "cheap → expensive"

| Solution | Format | Annual cost (1 user) |
| --- | --- | --- |
| Our gateway + Python/Node + Mobiflight/SimBridge + Little Navmap | local | **€0** |
| + FSUIPC7 (one-time) | local | ~€30 (one-time) |
| + MSFS Standard | game | ~$69.99 (one-time) |
| + Navigraph Unlimited | subscription | €97.97/year |
| DeepSeek API (Fast+Smart through shift-router) | by volume | from a few $/month with active use |
| Fully local LLM (Ollama + open weights) | local | €0 (a GPU is required) |

---

## Conclusions for air-gapped deployment

- **Everything needed for the MVP is available locally and for free**: the
  gateway, SimConnect, MobiFlight/SimBridge, the web client, Little Navmap.
- **Paid elements are optional only**: Navigraph (IFR convenience), FSUIPC7
  (extended bridge), study-level aircraft, the game itself.
- **The LLM area in an isolated network requires a local model** (Ollama/vLLM):
  DeepSeek cloud APIs are unavailable without internet. `dsh-shift-router` then
  routes between two local models instead of cloud Fast/Smart.
