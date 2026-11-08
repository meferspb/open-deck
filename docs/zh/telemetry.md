# 📊 遥测变量目录

> 本文件由 `msfs_gateway/telemetry.py` 生成；请勿手动编辑。
> 更新：`python -m msfs_gateway.docsgen --write`。

注册表是唯一事实来源：面板配置文件将仪表绑定到这些键，网关读取 SimVar 并发送命令。

## 如何阅读表格

- **键**——遥测帧和配置文件 `bindings` 中的变量名。
- **类型**——`number`、`bool` 或 `string`；`bool` 在 JSON 中为 `true/false`，数字为 `float`。
- **读取**——网关从中获取值的 SimVar（对于 `custom.*` 没有来源：它们由 WASM 桥根据配置文件描述读取）。
- **命令**——用于更改变量的 SimConnect 事件；破折号表示“只读”。

## 按组划分的变量

### 电气与电源

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `power.batteryMaster` | bool | — | ELECTRICAL MASTER BATTERY | TOGGLE_MASTER_BATTERY | 电池主开关 |
| `power.avionicsMaster` | bool | — | AVIONICS MASTER SWITCH | TOGGLE_AVIONICS_MASTER | 航电电源 |
| `power.busVolts` | number | V | ELECTRICAL MAIN BUS VOLTAGE | — | 主总线电压 |

### 发动机

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `engine.rpm` | number | RPM | GENERAL ENG RPM:1 | — | 发动机 RPM |
| `engine.fuelFlowGph` | number | GPH | ENG FUEL FLOW GPH:1 | — | 每小时燃油流量 |
| `engine.torquePct` | number | % | TURB ENG MAX TORQUE PERCENT:1 | — | 涡桨发动机扭矩 |
| `engine.ittC` | number | °C | TURB ENG ITT:1 | — | ITT 温度 |
| `engine.propRpm` | number | RPM | PROP RPM:1 | — | 螺旋桨 RPM |
| `engine.n1Pct` | number | % | TURB ENG N1:1 | — | 1 号发动机 N1 |
| `engine.n1Pct2` | number | % | TURB ENG N1:2 | — | 2 号发动机 N1 |

### 空间姿态

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `attitude.pitchDeg` | number | ° | PLANE PITCH DEGREES | — | 俯仰 |
| `attitude.bankDeg` | number | ° | PLANE BANK DEGREES | — | 横滚 |

### 高度

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `altitude.indicatedFt` | number | FT | INDICATED ALTITUDE | — | 指示高度 |

### 速度

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `speed.iasKt` | number | KT | AIRSPEED INDICATED | — | 指示空速 |

### VSI

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `verticalSpeed.fpm` | number | FPM | VERTICAL SPEED | — | 垂直速度 |

### 航向

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `heading.magneticDeg` | number | ° | PLANE HEADING DEGREES MAGNETIC | — | 磁航向 |

### 机翼襟翼

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `flaps.percent` | number | % | TRAILING EDGE FLAPS LEFT PERCENT | — | 襟翼位置 |

### 燃油

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `fuel.leftGal` | number | GAL | FUEL LEFT QUANTITY | — | 左油箱燃油 |
| `fuel.rightGal` | number | GAL | FUEL RIGHT QUANTITY | — | 右油箱燃油 |
| `fuel.totalGal` | number | GAL | — | — | 总燃油 |

### 自动驾驶

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `autopilot.headingBugDeg` | number | ° | AUTOPILOT HEADING LOCK DIR | HEADING_BUG_SET | 目标航向（航向 bug） |
| `autopilot.master` | bool | — | AUTOPILOT MASTER | AP_MASTER | 自动驾驶已接通 |
| `autopilot.approachHold` | bool | — | AUTOPILOT APPROACH HOLD | AP_APR_HOLD | APR 模式——接通命令 |
| `autopilot.approach` | bool | — | AUTOPILOT APPROACH HOLD | — | APR 模式已激活 |

### 飞机状态

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `aircraft.onGround` | bool | — | SIM ON GROUND | — | 飞机在地面 |
| `aircraft.radioAltitudeFt` | number | FT | RADIO HEIGHT | — | 跑道上方无线电高度 |
| `aircraft.title` | string | — | TITLE | — | 模拟器中的飞机标题 |

### 滑行

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `groundSpeed.kt` | number | KT | GPS GROUND SPEED | — | 地速 |

### 导航（ILS）

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `nav.localizer` | number | dots | NAV CDI:1 | — | 航向道偏差 |
| `nav.glideSlope` | number | ° | NAV GLIDE SLOPE ERROR | — | 下滑道偏差 |
| `nav.locFlag` | bool | — | HSI CDI NEEDLE VALID | — | 航向道已捕获 |
| `nav.gsFlag` | bool | — | HSI GSI NEEDLE VALID | — | 下滑道已捕获 |

### 操纵

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `controls.throttlePct` | number | % | GENERAL ENG THROTTLE LEVER POSITION:1 | THROTTLE_SET | 油门杆位置（辅助命令） |
| `controls.rudder` | number | % | RUDDER POSITION | RUDDER_SET | 方向舵（辅助命令） |

### 刹车

| 键 | 类型 | 单位 | 读取（SimVar） | 命令 | 描述 |
| --- | --- | --- | --- | --- | --- |
| `brakes.parking` | bool | — | BRAKE PARKING POSITION | PARKING_BRAKES | 驻车制动 |

## 带命令的变量

这些键可以通过 `POST /api/sim/command` 和 WebSocket `command` 更改。值会被转换为变量类型；对于带参数的事件，会进行缩放（例如百分比 → 0..16383）。

| 键 | 事件 | 参数 | 缩放 |
| --- | --- | --- | --- |
| `power.batteryMaster` | `TOGGLE_MASTER_BATTERY` | 否 | 1.0 |
| `power.avionicsMaster` | `TOGGLE_AVIONICS_MASTER` | 否 | 1.0 |
| `autopilot.headingBugDeg` | `HEADING_BUG_SET` | 是 | 1.0 |
| `autopilot.master` | `AP_MASTER` | 否 | 1.0 |
| `autopilot.approachHold` | `AP_APR_HOLD` | 否 | 1.0 |
| `controls.throttlePct` | `THROTTLE_SET` | 是 | 163.83 |
| `controls.rudder` | `RUDDER_SET` | 是 | 163.83 |
| `brakes.parking` | `PARKING_BRAKES` | 否 | 1.0 |

## 自定义变量 `custom.*`

配置文件可以在 `variables` 区块中声明自己的 LVAR/RPN；键必须以小写段开头（通常是 `custom.`），且不得与内置变量冲突。此类键会在帧中作为普通变量出现。

允许的类型：bool、number、string；来源：lvar、rpn。键格式：`^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$`。

示例：

```json
{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",
  "name": "APU_BLEED", "initial": false }
```

详情见 [profile-schema.md](profile-schema.md)。
