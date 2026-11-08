# 🔌 Open Deck for MSFS ネットワークプロトコル

すべての通信は単一の TCP ポート（デフォルト `8760`）を経由します:

- **HTTP 静的ファイル** — `web/` からのファイル（パネル、エディター、ログイン、
  アシスト）。
- **REST API** — プロファイル、テレメトリ、コマンド、アシスト、APK ビルド。
- **WebSocket `/ws`** — テレメトリストリームとコマンド確認応答。

## 0. 規約

- ベース URL: `http://<host>:<port>`。すべてのパスは相対です。
- JSON は UTF-8、`Content-Type: application/json; charset=utf-8`。
- API 応答: `Cache-Control: no-store`。静的ファイル: `no-cache`。
- **CORS は意図的に無効化されています**: API は同一オリジンのクライアント向け
  に設計されており、サードパーティのページは応答を読み取れません。
- **同一オリジン保護**: ブラウザが `Origin` を送信する場合、そのホストと
  実効ポートは `Host` と一致しなければなりません。そうでなければ `POST`/`PUT`
  および WebSocket リクエストは `403` `origin_not_allowed` を受け取ります。
  `Origin` のないクライアント（Android、curl）は許可されます。
- **Host 許可リスト**: `Host` は localhost、マシン名、FQDN、ローカル IP、または
  `--allow-host` の名前を指さなければなりません。そうでなければ
  `403 host_not_allowed`。これは DNS リバインディングへの保護です。
- リクエストボディの上限 — **2 MiB**。未知の `Content-Length` → `411`。
- パスワード（有効な場合）とセッションはセクション 2 で説明します。
- 自動検出ビーコンのプロトコルバージョンは `protocol: 1` です。

---

## 1. アクセス: 公開とセッション下

パスワードが設定されていない場合、すべてが利用可能です。設定されている場合、
セッションなしで開かれるのはログインページ、そのファイル、ライセンスで必要
なサービスデータのみです:

| パス | アクセス | 目的 |
| --- | --- | --- |
| `/login.html`、`/js/login.js`、`/css/*`、`/img/*` | 公開 | ログインページとスタイル |
| `/api/auth/status`、`/api/auth/login`、`/api/auth/logout` | 公開 | ログイン/ログアウト |
| `/api/health` | 公開 | 「これはゲートウェイか?」、バージョン、パスワードフラグ |
| `/api/integrity` | 公開 | UI の SHA-256 チェック |
| `/api/donation` | 公開 | 作者サポートブロック |
| `/license` | 公開 | ライセンステキスト |
| それ以外すべて | セッション必須 | プロファイル、テレメトリ、コマンド、QR、APK、アシスト、`/ws` |

セッションがない場合:

- API は `401` と `{"error","code":"unauthorized"}`、および
  `WWW-Authenticate: Bearer realm="open-deck"` で応答します。
- HTML ページは `/login.html?next=<path>` へ `302` を返します。
- WebSocket ハンドシェイクは `401` で拒否されます（ブラウザは接続エラーを
  表示します）。

---

## 2. 認証

パスワードは 6 文字以上で、`config/auth.json` に PBKDF2 ハッシュとして保存
されます（210,000 イテレーション、ランダムソルト）。セッションは 32 バイトの
ランダム値で、12 時間の TTL を持ち、アクセス時に延長されます。

トークンは 3 つの方法で受け付けられます:

| 方法 | 場所 | 対象 |
| --- | --- | --- |
| Cookie `open_deck_session` | `HttpOnly; SameSite=Lax` | ブラウザと Android WebView |
| `Authorization: Bearer <token>` | ヘッダー | ネイティブクライアント |
| `?token=<token>` | `/ws` のみ | Cookie なしの WebSocket |

### `GET /api/auth/status`

```json
{ "required": true, "authenticated": false }
```

### `POST /api/auth/login`

```json
{ "password": "secret" }
```

成功 — `200`、Cookie、トークン:

```json
{ "ok": true, "required": true, "token": "<43 characters>", "expiresIn": 43200 }
```

エラー:

| ステータス | `code` | いつ |
| --- | --- | --- |
| `400` | `missing_password` | `password` がない |
| `401` | `bad_password` | パスワードが正しくない |
| `429` | `rate_limited` | アドレスから 5 回失敗した後。`Retry-After` を含む |

パスワードが設定されていない場合、応答は
`{"ok":true,"required":false}` です。

### `POST /api/auth/logout`

現在のセッションを無効化し、Cookie をクリアします: `{"ok": true}`。

### `POST /api/pair`

セッション必須。スマートフォンからのログイン用ワンタイムトークン:

```json
{ "url": "http://192.168.1.10:8760/?pair=…", "token": "…", "expiresIn": 600, "required": true }
```

`url` にアクセスすると、トークンが通常のセッション（Cookie）と交換され、`/`
にリダイレクトされます。再利用すると `/login.html?error=pair` が返されます。

---

## 3. REST API

以下で、`{id}` はプロファイル識別子です（`[a-z0-9][a-z0-9-]{1,63}`）。

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "authRequired": true,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  }
}
```

### `GET /api/profiles`

```json
{ "profiles": [
  { "id": "cessna-172-skyhawk", "name": "Cessna 172S Skyhawk", "icao": "C172",
    "revision": 3, "widgetCount": 11 }
] }
```

### `GET /api/profiles/{id}`

完全なプロファイル（[profile-schema.md](profile-schema.md) を参照）。
`404 not_found` — ファイルがない。`422 invalid_profile` — 検証に失敗。

### `PUT /api/profiles/{id}`

ボディは完全な JSON プロファイルです。ボディ内の `id` は URL と一致しなければ
なりません（`400 id_mismatch`）。応答 `{"ok": true, "profile": {…}}`。

### `GET /api/telemetry`

最新のフレーム（WebSocket 経由の `telemetry` と同じ形式）。`seq` は増加し、
`values` はすべてのレジストリキーを含みます。

### `GET /api/telemetry/variables`

変数カタログ:

```json
{ "variables": [
  { "key": "speed.iasKt", "label": "Indicated airspeed", "kind": "number",
    "unit": "KT", "writable": false, "simVar": "AIRSPEED INDICATED", "simEvent": null }
] }
```

完全な人間可読カタログは [telemetry.md](telemetry.md) にあります。

### `GET /api/integrity`

```json
{ "verified": true, "checkedAt": "2026-11-01T…", "manifestPresent": true,
  "files": { "web/index.html": "<sha256>" }, "errors": [] }
```

### `GET /api/donation`

`config/donation.json` からの作者サポート詳細（唯一のソースはホスト設定）。
作者 — Viktor Krasnikov、Donat —
[`https://taps.uz/open_deck_fs`](https://taps.uz/open_deck_fs)。

### `GET /api/connect`

スマートフォン/タブレット用アドレス:

```json
{
  "host": "FLIGHTSIM-PC",
  "primaryUrl": "http://192.168.1.10:8760/",
  "phoneUrl": "http://192.168.1.10:8760/?device=phone",
  "urls": [
    { "url": "http://192.168.1.10:8760/", "host": "192.168.1.10",
      "private": true, "loopback": false, "linkLocal": false }
  ],
  "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
  "qr": { "scale": 6, "border": 4, "maxTextLength": 512 }
}
```

並び順: `192.168.*`、次に `10.*`、`172.16–31.*`、リンクローカル、ループバック。

### `GET /api/qr.svg?text=…&scale=6&border=4`

QR コード付きの SVG（最大 512 文字。ホスト上で生成され、ライブラリなし）。
`400 missing_text` — `text` がない。`400`（`code` = `error`）— `scale`/`border`
が数値でない。`422 qr_too_long` — テキストがサポートされる QR バージョンに
収まらない。

### `POST /api/sim/command`

```json
{ "key": "power.batteryMaster", "value": true }
```

成功 — `200` と `{"type":"ack","id":…,"key":…,"ok":true,"value":…}`。
エラー: `400` と `code` = `invalid_key`、`not_writable`、`invalid_value`、
`rate_limited`、または `sim_error`。`409 sim_rejected` — シミュレーターが拒否。
パラメーターイベントを持つ変数の場合、値はスケーリングされます
（パーセント → 0..16383）。

### `POST /api/sim/aircraft`

```json
{ "profileId": "cessna-172-sixpack" }
```

応答: `{"ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false}`。
`pinned: true` — プロバイダーは機体を切り替えられない（SimConnect）ため、
シミュレーターで機体が変わるまで選択が固定されます。`404` — そのような
プロファイルはない。

### アシスト

`GET /api/assist` — ループ状態:

```json
{
  "telemetry": {
    "onGround": true, "radioAltitudeFt": 0, "groundSpeedKt": 12.3,
    "iasKt": 0, "headingDeg": 274, "localizerDeg": 0.0,
    "glideSlopeDeg": 0.0, "locValid": false, "gsValid": false,
    "autopilotMaster": false, "approach": false,
    "throttlePct": 18.4, "rudderPct": -3.2, "parkingBrake": false
  },
  "taxi": { "engaged": true, "targetSpeedKt": 12, "targetHeadingDeg": 274,
            "throttlePct": 18.4, "rudderPct": -3.2, "message": "…" },
  "landing": { "phase": "off", "message": "…", "throttlePct": 0, "active": false },
  "limits": { "taxiSpeedMinKt": 3, "taxiSpeedMaxKt": 25,
              "flareStartFt": 60, "flareIdleFt": 15 }
}
```

`POST /api/assist/taxi`:

| `action` | フィールド | 意味 |
| --- | --- | --- |
| `engage` | — | 速度/方位保持を有効化（地上のみ） |
| `disengage` | — | 無効化 |
| `stop` | — | スロットル 0、パーキングブレーキ |
| `speed` | `value`（3…25） | タキシー速度を設定 |
| `heading` | `delta`（±） | 目標方位を回転 |

`POST /api/assist/landing`: `action` = `arm`（AP + APR）、`disarm`、`toga`。

応答: `{"ok": true|false, "message": "…", "status": {…}}`。
`200` — アクション実行。`409` — 拒否（地上でない、速度が低すぎる、MSFS への
接続がない、未知のアクション）。

### Android APK ビルド

- `GET /api/android/settings` — `{settings, toolchain, apk, prebuiltApk}`。
- `PUT /api/android/settings` — 設定を保存（名前、パッケージ ID、バージョン、
  ゲートウェイアドレス、ツールパス）。`422 invalid_settings`。
- `GET /api/android/build` — ジョブ状態:
  `{jobId, state, running, log, apk, error}`（`state`:
  `idle|running|success|failed`）。
- `POST /api/android/build` — 開始。`202` と `jobId`、`409 build_running`、
  `422 invalid_settings`。
- `GET /api/android/apk` — APK をダウンロード
  （`application/vnd.android.package-archive`）。ビルドがない場合は
  ディストリビューションのビルド済み APK、それもなければ
  `404 apk_missing`。

### 静的ファイルとサービスページ

- `GET /` — パネル（`index.html`）、`GET /editor.html` — エディター、
  `GET /android.html` — APK ビルド、`GET /assist.html` — アシスト、
  `GET /login.html` — ログイン。
- `GET /license` — ライセンステキスト。
- `HEAD` — 静的ファイルのみ。`/api/*` には `405`。
- `OPTIONS` — CORS ヘッダーなしの `204`。

---

## 4. WebSocket `/ws`

ハンドシェイク — RFC 6455、バージョン 13。テキストメッセージのみ。バイナリ
メッセージは `1002` でクローズされます。

### 4.1. 認可

トークンは Cookie、`Authorization: Bearer`、または `?token=`（`/ws` 用）から
取得されます。有効なセッションがない場合 — HTTP `401`、アップグレードは実行
されません。ワンタイムペアリングトークンはここでは有効ではありません:
`/?pair=` 経由でのみ受け付けられます。`Origin` と `Host` が一致しない場合 —
HTTP `403`、アップグレードは実行されません。

### 4.2. サーバー → クライアント

#### `hello` — 最初のメッセージ

```json
{
  "type": "hello",
  "clientId": "a1b2c3d4",
  "server": { "name": "Open Deck for MSFS", "version": "0.1.0",
              "telemetryHz": 30.0, "uptimeSec": 1.2 },
  "profiles": [ … ],
  "state": { /* full telemetry frame */ }
}
```

#### `telemetry` — 定期的（1 秒あたり `telemetryHz` 回）

```json
{
  "type": "telemetry",
  "seq": 1234,
  "ts": 1762340000000,
  "sim": { "provider": "mock", "connected": true,
           "aircraftTitle": "…", "profileId": "…" },
  "values": { "speed.iasKt": 108.0, "altitude.indicatedFt": 4520.0, … }
}
```

- `seq` は単調増加 — フレーム損失を明らかにします。
- `values` は常にすべてのレジストリキーを含みます。`null` は「データなし」を
  意味します: SimVar が SimConnect に受け入れられなかったか、テレメトリが
  古くなっています。クライアントはゼロを代入せず、ダッシュを表示します。

#### `aircraft`

```json
{ "type": "aircraft", "profileId": "cessna-172-sixpack", "aircraftTitle": "…" }
```

機体の変更/自動検出後に到着し、クライアントがプロファイルを切り替えます。

#### `ack`

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong`

`ping` への応答: `{ "type": "pong", "t": <echo>, "ts": <unix ms> }`。

#### `error`

`{ "type": "error", "code": "bad_json"|"unknown_type", "error": "…" }`。

### 4.3. クライアント → サーバー

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` は任意です。サーバーはそれを `ack` で返します。

### 4.4. `ack` コード

| `code` | 意味 |
| --- | --- |
| `invalid_key` | 空/未知のキー |
| `not_writable` | 読み取り専用変数 |
| `invalid_value` | 値を型に変換できない |
| `rate_limited` | WebSocket クライアントまたは REST の IP から 1 秒あたり 30 コマンド超 |
| `sim_rejected` | シミュレーターがコマンドを拒否 |
| `sim_error` | プロバイダーの内部エラー |

### 4.5. 制限と動作

- 最大メッセージサイズ — 256 KiB。それより大きい — `1002`。
- クライアントごと — 8 テレメトリフレームのキュー。オーバーフロー時は最も
  古いものが破棄されます（遅いクライアントが他のクライアントを遅くしません）。
- 制御フレーム（ping/pong/close）はフラグメント化されず、≤125 バイトです。
- 読み取りアイドルタイムアウト — 90 秒。クライアントは 20 秒ごとに `ping` を
  送信します。
- クローズ: `1000` — 正常、`1002` — プロトコル違反。

### 4.6. クライアントへの推奨事項

- 視覚的な状態は `ack` ではなく `telemetry.values` から取得します。
- バックオフ付きで再接続します（500 ms → 8 s、ジッター）。45 秒間メッセージが
  到着しない場合 — 接続を「ハーフオープン」と見なして再接続します。
- UI をブロックしないでください: 「待機中」を表示し、`ok:false`/タイムアウトで
  ロールバックします。

---

## 5. QR ログイン（ペアリング）

```
Phone (no session)                      Gateway
        │  GET /?pair=<one-time token>   │
        ├───────────────────────────────►│
        │                                │ token check (10 min, once)
        │  302 / + Set-Cookie open_deck_session  │
        │◄───────────────────────────────┤
        │  GET / (with cookie)           │
        └───────────────────────────────►│ panel
```

QR コードはゲートウェイ自体（`/api/qr.svg`）によって描画されます。トークンは
`POST /api/pair`（セッション必須）によって作成されます。これにより、スマート
フォンはパスワードを入力せずにログインします。トークンはワンタイムであり、
セッションではありません: Cookie や Bearer トークンとして使用しようとすると
`401` が返り、その TTL は延長されません。

---

## 6. 自動検出（UDP ブロードキャスト）

ホストは 3 秒ごとに JSON ビーコンを UDP ポート `8761` に送信します（Android と
ネイティブクライアント向け。ブラウザは UDP をサポートしていません）。

```json
{
  "type": "open-deck-msfs",
  "protocol": 1,
  "name": "FLIGHTSIM-PC",
  "version": "0.1.0",
  "httpPort": 8760,
  "telemetryHz": 30.0,
  "profiles": ["cessna-172-skyhawk", "piper-pa28-archer-ii"],
  "auth": true,
  "ts": 1762340000
}
```

| フィールド | 説明 |
| --- | --- |
| `type` | 常に `open-deck-msfs` |
| `protocol` | ビーコンスキーマのバージョン |
| `name` | ホスト名 |
| `httpPort` | HTTP/WebSocket ポート |
| `telemetryHz` | テレメトリレート |
| `profiles` | 利用可能なプロファイル |
| `auth` | パスワードが有効な場合にのみ存在（`true`） |
| `ts` | Unix 時間 |

手動チェック:

```powershell
python -m msfs_gateway.discovery --listen
```

---

## 7. HTTP エラー

形式: `{"error": "text", "code": "machine_code"}`。

| ステータス | 一般的なコード |
| --- | --- |
| `400` | `bad_request`、`bad_json`、`invalid_value`、`id_mismatch`、`missing_password` |
| `401` | `unauthorized`、`bad_password` |
| `404` | `not_found`、`apk_missing` |
| `409` | `build_running`、`sim_rejected`、アシストの拒否 |
| `411` | `length_required` |
| `413` | `too_large` |
| `422` | `invalid_profile`、`invalid_settings`、`qr_too_long` |
| `429` | `rate_limited` |
| `501` | サポートされていない HTTP メソッド（stdlib） |

---

## 8. 例

### ログインとプロファイルリクエスト

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

### Cookie の代わりに Bearer

```bash
TOKEN=$(curl -s -H "Content-Type: application/json" \
  -d '{"password":"secret"}' http://127.0.0.1:8760/api/auth/login | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/telemetry
```

### コマンド

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
     -d '{"key":"power.batteryMaster","value":true}' \
     http://127.0.0.1:8760/api/sim/command
```

### WebSocket（Python、ライブラリなし）

```python
import json, socket, base64, os
sock = socket.create_connection(("127.0.0.1", 8760))
key = base64.b64encode(os.urandom(16)).decode()
sock.sendall((
    "GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Cookie: open_deck_session=<token>\r\n\r\n"
).encode())
# その後、RFC 6455 フレームを読み取る（msfs_gateway/websocket.py を参照）
```

---

## 9. 互換性

- プロファイルスキーマ — `schemaVersion: 1`。古い `v0` 形式は読み取り時に
  `legacy.py` によって適応されます。
- ビーコン — `protocol: 1`。クライアントは新しいオプションフィールド
  （`auth`）を無視しなければなりません。
- API は URL でバージョン管理されません: 破壊的変更は新しいメジャー
  ゲートウェイバージョンでのみ行われます。
