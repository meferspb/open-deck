# 🏗️ Open Deck for MSFS アーキテクチャ

このドキュメントでは、コンポーネント、データフロー、主要な設計上の決定を
説明します。プロファイル形式は [profile-schema.md](profile-schema.md)、
ネットワークプロトコルは [protocol.md](protocol.md) で扱います。

---

## 1. 高レベル図

```
┌───────────────────────────── Windows Host (Core Gateway) ─────────────────────────────┐
│                                                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌────────────────────┐   │
│  │  SimProvider  │──▶│      Hub      │──▶│ WebSocket /ws │──▶│  Web client (JS)   │   │
│  │  (mock /      │   │  (broadcast,  │   │               │   │  Android client    │   │
│  │   SimConnect) │   │   commands)   │   ├───────────────┤   └────────────────────┘   │
│  └──────▲────────┘   └──────▲────────┘   │  HTTP /api    │                            │
│         │                   │            │  HTTP / (static)│                          │
│         │ read()            │ profiles   └───────┬───────┘                            │
│         │ apply_command()   │ list/get/save      │                                    │
│  ┌──────┴────────┐   ┌──────┴────────┐          │                                    │
│  │  telemetry.py │   │  profiles.py  │          │  REST + WebSocket on ONE port      │
│  │ (SimVar reg.) │   │  (validation) │          └────────────────────────────────────┘
│  └───────────────┘   └───────────────┘                                               │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ SimConnect API (native, ctypes) — or mock without MSFS
        │
┌───────┴────────┐
│  MSFS 2020/24  │
└────────────────┘
```

---

## 2. コンポーネントと責務

### 2.1. `telemetry.py` — 正規の変数レジストリ

量に関する唯一の真実の源: キー名、型、単位、SimVar バインディング
（`sim_var`/`sim_unit`）、書き込みイベント（`sim_event`）。プロファイルは
これらのキーのみを参照するため、SimVar の名前変更は 1 か所の編集で済みます。

```python
Variable("power.batteryMaster", "bool", "Master battery",
         sim_var="ELECTRICAL MASTER BATTERY", sim_unit="bool",
         sim_event="TOGGLE_MASTER_BATTERY")
```

### 2.2. `sim/` — テレメトリソース（プロバイダー）

共通の `SimProvider` インターフェース:

| メソッド | 目的 |
| --- | --- |
| `connected` | シミュレーターへのライブ接続があるかどうか |
| `start()` / `stop()` | プロバイダーのバックグラウンドスレッド |
| `read()` | 値のスナップショット `dict[key, value]` |
| `apply_command(key, value)` | クライアントコマンドを適用 |
| `select_aircraft(profile_id)` | 機体を切り替え（mock のみ対応） |

実装:

- **`MockSim`** — 手続き型のフライト: バンク/ピッチ/方位/速度/高度が滑らかな
  正弦波に沿って変化し、燃料が消費されます。MSFS なしの開発、デモ、自動
  テストに必要です。
- **`SimConnectSim`** — `ctypes` 経由のネイティブ SimConnect。数値データムの
  ブロックを購読し（`AddToDataDefinition` + `RequestDataOnSimObject`）、
  文字列 `TITLE`/`ATC MODEL` を別途購読し、`read()` で値をキャッシュし、
  コマンドをイベントとして送信します（`MapClientEventToSimEvent` +
  `TransmitClientEvent`）。SimConnect の呼び出し（コマンドを含む）は
  ディスパッチスレッド上で行われます（`run_on_dispatch`）。これは API が
  マルチスレッド呼び出し向けに設計されていないためです。ユーザーの
  `SimConnect.cfg` が存在しないチャネルを指している場合、一時的な設定を
  通じて TCP `127.0.0.1:19999`（MSFS 2020/2024 のポート）で再接続を試みます。
  実際の MSFS 2020 への接続は検証済みです。ライブの数値交換、WASM モジュール、
  飛行中のアシストが次の検証ステップです。

`create_sim()` ファクトリは `--sim` 設定からプロバイダーを選択します:

- `mock` → 常に mock。
- `simconnect` → SimConnect のみ、エラー時は終了。
- `auto` → SimConnect、失敗時は mock にフォールバック（ゲートウェイは常に
  起動）。

### 2.3. `hub.py` — テレメトリバス

- `--telemetry-hz` レートの単一の「ティッカー」スレッドが `sim.read()` を収集し、
  フレームをすべての WebSocket クライアントにブロードキャストします。
- 各クライアントは独自のキュー（8 フレーム）と送信スレッドを持ちます: 遅い
  タブレットが他のクライアントへの配信を止めることはなく、古いフレームは
  破棄されます。
- **コマンドレート制限**（クライアントごとに ≤30/s）— タッチの固着に対する
  保護。
- `build_message()` は値を正規化し（小数点以下 3 桁に丸め、キーの完全な集合）、
  `seq`、`ts`、`sim` メタデータを追加します。

### 2.4. `profiles.py` + `legacy.py` — 機体プロファイル

- `validate_profile()` — 厳格な構造チェック（計器タイプ、バインディング、
  コマンド、矩形、ゲージ範囲）。
- `ProfileStore` — スレッドセーフなアトミック保存（tmp + `fsync` +
  `os.replace`）。
- `legacy.adapt()` — 仕様の「ピクセル」v0 形式を内部形式（0..1 の比率座標）に
  変換し、古いパネルをそのまま読み込めるようにします。

### 2.5. `http_api.py` + `websocket.py` — ネットワーク

- `ThreadingHTTPServer` が `web/` の静的ファイルと REST API を提供し、単一
  ポートで WebSocket アップグレードを実行します — ファイアウォールルール 1 つ。
- `websocket.py` — stdlib 上の最小限の RFC 6455 実装（テキスト、ping/pong、
  クローズ）。
- `auth.py` — オプションのパスワードログイン: PBKDF2 ハッシュ、インメモリ
  セッション、`HttpOnly` Cookie、Bearer トークン、ワンタイム QR トークン、
  試行回数制限。
- セキュリティヘッダー: CSP `default-src 'self'`、`X-Content-Type-Options`、
  `Referrer-Policy`。静的ファイルはキャッシュなし（ライブ開発）。
- `/api/connect` + `qr.py` — スマートフォンの迅速な接続: ホストがネットワーク
  アドレスを列挙し（最初に `192.168.x`、次に `10.x`、`172.16-31.x`）、QR
  コードはカスタム stdlib ジェネレーター（バイトモード、EC L、バージョン
  1〜10、すべてのマスク）で描画され、外部ライブラリやインターネットを
  必要としません。

### 2.5a. `auth.py` — パスワードログイン

- パスワードは PBKDF2 ハッシュ（`config/auth.json`）としてのみ保存され、
  `hmac.compare_digest` で検証されます。アドレスごとに 1 分あたり 5 回の
  失敗でブロックされます。
- セッションはプロセスメモリ内に存在します（32 バイト、12 時間の TTL、
  アクティビティで延長）。ブラウザは `open_deck_session` Cookie
  （`HttpOnly`、`SameSite=Lax`）を受け取り、ネイティブクライアントは Bearer
  または WebSocket 用の `?token=` を使用します。
- ワンタイム QR トークン（`POST /api/pair`、10 分）により、スマートフォンは
  パスワードを入力せずにログインできます。このようなトークンは `/?pair=`
  経由でのみ受け付けられます: `SessionStore.validate` は `pairing` セッション
  を拒否するため、Cookie や Bearer トークンとしては使用できません。
- `Origin` が `Host` と一致しないブラウザの POST/PUT および WebSocket
  リクエストは `403` で拒否されます（クロスサイト WebSocket ハイジャックと
  CSRF への保護）。`Origin` のないクライアント（Android、curl）は許可されます。
- `Host` ヘッダーはさらに localhost、マシン名、FQDN、ローカル IP に対して
  チェックされます。これにより、`Origin` と `Host` の両方が攻撃者のドメイン
  に属する DNS リバインディングを防ぎます。
- 公開されるのはログイン、`/api/health`、`/api/integrity`、`/api/donation`、
  `/license` のみです。それ以外はすべて閉じられています。

### 2.5b. `assist.py` — 着陸・タキシーアシスト

- **タキシー**: 対地速度による PI スロットルコントローラーと方位による P
  ラダーコントローラー。地上でのみ有効化され、離陸/ブレーキ/35 kt 超の速度で
  無効化されます。「STOP」はスロットル 0 とパーキングブレーキです。
- **着陸**: ARM で AP と APR を有効化し、60〜15 ft の間でスロットルを線形に
  絞り、接地時に AP を解除します。TOGA — フルスロットル。エレベーターには
  触れません。
- 10 Hz のスレッドが `sim.read()` を読み取り、`Hub.apply_assist_command` を
  通じてコマンドを送信します（レート制限や余分な読み取りなし）。
- これは補助ループです: 最終的な判断と制御はパイロットに残ります。

### 2.6. `integrity.py` — ドネーション保護（ライセンス条件）

5 つの重要ファイル（`web/js/ui/donation.js`、`web/css/donation.css`、
`config/donation.json` を含む）の SHA-256 を `integrity/manifest.json`
マニフェストと比較します。ホストは不一致時に起動をブロックします。クライアント
（`web/js/ui/integrity.js`）はさらに DOM 内のブロックの可視性を監視します。
作者 — Viktor Krasnikov（[github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)）、
Donat — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。

### 2.7. `discovery.py` — ホスト自動検出（UDP ブロードキャスト）

バックグラウンドスレッドが N 秒ごとに JSON ビーコン（ホスト名、バージョン、
`httpPort`、周波数、プロファイル一覧）を UDP ブロードキャスト
（`255.255.255.255` + 各インターフェースの定向ブロードキャスト）で送信します。
`listen_once()` はネイティブクライアントとテスト用の受信側です。ブラウザは
UDP をサポートしていないため、Web クライアントには不要です（すでにホスト
自体から起動しているため）。

### 2.8. `web/editor.*` — ビジュアルパネルエディター

`/editor.html` + `web/js/editor.js` — ドラッグ&ドロップエディター: 計器の移動
とリサイズ、バインディングの設定（カタログ
`GET /api/telemetry/variables` とプロファイルで宣言された `custom.*` からの
ドロップダウンリスト）、オプション（ゲージ、単位、トーン）、タイプパレット
からの追加、削除。保存は `PUT /api/profiles/{id}` を通じて行われます。プレビュー
はデモ値で実際の計器を（`widgets/registry.js` レジストリを通じて）描画します。
フォームファクタのオーバーライドはアクティブなフォームファクタで編集されます:
オーバーライドがない場合、編集は `layout.base` に入ります。編集履歴（変更前の
`widgets` のスナップショット）は、ドラッグ、リサイズ、プロパティ、追加、削除の
元に戻す/やり直しを提供します。また、1 % グリッドスナップ（Shift で一時的に
無効化）と、ジオメトリを他のフォームファクタにワンボタンでコピーする機能も
あります。

### 2.8a. 機体の自動検出

`SimConnectSim` は `TITLE` と `ATC MODEL` を別々の文字列データム
（`SIMCONNECT_DATATYPE_STRING256`）として読み取り、`aircraft.title` /
`aircraft.atcModel` に保存します。`hub.py` は `sim.match.title` / `atcModel`
ルール（glob、大文字小文字を区別しない）を保持し、プロバイダー自身が設定
しない場合、毎フレームでプロファイルを選択します。クライアントはテレメトリの
`sim.profileId` を監視し、機体が変わるとパネルを再読み込みします。一覧からの
手動選択は 5 秒間固定され、まだ到着していないフレームとの競合を防ぎます。

### 2.8b. `web/js/ui/comfort.js` — 輝度とキオスク

パネル輝度には 3 つのレベル（100/72/45 %）があり、`localStorage` に保存され、
`<html>` の `data-brightness` 属性を介して適用されます: CSS は計器シーンのみを
暗くし、UI は読みやすいままです。キオスクモードは上部パネルとステータスバーを
隠し、シーンをフルモードに切り替え、小さな終了ボタンを残します。`Esc` で UI が
復元されます。ショートカット: `B` — 輝度、`F` と `Esc` — キオスク。

### 2.9. WASM ブリッジ: Client Data Area 経由の LVAR/RPN

複雑な機体（PMDG、Fenix、FlyByWire、iniBuilds）は状態を独自の変数に保持
します。プロファイルは `variables` ブロックでそれらを宣言し（`source: lvar`
または `rpn`）、ブリッジは **SimConnect Client Data Area** を通じてそれらを
読み書きします — WASM モジュール（MobiFlight / SimBridge）がそこにデータを
公開します。

```
hub.build_message()
   └─ hub._custom_values(profile_id)        # 0.25 秒キャッシュ
        └─ WasmBridge.read_specs(specs)      # wasm_bridge.py
             ├─ read_lvars(names)            # ブロック: 名前 128 B + double 8 B
             └─ execute_rpn(script)          # Command → Response
                  └─ ClientDataChannel.read_area / write_area   # client_data.py
                       └─ SimConnectClientDataBackend            # simconnect.py
                            └─ run_on_dispatch(...)  # SimConnect スレッド上で呼び出し
```

レイヤー:

- **`sim/client_data.py`** — 同期形式のプロトコル: `request_id` によるリクエスト
  の関連付け、タイムアウト、エリアサイズ増加時の再登録、切断時の保留中
  リクエストのリセット。トランスポートは抽象化されている（`ClientDataBackend`）
  ため、プロトコルは MSFS なしでテストされます。`LoopbackClientDataBackend` は
  テストとデモ用のインメモリ実装です。
- **`sim/simconnect.py`** — `SimConnectClientDataBackend`: `MapClientDataNameToID`、
  `AddToClientDataDefinition`、`RequestClientData`、`SetClientData`。すべての
  呼び出しは `run_on_dispatch` を通じてディスパッチスレッド上で行われ
  （SimConnect はマルチスレッド呼び出し向けに設計されていません）、応答は
  `SIMCONNECT_RECV_ID_CLIENT_DATA` で到着します。
- **`sim/wasm_bridge.py`** — LVAR ブロックのレイアウト、RPN コマンド、および
  `(<value>) (>L:NAME, number)` を通じた LVAR 書き込み。

デフォルトエリア: `MobiFlight.LVars`、`MobiFlight.Command`、
`MobiFlight.Response`。別のモジュールバージョンでは、`wasm_bridge.py` の定数で
オーバーライドされます。

`simconnect` プロバイダーでは自動的に有効になります（`--no-wasm` フラグで
無効化）。WASM モジュールがインストールされていない場合、応答は到着しません:
2 回連続のタイムアウト後、`ClientDataChannel` のサーキットブレーカーが一時的に
（30 秒）ポーリングを停止し、テレメトリストリームが毎フレームでブロックされ
ないようにします。`custom.*` キーは単にフレームから欠落します — 計器は正直に
「--」を表示し、SimVar テレメトリは動作し続けます。LVAR ブロックは 56 要素
（7616 バイト）に制限され、`MaxRecvData`/`MaxSendData` = 8192 に収まります。
mock モードでは値はプロファイルの `initial` から取得されます。受け入れられた
SimConnect 定義にない、または古い組み込み SimVar は `0` ではなく `null` として
返されます: パネルは「--」を表示し、アシストがそれらを実際のゼロと誤認する
ことはありません。

**検証状況:** プロトコルとエリア会計はテストでカバーされ（インメモリ
トランスポートによる MobiFlight エミュレーション）、ビルドと起動は検証済み
です。MSFS + WASM モジュールでのライブフライトはまだ実行されていません —
これがシミュレーターのインストールを必要とする唯一のステップです。

### 2.10. `android_build.py` — ディストリビューションからの Android APK ビルド

インストール済みアプリには Android ソース（`android/`）が含まれ、ビルド後は
ビルド済み APK が `android/dist` にあります。ページ `/android.html` と API
`/api/android/*` により、アプリ名、パッケージ ID、バージョン、デフォルトの
ゲートウェイアドレスを変更し、`gradle assembleDebug` を実行して、新しい APK を
ダウンロードできます。設定は `config/android-build.json` にあり、同じ値が
ビルドに `-P…` として渡され、`BuildConfig`/Android マニフェストに入ります。

ツールの検索: 設定 → `JAVA_HOME` / `ANDROID_HOME` → 一般的なパス。
ユーザープロファイルが書き込み可能でない場合（厳格なポリシー、サンドボックス）、
Gradle キャッシュ、`TMP`、デバッグキーストアは自動的にディストリビューショ
ンディレクトリ（`.gradle-home`、`.tmp`、`.android-home`）にリダイレクトされ、
ビルドは動作し続けます。ブラウザなしの CLI: `OpenDeck.exe --build-apk [config.json]`。

---

## 3. データフロー

### 3.1. テレメトリ（プッシュ）

```
MockSim/SimConnectSim._loop()
   └─ sim.read()                        # 値のスナップショット
        └─ hub.build_message()          # 正規化 + seq/ts/sim
             └─ hub._broadcast_text()   # 各 WebSocket キューへの JSON
                  └─ web: handleMessage('telemetry') → store → panel-view → widgets
```

### 3.2. コマンド（リクエスト/確認応答）

```
web: toggle-switch.onClick()
   └─ socket.command(key, value)        # {type:'command', id, key, value}
        └─ hub.handle_command()         # 検証 + レート制限
             └─ sim.apply_command()     # mock / SimConnect
                  └─ ack {type:'ack', id, ok, value}   (WebSocket 経由)
                       └─ client waits for confirmation via telemetry
```

### 3.3. プロファイル（プル）

```
web: api.listProfiles() → GET /api/profiles
   └─ api.getProfile(id) → GET /api/profiles/{id}
        └─ profiles.load_profile_file() → legacy.adapt_if_needed() → ensure_valid()
             └─ panel-view.mount(profile) → createWidgetInstance() by type
```

### 3.4. 自動検出（UDP プッシュ）

```
DiscoveryBeacon._loop()                      # デーモンスレッド
   └─ payload() {name, version, httpPort, profiles, auth?, ts}
        └─ sendto(255.255.255.255:8761) + directed broadcasts
             └─ Android/native client: listen_once() → http://<ip>:<port>/
```

---

## 4. 主要な設計上の決定

| 決定 | 理由 |
| --- | --- |
| Python stdlib のみ | エアギャップ: `pip install` は利用できない。1 つのインタープリターがすでにインストールされている |
| HTTP+WS に単一ポート | ファイアウォールルール 1 つ、診断が簡単 |
| 外部ライブラリなしの WebSocket | プロトコルの制御、依存関係なし |
| プロファイルはピクセルではなく 0..1 座標を使用 | すべてのフォームファクタに 1 つのプロファイル |
| `layout.base` + オーバーライド | phone/tablet は差分のみを指定 |
| 正規の SimVar レジストリ | プロファイルを特定のブリッジから分離 |
| クライアント側スムージング（Smoother） | 20〜30 Hz ネットワーク上での 60 fps アニメーション |
| ウィジェットは `clientWidth` で canvas を描画 | プレビューでの正直な HiDPI スケーリング |
| `auto` プロバイダー | MSFS なし、設定編集なしでゲートウェイが起動 |
| UDP 自動検出ビーコン | Android は手動 IP なしでホストを見つける。ブラウザには不要 |

---

## 5. MVP の境界と次のステップ

**すでに存在するもの**: stdlib ゲートウェイ、クライアントごとのキューを持つ
WebSocket、mock/SimConnect（+ TCP フォールバック）、LVAR/RPN WASM ブリッジ、
9 種類の計器、3 つのフォームファクタ、検証とアトミック保存を備えたプロファイル、
元に戻す/やり直しとレイアウトコピーを備えたエディター、UDP 自動検出、Android
クライアント、ディストリビューション内の APK ビルダー、Windows インストーラー、
QR 付きパスワードログイン、着陸・タキシーアシスト、整合性チェック、Python 248
および JS 35 のテスト。

次のステップ（README の「ロードマップ」を参照）:

- ライブフライト検証: 実際の機体での SimConnect/WASM、空中および地上での
  アシスト。
- APK のリリース署名（ビルダー設定の keystore）。
- mDNS（Bonjour）を UDP ビーコンの代替として。
- 空港チャートを使用したタキシー経路案内（現時点ではアシストは速度と方位のみを
  保持）。
- テレメトリの記録/再生（デモとプロファイリング用）。
