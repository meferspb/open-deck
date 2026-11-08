# 📊 テレメトリ変数カタログ

> このファイルは `msfs_gateway/telemetry.py` から生成されます。手動で編集しないで
> ください。更新: `python -m msfs_gateway.docsgen --write`。

レジストリは唯一の真実の源です: パネルプロファイルは計器をこれらのキーに
バインドし、ゲートウェイは SimVar を読み取り、コマンドを送信します。

## 表の読み方

- **Key** — テレメトリフレームおよびプロファイルの `bindings` 内の変数名。
- **Type** — `number`、`bool`、または `string`。`bool` は JSON で `true/false`
  として、数値は `float` として到着します。
- **Read** — ゲートウェイが値を取得する SimVar（`custom.*` にはソースが
  ありません: プロファイルの記述に従って WASM ブリッジが読み取ります）。
- **Command** — 変数の変更に使用される SimConnect イベント。ダッシュは
  「読み取り専用」を意味します。

## グループ別の変数

### 電気と電源

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `power.batteryMaster` | bool | — | ELECTRICAL MASTER BATTERY | TOGGLE_MASTER_BATTERY | バッテリーマスタースイッチ |
| `power.avionicsMaster` | bool | — | AVIONICS MASTER SWITCH | TOGGLE_AVIONICS_MASTER | アビオニクス電源 |
| `power.busVolts` | number | V | ELECTRICAL MAIN BUS VOLTAGE | — | メインバス電圧 |

### エンジン

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `engine.rpm` | number | RPM | GENERAL ENG RPM:1 | — | エンジン RPM |
| `engine.fuelFlowGph` | number | GPH | ENG FUEL FLOW GPH:1 | — | 時間あたりの燃料流量 |
| `engine.torquePct` | number | % | TURB ENG MAX TORQUE PERCENT:1 | — | ターボプロップエンジントルク |
| `engine.ittC` | number | °C | TURB ENG ITT:1 | — | ITT 温度 |
| `engine.propRpm` | number | RPM | PROP RPM:1 | — | プロペラ RPM |
| `engine.n1Pct` | number | % | TURB ENG N1:1 | — | エンジン #1 N1 |
| `engine.n1Pct2` | number | % | TURB ENG N1:2 | — | エンジン #2 N1 |

### 空間姿勢

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `attitude.pitchDeg` | number | ° | PLANE PITCH DEGREES | — | ピッチ |
| `attitude.bankDeg` | number | ° | PLANE BANK DEGREES | — | バンク |

### 高度

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `altitude.indicatedFt` | number | FT | INDICATED ALTITUDE | — | 指示高度 |

### 速度

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `speed.iasKt` | number | KT | AIRSPEED INDICATED | — | 指示対気速度 |

### VSI

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `verticalSpeed.fpm` | number | FPM | VERTICAL SPEED | — | 垂直速度 |

### 方位

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `heading.magneticDeg` | number | ° | PLANE HEADING DEGREES MAGNETIC | — | 磁方位 |

### 主翼フラップ

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `flaps.percent` | number | % | TRAILING EDGE FLAPS LEFT PERCENT | — | フラップ位置 |

### 燃料

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `fuel.leftGal` | number | GAL | FUEL LEFT QUANTITY | — | 左タンク燃料 |
| `fuel.rightGal` | number | GAL | FUEL RIGHT QUANTITY | — | 右タンク燃料 |
| `fuel.totalGal` | number | GAL | — | — | 総燃料 |

### オートパイロット

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `autopilot.headingBugDeg` | number | ° | AUTOPILOT HEADING LOCK DIR | HEADING_BUG_SET | 目標方位（ヘディングバグ） |
| `autopilot.master` | bool | — | AUTOPILOT MASTER | AP_MASTER | オートパイロット作動 |
| `autopilot.approachHold` | bool | — | AUTOPILOT APPROACH HOLD | AP_APR_HOLD | APR モード — 作動コマンド |
| `autopilot.approach` | bool | — | AUTOPILOT APPROACH HOLD | — | APR モードアクティブ |

### 機体状態

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `aircraft.onGround` | bool | — | SIM ON GROUND | — | 機体が地上にある |
| `aircraft.radioAltitudeFt` | number | FT | RADIO HEIGHT | — | 滑走路からの電波高度 |
| `aircraft.title` | string | — | TITLE | — | シミュレーター内の機体タイトル |

### タキシー

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `groundSpeed.kt` | number | KT | GPS GROUND SPEED | — | 対地速度 |

### ナビゲーション（ILS）

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `nav.localizer` | number | dots | NAV CDI:1 | — | ローカライザー偏差 |
| `nav.glideSlope` | number | ° | NAV GLIDE SLOPE ERROR | — | グライドスロープ偏差 |
| `nav.locFlag` | bool | — | HSI CDI NEEDLE VALID | — | ローカライザー捕捉 |
| `nav.gsFlag` | bool | — | HSI GSI NEEDLE VALID | — | グライドスロープ捕捉 |

### 操作

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `controls.throttlePct` | number | % | GENERAL ENG THROTTLE LEVER POSITION:1 | THROTTLE_SET | スロットルレバー位置（アシストコマンド） |
| `controls.rudder` | number | % | RUDDER POSITION | RUDDER_SET | ラダー（アシストコマンド） |

### ブレーキ

| Key | Type | Unit | Read (SimVar) | Command | 説明 |
| --- | --- | --- | --- | --- | --- |
| `brakes.parking` | bool | — | BRAKE PARKING POSITION | PARKING_BRAKES | パーキングブレーキ |

## コマンド付きの変数

これらのキーは `POST /api/sim/command` および WebSocket の `command` を通じて
変更できます。値は変数の型に変換されます。パラメーター付きイベントの場合、
スケーリングされます（例: パーセント → 0..16383）。

| Key | イベント | パラメーター | スケール |
| --- | --- | --- | --- |
| `power.batteryMaster` | `TOGGLE_MASTER_BATTERY` | いいえ | 1.0 |
| `power.avionicsMaster` | `TOGGLE_AVIONICS_MASTER` | いいえ | 1.0 |
| `autopilot.headingBugDeg` | `HEADING_BUG_SET` | はい | 1.0 |
| `autopilot.master` | `AP_MASTER` | いいえ | 1.0 |
| `autopilot.approachHold` | `AP_APR_HOLD` | いいえ | 1.0 |
| `controls.throttlePct` | `THROTTLE_SET` | はい | 163.83 |
| `controls.rudder` | `RUDDER_SET` | はい | 163.83 |
| `brakes.parking` | `PARKING_BRAKES` | いいえ | 1.0 |

## カスタム変数 `custom.*`

プロファイルは `variables` ブロックで独自の LVAR/RPN を宣言できます。キーは
小文字のセグメントで始まる必要があり（通常は `custom.`）、組み込み変数と衝突
してはなりません。そのようなキーは通常の変数としてフレームに現れます。

許可される種類: bool、number、string。ソース: lvar、rpn。キー形式: `^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$`。

例:

```json
{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",
  "name": "APU_BLEED", "initial": false }
```

詳細は
[profile-schema.md](profile-schema.md#6-カスタム変数-lvar--rpn) にあります。
