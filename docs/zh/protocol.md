# 🔌 Open Deck for MSFS 网络协议

所有通信都通过单一 TCP 端口进行（默认 `8760`）：

- **HTTP 静态文件**——来自 `web/` 的文件（面板、编辑器、登录、辅助）；
- **REST API**——配置文件、遥测、命令、辅助、APK 构建；
- **WebSocket `/ws`**——遥测流和命令确认。

## 0. 约定

- 基础 URL：`http://<host>:<port>`；所有路径均为相对路径。
- JSON 为 UTF-8，`Content-Type: application/json; charset=utf-8`。
- API 响应：`Cache-Control: no-store`；静态文件：`no-cache`。
- **CORS 被有意禁用**：API 面向同源客户端设计，第三方页面无法读取响应。
- **同源保护**：如果浏览器发送了 `Origin`，其主机和有效端口必须与 `Host` 匹配。否则 `POST`/`PUT` 和 WebSocket 请求会收到 `403` `origin_not_allowed`。没有 `Origin` 的客户端（Android、curl）会被允许。
- **Host 允许列表**：`Host` 必须指向 localhost、机器名、FQDN、本地 IP，或 `--allow-host` 中的名称；否则返回 `403 host_not_allowed`。这是针对 DNS 重绑定的保护。
- 请求体限制——**2 MiB**；未知 `Content-Length` → `411`。
- 密码（如果启用）和会话在第 2 节描述。
- 自动发现信标中的协议版本为 `protocol: 1`。

---

## 1. 访问：公开与会话保护

如果未配置密码，则一切可用。如果配置了密码，则只有登录页面、其文件以及许可证所需的服务数据可以在没有会话的情况下访问：

| 路径 | 访问 | 用途 |
| --- | --- | --- |
| `/login.html`、`/js/login.js`、`/css/*`、`/img/*` | 公开 | 登录页面及其样式 |
| `/api/auth/status`、`/api/auth/login`、`/api/auth/logout` | 公开 | 登录/登出 |
| `/api/health` | 公开 | “这是网关吗？”，版本、密码标志 |
| `/api/integrity` | 公开 | UI SHA-256 检查 |
| `/api/donation` | 公开 | 作者支持区块 |
| `/license` | 公开 | 许可证文本 |
| 其他所有内容 | 需要会话 | 配置文件、遥测、命令、QR、APK、辅助、`/ws` |

没有会话时：

- API 响应 `401` 和 `{"error","code":"unauthorized"}`，并附带 `WWW-Authenticate: Bearer realm="open-deck"`；
- HTML 页面响应 `302` 跳转到 `/login.html?next=<path>`；
- WebSocket 握手被拒绝并返回 `401`（浏览器会显示连接错误）。

---

## 2. 身份验证

密码至少 6 个字符，并以 PBKDF2 哈希形式存储在 `config/auth.json` 中（210,000 次迭代，随机盐）。会话为 32 个随机字节，TTL 为 12 小时，访问时延长。

令牌可以通过三种方式接受：

| 方式 | 位置 | 适用对象 |
| --- | --- | --- |
| Cookie `open_deck_session` | `HttpOnly; SameSite=Lax` | 浏览器和 Android WebView |
| `Authorization: Bearer <token>` | 请求头 | 原生客户端 |
| `?token=<token>` | 仅 `/ws` | 没有 cookie 的 WebSocket |

### `GET /api/auth/status`

```json
{ "required": true, "authenticated": false }
```

### `POST /api/auth/login`

```json
{ "password": "secret" }
```

成功——`200`、cookie 和令牌：

```json
{ "ok": true, "required": true, "token": "<43 characters>", "expiresIn": 43200 }
```

错误：

| 状态 | `code` | 何时 |
| --- | --- | --- |
| `400` | `missing_password` | 没有 `password` |
| `401` | `bad_password` | 密码不正确 |
| `429` | `rate_limited` | 同一地址失败 5 次后；包含 `Retry-After` |

如果未配置密码，响应为 `{"ok":true,"required":false}`。

### `POST /api/auth/logout`

撤销当前会话并清除 cookie：`{"ok": true}`。

### `POST /api/pair`

需要会话。用于从手机登录的一次性令牌：

```json
{ "url": "http://192.168.1.10:8760/?pair=…", "token": "…", "expiresIn": 600, "required": true }
```

访问 `url` 会将令牌交换为常规会话（cookie）并重定向到 `/`；重复使用会返回 `/login.html?error=pair`。

---

## 3. REST API

下文中的 `{id}` 是配置文件标识符（`[a-z0-9][a-z0-9-]{1,63}`）。

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "authRequired": true,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  }
}
```

### `GET /api/profiles`

```json
{ "profiles": [
  { "id": "cessna-172-skyhawk", "name": "Cessna 172S Skyhawk", "icao": "C172",
    "revision": 3, "widgetCount": 11 }
] }
```

### `GET /api/profiles/{id}`

完整配置文件（参见 [profile-schema.md](profile-schema.md)）。`404 not_found`——没有文件；`422 invalid_profile`——校验失败。

### `PUT /api/profiles/{id}`

请求体是完整的 JSON 配置文件；请求体中的 `id` 必须与 URL 匹配（`400 id_mismatch`）。响应 `{"ok": true, "profile": {…}}`。

### `GET /api/telemetry`

最新帧（格式与 WebSocket 上的 `telemetry` 相同）。`seq` 递增；`values` 包含所有注册表键。

### `GET /api/telemetry/variables`

变量目录：

```json
{ "variables": [
  { "key": "speed.iasKt", "label": "Indicated airspeed", "kind": "number",
    "unit": "KT", "writable": false, "simVar": "AIRSPEED INDICATED", "simEvent": null }
] }
```

完整的人类可读目录见 [telemetry.md](telemetry.md)。

### `GET /api/integrity`

```json
{ "verified": true, "checkedAt": "2026-11-01T…", "manifestPresent": true,
  "files": { "web/index.html": "<sha256>" }, "errors": [] }
```

### `GET /api/donation`

来自 `config/donation.json` 的作者支持详情（唯一来源是主机配置）。作者——Viktor Krasnikov，捐赠——[`https://taps.uz/open_deck_fs`](https://taps.uz/open_deck_fs)。

### `GET /api/connect`

供手机/平板使用的地址：

```json
{
  "host": "FLIGHTSIM-PC",
  "primaryUrl": "http://192.168.1.10:8760/",
  "phoneUrl": "http://192.168.1.10:8760/?device=phone",
  "urls": [
    { "url": "http://192.168.1.10:8760/", "host": "192.168.1.10",
      "private": true, "loopback": false, "linkLocal": false }
  ],
  "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
  "qr": { "scale": 6, "border": 4, "maxTextLength": 512 }
}
```

排序：`192.168.*`，然后 `10.*`、`172.16–31.*`、链路本地、回环。

### `GET /api/qr.svg?text=…&scale=6&border=4`

包含二维码的 SVG（最多 512 个字符；在主机上生成，无需库）。`400 missing_text`——没有 `text`；`400`（`code` = `error`）——`scale`/`border` 不是数字；`422 qr_too_long`——文本无法放入支持的 QR 版本。

### `POST /api/sim/command`

```json
{ "key": "power.batteryMaster", "value": true }
```

成功——`200`，返回 `{"type":"ack","id":…,"key":…,"ok":true,"value":…}`。错误：`400`，`code` = `invalid_key`、`not_writable`、`invalid_value`、`rate_limited` 或 `sim_error`；`409 sim_rejected`——模拟器拒绝了该命令。对于带参数事件的变量，值会进行缩放（百分比 → 0..16383）。

### `POST /api/sim/aircraft`

```json
{ "profileId": "cessna-172-sixpack" }
```

响应：`{"ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false}`。`pinned: true`——提供程序无法切换飞机（SimConnect），因此选择会被锁定，直到模拟器中的飞机发生变化。`404`——没有该配置文件。

### 辅助

`GET /api/assist`——回路状态：

```json
{
  "telemetry": {
    "onGround": true, "radioAltitudeFt": 0, "groundSpeedKt": 12.3,
    "iasKt": 0, "headingDeg": 274, "localizerDeg": 0.0,
    "glideSlopeDeg": 0.0, "locValid": false, "gsValid": false,
    "autopilotMaster": false, "approach": false,
    "throttlePct": 18.4, "rudderPct": -3.2, "parkingBrake": false
  },
  "taxi": { "engaged": true, "targetSpeedKt": 12, "targetHeadingDeg": 274,
            "throttlePct": 18.4, "rudderPct": -3.2, "message": "…" },
  "landing": { "phase": "off", "message": "…", "throttlePct": 0, "active": false },
  "limits": { "taxiSpeedMinKt": 3, "taxiSpeedMaxKt": 25,
              "flareStartFt": 60, "flareIdleFt": 15 }
}
```

`POST /api/assist/taxi`：

| `action` | 字段 | 含义 |
| --- | --- | --- |
| `engage` | — | 启用速度/航向保持（仅地面） |
| `disengage` | — | 禁用 |
| `stop` | — | 油门 0，驻车制动 |
| `speed` | `value`（3…25） | 设置滑行速度 |
| `heading` | `delta`（±） | 转动目标航向 |

`POST /api/assist/landing`：`action` = `arm`（AP + APR）、`disarm`、`toga`。

响应：`{"ok": true|false, "message": "…", "status": {…}}`。`200`——已执行操作；`409`——被拒绝（不在地面、速度过低、未连接 MSFS、未知操作）。

### Android APK 构建

- `GET /api/android/settings` — `{settings, toolchain, apk, prebuiltApk}`。
- `PUT /api/android/settings` — 保存设置（名称、包 id、版本、网关地址、工具路径）。`422 invalid_settings`。
- `GET /api/android/build` — 作业状态：`{jobId, state, running, log, apk, error}`（`state`：`idle|running|success|failed`）。
- `POST /api/android/build` — 启动；`202` 并返回 `jobId`，`409 build_running`，`422 invalid_settings`。
- `GET /api/android/apk` — 下载 APK（`application/vnd.android.package-archive`）；如果没有构建，则返回发行版中的预构建 APK，否则 `404 apk_missing`。

### 静态文件和服务页面

- `GET /` — 面板（`index.html`），`GET /editor.html` — 编辑器，`GET /android.html` — APK 构建，`GET /assist.html` — 辅助，`GET /login.html` — 登录。
- `GET /license` — 许可证文本。
- `HEAD` — 仅静态文件；对于 `/api/*` — `405`。
- `OPTIONS` — `204`，不带 CORS 头。

---

## 4. WebSocket `/ws`

握手——RFC 6455，版本 13。仅文本消息；二进制消息会以 `1002` 关闭。

### 4.1. 授权

令牌来自 cookie、`Authorization: Bearer` 或 `?token=`（用于 `/ws`）。没有有效会话——HTTP `401`，不执行升级。一次性配对令牌在这里无效：它只能通过 `/?pair=` 接受。如果 `Origin` 和 `Host` 不匹配——HTTP `403`，不执行升级。

### 4.2. 服务器 → 客户端

#### `hello` — 第一条消息

```json
{
  "type": "hello",
  "clientId": "a1b2c3d4",
  "server": { "name": "Open Deck for MSFS", "version": "0.1.0",
              "telemetryHz": 30.0, "uptimeSec": 1.2 },
  "profiles": [ … ],
  "state": { /* full telemetry frame */ }
}
```

#### `telemetry` — 定期发送（每秒 `telemetryHz` 次）

```json
{
  "type": "telemetry",
  "seq": 1234,
  "ts": 1762340000000,
  "sim": { "provider": "mock", "connected": true,
           "aircraftTitle": "…", "profileId": "…" },
  "values": { "speed.iasKt": 108.0, "altitude.indicatedFt": 4520.0, … }
}
```

- `seq` 是单调递增的——它可揭示帧丢失；
- `values` 始终包含所有注册表键。`null` 表示“无数据”：SimVar 未被 SimConnect 接受或遥测已过期。客户端会显示破折号，而不是替代为零。

#### `aircraft`

```json
{ "type": "aircraft", "profileId": "cessna-172-sixpack", "aircraftTitle": "…" }
```

在飞机变化/自动识别后到达，以便客户端切换配置文件。

#### `ack`

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong`

对 `ping` 的响应：`{ "type": "pong", "t": <echo>, "ts": <unix ms> }`。

#### `error`

`{ "type": "error", "code": "bad_json"|"unknown_type", "error": "…" }`。

### 4.3. 客户端 → 服务器

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` 是任意值；服务器会在 `ack` 中返回它。

### 4.4. `ack` 代码

| `code` | 含义 |
| --- | --- |
| `invalid_key` | 空/未知键 |
| `not_writable` | 只读变量 |
| `invalid_value` | 值无法转换为该类型 |
| `rate_limited` | WebSocket 客户端每秒超过 30 条命令，或 REST 的 IP 超过限制 |
| `sim_rejected` | 模拟器拒绝了命令 |
| `sim_error` | 提供程序内部错误 |

### 4.5. 限制与行为

- 最大消息大小——256 KiB；更大——`1002`。
- 每个客户端——8 个遥测帧的队列；溢出时丢弃最旧的帧（慢速客户端不会拖慢其他客户端）。
- 控制帧（ping/pong/close）不进行分片，且 ≤125 字节。
- 读取空闲超时——90 秒；客户端每 20 秒发送一次 `ping`。
- 关闭：`1000`——正常，`1002`——协议违规。

### 4.6. 客户端建议

- 视觉状态来自 `telemetry.values`，而不是 `ack`。
- 使用退避重连（500 ms → 8 s，带抖动）；如果 45 秒内没有消息到达——将连接视为“半开”并重连。
- 不要阻塞 UI：显示“等待中”，在 `ok:false`/超时时回滚。

---

## 5. QR 登录（配对）

```
Phone (no session)                      Gateway
        │  GET /?pair=<one-time token>   │
        ├───────────────────────────────►│
        │                                │ token check (10 min, once)
        │  302 / + Set-Cookie open_deck_session  │
        │◄───────────────────────────────┤
        │  GET / (with cookie)           │
        └───────────────────────────────►│ panel
```

二维码由网关自身绘制（`/api/qr.svg`）；令牌由 `POST /api/pair` 创建（需要会话）。这样手机无需输入密码即可登录。令牌是一次性的，且不是会话：尝试将其用作 cookie 或 Bearer 令牌会返回 `401`，其 TTL 也不会延长。

---

## 6. 自动发现（UDP 广播）

主机每 3 秒向 UDP 端口 `8761` 发送 JSON 信标（用于 Android 和原生客户端；浏览器不支持 UDP）。

```json
{
  "type": "open-deck-msfs",
  "protocol": 1,
  "name": "FLIGHTSIM-PC",
  "version": "0.1.0",
  "httpPort": 8760,
  "telemetryHz": 30.0,
  "profiles": ["cessna-172-skyhawk", "piper-pa28-archer-ii"],
  "auth": true,
  "ts": 1762340000
}
```

| 字段 | 描述 |
| --- | --- |
| `type` | 始终为 `open-deck-msfs` |
| `protocol` | 信标模式版本 |
| `name` | 主机名 |
| `httpPort` | HTTP/WebSocket 端口 |
| `telemetryHz` | 遥测频率 |
| `profiles` | 可用的配置文件 |
| `auth` | 仅在启用密码时出现（`true`） |
| `ts` | Unix 时间 |

手动检查：

```powershell
python -m msfs_gateway.discovery --listen
```

---

## 7. HTTP 错误

格式：`{"error": "text", "code": "machine_code"}`。

| 状态 | 典型代码 |
| --- | --- |
| `400` | `bad_request`、`bad_json`、`invalid_value`、`id_mismatch`、`missing_password` |
| `401` | `unauthorized`、`bad_password` |
| `404` | `not_found`、`apk_missing` |
| `409` | `build_running`、`sim_rejected`、辅助拒绝 |
| `411` | `length_required` |
| `413` | `too_large` |
| `422` | `invalid_profile`、`invalid_settings`、`qr_too_long` |
| `429` | `rate_limited` |
| `501` | 不支持的 HTTP 方法（标准库） |

---

## 8. 示例

### 登录和获取配置文件

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

### 使用 Bearer 代替 cookie

```bash
TOKEN=$(curl -s -H "Content-Type: application/json" \
  -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/telemetry
```

### 命令

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
     -d '{"key":"power.batteryMaster","value":true}' \
     http://127.0.0.1:8760/api/sim/command
```

### WebSocket（Python，无库）

```python
import json, socket, base64, os
sock = socket.create_connection(("127.0.0.1", 8760))
key = base64.b64encode(os.urandom(16)).decode()
sock.sendall((
    "GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Cookie: open_deck_session=<token>\r\n\r\n"
).encode())
# 然后读取 RFC 6455 帧（参见 msfs_gateway/websocket.py）
```

---

## 9. 兼容性

- 配置文件模式——`schemaVersion: 1`；旧的 `v0` 格式在读取时由 `legacy.py` 适配。
- 信标——`protocol: 1`；客户端必须忽略新的可选字段（`auth`）。
- API 不在 URL 中版本化：破坏性更改仅出现在新的网关主版本中。
