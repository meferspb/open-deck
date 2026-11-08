# 🧩 仪表目录

> 本文件由 `msfs_gateway/profiles.py`（类型和必需绑定）和 Web 客户端（选项）生成。更新：
> `python -m msfs_gateway.docsgen --write`。

每个仪表都是配置文件 `widgets[]` 数组中的一个元素。完整的配置文件模式见 [profile-schema.md](profile-schema.md)。

## 通用结构

```json
{
  "id": "attitude-main",
  "type": "attitude",
  "label": "Attitude indicator",
  "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
  "layout": {
    "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
    "phone": { "x": 0.03, "y": 0.02, "w": 0.94, "h": 0.3 }
  },
  "options": { "unit": "FT", "decimals": 0 }
}
```

- `id`——唯一的 slug（`[a-z0-9][a-z0-9-]`），在编辑器中使用并用于绑定事件。
- `layout`——面板比例中的坐标；`base` 是必需的，`phone`、`tablet-sm`、`tablet-lg` 是可选的。
- `options`——依类型而定的可选对象。
- `command`——拨动开关和旋转选择器必需（见下文）。

## 仪表类型

| 类型 | 仪表 | 必需绑定 | `command` | 主要选项 |
| --- | --- | --- | --- | --- |
| `attitude` | 姿态仪 | `pitch`、`bank` | — | — |
| `gauge.radial` | 圆形仪表 | `value` | — | `min`*、`max`*、`redline`、`zones`、`majorTicks`、`minorTicks`、`decimals`、`unit` |
| `readout` | 数字读数 | `value` | — | `unit`、`decimals`、`caption`、`alarm` |
| `switch.toggle` | 拨动开关 | `state` | 必需 | `caption`、`onLabel`、`offLabel` |
| `knob.rotary` | 旋转选择器 / 编码器 | `value` | 必需 | `min`、`max`、`step`、`wrap`、`unit`、`decimals`、`caption` |
| `annunciator` | 信号灯 | `active` | — | `caption`、`tone`、`invert` |
| `vsi` | VSI | `value` | — | `limit` |
| `altimeter` | 高度表 | `value` | — | — |
| `heading` | 航向指示器 | `heading` | — | — |

选项旁的 `*` 表示该选项是必需的。其他选项具有合理的默认值，用于配置外观。

## 类型说明

### `attitude` — 姿态仪

姿态仪：通过 `pitch`/`bank` 显示俯仰和横滚、横滚刻度以及零位标记。没有其他选项。

最小示例：

```json
{ "id": "attitude", "type": "attitude", "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `gauge.radial` — 圆形仪表

圆形指针仪表：`value` 在 `min..max` 范围内、刻度线、红色区域、标题和单位。

| 选项 | 含义 | 必需 |
| --- | --- | --- |
| `min` | 仪表最小值 | 是 |
| `max` | 仪表最大值 | 是 |
| `redline` | 红色区域（在 min..max 范围内） | 否 |
| `zones` | 额外的彩色区域 | 否 |
| `majorTicks` | 主刻度线数量 | 否 |
| `minorTicks` | 次刻度线数量 | 否 |
| `decimals` | 小数点后的位数 | 否 |
| `unit` | 单位标签 | 否 |

最小示例：

```json
{ "id": "speed", "type": "gauge.radial", "bindings": { "value": "speed.iasKt" }, "options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `readout` — 数字读数

数字读数：使用给定的小数位数、单位和标题格式化 `value`；可以高亮警报阈值。

| 选项 | 含义 | 必需 |
| --- | --- | --- |
| `unit` | 单位 | 否 |
| `decimals` | 小数点后的位数 | 否 |
| `caption` | 值上方的标题 | 否 |
| `alarm` | 警报高亮阈值 | 否 |

最小示例：

```json
{ "id": "alt", "type": "readout", "bindings": { "value": "altitude.indicatedFt" }, "options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `switch.toggle` — 拨动开关

拨动开关：显示布尔 `state` 并发送 `command.key` 命令；`set` 操作发送相反的值，`toggle` 发送切换事件。

| 选项 | 含义 | 必需 |
| --- | --- | --- |
| `caption` | 开关标题 | 否 |
| `onLabel` | 开启状态的文本 | 否 |
| `offLabel` | 关闭状态的文本 | 否 |

最小示例：

```json
{ "id": "battery", "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" }, "command": { "key": "power.batteryMaster", "action": "set" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `knob.rotary` — 旋转选择器 / 编码器

旋转选择器/编码器：旋转和滑动会在 `min..max` 范围内按 `step` 改变 `value`，并发送带新值的命令。

| 选项 | 含义 | 必需 |
| --- | --- | --- |
| `min` | 最小值 | 否 |
| `max` | 最大值 | 否 |
| `step` | 变化步长 | 否 |
| `wrap` | 循环值 | 否 |
| `unit` | 单位 | 否 |
| `decimals` | 小数点后的位数 | 否 |
| `caption` | 标题 | 否 |

最小示例：

```json
{ "id": "hdg", "type": "knob.rotary", "bindings": { "value": "autopilot.headingBugDeg" }, "command": { "key": "autopilot.headingBugDeg", "action": "set" }, "options": { "min": 0, "max": 359, "step": 1, "wrap": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `annunciator` — 信号灯

信号灯：当 `active` 为 true 时点亮；标题、色调和反转通过选项配置。

| 选项 | 含义 | 必需 |
| --- | --- | --- |
| `caption` | 灯标题 | 否 |
| `tone` | 发光颜色/色调 | 否 |
| `invert` | 反转逻辑 | 否 |

最小示例：

```json
{ "id": "bus", "type": "annunciator", "bindings": { "active": "power.busVolts" }, "options": { "caption": "BUS OFF", "invert": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `vsi` — VSI

VSI：垂直速度指针，仪表受 `limit` 限制，标签以 fpm 为单位。

| 选项 | 含义 | 必需 |
| --- | --- | --- |
| `limit` | 仪表限制，fpm | 否 |

最小示例：

```json
{ "id": "vsi", "type": "vsi", "bindings": { "value": "verticalSpeed.fpm" }, "options": { "limit": 2000 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `altimeter` — 高度表

基于 `value` 的三针高度表（百英尺/千英尺/万英尺）。

最小示例：

```json
{ "id": "altimeter", "type": "altimeter", "bindings": { "value": "altitude.indicatedFt" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `heading` — 航向指示器

带旋转罗盘卡和“bug”的航向指示器；值为以度表示的磁航向。

最小示例：

```json
{ "id": "heading", "type": "heading", "bindings": { "heading": "heading.magneticDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

## 来自拨动开关和旋转选择器的命令

`command` 区块描述要发送到网关的内容：

| 字段 | 含义 |
| --- | --- |
| `key` | 带“接受命令”标志的变量（参见遥测目录） |
| `action` | `set`——发送新值；`toggle`——切换事件 |
| `value` | 对于 `set`：`true/false`/数字；默认是当前值的相反值 |

拨动开关示例：

```json
{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" } }
```

## 校验

- 类型必须在上面的列表中；编辑器不会保存未知类型。
- 必需的 `bindings` 角色必须引用现有遥测键。
- `layout.base` 和覆盖项必须是 `0..1` 范围内的矩形（参见配置文件模式）。
