# 📄 機体 JSON プロファイルスキーマ

プロファイルは、計器パネルを宣言的に記述する単一のファイル
`profiles/{id}.json` です。ホストはそれを厳格に検証し
（`msfs_gateway/profiles.py`）、クライアントはそれを「オンザフライ」で
レンダリングします。

すべてのサイズと座標は**パネル比率（0..1）**であり、ピクセルではありません:
1 つのプロファイルがスマートフォンでも大型タブレットでも動作します。

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

## 1. トップレベルフィールド

| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `schemaVersion` | int | はい | 常に `1` |
| `id` | slug | はい | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `name` | string | はい | UI 用の名前 |
| `icao` | string | いいえ | 2〜4 文字のコード（例: `C172`） |
| `revision` | int ≥ 1 | いいえ | プロファイルのバージョン |
| `description` | string | いいえ | 説明 |
| `sim.match` | object | いいえ | 機体の自動検出ルール |
| `panel` | object | はい | 背景、グリッド、キャプション |
| `widgets` | array 1..64 | はい | 計器 |
| `variables` | array 0..64 | いいえ | カスタム LVAR/RPN（§6 を参照） |

`sim.match.title` はシミュレーター内の機体名に対する glob（大文字小文字を
区別しない）です。たとえば `"Cessna Skyhawk*"` は任意のリバリーと名前の
バリエーションを拾います。`sim.match.atcModel` は ATC モデル（`C172`）に
対する glob で、名前が一致しなかった場合に使用されます。ゲートウェイが
SimConnect を通じて `TITLE` と `ATC MODEL` を読み取るとすぐに、クライアントは
プロファイルを自動的に選択します。一覧からの手動選択は、シミュレーターで
別の機体が読み込まれるまで有効のままです。

---

## 2. `panel`

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `background` | color `#RGB(A)` / `#RRGGBB(AA)` | パネル背景 |
| `gridSize` | int | 背景グリッドのステップ（「単位」、任意） |
| `footer` | string | パネル下部のキャプション |

---

## 3. `widgets[]` — 共通構造

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

| フィールド | 目的 |
| --- | --- |
| `id` | 一意のウィジェット slug |
| `type` | 下の表のタイプ |
| `label` | aria ラベル / キャプション |
| `bindings` | 正規テレメトリキーへのバインディング |
| `command` | 制御計器用 — 変数の変更方法 |
| `options` | タイプ依存の設定（ゲージ、ラベル、トーン） |
| `layout` | ジオメトリ（§4 を参照） |

### `bindings`

キーは正規レジストリ `msfs_gateway/telemetry.py` から取得します（フラットで
ドット区切り）: `power.batteryMaster`、`attitude.pitchDeg`、`engine.rpm`、
`speed.iasKt`、`autopilot.headingBugDeg` など。サーバーは検証中に未知のキーを
拒否します。型と単位を含む完全な一覧は [telemetry.md](telemetry.md) に、
計器タイプとオプションの説明は [widgets.md](widgets.md) にあります。

---

## 4. `layout` — フォームファクタ適応

```json
"layout": {
  "base":       { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "phone":      { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 },
  "tablet-sm":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "tablet-lg":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 }
}
```

- `base` は必須です。`phone` / `tablet-sm` / `tablet-lg` はオプションの
  **オーバーライド**で、`base` の上にマージされます（異なるフィールドのみを
  指定できます）。
- `x`、`y` — 左上隅。`w`、`h` — 幅/高さ。すべて 0..1 の比率で、`w,h > 0`、
  矩形はパネルの境界を超えてはなりません。
- 値 `x,y,w,h` は「追加」でもかまいません — クライアントは CSS 変数
  `--w`/`--h` を通じて計器の寸法からテキストサイズを導出します。

---

## 5. 計器タイプ

| `type` | 機能 | `bindings`（必須ロール） | `command` | 主要な `options` |
| --- | --- | --- | --- | --- |
| `attitude` | 姿勢指示器（canvas） | `pitch`、`bank` | — | — |
| `gauge.radial` | 針付き円形ゲージ | `value` | — | `min`、`max`、`redline`、`unit`、`decimals`、`majorTicks`、`minorTicks`、`zones[]` |
| `readout` | デジタル表示 | `value` | — | `caption`、`unit`、`decimals`、`alarm.{below,above}` |
| `switch.toggle` | トグルスイッチ | `state` | `{key, action: set|toggle}` | `caption`、`onLabel`、`offLabel` |
| `knob.rotary` | ロータリーセレクター（スワイプ/ホイール/矢印） | `value` | `{key, action: set}` | `min`、`max`、`step`、`wrap`、`unit`、`decimals`、`caption` |
| `annunciator` | アナンシエーターライト | `active` | — | `caption`、`tone: ok|warn|danger`、`invert` |
| `vsi` | VSI（canvas） | `value` | — | `limit`（デフォルト 2000 FPM） |
| `altimeter` | 三針高度計 | `value` | — | — |
| `heading` | コンパスカードと「バグ」付き方位指示器 | `heading`（オプションで `bug`） | — | — |

### タイプ別の `options`

- **`gauge.radial`**: `min`/`max` — ゲージ範囲。`redline` — `redline` から
  `max` までの赤い弧。`zones` — 色付きセクター用の `{from, to, tone}` の配列
  （`ok`/`warn`/`danger`）。`majorTicks`/`minorTicks` — 目盛り。
  `decimals` — 数値の桁数。`unit` — 単位ラベル。
- **`readout`**: `caption` — 見出し。`unit` — 単位。`decimals`。`alarm` —
  強調しきい値 `{below, above}`。
- **`switch.toggle`**: `caption`、`onLabel`/`offLabel` — 状態テキスト。
  `command.action = "toggle"` — 明示的な値なしでトグルを送信。
- **`knob.rotary`**: `min`/`max`/`step`/`wrap` — 範囲とステップ。`unit`、
  `decimals` — 表示。`wrap = true` — 範囲をループ（例: 0〜359°）。
- **`annunciator`**: `tone` — ランプの色。`invert = true` — false 値で点灯
  （電源オフ時の「BUS OFF」インジケーター）。
- **`vsi`**: `limit` — フィート/分単位のゲージ限界（デフォルト 2000）。限界に
  達すると針は ±90° になります。
- **`heading`**: オプションの `bug` バインディングは、目標方位
  （`autopilot.headingBugDeg`）を別のポインターとして描画します。
- **`attitude`**: オプションなし。キャプションは計器の `label` から取得します。
- 未知のオプションは（互換性のために）拒否されませんが、クライアントでも
  使用されません — [widgets.md](widgets.md) で確認してください。

### `command`

```json
"command": { "key": "power.batteryMaster", "action": "set" }
```

`key` は**書き込み可能**な変数（`sim_event` を持つもの）でなければなりません。
`action`: `set` — `value` から値を設定。`toggle` — トグル。

---

## 6. カスタム変数: LVAR / RPN

デフォルトの SimVar は Cessna 172 とほとんどのシンプルな機体をカバーしますが、
PMDG、Fenix、FlyByWire、iniBuilds は状態を独自の変数に保持します。プロファイル
は `variables` ブロックでそれらを宣言でき、ウィジェットは結果のキー
（`custom.*`）を通常のキーと同様に参照できます。

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

| フィールド | 説明 |
| --- | --- |
| `key` | `custom.fuelLbs` 形式のキー（最初のセグメントは小文字、その後 camelCase）。組み込み変数と衝突してはなりません |
| `kind` | `number` / `bool` / `string` |
| `source` | `lvar` — WASM ブリッジ経由で LVAR を読み取る。`rpn` — RPN スクリプトで計算 |
| `name` | LVAR 名（`source: lvar` 用）、最大 127 UTF-8 バイト |
| `expression` | RPN スクリプト（`source: rpn` 用）。応答は数値/フラグに解析されます |
| `initial` | mock モード（MSFS なし）の初期値 |
| `label`、`unit` | エディター用のラベル |

ウィジェットのバインディングは**組み込み + 宣言済み**のキーに対して検証され
ます:

```json
{ "id": "fuel", "type": "readout", "bindings": { "value": "custom.fuelLbs" } }
```

仕組み:

- **mock モード**ではプロバイダーが `initial` を代入します — MSFS なしで
  パネルが動作します。
- **実際のフライト**では、値は MobiFlight/SimBridge WASM モジュールを通じて
  `WasmBridge`（`read_specs`）によって読み取られます。バスは最大 1 秒あたり
  4 回ポーリングし、フレーム間でキャッシュします。
- ブリッジが接続されていない場合、キーはフレームから単に欠落します — 計器は
  「--」を表示します（0.0 を代入するのは嘘になります）。

プロファイルの例:
[`profiles/demo-lvar-panel.json`](../../profiles/demo-lvar-panel.json)。

---

## 7. 完全な例（Cessna 172S）

[`profiles/cessna-172-skyhawk.json`](../../profiles/cessna-172-skyhawk.json) を
参照してください — 11 個の計器: 姿勢指示器、速度/高度/旋回（表示）、
タコメーターと燃料（ゲージ）、バッテリー/アビオニクススイッチ、BUS OFF
ランプ、フラップ、ヘディングバグ設定器（ノブ）。2 番目の例は
`profiles/piper-pa28-archer-ii.json` です（`layout.base` のみで、フォールバック
レイアウトをテスト）。

---

## 8. v0 形式との後方互換性

仕様の元の形式（ピクセルの `position` と `sim_var` を持つ `bindings[]`）は、
`msfs_gateway/legacy.py` アダプターを通じてサポートされます: 読み込み時に
内部形式に変換され、座標はピクセルからパネル比率に再計算されます（デフォルト
キャンバスは 1280×800、または `layout.canvas`/`target_aspect_ratio` から）。
`PUT /api/profiles/{id}` を通じた保存は内部形式を書き込みます。
