# Open Deck for MSFS — 服务说明

本文档说明网关的功能、组成、客户端如何与其交互，以及如何启用密码登录。它面向“为自己”搭建面板的飞行员，以及需要理解内部设计的开发者。

- 版本：0.1.0
- 主机平台：Windows 10/11
- 客户端：浏览器（PC、手机、平板）、Android 8+
- 许可证：[GNU AGPL-3.0](../../LICENSE) + 第 7 条附加条款

## 1. 用途

Open Deck for MSFS 将手机或平板变成 Microsoft Flight Simulator 2020/2024 的仪表板。网关与模拟器运行在同一台计算机上，通过 SimConnect 读取遥测数据，通过本地网络提供服务，并接受命令（开关、旋转选择器、按钮）。面板由飞机 JSON 配置文件描述，并可直接在浏览器中编辑。

关键特性：

- **离线**：无外部 CDN、字体、API 或遥测。一切都能在隔离网络和无法访问互联网的机器上运行。
- **单一端口**：静态文件、REST 和 WebSocket 都使用一个 TCP 端口（默认 8760）——只需一条防火墙规则。
- **无依赖**：主机为 Python 3.11+ 和标准库；客户端为原生 ES 模块；Android 为不使用 AndroidX 的 Kotlin。
- **可选密码**：可以使用至少 6 个字符的密码保护 API 和遥测访问，支持会话、QR 登录和暴力破解防护。

## 2. 运行模型

```
┌──────────────────┐   SimConnect / WASM    ┌─────────────────────────────┐
│  MSFS 2020/2024  │◄──────────────────────►│ Open Deck for MSFS (Windows)│
│  aircraft, LVAR  │   SimVar, TITLE, ATC   │                             │
└──────────────────┘   Client Data Area     │  ┌───────────────────────┐  │
                                             │  │ SimProvider           │  │
┌──────────────────┐        HTTP/WS          │  │  auto / mock / simconn│  │
│  PC browser      │◄───────────────────────►│  └──────────┬────────────┘  │
│  panel, editor   │   8760, static + API    │             │               │
└──────────────────┘                         │  ┌──────────▼────────────┐  │
┌──────────────────┐        HTTP/WS          │  │ Hub: telemetry 30 Hz  │  │
│  Phone/tablet    │◄───────────────────────►│  │ commands, sessions    │  │
└──────────────────┘                         │  └──────────┬────────────┘  │
┌──────────────────┐   HTTP (WebView)        │             │               │
│  Android client  │◄───────────────────────►│  Profiles, integrity,     │
└──────────────────┘   UDP beacon 8761       │  authentication, APK      │
                                             └─────────────────────────────┘
```

数据流：

1. 遥测提供程序（`simconnect`、`mock` 或 `auto`）每个 tick 读取一次变量值。
2. 总线（`Hub`）组装帧，添加服务字段，并以配置的频率（默认 30 Hz，最大 60）广播给所有 WebSocket 客户端。
3. 客户端绘制仪表；命令返回总线，经过校验后由提供程序应用。
4. 当飞机变化时，网关按名称/ATC 模型选择匹配的配置文件，并通知客户端。

## 3. 组件

| 组件 | 文件 | 职责 |
| --- | --- | --- |
| 入口点 | `msfs_gateway/app.py` | 依赖装配、生命周期、横幅、`--set-password` / `--build-apk` 模式 |
| 设置 | `msfs_gateway/settings.py` | CLI 参数、路径、默认值 |
| HTTP/WebSocket | `msfs_gateway/http_api.py`、`websocket.py` | 静态文件、REST、RFC 6455 握手和帧、身份验证 |
| 总线 | `msfs_gateway/hub.py` | 遥测帧、订阅、命令、命令限制、飞机自动识别 |
| 提供程序 | `msfs_gateway/sim/` | `mock`、`simconnect`、客户端数据区、LVAR/RPN WASM 桥 |
| 配置文件 | `msfs_gateway/profiles.py` | 读取/校验/原子保存 JSON 配置文件 |
| 遥测 | `msfs_gateway/telemetry.py` | 变量目录、类型、值转换 |
| 身份验证 | `msfs_gateway/auth.py` | PBKDF2 哈希、会话、QR 令牌、尝试次数限制 |
| 自动发现 | `msfs_gateway/discovery.py` | 包含名称、版本和密码标志的 UDP 信标 |
| 完整性 | `msfs_gateway/integrity.py` | 关键 UI 文件的 SHA-256 |
| QR | `msfs_gateway/qr.py` | 内置 QR 生成器（SVG），无依赖 |
| APK 构建 | `msfs_gateway/android_build.py` | 设置、JDK/SDK/Gradle 查找、Gradle 启动、APK 交付 |
| 辅助 | `msfs_gateway/assist.py` | 滑行（速度/航向）和着陆（APR、retard、TOGA）回路 |
| 文档生成器 | `msfs_gateway/docsgen.py` | 从代码注册表生成 `docs/telemetry.md` 和 `docs/widgets.md` |
| Web 客户端 | `web/` | 面板、编辑器、登录、辅助、APK 构建页面 |
| Android | `android/` | WebView 外壳、UDP 发现、完整性检查、登录 cookie |
| 构建与检查 | `scripts/`、`packaging/` | 安装程序、`check.ps1`、QR 验证 |

## 4. 遥测

### 4.1. 帧

帧是一个 JSON 对象，在连接后立即通过 WebSocket 到达，然后按网关的频率持续到达：

```json
{
  "type": "telemetry",
  "seq": 421,
  "ts": 1793541762842,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  },
  "values": {
    "attitude.pitchDeg": 2.4,
    "attitude.bankDeg": -6.1,
    "speed.iasKt": 108.2,
    "altitude.indicatedFt": 4520.0,
    "heading.magneticDeg": 274.0,
    "verticalSpeed.fpm": 120.0,
    "engine.rpm": 2380.0,
    "power.batteryMaster": true,
    "custom.lvar.apuBleed": 0.0
  }
}
```

`seq` 单调递增，`ts` 为 Unix 毫秒。客户端通过 `seq` 检测丢帧，并继续绘制（这对指针没有影响）。

### 4.2. 变量

带类型、单位、SimVar 和事件的完整目录见 [telemetry.md](telemetry.md)。下面仅列出类别。

变量目录是唯一事实来源（`telemetry.py`）。每个条目都有一个类型（`number`、`bool`、`string`）、一个“接受命令”标志和一个描述。客户端可以通过 `GET /api/telemetry/variables` 获取目录。

类别：

- 姿态、高度、速度、航向、VSI；
- 发动机（RPM、进气压力/扭矩、N1、ITT、燃油）；
- 电气、襟翼、自动驾驶；
- `custom.<...>`——来自活动配置文件的 LVAR/RPN。

### 4.3. 提供程序

| 提供程序 | 何时使用 | 特性 |
| --- | --- | --- |
| `simconnect` | 真实飞行 | `ctypes` + `SimConnect.dll`；字符串数据项 `TITLE`、`ATC MODEL`；用于 LVAR/RPN 的客户端数据区。如果标准 `SimConnect.cfg` 无法工作，网关会通过临时配置自行尝试 TCP `127.0.0.1:19999`（MSFS 2020/2024 端口） |
| `mock` | 演示、开发、测试 | 程序化飞行模型，LVAR 初始值来自配置文件 |
| `auto` | 默认 | 尝试连接 SimConnect，失败时回退到 mock |

如果未安装 WASM 模块，`custom.*` 键只是不会出现，面板显示“--”——其余遥测继续工作。连续两次超时后，Client Data 断路器会暂停轮询 30 秒，以免阻塞遥测广播线程。

### 4.4. 投递与恢复能力

- 每个 WebSocket 客户端都有自己的队列（8 帧）和发送线程：慢速平板不会拖慢其他客户端，旧帧会被丢弃。
- 客户端重连使用指数退避；如果超过 45 秒没有消息到达，客户端会认为连接“半开”并重连。
- 会话可能在飞行期间过期——客户端每分钟检查一次状态，并重定向到登录页面。

## 5. 飞机配置文件

配置文件是 `profiles/` 中的 JSON 文件。详细模式见 [`profile-schema.md`](profile-schema.md)。简要说明：

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk",
  "icao": "C172",
  "revision": 3,
  "sim": { "match": { "title": "*Cessna*172*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S" },
  "widgets": [
    {
      "id": "attitude",
      "type": "attitude",
      "label": "Attitude indicator",
      "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
      "layout": {
        "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
        "phone": { "x": 0.03, "y": 0.015, "w": 0.94, "h": 0.3 }
      }
    }
  ]
}
```

- `sim.match`——飞机标题和 ATC 模型的模板（glob）；网关会自动切换配置文件。
- `layout`——面板比例（0..1）中的坐标；`base` 以及覆盖项 `phone`、`tablet-sm`、`tablet-lg`。
- `revision`——每次从编辑器保存时递增。
- 保存是原子的：临时文件 → `fsync` → `os.replace`。

## 6. 客户端

### 6.1. Web 面板

- 三种形态因素，根据屏幕宽度自动选择；手动选择会被记住。
- 仪表：姿态仪、圆形仪表、读数、开关、旋转选择器、VSI、高度表、航向指示器；通过 `requestAnimationFrame` 实现动画。
- 舒适性：亮度 100/72/45 %（`B`），kiosk 模式（`F`，按 `Esc` 退出）。
- 手机按钮显示用于快速登录的二维码。

### 6.2. 编辑器

`/editor.html`：拖放、调整大小、1 % 网格、撤销/重做、在形态因素之间复制布局、保存到主机。

### 6.3. Android

WebView 外壳：通过 UDP 信标找到主机或接受手动地址，检查 UI 完整性并打开面板。如果网关上启用了密码，WebView 会显示登录页面；会话存储在 WebView cookie 中，并在应用重启后保留。受密码保护的主机会标记为锁形图标。

### 6.4. 登录页面

`/login.html` 是无需登录即可访问的唯一页面（连同其样式）。它显示密码字段、错误信息、作者支持区块，以及会话已激活时的“登出”按钮。密码仅发送到自己的网关，通过本地网络上的 HTTP 传输（参见“安全”部分）。

## 7. 网络与连接

| 内容 | 端口 | 协议 |
| --- | --- | --- |
| 静态文件、REST、WebSocket | 8760（可通过 `--port` 配置） | TCP/HTTP + WS |
| 自动发现 | 8761 | UDP 广播 |

- 网关监听 `0.0.0.0`，并在启动时打印所有地址。
- Android 通过信标找到主机：PC 名称、版本、配置文件数量、密码标志。
- 面板上的二维码包含地址和一次性令牌：手机一次扫描即可登录，无需输入密码（令牌有效期为 10 分钟且仅使用一次）。
- 手动地址输入：`192.168.1.10`、`192.168.1.10:8760` 或完整 URL。

## 8. 密码身份验证

### 8.1. 如何启用

以下任意方式：

```powershell
# 1. 将密码保存到 config/auth.json（持久化）
OpenDeck.exe --set-password
#    或无需提示：
OpenDeck.exe --set-password "my-password"

# 2. 仅本次运行传递密码（不写入磁盘）
OpenDeck.exe --password "my-password"

# 3. 环境变量
$env:OPEN_DECK_PASSWORD = "my-password"
```

在已安装的应用中，开始菜单有“设置密码”快捷方式用于此目的。文件 `config/auth.json` **仅存储 PBKDF2 哈希**（随机盐，210,000 次迭代）；删除该文件后登录会再次变为可选。`--no-auth` 标志会忽略该文件和密码（仅限可信网络）。

`--password` 中的密码不会写入磁盘，但会在进程列表中可见（`Get-Process` / 任务管理器）。对于长期使用，优先使用 `--set-password`：它在启动时在内存中哈希一次。

最小密码长度为 **6 个字符**；限制：不超过 256 个字符，无控制字符，无前导或尾随空格。

### 8.2. 登录如何工作

1. 客户端打开 `/login.html` 并输入密码。
2. `POST /api/auth/login` 验证 PBKDF2 哈希；成功后创建会话（32 个随机字节，12 小时 TTL，活动时延长）。
3. 服务器设置 `open_deck_session` cookie，带 `HttpOnly`、`SameSite=Lax`——JavaScript 无法看到它，浏览器会自动发送。
4. 对于原生客户端，JSON 响应返回 `token`；它可以作为 `Authorization: Bearer <token>` 或 WebSocket 的 `?token=` 传递。
5. `POST /api/auth/logout` 撤销会话并清除 cookie。

只有以下内容可公开访问：

| 路径 | 原因 |
| --- | --- |
| `/login.html`、`/js/login.js`、`/css/*`、`/img/*` | 登录页面及其样式 |
| `/api/auth/status`、`/api/auth/login`、`/api/auth/logout` | 登录本身 |
| `/api/health` | “这是网关吗？”检查和密码标志 |
| `/api/integrity` | UI 完整性检查（许可证条件） |
| `/api/donation` | 作者支持区块（许可证条件） |
| `/license` | 许可证文本 |

其他所有内容——配置文件、遥测、命令、Android 设置、APK 构建、QR、`WS /ws`——都需要会话。没有会话的页面会响应重定向到 `/login.html?next=…`。

### 8.3. 暴力破解防护

- 60 秒内来自同一 IP 的 5 次失败尝试 → 封锁 60 秒（响应 `429`，带 `Retry-After`）。
- 哈希比较使用 `hmac.compare_digest`（恒定时间）。
- 失败尝试会记录地址，但不记录密码。

### 8.4. 从手机进行 QR 登录

面板上的“手机”按钮请求 `POST /api/pair`（需要会话）。网关签发一个 10 分钟的一次性令牌；二维码编码 `http://<address>:<port>/?pair=<token>`。手机打开链接后，网关将令牌交换为常规会话、设置 cookie 并重定向到 `/`。配对令牌本身不是会话：作为 cookie 或 Bearer 令牌会返回 `401`，因此链接在交换后无法重复使用。重复使用令牌会被拒绝。

## 9. 着陆与滑行辅助

页面 `/assist.html` 和 API `/api/assist*` 添加两个辅助回路。这**不是经认证的自动驾驶**：飞行员控制飞行，并可随时禁用辅助。

### 9.1. 滑行

- 仅在飞机位于地面、驻车制动已释放且速度低于 35 kt 时启用。
- 使用 PI 油门控制器保持目标地速（3–25 kt），并使用 P 方向舵控制器保持航向；飞行员通过 ±1°/±5° 按钮改变航向。
- “STOP”：油门 0，方向舵 0，驻车制动。
- 如果飞机离地、拉起驻车制动或速度超过 35 kt，会自动断开。

### 9.2. 着陆

- ARM：启用 `AP_MASTER` 和 `AP_APR_HOLD`（ILS 进近）。需要至少 40 kt 的速度且飞机在空中。
- 在 60–15 ft 无线电高度，辅助将油门从 45 % 线性减小到 0。
- 接地时：油门 0，自动驾驶关闭；减速到 5 kt 以下后——“rollout complete”。
- TOGA：全油门，AP 和 APR 关闭（复飞）。
- 辅助不会触碰升降舵：进近和拉平仍由自动驾驶/飞行员负责。

状态和设定值：`GET /api/assist`；操作——`POST /api/assist/taxi`（`engage`、`disengage`、`stop`、`speed`、`heading`）和 `POST /api/assist/landing`（`arm`、`disarm`、`toga`）。所有请求都需要会话。

## 10. API

基础 URL：`http://<host>:<port>`。所有响应均为 JSON；错误格式为 `{"error": "…", "code": "…"}`。

| 方法 | 路径 | 访问 | 描述 |
| --- | --- | --- | --- |
| GET | `/api/health` | 公开 | 状态、版本、频率、密码标志 |
| GET | `/api/auth/status` | 公开 | `{required, authenticated}` |
| POST | `/api/auth/login` | 公开 | `{password}` → 会话 + cookie |
| POST | `/api/auth/logout` | 公开 | 撤销当前会话 |
| POST | `/api/pair` | 需要会话 | 一次性 QR 令牌 |
| GET | `/api/profiles` | 需要会话 | 配置文件列表 |
| GET | `/api/profiles/{id}` | 需要会话 | 完整配置文件 |
| PUT | `/api/profiles/{id}` | 需要会话 | 保存配置文件（请求体中的 id = URL 中的 id） |
| GET | `/api/telemetry` | 需要会话 | 最新帧 |
| GET | `/api/telemetry/variables` | 需要会话 | 变量目录 |
| POST | `/api/sim/command` | 需要会话 | `{key, value}` → 确认 |
| POST | `/api/sim/aircraft` | 需要会话 | `{profileId}` — 手动选择飞机 |
| GET | `/api/integrity` | 公开 | SHA-256 检查结果 |
| GET | `/api/donation` | 公开 | 作者支持详情 |
| GET | `/api/connect` | 需要会话 | 用于 QR/提示的网关地址 |
| GET | `/api/qr.svg?text=…` | 需要会话 | 包含二维码的 SVG |
| GET/PUT | `/api/android/settings` | 需要会话 | APK 构建设置 |
| GET/POST | `/api/android/build` | 需要会话 | APK 构建的启动/状态 |
| GET | `/api/android/apk` | 需要会话 | 下载 APK |
| GET | `/api/assist` | 需要会话 | 辅助状态和遥测 |
| POST | `/api/assist/taxi` | 需要会话 | 滑行辅助控制 |
| POST | `/api/assist/landing` | 需要会话 | ARM / DISARM / TOGA |
| WS | `/ws` | 需要会话 | 遥测和命令 |

登录和请求示例：

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"my-password"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

命令：

```json
{"type": "command", "id": "c17", "key": "power.batteryMaster", "value": true}
```

响应：`{"type": "ack", "id": "c17", "ok": true, "value": true}` 或 `ok:false` 并附错误码。每个客户端的命令限制约为每秒 20 条。

## 11. 安装与启动

### 11.1. Windows 安装程序

`OpenDeck-Setup-<version>.exe` — 按用户安装，无需管理员权限，不需要 Python。会为以下内容创建快捷方式：启动网关、在浏览器中打开面板、APK 构建页面、“设置密码”和卸载。

### 11.2. 从源代码

```powershell
python -m msfs_gateway --sim auto          # 真实飞行
python -m msfs_gateway --sim mock          # 无模拟器的演示
python -m msfs_gateway --password "secret123"
```

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8760` | 地址和端口 |
| `--allow-host NAME` | — | Host 的额外 DNS 名称（如果通过名称打开面板） |
| `--sim` | `auto` | `auto`、`mock`、`simconnect` |
| `--telemetry-hz` | `30` | 帧率，1..60 |
| `--simconnect-dll` | 自动检测 | `SimConnect.dll` 的路径 |
| `--simconnect-host` | `127.0.0.1` | SimConnect 地址（远程模拟器） |
| `--simconnect-port` | `19999` | SimConnect TCP 端口 |
| `--profile-dir` | `profiles/` | 配置文件目录 |
| `--password` | — | 本次运行的密码 |
| `--set-password [PWD]` | — | 保存哈希并退出 |
| `--auth-file` | `config/auth.json` | 哈希文件 |
| `--web-dir` / `--profile-dir` | `web/` / `profiles/` | 静态文件和配置文件目录 |
| `--donation-config` | `config/donation.json` | 作者支持详情 |
| `--log-level` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |
| `--discovery-port` / `--discovery-interval` | `8761` / `3` | UDP 信标：端口和周期 |
| `--no-auth` | — | 忽略密码 |
| `--no-wasm` | — | 无 LVAR/RPN |
| `--no-discovery` | — | 无 UDP 信标 |
| `--build-apk [CONFIG]` | — | 构建 APK 并退出 |

### 11.3. Android APK

安装内容包含 Android 源代码；构建好的 APK 会输出到 `android/dist/OpenDeck-Android-<version>.apk`。页面 `/android.html`（需要登录）允许修改名称、包 id、版本和默认网关地址，并在本地构建 APK。需要 JDK 17、Android SDK 和 Gradle 8.x；在发行版中，APK 已附带。

## 12. 诊断

| 症状 | 检查内容 |
| --- | --- |
| 手机无法打开面板 | 同一 Wi-Fi、横幅中的地址、Windows 防火墙（端口 8760）、`--host 0.0.0.0` |
| “需要密码登录” | 已设置密码；在 `/login.html` 中输入；QR 令牌有效期为 10 分钟 |
| “密码不正确” | 键盘布局/大小写；重置：删除 `config/auth.json` 或使用 `--no-auth` |
| 仪表显示“--” | 无 SimConnect/WASM、选择了 mock、飞机没有配置文件、模拟器仍在主菜单 |
| 配置文件不切换 | `sim.match` 与名称/模型不匹配；手动选择 |
| APK 构建无法启动 | 未找到 JDK/SDK/Gradle；在 `/android.html` 上指定路径 |
| “完整性违规” | 关键文件已被修改；`python -m msfs_gateway.integrity --write` |
| `SimConnect_Open … 0x80004005` | 网关会自行尝试 TCP `127.0.0.1:19999`；如果仍无帮助——检查 `%APPDATA%\Microsoft Flight Simulator\SimConnect.cfg`（它会覆盖设置）以及是否已加载飞行；对于远程模拟器，设置 `--simconnect-host/--simconnect-port` |

日志：网关控制台（`--log-level DEBUG`）、浏览器的“网络”选项卡，以及 Android 的 `adb logcat`（标签 `OpenDeckDiscovery`）。

## 13. 安全

- 密码可以保护 API 和遥测免受“Wi-Fi 邻居”的访问，但**流量通过无 TLS 的 HTTP 传输**。在可信的家庭网络中这是可以接受的；对于访客网络，请使用单独的 VLAN 或带 TLS 的反向代理。
- 会话 cookie 为 `HttpOnly` + `SameSite=Lax`；CSRF 风险降低。URL 令牌仅用于 WebSocket（`?token=`）和一次性 QR（`?pair=`）。QR 令牌只能通过 `/?pair=` 接受，且不是会话。
- 对浏览器 POST/PUT 和 WebSocket 的 `Origin` 检查：带外部 `Origin` 的请求会收到 `403`；没有 `Origin` 的客户端会被允许。
- `Host` 检查对照本地名称/IP：未知 Host 会收到 `403`（防止 DNS 重绑定）。
- 登录尝试限制为每个地址每分钟 5 次。
- CORS 被有意禁用：第三方页面无法读取 API 响应。
- 如果未设置密码，网关会在控制台中明确警告面板和命令对本地网络上的所有人可用。
- UDP 信标未签名：网络上的任何主机都可以冒充网关。不要将网关暴露到互联网。
- Android：WebView 导航允许列表，禁止访问 `file:`/`content:`，禁止混合内容。

## 14. 限制

- SimConnect/WASM 的实时运行需要安装 MSFS；在仓库中，逻辑通过仿真验证。
- APK 使用调试密钥签名；发布签名尚未自动化。
- 无 mDNS：仅使用 UDP 信标。
- 每个端口一个活动网关；配置文件是文件，没有数据库。

## 15. 术语表

| 术语 | 含义 |
| --- | --- |
| **网关** | 模拟器所在 PC 上的进程：读取遥测并将其提供给客户端 |
| **主机** | 运行网关的机器（在 Android 客户端中——发现到的 PC） |
| **配置文件** | 包含特定飞机仪表和布局的 JSON 文件 |
| **仪表 / 控件** | 面板元素：姿态仪、仪表、开关等 |
| **形态因素** | 屏幕类别：`phone`、`tablet-sm`、`tablet-lg` |
| **飞机** | 模拟器中的特定飞机；配置文件通过 `TITLE`/`ATC MODEL` 选择 |
| **遥测** | JSON 帧中 SimVar 和 `custom.*` 值的流 |
| **帧** | 包含 `seq`、`ts`、`sim`、`values` 的单条 `telemetry` 消息 |
| **LVAR** | 飞机本地变量（PMDG、Fenix、FBW 等） |
| **RPN** | 逆波兰表示法——用于在 MSFS 中计算值的脚本 |
| **WASM 桥** | 通过 MobiFlight/SimBridge 模块的客户端数据区交换 LVAR/RPN |
| **客户端数据区** | 用于交换数据块的命名 SimConnect 区域 |
| **AP / APR / AT** | 自动驾驶 / ILS 进近模式 / 自动油门 |
| **Retard** | 拉平期间平滑减小油门（着陆辅助） |
| **TOGA** | 起飞/复飞：全油门并复飞 |
| **配对** | 使用一次性 QR 令牌从手机登录 |
| **会话** | 活动登录：cookie/Bearer 中的令牌，TTL 12 小时 |
| **完整性** | 将关键 UI 文件的 SHA-256 与清单进行比较 |
| **Air-gapped** | 没有互联网访问的网络；所有资源均为本地 |

## 16. 反馈与支持

- **作者：** Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)。
- **捐赠：** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。
- 错误和建议——通过 GitHub issue 模板（参见 `.github/`）。
- 漏洞——根据 [SECURITY.md](security.md) 私下报告。
- 安装问题——Discussions（如果启用）或使用“Bug”模板提交 issue。
- 许可证和强制的作者支持区块——[LICENSE](../../LICENSE)。

## 17. 许可证

[GNU Affero 通用公共许可证 v3.0](../../LICENSE) 和[第 7 条附加条款](../../COPYING.ADDITIONAL)：源代码开放，修改版本在 AGPL 下分发；作者支持区块和完整性检查是强制性的，不可移除。
