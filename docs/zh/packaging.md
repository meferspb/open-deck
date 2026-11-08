# Windows 安装程序

单个文件 `OpenDeck-Setup-<版本>.exe`：双击 → “下一步” → 完成。无需管理员权限，不需要 Python 和互联网。

## 安装期间会发生什么

| | |
|---|---|
| 目录 | `%LOCALAPPDATA%\OpenDeck`（位于用户配置文件中，无需 UAC） |
| 内容 | `OpenDeck.exe`——内置 Python 3.13 和标准库的网关 |
| | `web/`——Web 客户端（面板和编辑器），`profiles/`——飞机配置文件 |
| | `config/donation.json`——作者信息，`integrity/`——完整性清单 |
| | `android/`——Android 源代码，以及构建后的就绪 APK（`android/dist/OpenDeck-Android-<版本>.apk`），`config/android-build.json`——APK 构建设置 |
| | `docs/`——完整文档（服务、协议、变量、仪表、配置文件模式） |
| 快捷方式 | 桌面、开始菜单（启动、在浏览器中打开面板、构建 Android APK、“设置密码”、卸载） |
| 卸载 | “程序和功能”或“卸载”快捷方式 |

数据位于 `.exe` 旁边，因此配置文件和信息可以在不重新安装的情况下编辑（修改受保护文件后需要重建清单，参见根目录 README）。

## 构建（在开发机器上，需要一次互联网连接）

要求：

- Python 3.11+ 和 PyInstaller：`python -m pip install pyinstaller`
- NSIS 3.x：`makensis.exe` 在 `PATH` 中，或 `NSIS_HOME`，或 `-NsisPath`

```powershell
# 从仓库根目录
pwsh -File scripts/build-installer.ps1 -Version 0.1.0 -NsisPath "C:\Program Files (x86)\NSIS"
```

脚本的步骤：重建完整性清单 → 运行测试 → 构建 `build/pyinstaller/dist/OpenDeck`（PyInstaller，onedir）→ 将 `web/`、`profiles/`、`config/`、`integrity/` 放在旁边 → 验证 `.exe` 可以启动（`--help`）→ 将安装程序编译到 `dist/OpenDeck-Setup-<版本>.exe`。

标志：`-SkipTests`、`-NsisPath <文件夹>`、`-Version 0.2.0`。

脚本还会验证安装程序已构建，并打印最终路径和大小。完整步骤列表——见 `scripts/build-installer.ps1` 文件开头。

密码登录：“设置密码”快捷方式会运行 `OpenDeck.exe --set-password` 并在控制台中询问密码；哈希保存在 `.exe` 旁边的 `config/auth.json` 中。删除该文件会再次开放无登录访问。

## 发布前

1. 检查 `config/donation.json`：作者 Viktor Krasnikov，捐赠链接——`https://taps.uz/open_deck_fs`。
2. 重建清单：`python -m msfs_gateway.integrity --write`（构建脚本会自行执行此操作，但再检查一次也无妨）。
3. 在干净机器上运行安装程序：无管理员安装、启动、从同一网络中的手机访问面板、卸载。

## 静默安装 / 部署

```bat
OpenDeck-Setup-0.1.0.exe /S /D=C:\Tools\OpenDeck
Uninstall.exe /S
```

`/D=` 必须放在最后且不带引号（NSIS 限制）。

## 限制

- 安装程序未签名：SmartScreen 可能会警告“未知发布者”——“更多信息” → “仍要运行”。发布需要代码签名证书（EV/OV）。
- 不会添加防火墙规则（需要管理员权限）。首次启动时 Windows 会询问网络访问——请允许专用网络，否则客户端无法连接。
- 按用户安装：应用仅对当前用户可见。
- 注册表/快捷方式创建在 `HKCU` 中——在具有严格策略的机器上（AppLocker、禁止写入用户配置文件），安装可能会被阻止；此时请使用便携方式：解压 `build/pyinstaller/dist/OpenDeck` 目录并从那里运行 `.exe`。
