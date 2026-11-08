# 📚 Open Deck for MSFS 文档

**Languages:** [English](../README.md) · [Русский](../ru/README.md) · [Deutsch](../de/README.md) · [中文](README.md) · [Español](../es/README.md) · [日本語](../ja/README.md)


<img src="../pic1.jpg" alt="Open Deck for MSFS" width="180" />

这里汇集了项目的所有文档。请先从仓库根目录的 README 开始——它提供了整体概览和快速入门；本索引可帮助你找到具体细节。

## 从哪里开始

| 如果你是…… | 按顺序阅读 |
| --- | --- |
| 想“为自己”搭建面板的飞行员 | [README](../../README_ZH.md) → [service.md](service.md) |
| 想了解工作原理的人 | [architecture.md](architecture.md) → [protocol.md](protocol.md) |
| 正在编写客户端或集成 | [protocol.md](protocol.md) → [telemetry.md](telemetry.md) |
| 正在修改代码 | [development.md](development.md) → [architecture.md](architecture.md) |
| 正在制作飞机配置文件 | [profile-schema.md](profile-schema.md) → [widgets.md](widgets.md) |
| 正在构建安装程序/APK | [packaging.md](packaging.md) → [android.md](android.md) |
| 正在审查安全性 | [security.md](security.md) |

## 文档

| 文档 | 内容 | 读者 |
| --- | --- | --- |
| [service.md](service.md) | 完整的服务说明：用途、运行模型、遥测、配置文件、客户端、网络、身份验证、辅助、API、安装、诊断、安全、许可证 | 所有人 |
| [architecture.md](architecture.md) | 内部设计：模块、数据流、WASM 桥、关键决策和 MVP 边界 | 开发者 |
| [protocol.md](protocol.md) | HTTP REST、WebSocket、密码和 QR 登录、自动发现、错误码和示例 | 集成者 |
| [telemetry.md](telemetry.md) | 所有变量的目录：类型、单位、SimVar、事件、`custom.*`——由代码生成 | 客户端和配置文件开发者 |
| [widgets.md](widgets.md) | 仪表目录：必需的绑定、`command`、选项、JSON 示例——由代码生成 | 配置文件作者 |
| [profile-schema.md](profile-schema.md) | JSON 配置文件模式：字段、布局、校验、兼容性、完整示例 | 配置文件作者 |
| [development.md](development.md) | 如何修改代码：模块地图、添加变量/仪表/配置文件/提供程序/页面、测试、发布 | 贡献者 |
| [pricing.md](pricing.md) | 针对 air-gapped 场景的“连接服务 vs 本地替代方案”对比 | 选择技术栈的人 |
| [android.md](android.md) | Android 客户端：构建、架构、登录、调试 | Android 开发者 |
| [packaging.md](packaging.md) | 安装程序：内容、构建、快捷方式、卸载、静默参数 | 发布工程师 |
| [contributing.md](contributing.md) | 如何参与：风格、测试、配置文件、PR | 贡献者 |
| [security.md](security.md) | 威胁模型、受保护的内容、如何报告漏洞 | 所有人 |
| [changelog.md](changelog.md) | 版本历史 | 所有人 |

## 截图

`docs/screenshots/`——手机和平板上的面板、六连表、编辑器、登录页面和辅助。用于 README 和服务说明中。

## 保持文档最新

有两个文档是**由代码生成**的，并由测试检查：

```powershell
python -m msfs_gateway.docsgen --check   # telemetry.md 和 widgets.md
python -m msfs_gateway.docsgen --write   # 修改注册表后更新
```

如果你修改了 `telemetry.py`、`profiles.py` 或 Web 仪表——请更新文档并运行 `pwsh -File scripts/check.ps1`。

## 如何编写文档

- 用英语编写，段落简短，并附上 JSON/命令示例。
- 链接使用相对路径，以便在 GitHub 和本地都能正常工作。
- 不要重复模式定义：配置文件——放在 `profile-schema.md`，变量——放在 `telemetry.md`，仪表——放在 `widgets.md`，网络——放在 `protocol.md`。
- 如果更改了行为，请更新 README/服务说明和 `CHANGELOG.md`。
