# 变更日志

格式：[Keep a Changelog](https://keepachangelog.com/ru/1.1.0/)，
版本号：[SemVer](https://semver.org/lang/ru/)。

## [Unreleased]

### 变更

- 全面重塑为 **Open Deck for MSFS**：产品名称、Web 界面、Android 应用（`com.opendeck.msfs`）、可执行文件、安装程序、文档和飞机配置文件。
- 徽标和应用图标由 `docs/pic1.jpg` 生成；文件 `web/img/open-deck-mark.jpg`、`web/favicon.ico`、Android drawable 和 `packaging/windows/open-deck.ico`。

### 新增

- **捐赠**链接——[https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)——位于 Web 面板、编辑器、登录屏幕、辅助、Android 界面、README 和文档中。
- 注明作者 **Viktor Krasnikov** 和仓库 [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)。

### 修复

- SimConnect：`SIMCONNECT_RECV_SIMOBJECT_DATA` 的字段顺序已调整为与 `SimConnect.h` 一致（`dwFlags`/`dwEntryNumber`/`dwOutOf`/`dwDefineCount`）——否则实时数值遥测不会更新。
- SimConnect：命令在调度线程中执行；重连时重置 event id；失败的 `AddToDataDefinition` 不再使其他数据项的索引发生偏移。
- WASM/Client Data：超时后的断路器以及 LVAR 区块 ≤ 56 个元素，以免缺失的 WASM 模块阻塞遥测线程。
- QR 令牌不再作为常规会话接受，也不再延长 TTL。
- 为浏览器 POST/PUT 和 WebSocket 添加了 `Origin` 检查，并按本地名称/IP 检查 `Host`（关闭 DNS 重绑定）；为通过自己的 DNS 名称访问添加了 `--allow-host`。
- 关闭了 `login.js` 中通过 `next` 中的反斜杠进行的开放重定向。
- 请求体错误不再使 keep-alive 连接处于不同步状态；添加了并发连接限制。
- `pair`/`token` 令牌在请求日志中会被脱敏。
- 辅助：高度/速度/航向缺失时不再用零替代；如果 APR 未接通，AP 会回滚；连接丢失时回路会关闭；如果命令未发送，`stop` 会报告错误。
- 遥测：SimConnect 定义中不存在或已过时的内置 SimVar 会以 `null` 返回（UI 显示 `--`）。
- SimVar 精度：`TURB ENG MAX TORQUE PERCENT:1`（当前扭矩占最大值的百分比）和 `RADIO HEIGHT` 取代了离地高度。
- QR 对话框在打开时和 TTL 到期时重新创建一次性令牌。
- 编辑器在切换配置文件时清除历史记录，并警告未保存的更改。
- Android 构建器：`extraGradleArgs` 允许列表、类型检查、禁止驱动器相对 `outputDir`、安全的 `appName`。
- Android：手动输入时再次接受带端口的完整 URL。
- SimConnect：重连可以承受临时配置的 `OSError`；线程停止更加稳健。
- 自动发现信标在溢出时发送不带配置文件列表的内容，而不是完全跳过。
- 限制了内存限制器的增长；REST 命令获得了基于 IP 的速率限制。
- 关闭密码时，控制台会警告局域网中的开放访问。

## [0.1.0] — 2026-11-01

首个公开版本。

### 新增

- **着陆和滑行辅助**：地面速度/航向保持、ILS 进近的 ARM/DISARM/TOGA、60–15 英尺自动 retard、接地时断开 AP；页面 `/assist.html` 和 API `/api/assist*`。
- **密码登录**（至少 6 个字符）：`config/auth.json` 中的 PBKDF2 哈希、`HttpOnly` cookie 中 12 小时的会话、Bearer 令牌、从手机进行的一次性 QR 登录、尝试次数限制和暴力破解防护。
- Python 网关（仅标准库）：单端口上的 HTTP + WebSocket（RFC 6455）、UDP 自动发现、带 JSON 模式和校验的飞机配置文件。
- 遥测提供程序：`simconnect`（ctypes、字符串数据项 `TITLE` 和 `ATC MODEL`）、`mock` 以及自动回退 `auto`。
- 通过 SimConnect Client Data Area（MobiFlight/SimBridge）的 LVAR/RPN WASM 桥：请求通道、超时、重连、通过 RPN 写入 LVAR。
- 无框架 Web 客户端：姿态仪、圆形仪表、读数、拨动开关、旋转选择器、垂直速度表、高度表、航向指示器；三种形态因素。
- 面板编辑器：拖放、撤销/重做、网格、在形态因素之间复制布局、保存到主机。
- 按名称和 ATC 模型自动识别飞机；手动选择会锁定，直到模拟器中的飞机变化。
- 手机快速连接：二维码（基于标准库的自有生成器）和网络地址列表。
- Android 客户端：WebView 面板、UDP 发现、完整性检查。
- 发行版中的 Android APK 构建器：应用设置（名称、package id、版本、网关地址）、从 `/android.html` 页面构建以及 CLI `--build-apk`。
- Windows 安装程序（NSIS，按用户安装，无需管理员权限），内含预构建 APK 和 Android 源代码。
- 驾驶舱舒适性：三级面板亮度、kiosk 模式。
- 配置文件：Cessna 172S、Cessna 172 Six-Pack、Daher TBM 930、Airbus A320、Piper PA-28、LVAR 演示。

### 修复

- 缓慢或卡住的客户端不再停止遥测广播：每个连接都有自己的队列（8 帧）和发送线程，旧帧会被丢弃而不是阻塞总线。
- 协议违规时 WebSocket 以代码 1002 关闭（未标记、分片和过大的控制帧）。
- 网关停止不再等待卡住的客户端：关闭帧带超时发送，套接字无论如何都会关闭。
- POST/PUT 始终读取请求体——启动 APK 构建后 keep-alive 连接不再中断。
- APK 构建器：即使 Gradle 卡住且不打印任何内容，超时监视器也会触发；应用名称中禁止控制字符。
- Android：快速重启主机搜索时的竞态不再关闭新的 UDP 接收器。
- 编辑器：保存失败时修订号回滚，重复点击不会启动并行保存。
- 静态文件：带 NUL 字节的路径返回 404 而不是异常，HEAD 不重复响应体，客户端断开连接不再用堆栈跟踪污染日志。

- SimConnect：如果用户的 `SimConnect.cfg` 指向不存在的通道（`0x80004005` 错误的常见原因），网关会自动通过 TCP `127.0.0.1:19999` 重试连接——这是 MSFS 2020/2024 监听的端口；地址和端口可通过 `--simconnect-host` / `--simconnect-port` 配置。

### 文档

- 完整文档索引 `docs/README.md`；开发者指南 `docs/development.md`（代码地图、添加变量/仪表/配置文件/提供程序/页面、测试、发布）。
- `docs/telemetry.md` 和 `docs/widgets.md` 目录由代码生成（`python -m msfs_gateway.docsgen --write`）；测试和 CI 检查其最新性和相对链接。
- 完全重写 `docs/protocol.md`：访问、密码和 QR、所有 endpoint、WebSocket、辅助、APK 构建、错误码和示例。
- 更新 `docs/architecture.md`、`docs/service.md`（术语表、支持）、`docs/profile-schema.md`、README、`android/README.md`、`packaging/windows/README.md`；文档包含在安装程序中。

### 安全

- 启动时和浏览器中对关键界面文件进行 SHA-256 检查。
- CSP `default-src 'self'`、禁止外部资源、Android WebView 中的导航允许列表。
