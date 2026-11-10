# ✈️ Open Deck for MSFS

**Languages:** [English](README.md) · [Русский](README_RU.md) · [Deutsch](README_DE.md) · [中文](README_ZH.md) · [Español](README_ES.md) · [日本語](README_JA.md)


<img src="docs/pic1.jpg" alt="Open Deck for MSFS" width="220" />

**在你的手机和平板上显示 MSFS 2020/2024 仪表板——通过本地网络，无需互联网。**

Windows 网关通过 SimConnect（包括通过 WASM 模块读取 LVAR/RPN）从 Microsoft Flight Simulator 读取遥测数据，并通过 HTTP + WebSocket 将其提供给 Web 客户端和 Android 应用。面板由飞机 JSON 配置文件描述，并针对三种形态因素进行渲染。

项目完全自包含：**不依赖任何外部 CDN、字体或服务**——一切都能在隔离网络和无法访问互联网的机器上运行。

| | |
| --- | --- |
| 版本 | 0.1.0 |
| 测试 | 252 个 Python + 41 个 Node.js |
| 主机平台 | Windows 10/11（Python 3.11+ 或安装程序） |
| 客户端 | 浏览器（任何现代浏览器）、Android 8+ |
| 作者 | Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) |
| 捐赠 | [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) |
| 许可证 | [GNU AGPL-3.0](LICENSE) — 自由软件，附带强制的作者支持区块（第 7 条） |

## 截图

| 手机 | 大平板 |
| --- | --- |
| ![手机上的面板](docs/screenshots/phone.png) | ![平板上的面板](docs/screenshots/tablet-lg.png) |

| 经典 C172 六连表 | 面板编辑器 |
| --- | --- |
| ![六连表](docs/screenshots/sixpack-phone.png) | ![编辑器](docs/screenshots/editor.png) |

![从手机进行密码登录](docs/screenshots/login.png)

![着陆与滑行辅助](docs/screenshots/assist.png)

## 功能

### 网关

- **单一端口**同时提供静态文件、REST 和 WebSocket——只需一条防火墙规则；仅使用 Python 标准库，无需 `pip install`。
- **可替换的遥测源**：
  - `simconnect` — 通过 `ctypes` 使用原生 SimConnect；
  - `mock` — 无需模拟器的程序化“飞行”（演示和测试）；
  - `auto` — 使用 SimConnect，失败时回退到 mock。
- **飞机自动识别**：配置文件声明 `sim.match.title` 和 `atcModel`，网关读取 `TITLE`/`ATC MODEL` 并自动切换面板。
- **通过 WASM 读取 LVAR/RPN**（MobiFlight/SimBridge）：客户端数据区、带超时的同步通道、通过 RPN 写入 LVAR。
- **主机自动发现**：通过 UDP 信标（供原生客户端使用）、内置 HTTP 服务器、JSON API，以及对配置文件和命令的严格校验。

### 配置文件与仪表

- **6 个配置文件**：Cessna 172S、Cessna 172 Classic Six-Pack、Daher TBM 930、Airbus A320、Piper PA-28-181、LVAR 演示。
- **仪表**：姿态仪、圆形仪表、数字读数、拨动开关、旋转选择器（手势/滚轮）、信号灯、VSI、三针高度表、带“bug”的航向指示器。
- 以面板比例进行布局 + 覆盖项 `layout.phone`、`layout.tablet-sm`、`layout.tablet-lg`；模式和校验——参见 [`docs/zh/profile-schema.md`](docs/zh/profile-schema.md)。

### 客户端

- **Web 客户端**基于原生 ES 模块：平滑动画（rAF）、平滑处理、手势、命令控件、自动重连。
- **三种形态因素**，根据屏幕宽度自动选择。
- **驾驶舱舒适性**：面板亮度 100/72/45 %（按键 `B`）和无 UI 的 kiosk 模式（`F`，按 `Esc` 退出）。
- **手机扫码连接**：面板页面显示主机地址的二维码和网络地址列表。
- **Android 客户端**：WebView 面板、UDP 主机发现、完整性检查、带手动地址输入的连接界面。

### 安全

- **密码登录**（至少 6 个字符）：PBKDF2 哈希、会话保存在 `HttpOnly` cookie 中、原生客户端使用 Bearer 令牌、尝试次数限制、从手机扫码登录而无需输入密码。一次性 QR 令牌只能通过 `/?pair=` 使用，不能作为常规会话使用。
- **同源和 Host 保护**：带外部 `Origin` 的浏览器 POST/PUT 和 WebSocket 请求，以及带未知 `Host` 的请求都会被拒绝（`403`）。这可以阻止 CSRF、跨站 WebSocket 劫持和 DNS 重绑定；没有 `Origin` 的客户端（Android、curl）仍可正常工作。
- 只有登录页面、健康/完整性检查以及作者支持区块可公开访问——其他所有内容（配置文件、遥测、命令、APK 构建）均受保护。

### 着陆与滑行辅助

- **滑行**：保持目标速度（3–25 kt）和航向——网关计算油门和方向舵；“STOP”会将油门归零并拉起驻车制动。
- **着陆**：ARM 会启用 AP 和 APR，在 60–15 ft 时辅助会平滑减小油门，接地时断开自动驾驶；TOGA——复飞。
- 页面 `/assist.html`（面板标题栏中的“Assist”按钮）；在手机上也可用。辅助是一个辅助回路；飞行仍由飞行员控制。

### 工具

- **面板编辑器** `/editor.html`：拖放、调整大小、1 % 网格吸附、撤销/重做（`Ctrl+Z` / `Ctrl+Y`）、在形态因素之间复制布局、将配置文件保存到主机。
- **发行版内置 Android APK 构建器**：页面 `/android.html` 可以修改应用名称、包 id、版本和网关地址，构建 APK 并提供下载；还有 CLI `--build-apk`。
- **Windows 安装程序**（NSIS，按用户安装，无需管理员权限），内含预构建 APK 和 Android 源代码。

### 许可证与完整性

- 作者支持区块**不可移除**；关键文件的 SHA-256 会在主机启动时和浏览器中校验，不匹配时 UI 会被阻止。

## 安装（Windows，无需 Python）

从发布页面下载 `OpenDeck-Setup-<version>.exe`，运行并点击“下一步”——不需要管理员权限，也不需要 Python 或互联网。安装到 `%LOCALAPPDATA%\OpenDeck`，并创建快捷方式和“程序和功能”中的条目。

1. 启动 **Open Deck for MSFS**——会打开一个控制台，显示面板地址。
2. 在防火墙提示中允许应用访问专用网络。
3. 在此 PC 上打开面板，或在手机上输入打印的地址，或从面板（手机按钮）扫描二维码。

安装程序构建详情——参见 [`docs/zh/packaging.md`](docs/zh/packaging.md)。

## 密码登录

可以通过以下方式之一启用登录：

```powershell
# 将密码（PBKDF2 哈希）保存到 config/auth.json
OpenDeck.exe --set-password            # 在控制台中提示输入密码
OpenDeck.exe --set-password "my-password"

# 或仅用于本次运行
OpenDeck.exe --password "my-password"
```

最少 **6 个字符**。文件 `config/auth.json` 仅保存哈希；删除它即可再次允许无密码访问。在开始菜单中，安装程序会创建“设置密码”快捷方式。详情——参见[服务说明](docs/zh/service.md)。

已连接的客户端：

- 浏览器——页面 `/login.html`，然后是面板（cookie 有效期为 12 小时）；
- 手机——扫描面板上的二维码：一次性令牌无需密码即可登录（有效期 10 分钟）；
- Android——面板会自行显示登录界面；会话保存在 WebView 中。

## 从源代码运行

需要 **Python 3.11+**；Node.js——仅用于客户端测试。

```powershell
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# 无模拟器的演示模式：http://127.0.0.1:8760/
python -m msfs_gateway --sim mock

# 真实飞行：SimConnect，失败时回退到 mock
python -m msfs_gateway --sim auto

# 显式 DLL 路径和 60 Hz
python -m msfs_gateway --sim simconnect --simconnect-dll C:\SDK\SimConnect.dll --telemetry-hz 60
```

常用参数：

| 参数 | 默认值 | 用途 |
| --- | --- | --- |
| `--host` | `0.0.0.0` | 监听地址 |
| `--allow-host NAME` | — | Host 头的额外 DNS 名称（可重复） |
| `--port` | `8760` | HTTP 和 WebSocket 端口 |
| `--sim` | `auto` | `auto` / `mock` / `simconnect` |
| `--telemetry-hz` | `30` | 广播频率，1..60 Hz |
| `--simconnect-host` / `--simconnect-port` | `127.0.0.1` / `19999` | SimConnect 地址（包括远程模拟器） |
| `--profile-dir` | `profiles/` | JSON 配置文件目录 |
| `--password` / `--set-password` | — | 本次运行的密码 / 保存哈希并退出 |
| `--auth-file` / `--no-auth` | `config/auth.json` | 哈希文件 / 禁用登录 |
| `--no-wasm` | — | 禁用 WASM 桥 |
| `--no-discovery` | — | 禁用 UDP 自动发现 |
| `--build-apk [CONFIG]` | — | 构建 Android APK 并退出 |

## 从发行版构建 Android APK

已安装的应用包含 Android 源代码（`android/`）；构建好的 APK 会输出到 `android/dist/OpenDeck-Android-<version>.apk`，开始菜单中还有“构建 Android APK”（`http://127.0.0.1:8760/android.html`）。

在页面中可以设置应用名称、包 id、版本和默认网关地址；“Build APK”按钮会在同一台计算机上运行 `gradle assembleDebug`。需要 **JDK 17**、**Android SDK** 和 **Gradle 8.x**（可以在页面上指定路径，或通过 `JAVA_HOME` / `ANDROID_HOME` / `PATH` 中的 `gradle` 设置）。在发行版中，预构建的 APK 已位于 `android/dist`。

```powershell
OpenDeck.exe --build-apk                        # 使用 config/android-build.json 中的设置
OpenDeck.exe --build-apk C:\path\settings.json
```

## 文档

完整索引见 [docs/zh/README.md](docs/zh/README.md)。主要文档：

- [服务说明：用途、API、身份验证、辅助、操作](docs/zh/service.md)
- [架构与职责](docs/zh/architecture.md)
- [网络协议：REST、WebSocket、登录、QR、自动发现](docs/zh/protocol.md)
- [遥测变量目录](docs/zh/telemetry.md) *（由代码生成）*
- [仪表和选项目录](docs/zh/widgets.md) *（由代码生成）*
- [飞机配置文件模式](docs/zh/profile-schema.md)
- [Android 客户端：构建、登录、调试](docs/zh/android.md)
- [构建安装程序](docs/zh/packaging.md)
- [连接服务成本与本地替代方案对比](docs/zh/pricing.md)
- [变更日志](docs/zh/changelog.md)

## 仓库结构

```
msfs_gateway/            # Python 网关（标准库）
  sim/                   # 提供程序：mock、simconnect、client_data、wasm_bridge
  qr.py                  # 内置 QR 生成器（SVG）
  assist.py              # 着陆与滑行辅助
  android_build.py       # 从发行版构建 APK
  http_api.py, hub.py, profiles.py, integrity.py, discovery.py, websocket.py
web/                     # Web 客户端和编辑器（原生 JS，无构建步骤）
profiles/                # 飞机 JSON 配置文件
android/                 # Android 客户端（Kotlin，无 AndroidX）
packaging/               # PyInstaller + NSIS：Windows 安装程序
scripts/                 # build-installer.ps1、check.ps1、verify_qr.py
tests/                   # unittest（Python）和 node:test（JS）
docs/                    # 架构、协议、模式、截图
config/                  # 作者信息、APK 构建设置
integrity/               # 关键文件的 SHA-256 清单
```

## 测试

```powershell
python -m unittest discover -s tests        # 252 个测试
node --test "tests/web/*.test.mjs"          # 29 个测试
python -m ruff check msfs_gateway tests scripts
```

一次性运行所有检查：

```powershell
pwsh -File scripts/check.ps1
```

覆盖范围：遥测和配置文件、WebSocket（RFC 6455）、总线与命令、mock 提供程序、WASM/Client Data、QR（结构 + 参考矩阵）、APK 构建器、完整性、仪表几何和布局。

## 开发

参见 [`CONTRIBUTING.md`](docs/zh/contributing.md)：风格、测试、如何添加配置文件或仪表。安全问题——参见 [`SECURITY.md`](docs/zh/security.md)。

## 路线图

1. **使用 MSFS + MobiFlight/SimBridge 实机运行 WASM 桥**（逻辑和仿真已由测试覆盖）。
2. **APK 发布签名**：在构建器设置中配置 keystore/alias。
3. **mDNS（Bonjour）**作为 UDP 信标的替代方案。
4. **编辑器**：对齐参考线、多选。
5. **Android**：原生 Compose 渲染、kiosk 模式的前台服务。
6. **遥测录制/回放**，用于演示和性能分析。

## 安全

项目面向**可信的本地网络**设计：无 TLS 的 HTTP、可选身份验证，以及未签名的 UDP 信标。不要将网关暴露到互联网。更多内容——参见 [`SECURITY.md`](docs/zh/security.md)。

## 支持 / 捐赠

- **捐赠：** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
- **作者：** Viktor Krasnikov
- **仓库：** [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)

## 许可证

本项目在 **GNU Affero 通用公共许可证 v3.0（AGPL-3.0）** 下分发，并附带符合**第 7 条**的附加条款。

* 你可以自由使用、研究、修改和分发此代码，前提是保留相同的许可证（AGPL-3.0），并公开任何修改的源代码（包括根据第 13 条在服务器上/通过网络使用）。
* **强制条件（第 7(b) 条和第 5(d) 条）：** 在所有分支、构建和修改版本中，**严禁**移除、隐藏或更改程序用户界面和文档中对原作者（**Viktor Krasnikov**，[https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)）的提及，以及对开发者支持（捐赠）页面的有效链接：[捐赠 — https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。

附加条款的详细法律文本见文件 [COPYING.ADDITIONAL](./COPYING.ADDITIONAL)。基础许可证的完整文本见文件 [LICENSE](./LICENSE)。
