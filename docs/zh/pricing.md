# 💰 服务成本对比：连接式与本地

本文档回答项目三个领域的“这要花多少钱”问题：

1. **LLM/AI 领域**——用于 agent（DeepSeek Harness + `dsh-shift-router`）的模型，在廉价（Fast）和智能（Smart）链之间路由请求。
2. **模拟器集成领域**——SimConnect / WASM 桥、导航、飞机。
3. **网关基础设施**——服务器、运行时、工具。

所有价格均为**真实价格，截至 2026 年 10 月底**。连接式（云）服务按订阅/用量计费；本地替代方案免费，但需要自行安装和维护。付费前请查看提供商的当前定价页面。

---

## 1. LLM / AI agent（用于 dsh-shift-router）

路由器将负载分为 **Fast**（廉价、快速）和 **Smart**（更昂贵、复杂任务）。DeepSeek API 价格按**每 100 万 token** 计算。

| 服务 / 模型 | 在 shift-router 中的角色 | 输入价格（缓存未命中） | 输入价格（缓存命中） | 输出价格 | 本地安装 |
| --- | --- | --- | --- | --- | --- |
| **DeepSeek `deepseek-flash`**（V4.1-Flash） | Fast 链 | 非高峰 $0.15 / 高峰 $0.30 | 非高峰 $0.003 / 高峰 $0.006 | 非高峰 $0.60 / 高峰 $1.20 | ❌ 云 |
| **DeepSeek `deepseek-v4-pro`**（V4-Pro） | Smart 链 | 非高峰 $0.66 / 高峰 $1.32 | 非高峰 $0.022 / 高峰 $0.044 | 非高峰 $1.98 / 高峰 $3.96 | ❌ 云 |
| DeepSeek **Search**（Web 搜索） | agent 工具 | 每 1,000 次请求 $0.75 | — | — | ❌ 云 |
| DeepSeek **Fetch**（URL 读取） | agent 工具 | 每 1,000 次请求 $0.75 | — | — | ❌ 云 |
| **Ollama** + 开放权重（Llama / Qwen / DeepSeek-R1-Distill） | 本地 Fast/Smart | 免费 | 免费 | 免费 | ✅ **是，本地** |
| **vLLM / llama.cpp**（自托管推理） | 本地 Fast/Smart | 免费 | 免费 | 免费 | ✅ **是，本地** |

> **备注。**
> - 非高峰 = 高峰费率的一半。高峰：周一至周五 01:00–04:00 和 06:00–10:00 UTC。其他所有时间（包括周末）均为非高峰。
> - 根据 DeepSeek 的说法，通过 DeepSeek Harness 进行的 Search/Fetch 调用在 2026 年 11 月 1 日 00:00（北京时间）之前免费；从该日期起——每 1,000 次 $0.75。
> - 本地模型在金钱方面免费，但它们“消耗”GPU、电力和设置时间。对于 air-gapped 部署，这是唯一的方式。
> - DeepSeek 定价来源：[api-docs.deepseek.com/quick_start/pricing](https://api-docs.deepseek.com/quick_start/pricing)

---

## 2. 模拟器桥（SimConnect / WASM / 变量）

| 服务 / 工具 | 类型 | 价格 | 本地安装 | 备注 |
| --- | --- | --- | --- | --- |
| **SimConnect SDK**（MSFS 2020/2024） | 原生 API | 免费（包含在 SDK 中） | ✅ 是 | 标准 SimVar；足以满足 MVP |
| **MobiFlight WASM Module** | LVAR/HVAR WASM 桥 | 免费（开源，接受捐赠） | ✅ 是 | 扩展对复杂飞机自定义变量的访问 |
| **SimBridge**（FlyByWire） | WASM 网关 | 免费（开源） | ✅ 是 | 适用于 FBW/自定义飞机 |
| **FSUIPC7** | 通用桥 | 一次性约 €30（注册） | ✅ 是 | 付费，但自包含且无需订阅 |

> **领域总结：** MVP 完全建立在免费技术栈（SimConnect + MobiFlight/SimBridge）之上。FSUIPC7 是可选的付费桥。

---

## 3. 导航、图表、飞行计划

| 服务 | 类型 | 价格 | 本地安装 | 备注 |
| --- | --- | --- | --- | --- |
| **Navigraph Unlimited** | 订阅 | **€10.86/月** 或 **€97.97/年** | 部分（Hub 本地，数据按订阅） | Jeppesen 图表、AIRAC 周期、移动地图 |
| **SimBrief** | 云端计划器 | 免费 | ❌（云） | 飞行计划、燃油、简报 |
| **Little Navmap** | 桌面工具 | 免费（开源） | ✅ 是 | 计划 + 移动地图，无 Jeppesen 图表 |
| **ChartFox** | 图表目录 | 免费 | 部分 | 按国家提供的官方图表，无移动地图 |
| **内置 EFB MSFS 2024** | 模拟器的一部分 | 包含在游戏价格中 | ✅ 是（本地） | 游戏内图表，覆盖范围有限 |

> **来源：** [aerosimnews.com — Navigraph 2026（价格、替代方案）](https://www.aerosimnews.com/de/navigraph-vergleich-2026-preise-alternativen/)

---

## 4. 模拟器本身与学习级飞机

| 产品 | 类型 | 价格（近似） | 本地安装 |
| --- | --- | --- | --- |
| **MSFS 2020 / 2024 — 标准版** | 游戏 | 约 $69.99 | ✅ 是 |
| **MSFS — 豪华版 / 高级豪华版** | 游戏 | 约 $89.99 / 约 $119.99 | ✅ 是 |
| **FlyByWire A32NX** | 飞机 | 免费（开源） | ✅ 是 |
| **PMDG 737 / Fenix A320 / iniBuilds** | 飞机 | 每架约 $50–$70 | ✅ 是（通过商店/安装程序） |

> 飞机价格取决于版本和促销；请查看商店。

---

## 5. 网关和客户端基础设施（我们的项目）

| 组件 | 价格 | 本地安装 |
| --- | --- | --- |
| Python 3.13（网关、标准库、无 pip 依赖） | 免费 | ✅ 是 |
| Node.js 22（客户端测试） | 免费 | ✅ 是 |
| 内置 HTTP + WebSocket 服务器（标准库） | 免费 | ✅ 是 |
| Web 客户端（原生 JS，无 CDN） | 免费 | ✅ 是 |
| `dsh-shift-router`（npm，MIT） | 免费 | ✅ 是 |

---

## 总结表“从便宜到昂贵”

| 方案 | 形式 | 年度成本（1 位用户） |
| --- | --- | --- |
| 我们的网关 + Python/Node + Mobiflight/SimBridge + Little Navmap | 本地 | **€0** |
| + FSUIPC7（一次性） | 本地 | 约 €30（一次性） |
| + MSFS 标准版 | 游戏 | 约 $69.99（一次性） |
| + Navigraph Unlimited | 订阅 | €97.97/年 |
| DeepSeek API（通过 shift-router 使用 Fast+Smart） | 按用量 | 积极使用时每月几美元起 |
| 完全本地 LLM（Ollama + 开放权重） | 本地 | €0（需要 GPU） |

---

## air-gapped 部署的结论

- **MVP 所需的一切都可以在本地免费获得**：网关、SimConnect、MobiFlight/SimBridge、Web 客户端、Little Navmap。
- **付费元素只是可选项**：Navigraph（IFR 便利）、FSUIPC7（扩展桥）、学习级飞机、游戏本身。
- **隔离网络中的 LLM 领域需要本地模型**（Ollama/vLLM）：没有互联网时无法使用 DeepSeek 云 API。此时 `dsh-shift-router` 会在两个本地模型之间路由，而不是云端的 Fast/Smart。
