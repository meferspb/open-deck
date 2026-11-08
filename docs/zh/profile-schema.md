# 📄 飞机 JSON 配置文件模式

配置文件是一个单独的文件 `profiles/{id}.json`，以声明式方式描述仪表板。主机会严格校验它（`msfs_gateway/profiles.py`），客户端会“即时”渲染它。

所有尺寸和坐标均为**面板比例（0..1）**，而不是像素：一个配置文件可同时适用于手机和大平板。

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk SP",
  "icao": "C172",
  "revision": 3,
  "description": "…",
  "sim": { "match": { "title": "Cessna Skyhawk*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S · OPEN DECK" },
  "widgets": [ … ]
}
```

---

## 1. 顶层字段

| 字段 | 类型 | 必需 | 描述 |
| --- | --- | --- | --- |
| `schemaVersion` | int | 是 | 始终为 `1` |
| `id` | slug | 是 | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `name` | string | 是 | UI 中显示的名称 |
| `icao` | string | 否 | 2–4 个字符的代码（例如 `C172`） |
| `revision` | int ≥ 1 | 否 | 配置文件版本 |
| `description` | string | 否 | 说明 |
| `sim.match` | object | 否 | 飞机自动识别规则 |
| `panel` | object | 是 | 背景、网格、标题 |
| `widgets` | array 1..64 | 是 | 仪表 |
| `variables` | array 0..64 | 否 | 自定义 LVAR/RPN（见 §6） |

`sim.match.title` 是针对模拟器中飞机名称的 glob（不区分大小写），例如 `"Cessna Skyhawk*"` 会匹配任何涂装和名称变体。`sim.match.atcModel` 是针对 ATC 模型（`C172`）的 glob，在名称未匹配时使用。一旦网关通过 SimConnect 读取到 `TITLE` 和 `ATC MODEL`，客户端就会自动采用该配置文件；从列表中进行的手动选择会一直有效，直到在模拟器中加载不同的飞机。

---

## 2. `panel`

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| `background` | 颜色 `#RGB(A)` / `#RRGGBB(AA)` | 面板背景 |
| `gridSize` | int | 背景网格步长，以“单位”计（可选） |
| `footer` | string | 面板底部标题 |

---

## 3. `widgets[]` — 通用结构

```json
{
  "id": "battery-switch",
  "type": "switch.toggle",
  "label": "Battery",
  "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" },
  "options": { "caption": "BATTERY", "onLabel": "ON", "offLabel": "OFF" },
  "layout": {
    "base": { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
    "phone": { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 }
  }
}
```

| 字段 | 用途 |
| --- | --- |
| `id` | 唯一的控件 slug |
| `type` | 下表中的类型 |
| `label` | aria 标签 / 标题 |
| `bindings` | 与规范遥测键的绑定 |
| `command` | 对于控制类仪表——如何更改变量 |
| `options` | 依类型而定的设置（仪表、标签、色调） |
| `layout` | 几何信息（见 §4） |

### `bindings`

键来自规范注册表 `msfs_gateway/telemetry.py`（扁平，带点）：`power.batteryMaster`、`attitude.pitchDeg`、`engine.rpm`、`speed.iasKt`、`autopilot.headingBugDeg` 等。服务器在校验期间会拒绝未知键。带类型和单位的完整列表见 [telemetry.md](telemetry.md)；仪表类型和选项的说明见 [widgets.md](widgets.md)。

---

## 4. `layout` — 形态因素自适应

```json
"layout": {
  "base":       { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "phone":      { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 },
  "tablet-sm":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "tablet-lg":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 }
}
```

- `base` 是必需的；`phone` / `tablet-sm` / `tablet-lg` 是可选的**覆盖项**，会合并到 `base` 之上（可以只指定不同的字段）。
- `x`、`y`——左上角；`w`、`h`——宽度/高度。全部为 0..1 比例，`w,h > 0`，且矩形不得超出面板边界。
- 值 `x,y,w,h` 也可以是“额外的”——客户端通过 CSS 变量 `--w`/`--h` 从仪表尺寸推导文本大小。

---

## 5. 仪表类型

| `type` | 功能 | `bindings`（必需角色） | `command` | 关键 `options` |
| --- | --- | --- | --- | --- |
| `attitude` | 姿态仪（canvas） | `pitch`、`bank` | — | — |
| `gauge.radial` | 带指针的圆形仪表 | `value` | — | `min`、`max`、`redline`、`unit`、`decimals`、`majorTicks`、`minorTicks`、`zones[]` |
| `readout` | 数字读数 | `value` | — | `caption`、`unit`、`decimals`、`alarm.{below,above}` |
| `switch.toggle` | 拨动开关 | `state` | `{key, action: set|toggle}` | `caption`、`onLabel`、`offLabel` |
| `knob.rotary` | 旋转选择器（滑动/滚轮/箭头） | `value` | `{key, action: set}` | `min`、`max`、`step`、`wrap`、`unit`、`decimals`、`caption` |
| `annunciator` | 信号灯 | `active` | — | `caption`、`tone: ok|warn|danger`、`invert` |
| `vsi` | VSI（canvas） | `value` | — | `limit`（默认 2000 FPM） |
| `altimeter` | 三针高度表 | `value` | — | — |
| `heading` | 带罗盘卡和“bug”的航向指示器 | `heading`（可选 `bug`） | — | — |

### 按类型划分的 `options`

- **`gauge.radial`**：`min`/`max`——仪表范围；`redline`——从 `redline` 到 `max` 的红色弧线；`zones`——用于彩色扇区的 `{from, to, tone}` 数组（`ok`/`warn`/`danger`）；`majorTicks`/`minorTicks`——刻度线；`decimals`——数值中的小数位数；`unit`——单位标签。
- **`readout`**：`caption`——标题；`unit`——单位；`decimals`；`alarm`——高亮阈值 `{below, above}`。
- **`switch.toggle`**：`caption`、`onLabel`/`offLabel`——状态文本；`command.action = "toggle"`——发送不带显式值的切换命令。
- **`knob.rotary`**：`min`/`max`/`step`/`wrap`——范围和步长；`unit`、`decimals`——显示；`wrap = true`——循环范围（例如 0–359°）。
- **`annunciator`**：`tone`——灯的颜色；`invert = true`——在值为假时点亮（例如断电时的“BUS OFF”指示器）。
- **`vsi`**：`limit`——仪表限制，单位为英尺/分钟（默认 2000）；达到限制时指针转到 ±90°。
- **`heading`**：可选的 `bug` 绑定将目标航向（`autopilot.headingBugDeg`）绘制为单独的指针。
- **`attitude`**：无选项；标题来自仪表的 `label`。
- 未知选项不会被拒绝（为了兼容性），但客户端也不会使用它们——请查阅 [widgets.md](widgets.md)。

### `command`

```json
"command": { "key": "power.batteryMaster", "action": "set" }
```

`key` 必须是**可写**变量（具有 `sim_event` 的变量）。`action`：`set`——从 `value` 设置值；`toggle`——切换它。

---

## 6. 自定义变量：LVAR / RPN

默认 SimVar 覆盖 Cessna 172 和大多数简单飞机，但 PMDG、Fenix、FlyByWire 和 iniBuilds 将自己的状态保存在专属变量中。配置文件可以在 `variables` 区块中声明它们，控件可以像引用普通键一样引用生成的键（`custom.*`）。

```json
"variables": [
  {
    "key": "custom.fuelLbs",
    "kind": "number",
    "source": "lvar",
    "name": "PMDG_FUEL_LBS",
    "label": "Fuel (pounds)",
    "unit": "LBS",
    "initial": 1200
  },
  {
    "key": "custom.apuOn",
    "kind": "bool",
    "source": "lvar",
    "name": "PMDG_APU_ON"
  },
  {
    "key": "custom.cabinAlt",
    "kind": "number",
    "source": "rpn",
    "expression": "(A:CABIN ALTITUDE, feet)"
  }
]
```

| 字段 | 描述 |
| --- | --- |
| `key` | 形式为 `custom.fuelLbs` 的键（第一段小写，之后为 camelCase）；不得与内置变量冲突 |
| `kind` | `number` / `bool` / `string` |
| `source` | `lvar`——通过 WASM 桥读取 LVAR；`rpn`——使用 RPN 脚本计算 |
| `name` | LVAR 名称（用于 `source: lvar`），最多 127 个 UTF-8 字节 |
| `expression` | RPN 脚本（用于 `source: rpn`）；响应会被解析为数字/标志 |
| `initial` | mock 模式（无 MSFS）下的初始值 |
| `label`、`unit` | 供编辑器使用的标签 |

控件绑定会根据**内置 + 已声明**的键进行校验：

```json
{ "id": "fuel", "type": "readout", "bindings": { "value": "custom.fuelLbs" } }
```

工作原理：

- 在 **mock 模式**下，提供程序会用 `initial` 替代——面板无需 MSFS 即可动起来；
- 在**真实飞行**中，值由 `WasmBridge`（`read_specs`）通过 MobiFlight/SimBridge WASM 模块读取；总线每秒最多轮询 4 次，并在帧之间缓存它们；
- 如果桥未连接，这些键只是不会出现在帧中——仪表显示“--”（用 0.0 替代会是一种谎言）。

示例配置文件：[`profiles/demo-lvar-panel.json`](../../profiles/demo-lvar-panel.json)。

---

## 7. 完整示例（Cessna 172S）

参见 [`profiles/cessna-172-skyhawk.json`](../../profiles/cessna-172-skyhawk.json)——11 个仪表：姿态仪、速度/高度/转弯（读数）、转速表和燃油（仪表）、电池/航电开关、BUS OFF 灯、襟翼、航向 bug 设置器（旋钮）。第二个示例是 `profiles/piper-pa28-archer-ii.json`（仅 `layout.base`，用于测试回退布局）。

---

## 8. 与 v0 格式的向后兼容性

规范中的原始格式（带像素 `position` 和 `sim_var` 的 `bindings[]`）通过 `msfs_gateway/legacy.py` 适配器支持：加载时会转换为内部格式，坐标会从像素重新计算为面板比例（默认画布为 1280×800，或来自 `layout.canvas`/`target_aspect_ratio`）。通过 `PUT /api/profiles/{id}` 保存会写入内部格式。
