# 参与开发

感谢你愿意提供帮助！项目很小且有意保持简单：无依赖的 Python、无打包器的原生 JS、基于纯 SDK/Kotlin 的 Android。

## 开发者快速入门

```powershell
# 1. 克隆仓库
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# 2. 以演示模式启动网关（不需要 MSFS）
python -m msfs_gateway --sim mock

# 3. 打开 http://127.0.0.1:8760/
```

要求：**Python 3.11+**。客户端测试需要 **Node.js 20+**。构建 Android APK 需要 **JDK 17**、**Android SDK** 和 **Gradle 8.x**。

## PR 前的检查

```powershell
pwsh -File scripts/check.ps1
```

脚本会运行：

- 针对 Python 的 `ruff check` 和 `ruff format --check`；
- `python -m unittest discover -s tests`（252 个测试）；
- 如果安装了 Node.js，则运行 `node --test "tests/web/*.test.mjs"`（29 个测试）。

安装 lint 工具：`python -m pip install ruff`。

## 代码风格

- **Python**：PEP 8，使用 `ruff format` 格式化，行宽 100。仅使用标准库——不添加新依赖。
- **JS**：ES 模块，无框架和外部 CDN。语法检查——`node --check`，测试——`node --test`。
- **Kotlin**：仅使用 Android SDK 和 Kotlin 标准库，不使用 AndroidX 和第三方库。
- 注释和文档——使用俄语；代码中的名称——使用英语。
- 所有用户可见字符串都必须**离线**工作：不得使用外部字体、图片和 API。

## 可以改进的地方

参见 [`README.md`](../../README_ZH.md) 和 [`docs/architecture.md`](architecture.md)。不错的方向：

- 新的飞机配置文件（`profiles/*.json`）——欢迎提交；
- 新的仪表类型（`web/js/widgets/`，注册表 `registry.js`）及其在 `msfs_gateway/profiles.py` 中的注册（`WIDGET_TYPES`、`REQUIRED_BINDINGS`）；
- 测试：纯逻辑（仪表几何、配置文件、协议）——优先；
- 文档：代码与 `docs/` 之间的差异视为 bug。

## 飞机配置文件

1. 从 `profiles/` 复制现有配置文件并修改 `id`、`name`、`sim.match`。
2. 检查校验：`python -c "from msfs_gateway.profiles import ProfileStore; ..."`——或直接启动网关：损坏的配置文件会被跳过并给出警告。
3. 从 `GET /api/telemetry/variables` 获取绑定（编辑器会以列表形式显示它们）。
4. 在 PR 中附上说明，指出你是在哪个插件上测试的。

## 提交与 PR

- 原子提交，使用祈使句消息：`add A320 profile`、`fix QR mask`。
- 在 PR 中——说明修改了什么、为什么以及如何验证（测试/截图）。
- 对于界面更改，请在 `docs/screenshots/` 中附上截图。

## 贡献许可

提交 PR 即表示你同意你的贡献在项目许可证（[LICENSE](../../LICENSE)）下分发。不要移除或替换作者支持区块和完整性检查——这是许可证条件。
