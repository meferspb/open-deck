# 🏗️ Open Deck for MSFS 架构

本文档介绍组件、数据流和关键设计决策。配置文件格式见 [profile-schema.md](profile-schema.md)，网络协议见 [protocol.md](protocol.md)。

---

## 1. 高层示意图

```
┌───────────────────────────── Windows Host (Core Gateway) ─────────────────────────────┐
│                                                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌────────────────────┐   │
│  │  SimProvider  │──▶│      Hub      │──▶│ WebSocket /ws │──▶│  Web client (JS)   │   │
│  │  (mock /      │   │  (broadcast,  │   │               │   │  Android client    │   │
│  │   SimConnect) │   │   commands)   │   ├───────────────┤   └────────────────────┘   │
│  └──────▲────────┘   └──────▲────────┘   │  HTTP /api    │                            │
│         │                   │            │  HTTP / (static)│                          │
│         │ read()            │ profiles   └───────┬───────┘                            │
│         │ apply_command()   │ list/get/save      │                                    │
│  ┌──────┴────────┐   ┌──────┴────────┐          │                                    │
│  │  telemetry.py │   │  profiles.py  │          │  REST + WebSocket on ONE port      │
│  │ (SimVar reg.) │   │  (validation) │          └────────────────────────────────────┘
│  └───────────────┘   └───────────────┘                                               │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ SimConnect API (native, ctypes) — or mock without MSFS
        │
┌───────┴────────┐
│  MSFS 2020/24  │
└────────────────┘
```

---

## 2. 组件与职责

### 2.1. `telemetry.py` — 规范变量注册表

关于量的唯一事实来源：键名、类型、单位、SimVar 绑定（`sim_var`/`sim_unit`）以及写入事件（`sim_event`）。配置文件只引用这些键，因此重命名 SimVar 只需修改一处。

```python
Variable("power.batteryMaster", "bool", "Master battery",
         sim_var="ELECTRICAL MASTER BATTERY", sim_unit="bool",
         sim_event="TOGGLE_MASTER_BATTERY")
```

### 2.2. `sim/` — 遥测源（提供程序）

通用的 `SimProvider` 接口：

| 方法 | 用途 |
| --- | --- |
| `connected` | 是否存在与模拟器的实时连接 |
| `start()` / `stop()` | 提供程序的后台线程 |
| `read()` | 值快照 `dict[key, value]` |
| `apply_command(key, value)` | 应用客户端命令 |
| `select_aircraft(profile_id)` | 切换飞机（仅 mock 支持） |

实现：

- **`MockSim`** — 程序化飞行：横滚/俯仰/航向/速度/高度沿平滑正弦曲线变化，燃油会被消耗。用于无 MSFS 的开发、演示和自动化测试。
- **`SimConnectSim`** — 通过 `ctypes` 使用原生 SimConnect。订阅一组数值数据项（`AddToDataDefinition` + `RequestDataOnSimObject`），单独订阅字符串 `TITLE`/`ATC MODEL`，在 `read()` 中缓存值，并以事件形式发送命令（`MapClientEventToSimEvent` + `TransmitClientEvent`）。包括命令在内的 SimConnect 调用都在调度线程上执行（`run_on_dispatch`），因为该 API 并非为多线程调用而设计。如果用户的 `SimConnect.cfg` 指向不存在的通道，则通过临时配置经 TCP `127.0.0.1:19999`（MSFS 2020/2024 端口）重试连接。与实时 MSFS 2020 的连接已经验证；实时数值交换、WASM 模块和飞行中的辅助是下一步验证内容。

`create_sim()` 工厂根据 `--sim` 设置选择提供程序：

- `mock` → 始终使用 mock；
- `simconnect` → 仅使用 SimConnect，出错时退出；
- `auto` → 使用 SimConnect，失败时回退到 mock（网关始终会启动）。

### 2.3. `hub.py` — 遥测总线

- 一个以 `--telemetry-hz` 频率运行的“ticker”线程收集 `sim.read()`，并将帧广播给所有 WebSocket 客户端；
- 每个客户端都有自己的队列（8 帧）和发送线程：慢速平板不会阻止向其他客户端投递，旧帧会被丢弃；
- **命令速率限制**（每个客户端 ≤30/s）——防止触摸卡住；
- `build_message()` 规范化值（四舍五入到 3 位小数，包含完整键集合），并添加 `seq`、`ts` 和 `sim` 元数据。

### 2.4. `profiles.py` + `legacy.py` — 飞机配置文件

- `validate_profile()` — 严格的结构检查（仪表类型、绑定、命令、矩形、仪表范围）；
- `ProfileStore` — 线程安全的原子保存（tmp + `fsync` + `os.replace`）；
- `legacy.adapt()` — 将规范中的“像素”v0 格式转换为内部格式（坐标以 0..1 比例表示），使旧面板可以按原样加载。

### 2.5. `http_api.py` + `websocket.py` — 网络

- `ThreadingHTTPServer` 提供 `web/` 静态文件和 REST API，并在同一端口上执行 WebSocket 升级——只需一条防火墙规则；
- `websocket.py` — 基于标准库的最小 RFC 6455 实现（文本、ping/pong、关闭）；
- `auth.py` — 可选密码登录：PBKDF2 哈希、内存会话、`HttpOnly` cookie、Bearer 令牌、一次性 QR 令牌、尝试次数限制；
- 安全头：CSP `default-src 'self'`、`X-Content-Type-Options`、`Referrer-Policy`；静态文件不缓存（实时开发）；
- `/api/connect` + `qr.py` — 手机快速连接：主机会列出其网络地址（先 `192.168.x`，然后 `10.x`、`172.16-31.x`），二维码由自定义标准库生成器绘制（字节模式、EC L、版本 1–10、所有掩码），无需外部库或互联网。

### 2.5a. `auth.py` — 密码登录

- 密码仅以 PBKDF2 哈希形式存储（`config/auth.json`），并使用 `hmac.compare_digest` 验证；来自同一地址每分钟 5 次失败 → 封锁。
- 会话保存在进程内存中（32 字节，12 小时 TTL，活动时延长）；浏览器收到 `open_deck_session` cookie（`HttpOnly`、`SameSite=Lax`），原生客户端使用 Bearer 或 WebSocket 的 `?token=`。
- 一次性 QR 令牌（`POST /api/pair`，10 分钟）允许手机无需输入密码即可登录。此类令牌只能通过 `/?pair=` 接受：`SessionStore.validate` 会拒绝 `pairing` 会话，因此它不能用作 cookie 或 Bearer 令牌。
- 如果浏览器 POST/PUT 和 WebSocket 请求的 `Origin` 与 `Host` 不匹配，则会被拒绝并返回 `403`（防止跨站 WebSocket 劫持和 CSRF）；没有 `Origin` 的客户端（Android、curl）会被允许。
- `Host` 头还会对照 localhost、机器名、FQDN 和本地 IP 进行检查。这可以阻止 DNS 重绑定，即 `Origin` 和 `Host` 都属于攻击者域名的情况。
- 只有登录、`/api/health`、`/api/integrity`、`/api/donation` 和 `/license` 可公开访问；其他所有内容均受保护。

### 2.5b. `assist.py` — 着陆与滑行辅助

- **滑行**：基于地速的 PI 油门控制器和基于航向的 P 方向舵控制器；仅在飞机位于地面时启用，在离地/刹车/速度超过 35 kt 时禁用；“STOP”会将油门归零并拉起驻车制动。
- **着陆**：ARM 会启用 AP 和 APR，在 60–15 ft 之间线性减小油门，接地时断开 AP；TOGA——全油门。它不会触碰升降舵。
- 一个 10 Hz 线程读取 `sim.read()`，并通过 `Hub.apply_assist_command` 发送命令（无速率限制或额外读取）。
- 这是一个辅助回路：最终决策和控制权仍属于飞行员。

### 2.6. `integrity.py` — 捐赠保护（许可证条件）

将五个关键文件（包括 `web/js/ui/donation.js`、`web/css/donation.css`、`config/donation.json`）的 SHA-256 与 `integrity/manifest.json` 清单进行比较。主机在不匹配时阻止启动；客户端（`web/js/ui/integrity.js`）还会监控该区块在 DOM 中的可见性。作者——Viktor Krasnikov（[github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)），捐赠——[https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。

### 2.7. `discovery.py` — 主机自动发现（UDP 广播）

后台线程每隔 N 秒通过 UDP 广播（`255.255.255.255` + 每个接口的定向广播）发送 JSON 信标（主机名、版本、`httpPort`、频率、配置文件列表）。`listen_once()` 是供原生客户端和测试使用的接收器。浏览器不支持 UDP，因此 Web 客户端不需要它（它已经从主机本身启动）。

### 2.8. `web/editor.*` — 可视化面板编辑器

`/editor.html` + `web/js/editor.js` — 拖放式编辑器：移动和调整仪表大小、配置绑定（来自目录 `GET /api/telemetry/variables` 的下拉列表，加上配置文件中声明的 `custom.*`）、选项（仪表、单位、色调）、从类型调色板添加以及删除。保存通过 `PUT /api/profiles/{id}` 完成。预览使用演示值绘制真实仪表（通过 `widgets/registry.js` 注册表）。形态因素覆盖项在活动形态因素中编辑：如果没有覆盖项，编辑会写入 `layout.base`。编辑历史（更改前 `widgets` 的快照）为拖动、调整大小、属性、添加和删除提供撤销和重做；还有 1 % 网格吸附（按住 Shift 可临时禁用）以及一键将几何信息复制到其他形态因素。

### 2.8a. 飞机自动识别

`SimConnectSim` 将 `TITLE` 和 `ATC MODEL` 作为单独的字符串数据项读取（`SIMCONNECT_DATATYPE_STRING256`），并将它们存储在 `aircraft.title` / `aircraft.atcModel` 中。`hub.py` 保留 `sim.match.title` / `atcModel` 规则（glob，不区分大小写），并在提供程序自身未设置配置文件时，在每一帧选择配置文件。客户端监视遥测中的 `sim.profileId`，并在飞机变化时重新加载面板；从列表中进行的手动选择会被锁定 5 秒，以免与尚未到达的帧冲突。

### 2.8b. `web/js/ui/comfort.js` — 亮度与 kiosk

面板亮度有三个级别（100/72/45 %），存储在 `localStorage` 中，并通过 `<html>` 上的 `data-brightness` 属性应用：CSS 仅调暗仪表场景，而 UI 仍保持可读。Kiosk 模式隐藏顶部面板和状态栏，将场景切换为全屏模式，并保留一个小退出按钮；`Esc` 恢复 UI。快捷键：`B` — 亮度，`F` 和 `Esc` — kiosk。

### 2.9. WASM 桥：通过客户端数据区读写 LVAR/RPN

复杂飞机（PMDG、Fenix、FlyByWire、iniBuilds）将自己的状态保存在专属变量中。配置文件在 `variables` 区块中声明它们（`source: lvar` 或 `rpn`），桥通过 **SimConnect 客户端数据区**读写它们——WASM 模块（MobiFlight / SimBridge）在那里发布数据。

```
hub.build_message()
   └─ hub._custom_values(profile_id)        # 0.25 s cache
        └─ WasmBridge.read_specs(specs)      # wasm_bridge.py
             ├─ read_lvars(names)            # block: name 128 B + double 8 B
             └─ execute_rpn(script)          # Command → Response
                  └─ ClientDataChannel.read_area / write_area   # client_data.py
                       └─ SimConnectClientDataBackend            # simconnect.py
                            └─ run_on_dispatch(...)  # calls on the SimConnect thread
```

层级：

- **`sim/client_data.py`** — 同步形式的协议：按 `request_id` 关联请求、超时、区域大小增长时重新注册，以及断开连接时重置待处理请求。传输层已抽象（`ClientDataBackend`），因此协议可以在没有 MSFS 的情况下测试；`LoopbackClientDataBackend` 是用于测试和演示的内存实现。
- **`sim/simconnect.py`** — `SimConnectClientDataBackend`：`MapClientDataNameToID`、`AddToClientDataDefinition`、`RequestClientData`、`SetClientData`。所有调用都通过 `run_on_dispatch` 在调度线程上执行（SimConnect 并非为多线程调用而设计），响应在 `SIMCONNECT_RECV_ID_CLIENT_DATA` 中到达。
- **`sim/wasm_bridge.py`** — LVAR 区块布局、RPN 命令，以及通过 `(<value>) (>L:NAME, number)` 写入 LVAR。

默认区域：`MobiFlight.LVars`、`MobiFlight.Command`、`MobiFlight.Response`；对于不同的模块版本，它们由 `wasm_bridge.py` 中的常量覆盖。

它会为 `simconnect` 提供程序自动启用（`--no-wasm` 标志可禁用它）。如果未安装 WASM 模块，响应不会到达：在连续两次超时后，`ClientDataChannel` 断路器会暂时（30 秒）停止轮询，因此遥测流不会在每一帧上被阻塞。`custom.*` 键只是不会出现在帧中——仪表会如实显示“--”，同时 SimVar 遥测继续工作。LVAR 区块限制为 56 个元素（7616 字节），以便适应 `MaxRecvData`/`MaxSendData` = 8192。在 mock 模式下，值取自配置文件的 `initial`。已接受的 SimConnect 定义中缺失或已过时的内置 SimVar 会返回 `null` 而不是 `0`：面板显示“--”，辅助也不会将它们误认为真实的零。

**验证状态：** 协议和区域计量由测试覆盖（通过内存传输模拟 MobiFlight），构建和启动已经验证；尚未使用 MSFS + WASM 模块进行实时飞行——这是唯一需要安装模拟器的步骤。

### 2.10. `android_build.py` — 从发行版构建 Android APK

已安装的应用包含 Android 源代码（`android/`），构建完成后 APK 位于 `android/dist`。页面 `/android.html` 和 API `/api/android/*` 允许修改应用名称、包 id、版本和默认网关地址，运行 `gradle assembleDebug` 并下载新的 APK。设置在 `config/android-build.json` 中；相同的值作为 `-P…` 传入构建，并最终进入 `BuildConfig`/Android 清单。

工具查找：设置 → `JAVA_HOME` / `ANDROID_HOME` → 典型路径。如果用户配置文件不可写（严格策略、沙箱），Gradle 缓存、`TMP` 和调试 keystore 会自动重定向到发行版目录（`.gradle-home`、`.tmp`、`.android-home`）——构建继续正常工作。无浏览器 CLI：`OpenDeck.exe --build-apk [config.json]`。

---

## 3. 数据流

### 3.1. 遥测（推送）

```
MockSim/SimConnectSim._loop()
   └─ sim.read()                        # snapshot of values
        └─ hub.build_message()          # normalization + seq/ts/sim
             └─ hub._broadcast_text()   # JSON into each WebSocket queue
                  └─ web: handleMessage('telemetry') → store → panel-view → widgets
```

### 3.2. 命令（请求/确认）

```
web: toggle-switch.onClick()
   └─ socket.command(key, value)        # {type:'command', id, key, value}
        └─ hub.handle_command()         # validation + rate limit
             └─ sim.apply_command()     # mock / SimConnect
                  └─ ack {type:'ack', id, ok, value}   (over WebSocket)
                       └─ client waits for confirmation via telemetry
```

### 3.3. 配置文件（拉取）

```
web: api.listProfiles() → GET /api/profiles
   └─ api.getProfile(id) → GET /api/profiles/{id}
        └─ profiles.load_profile_file() → legacy.adapt_if_needed() → ensure_valid()
             └─ panel-view.mount(profile) → createWidgetInstance() by type
```

### 3.4. 自动发现（UDP 推送）

```
DiscoveryBeacon._loop()                      # daemon thread
   └─ payload() {name, version, httpPort, profiles, auth?, ts}
        └─ sendto(255.255.255.255:8761) + directed broadcasts
             └─ Android/native client: listen_once() → http://<ip>:<port>/
```

---

## 4. 关键设计决策

| 决策 | 原因 |
| --- | --- |
| 仅使用 Python 标准库 | air-gapped：无法使用 `pip install`；解释器已经安装 |
| HTTP+WS 共用一个端口 | 一条防火墙规则，诊断更简单 |
| 不使用外部库的 WebSocket | 可控制协议，无依赖 |
| 配置文件使用 0..1 坐标而非像素 | 一个配置文件适用于所有形态因素 |
| `layout.base` + 覆盖项 | 手机/平板只指定差异 |
| 规范的 SimVar 注册表 | 将配置文件与特定桥解耦 |
| 客户端平滑（Smoother） | 在 20–30 Hz 网络上实现 60 fps 动画 |
| 控件按 `clientWidth` 绘制 canvas | 预览中真实的 HiDPI 缩放 |
| `auto` 提供程序 | 网关无需 MSFS 且无需修改配置即可启动 |
| UDP 自动发现信标 | Android 无需手动 IP 即可找到主机；浏览器不需要 |

---

## 5. MVP 边界与后续步骤

**已经存在**：标准库网关、带每客户端队列的 WebSocket、mock/SimConnect（+ TCP 回退）、LVAR/RPN WASM 桥、9 种仪表类型、3 种形态因素、带校验和原子保存的配置文件、带撤销/重做和布局复制的编辑器、UDP 自动发现、Android 客户端、发行版中的 APK 构建器、Windows 安装程序、带 QR 的密码登录、着陆和滑行辅助、完整性检查、248 个 Python 和 35 个 JS 测试。

后续步骤（参见 README 的“路线图”）：

- 实时飞行验证：在真实飞机上验证 SimConnect/WASM，空中和地面的辅助；
- APK 发布签名（构建器设置中的 keystore）；
- mDNS（Bonjour）作为 UDP 信标的替代方案；
- 使用机场图表进行滑行路线规划（目前辅助仅保持速度和航向）；
- 遥测录制/回放，用于演示和性能分析。
