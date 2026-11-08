# 🛠️ 开发与内部设计

面向修改代码的开发者：什么内容位于何处，如何添加变量、仪表、配置文件、提供程序或页面，以及如何测试和发布。用户文档见 [service.md](service.md)，协议见 [protocol.md](protocol.md)。

## 1. 要求

- Windows 10/11（网关使用 `ctypes` 调用 SimConnect；其余部分跨平台）。
- Python **3.11+**；没有第三方依赖——仅使用标准库。
- Node.js **20+**——用于 Web 客户端测试（客户端本身不需要构建）。
- JDK 17 + Android SDK + Gradle 8.x——仅用于构建 APK。
- PyInstaller 和 NSIS——仅用于安装程序。

## 2. 代码地图

```
msfs_gateway/
  app.py            依赖装配、生命周期、CLI 模式
  settings.py       CLI 参数、路径、默认值
  telemetry.py      变量注册表（键、类型、SimVar、事件）
  hub.py            总线：帧、订阅、命令、飞机自动识别
  http_api.py       HTTP：静态文件、REST、WebSocket 升级、授权
  websocket.py      RFC 6455：帧、ping/pong、关闭、发送队列
  auth.py           密码、PBKDF2、会话、QR 令牌、尝试次数限制
  assist.py         滑行和着陆辅助（10 Hz）
  profiles.py       校验、存储、原子保存配置文件
  legacy.py         旧 v0 配置文件格式适配器
  integrity.py      关键文件的 SHA-256 清单
  discovery.py      自动发现 UDP 信标
  qr.py             基于标准库的 QR 生成器（SVG）
  android_build.py  设置、工具查找、Gradle 启动
  docsgen.py        生成 docs/telemetry.md 和 docs/widgets.md
  sim/              提供程序：mock、simconnect、client_data、wasm_bridge
web/                面板、编辑器、登录、辅助（原生 ES 模块）
profiles/           飞机 JSON 配置文件
android/            Kotlin 客户端（WebView + UDP 发现）
packaging/windows/  PyInstaller + NSIS
scripts/            build-installer.ps1、check.ps1、verify_qr.py
tests/              unittest（Python）和 node:test（JS）
docs/               本文档及其他文档
```

## 3. 如何添加遥测变量

1. 打开 `msfs_gateway/telemetry.py`，向 `_VARIABLES` 添加 `Variable(...)`：键、类型、标签、`sim_var`/`sim_unit`，以及（如有需要）`sim_event`、`sim_event_param`、`sim_event_scale`。
2. 对照 MSFS SDK 文档验证 SimVar 名称（大小写和单位很重要）。
3. 更新目录：`python -m msfs_gateway.docsgen --write`。
4. 运行 `python -m unittest tests.test_telemetry` 和完整测试套件。
5. 如果该变量是一个控件——请确保事件确实会改变状态（`bool` 比较使用当前值）。

## 4. 如何添加仪表

1. 创建 `web/js/widgets/my-widget.js`：一个包含 `update(state)` 和 `destroy()` 的类（参见 `base.js` 和相邻仪表）。渲染——canvas 或 DOM。
2. 在 `web/js/widgets/registry.js` 中注册类型。
3. 将类型添加到 `WIDGET_TYPES`，将必需角色添加到 `REQUIRED_BINDINGS`，并在需要时向 `msfs_gateway/profiles.py` 添加选项检查。
4. 在 `msfs_gateway/docsgen.py` 中描述仪表（`WIDGET_ORDER`、`WIDGET_TITLES`、`WIDGET_DESCRIPTIONS`、`WIDGET_OPTIONS`、示例），并运行 `python -m msfs_gateway.docsgen --write`。
5. 在三种形态因素（手机/小平板/大平板）和编辑器中检查；在 `tests/web/` 中添加几何测试。

## 5. 如何添加飞机配置文件

1. 从 `profiles/` 复制一个相似的配置文件，修改 `id`、`name`、`icao`、`sim.match`（针对 `TITLE`/`ATC MODEL` 的 glob）。
2. 检查校验：`python -m unittest tests.test_profiles`。
3. 构建 `base` 布局 + 各形态因素的差异；确保矩形不超出 `0..1`。
4. 在编辑器 `/editor.html` 中以及真实飞机上检查（如果 MSFS 可用）。
5. 将配置文件添加到 README（列表）和 CHANGELOG。

## 6. 如何添加遥测提供程序

1. 继承 `SimProvider`（`sim/base.py`）并实现 `start`、`stop`、`read`、`apply_command`、`connected`；如有需要——实现 `select_aircraft`、`aircraft_title`、`atc_model`。
2. 在 `sim/__init__.py:create_sim()` 中注册该选项，并将值添加到 `SIM_CHOICES`（`settings.py`）。
3. 线程安全：`read()` 和 `apply_command()` 可能从不同线程调用——请使用锁。
4. 使用模拟传输添加测试（参见 `tests/test_mock_sim.py`）。

## 7. 如何添加端点

1. 在 `_handle_api_get/post/put`（`http_api.py`）中处理路径。
2. 决定它是公开的还是受会话保护的：公开——仅放在 `PUBLIC_API_PATHS` 中；其他所有内容会自动受保护。
3. 通过 `_send_json`/`ApiError` 响应；错误携带机器可读的 `code`。
4. 在 `docs/protocol.md`（表格 + 示例）和 `docs/service.md`（API 部分）中记录该端点。
5. 在 `tests/` 中添加测试（单元 + 如需要则添加 HTTP 集成测试）。

## 8. 如何添加页面

1. 将 HTML 放在 `web/`，JS 放在 `web/js/`，样式放在 `web/css/`。
2. 页面默认**受保护**（`/login.html` 及其文件除外）；没有会话时服务器会返回 `302` 跳转到登录页。
3. 将链接添加到面板标题栏（`web/index.html`），然后重建清单：`python -m msfs_gateway.integrity --write`。
4. 在手机上（`?device=phone`）和 kiosk 模式下检查。

## 9. 测试与检查

```powershell
pwsh -File scripts/check.ps1       # ruff + format + 250 Python + 35 JS
python -m unittest discover -s tests
node --test "tests/web/*.test.mjs"
python -m msfs_gateway.docsgen --check
python -m msfs_gateway.integrity
```

测试策略：

- **纯逻辑**（校验、配置文件、QR、辅助控制器、身份验证）——无需网络或 MSFS 的单元测试。
- **HTTP/WebSocket**——在 `127.0.0.1:0` 上启动 `GatewayApplication.start_background()`，并使用 `http.client`/原始套接字。
- **SimConnect/WASM**——模拟 DLL/传输；实时飞行需手动验证。
- **Web**——使用 `node:test` 测试纯函数（布局、`isConnectionStale`）。

## 10. 文档

- `docs/telemetry.md` 和 `docs/widgets.md` **由代码生成**；手动编辑会被覆盖。请修改 `docsgen.py` 并运行 `--write`。
- 其他文档为手动维护；行为变化时，请更新 `service.md`、`protocol.md`、`profile-schema.md` 和 `CHANGELOG.md`。
- 最新性检查已内置于 `scripts/check.ps1`（docsgen --check）。
- 索引——[docs/README.md](README.md)。

## 11. 构建与发布

1. 更新版本（`msfs_gateway/__init__.py`、`config/android-build.json`、`packaging/windows/README.md`）。
2. `python -m msfs_gateway.integrity --write`（如果关键文件已更改）。
3. `pwsh -File scripts/build-installer.ps1 -Version <x.y.z> -NsisPath <NSIS>`。
4. 在干净机器上检查安装/卸载和 `--set-password`。
5. 构建 APK（`android/gradle assembleDebug`）并将其放入 `android/dist`。
6. 更新 `CHANGELOG.md`，提交并打标签 `v<x.y.z>`。

## 12. 约定

- Python：仅使用标准库，使用 `ruff format` 格式化，行宽 100。
- JS：ES 模块，无 CDN 或构建步骤；使用 `node --check` 和 `node:test`。
- Kotlin：仅使用 SDK 和标准库，不使用 AndroidX。
- 注释和文档——使用英语；标识符——使用英语。
- 除非绝对必要，不要添加外部依赖：项目旨在支持 air-gapped 安装。
