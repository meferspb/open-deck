# 🧩 計器カタログ

> このファイルは `msfs_gateway/profiles.py`（タイプと必須バインディング）および
> Web クライアント（オプション）から生成されます。更新:
> `python -m msfs_gateway.docsgen --write`。

各計器はプロファイルの `widgets[]` 配列の要素です。完全なプロファイル
スキーマは [profile-schema.md](profile-schema.md) にあります。

## 共通構造

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

- `id` — 一意の slug（`[a-z0-9][a-z0-9-]`）。エディターおよびイベントの
  バインディングで使用されます。
- `layout` — パネル比率の座標。`base` は必須で、`phone`、`tablet-sm`、
  `tablet-lg` はオプションです。
- `options` — タイプに依存するオプションのオブジェクト。
- `command` — トグルスイッチとロータリーセレクターに必須（以下を参照）。

## 計器タイプ

| タイプ | 計器 | 必須バインディング | `command` | 主なオプション |
| --- | --- | --- | --- | --- |
| `attitude` | 姿勢指示器 | `pitch`、`bank` | — | — |
| `gauge.radial` | 円形ゲージ | `value` | — | `min`*、`max`*、`redline`、`zones`、`majorTicks`、`minorTicks`、`decimals`、`unit` |
| `readout` | デジタル表示 | `value` | — | `unit`、`decimals`、`caption`、`alarm` |
| `switch.toggle` | トグルスイッチ | `state` | 必須 | `caption`、`onLabel`、`offLabel` |
| `knob.rotary` | ロータリーセレクター / エンコーダー | `value` | 必須 | `min`、`max`、`step`、`wrap`、`unit`、`decimals`、`caption` |
| `annunciator` | アナンシエーターライト | `active` | — | `caption`、`tone`、`invert` |
| `vsi` | VSI | `value` | — | `limit` |
| `altimeter` | 高度計 | `value` | — | — |
| `heading` | 方位指示器 | `heading` | — | — |

オプションの横の `*` は必須であることを意味します。その他のオプションには
適切なデフォルト値があり、外観の設定に使用されます。

## タイプの説明

### `attitude` — 姿勢指示器

姿勢指示器: `pitch`/`bank` によるピッチとバンク、バンクスケール、ゼロマーク。
追加のオプションはありません。

最小例:

```json
{ "id": "attitude", "type": "attitude", "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `gauge.radial` — 円形ゲージ

円形針ゲージ: `min..max` 範囲内の `value`、目盛り、赤ゾーン、キャプション、
単位。

| オプション | 意味 | 必須 |
| --- | --- | --- |
| `min` | ゲージの最小値 | はい |
| `max` | ゲージの最大値 | はい |
| `redline` | 赤ゾーン（min..max 範囲内） | いいえ |
| `zones` | 追加の色付きゾーン | いいえ |
| `majorTicks` | 主目盛りの数 | いいえ |
| `minorTicks` | 副目盛りの数 | いいえ |
| `decimals` | 小数点以下の桁数 | いいえ |
| `unit` | 単位ラベル | いいえ |

最小例:

```json
{ "id": "speed", "type": "gauge.radial", "bindings": { "value": "speed.iasKt" }, "options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `readout` — デジタル表示

デジタル表示: `value` を指定された桁数、単位、キャプションで整形します。
アラームしきい値を強調表示できます。

| オプション | 意味 | 必須 |
| --- | --- | --- |
| `unit` | 単位 | いいえ |
| `decimals` | 小数点以下の桁数 | いいえ |
| `caption` | 値の上のキャプション | いいえ |
| `alarm` | アラーム強調しきい値 | いいえ |

最小例:

```json
{ "id": "alt", "type": "readout", "bindings": { "value": "altitude.indicatedFt" }, "options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `switch.toggle` — トグルスイッチ

トグルスイッチ: 真偽値の `state` を表示し、`command.key` コマンドを送信します。
`set` アクションは反対の値を送信し、`toggle` はトグルイベントを送信します。

| オプション | 意味 | 必須 |
| --- | --- | --- |
| `caption` | トグルのキャプション | いいえ |
| `onLabel` | オン状態のテキスト | いいえ |
| `offLabel` | オフ状態のテキスト | いいえ |

最小例:

```json
{ "id": "battery", "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" }, "command": { "key": "power.batteryMaster", "action": "set" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `knob.rotary` — ロータリーセレクター / エンコーダー

ロータリーセレクター/エンコーダー: 回転とスワイプにより、`min..max` 範囲内で
`value` を `step` ずつ変更し、新しい値でコマンドを送信します。

| オプション | 意味 | 必須 |
| --- | --- | --- |
| `min` | 最小値 | いいえ |
| `max` | 最大値 | いいえ |
| `step` | 変更ステップ | いいえ |
| `wrap` | 値をループ | いいえ |
| `unit` | 単位 | いいえ |
| `decimals` | 小数点以下の桁数 | いいえ |
| `caption` | キャプション | いいえ |

最小例:

```json
{ "id": "hdg", "type": "knob.rotary", "bindings": { "value": "autopilot.headingBugDeg" }, "command": { "key": "autopilot.headingBugDeg", "action": "set" }, "options": { "min": 0, "max": 359, "step": 1, "wrap": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `annunciator` — アナンシエーターライト

アナンシエーターライト: `active` が true のときに点灯します。キャプション、
トーン、反転はオプションで設定します。

| オプション | 意味 | 必須 |
| --- | --- | --- |
| `caption` | ランプのキャプション | いいえ |
| `tone` | 発光色/トーン | いいえ |
| `invert` | ロジックを反転 | いいえ |

最小例:

```json
{ "id": "bus", "type": "annunciator", "bindings": { "active": "power.busVolts" }, "options": { "caption": "BUS OFF", "invert": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `vsi` — VSI

VSI: 垂直速度針で、ゲージは `limit` によって制限され、ラベルは fpm です。

| オプション | 意味 | 必須 |
| --- | --- | --- |
| `limit` | ゲージ限界、fpm | いいえ |

最小例:

```json
{ "id": "vsi", "type": "vsi", "bindings": { "value": "verticalSpeed.fpm" }, "options": { "limit": 2000 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `altimeter` — 高度計

`value` に基づく三針高度計（数百/数千/数万フィート）。

最小例:

```json
{ "id": "altimeter", "type": "altimeter", "bindings": { "value": "altitude.indicatedFt" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `heading` — 方位指示器

回転するコンパスカードと「バグ」を備えた方位指示器。値は度単位の磁方位です。

最小例:

```json
{ "id": "heading", "type": "heading", "bindings": { "heading": "heading.magneticDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

## トグルスイッチとロータリーセレクターからのコマンド

`command` ブロックは、ゲートウェイに何を送信するかを記述します:

| フィールド | 意味 |
| --- | --- |
| `key` | 「コマンド受け付け」フラグを持つ変数（テレメトリカタログを参照） |
| `action` | `set` — 新しい値を送信。`toggle` — トグルイベント |
| `value` | `set` の場合: `true/false`/数値。デフォルトでは現在の値の反対 |

トグルスイッチの例:

```json
{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" } }
```

## 検証

- タイプは上の一覧に含まれている必要があります。エディターは未知のタイプを
  保存しません。
- 必須の `bindings` ロールは既存のテレメトリキーを参照しなければなりません。
- `layout.base` とオーバーライドは `0..1` 内の矩形でなければなりません
  （プロファイルスキーマを参照）。
