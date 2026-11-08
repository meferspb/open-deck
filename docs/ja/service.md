# Open Deck for MSFS — サービス説明

このドキュメントでは、ゲートウェイが何を行い、何で構成され、クライアントが
どのようにやり取りし、パスワードログインをどのように有効化するかを説明します。
「自分のために」パネルをセットアップするパイロットと、内部設計を理解する必要
がある開発者を対象としています。

- バージョン: 0.1.0
- ホストプラットフォーム: Windows 10/11
- クライアント: ブラウザ（PC、スマートフォン、タブレット）、Android 8+
- ライセンス: [GNU AGPL-3.0](../../LICENSE) + 追加条件 Section 7

## 1. 目的

Open Deck for MSFS は、スマートフォンやタブレットを Microsoft Flight
Simulator 2020/2024 の計器パネルに変えます。ゲートウェイはシミュレーターと
同じコンピューター上で動作し、SimConnect を通じてテレメトリを読み取り、
ローカルネットワーク経由で配信し、コマンド（スイッチ、ロータリーセレクター、
ボタン）を受け付けます。パネルは機体の JSON プロファイルで記述され、ブラウザ
上で直接編集できます。

主な特性:

- **オフライン**: 外部 CDN、フォント、API、テレメトリはありません。すべてが
  分離されたネットワーク上、およびインターネット接続のないマシン上で動作
  します。
- **単一ポート**: 静的ファイル、REST、WebSocket を単一の TCP ポート（デフォルト
  8760）で提供 — ファイアウォールルール 1 つで十分です。
- **依存関係なし**: ホストは Python 3.11+ と標準ライブラリ。クライアントは
  バニラ ES モジュール。Android は AndroidX なしの Kotlin。
- **オプションのパスワード**: API とテレメトリへのアクセスを 6 文字以上の
  パスワードで閉じることができ、セッション、QR ログイン、ブルートフォース保護
  を備えます。

## 2. 運用モデル

```
┌──────────────────┐   SimConnect / WASM    ┌─────────────────────────────┐
│  MSFS 2020/2024  │◄──────────────────────►│ Open Deck for MSFS (Windows)│
│  aircraft, LVAR  │   SimVar, TITLE, ATC   │                             │
└──────────────────┘   Client Data Area     │  ┌───────────────────────┐  │
                                             │  │ SimProvider           │  │
┌──────────────────┐        HTTP/WS          │  │  auto / mock / simconn│  │
│  PC browser      │◄───────────────────────►│  └──────────┬────────────┘  │
│  panel, editor   │   8760, static + API    │             │               │
└──────────────────┘                         │  ┌──────────▼────────────┐  │
┌──────────────────┐        HTTP/WS          │  │ Hub: telemetry 30 Hz  │  │
│  Phone/tablet    │◄───────────────────────►│  │ commands, sessions    │  │
└──────────────────┘                         │  └──────────┬────────────┘  │
┌──────────────────┐   HTTP (WebView)        │             │               │
│  Android client  │◄───────────────────────►│  Profiles, integrity,     │
└──────────────────┘   UDP beacon 8761       │  authentication, APK      │
                                             └─────────────────────────────┘
```

データフロー:

1. テレメトリプロバイダー（`simconnect`、`mock`、または `auto`）がティック
   ごとに 1 回変数の値を読み取ります。
2. バス（`Hub`）がフレームを組み立て、サービスフィールドを追加し、設定された
   レート（デフォルト 30 Hz、最大 60）ですべての WebSocket クライアントに
   ブロードキャストします。
3. クライアントが計器を描画します。コマンドはバスに戻り、検証され、プロバイダー
   によって適用されます。
4. 機体が変わると、ゲートウェイは名前/ATC モデルで一致するプロファイルを選択
   し、クライアントに通知します。

## 3. コンポーネント

| コンポーネント | ファイル | 責務 |
| --- | --- | --- |
| エントリポイント | `msfs_gateway/app.py` | 依存関係の組み立て、ライフサイクル、バナー、`--set-password` / `--build-apk` モード |
| 設定 | `msfs_gateway/settings.py` | CLI 引数、パス、デフォルト |
| HTTP/WebSocket | `msfs_gateway/http_api.py`、`websocket.py` | 静的ファイル、REST、RFC 6455 ハンドシェイクとフレーム、認証 |
| バス | `msfs_gateway/hub.py` | テレメトリフレーム、購読、コマンド、コマンド制限、機体の自動検出 |
| プロバイダー | `msfs_gateway/sim/` | `mock`、`simconnect`、Client Data Area、LVAR/RPN WASM ブリッジ |
| プロファイル | `msfs_gateway/profiles.py` | JSON プロファイルの読み取り/検証/アトミック保存 |
| テレメトリ | `msfs_gateway/telemetry.py` | 変数カタログ、型、値の変換 |
| 認証 | `msfs_gateway/auth.py` | PBKDF2 ハッシュ、セッション、QR トークン、試行回数制限 |
| 自動検出 | `msfs_gateway/discovery.py` | 名前、バージョン、パスワードフラグ付き UDP ビーコン |
| 整合性 | `msfs_gateway/integrity.py` | 重要 UI ファイルの SHA-256 |
| QR | `msfs_gateway/qr.py` | 組み込み QR ジェネレーター（SVG）、依存関係なし |
| APK ビルド | `msfs_gateway/android_build.py` | 設定、JDK/SDK/Gradle の検索、Gradle 起動、APK 配信 |
| アシスト | `msfs_gateway/assist.py` | タキシー（速度/方位）と着陸（APR、retard、TOGA）のループ |
| ドキュメント生成 | `msfs_gateway/docsgen.py` | コードレジストリから `docs/telemetry.md` と `docs/widgets.md` を生成 |
| Web クライアント | `web/` | パネル、エディター、ログイン、アシスト、APK ビルドページ |
| Android | `android/` | WebView シェル、UDP 検出、整合性チェック、ログイン Cookie |
| ビルドとチェック | `scripts/`、`packaging/` | インストーラー、`check.ps1`、QR 検証 |

## 4. テレメトリ

### 4.1. フレーム

フレームは JSON オブジェクトで、接続直後およびその後ゲートウェイのレートで
WebSocket 経由で到着します:

```json
{
  "type": "telemetry",
  "seq": 421,
  "ts": 1793541762842,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  },
  "values": {
    "attitude.pitchDeg": 2.4,
    "attitude.bankDeg": -6.1,
    "speed.iasKt": 108.2,
    "altitude.indicatedFt": 4520.0,
    "heading.magneticDeg": 274.0,
    "verticalSpeed.fpm": 120.0,
    "engine.rpm": 2380.0,
    "power.batteryMaster": true,
    "custom.lvar.apuBleed": 0.0
  }
}
```

`seq` は単調増加し、`ts` は Unix ミリ秒です。クライアントは `seq` で欠落
フレームを検出し、そのまま描画を続けます（針には影響しません）。

### 4.2. 変数

型、単位、SimVar、イベントを含む完全なカタログは
[telemetry.md](telemetry.md) にあります。以下ではカテゴリのみを挙げます。

変数カタログは唯一の真実の源です（`telemetry.py`）。各エントリには型
（`number`、`bool`、`string`）、「コマンド受け付け」フラグ、説明があります。
クライアントは `GET /api/telemetry/variables` を通じてカタログを取得できます。

カテゴリ:

- 姿勢、高度、速度、方位、VSI。
- エンジン（RPM、マニホールド/トルク、N1、ITT、燃料）。
- 電気、フラップ、オートパイロット。
- `custom.<...>` — アクティブなプロファイルからの LVAR/RPN。

### 4.3. プロバイダー

| プロバイダー | 使用場面 | 機能 |
| --- | --- | --- |
| `simconnect` | 実際のフライト | `ctypes` + `SimConnect.dll`。文字列データム `TITLE`、`ATC MODEL`。LVAR/RPN 用 Client Data Area。標準の `SimConnect.cfg` が動作しない場合、ゲートウェイ自体が一時的な設定を通じて TCP `127.0.0.1:19999`（MSFS 2020/2024 のポート）を試みます |
| `mock` | デモ、開発、テスト | 手続き型フライトモデル、プロファイルからの初期 LVAR 値 |
| `auto` | デフォルト | SimConnect への接続を試み、失敗時は mock にフォールバック |

WASM モジュールがインストールされていない場合、`custom.*` キーは単に欠落し、
パネルは「--」を表示します — 残りのテレメトリは動作し続けます。2 回連続の
タイムアウト後、Client Data サーキットブレーカーが 30 秒間ポーリングを一時停止
し、テレメトリブロードキャストスレッドをブロックしないようにします。

### 4.4. 配信と耐障害性

- 各 WebSocket クライアントは独自のキュー（8 フレーム）と送信スレッドを
  持ちます: 遅いタブレットが他のクライアントを遅くすることはなく、古い
  フレームは破棄されます。
- クライアントの再接続は指数バックオフを使用します。45 秒を超えてメッセージ
  が到着しない場合、クライアントは接続を「ハーフオープン」と見なして再接続
  します。
- セッションは飛行中に期限切れになる可能性があります — クライアントは 1 分に
  1 回ステータスを確認し、ログインページにリダイレクトします。

## 5. 機体プロファイル

プロファイルは `profiles/` 内の JSON ファイルです。詳細なスキーマは
[`profile-schema.md`](profile-schema.md) にあります。要約:

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk",
  "icao": "C172",
  "revision": 3,
  "sim": { "match": { "title": "*Cessna*172*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S" },
  "widgets": [
    {
      "id": "attitude",
      "type": "attitude",
      "label": "Attitude indicator",
      "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
      "layout": {
        "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
        "phone": { "x": 0.03, "y": 0.015, "w": 0.94, "h": 0.3 }
      }
    }
  ]
}
```

- `sim.match` — 機体タイトルと ATC モデルのテンプレート（glob）。ゲートウェイ
  がプロファイル自体を切り替えます。
- `layout` — パネル比率（0..1）の座標。`base` とオーバーライド `phone`、
  `tablet-sm`、`tablet-lg`。
- `revision` — エディターからの保存ごとに増加します。
- 保存はアトミックです: 一時ファイル → `fsync` → `os.replace`。

## 6. クライアント

### 6.1. Web パネル

- 画面幅による自動選択を備えた 3 つのフォームファクタ。手動選択は記憶され
  ます。
- 計器: 姿勢指示器、円形ゲージ、表示、スイッチ、ロータリーセレクター、VSI、
  高度計、方位指示器。アニメーションは `requestAnimationFrame` 経由。
- 快適性: 輝度 100/72/45 %（`B`）、キオスクモード（`F`、`Esc` で終了）。
- スマートフォンボタンはクイックログイン用の QR コードを表示します。

### 6.2. エディター

`/editor.html`: ドラッグ&ドロップ、リサイズ、1 % グリッド、元に戻す/やり直し、
フォームファクタ間のレイアウトコピー、ホストへの保存。

### 6.3. Android

WebView シェル: UDP ビーコンでホストを見つけるか手動アドレスを受け付け、UI の
整合性をチェックし、パネルを開きます。ゲートウェイでパスワードが有効な場合、
WebView はログインページを表示します。セッションは WebView Cookie に保存され、
アプリの再起動後も維持されます。パスワード保護されたホストはロックでマーク
されます。

### 6.4. ログインページ

`/login.html` はログインなしで利用可能な唯一のページです（そのスタイルと
ともに）。パスワードフィールド、エラー、作者サポートブロック、およびセッション
がすでにアクティブな場合の「ログアウト」ボタンを表示します。パスワードは
自身のゲートウェイにのみ、ローカルネットワーク上の HTTP 経由で送信されます
（「セキュリティ」セクションを参照）。

## 7. ネットワークと接続

| 内容 | ポート | プロトコル |
| --- | --- | --- |
| 静的ファイル、REST、WebSocket | 8760（`--port` で設定可能） | TCP/HTTP + WS |
| 自動検出 | 8761 | UDP ブロードキャスト |

- ゲートウェイは `0.0.0.0` でリッスンし、起動時にすべてのアドレスを表示します。
- Android はビーコンでホストを見つけます: PC 名、バージョン、プロファイル数、
  パスワードフラグ。
- パネルの QR コードにはアドレスとワンタイムトークンが含まれます: スマート
  フォンは 1 回のスキャンでパスワード入力なしにログインします（トークンは
  10 分間有効で、1 回のみ使用）。
- 手動アドレス入力: `192.168.1.10`、`192.168.1.10:8760`、または完全な URL。

## 8. パスワード認証

### 8.1. 有効化方法

次のいずれかの方法:

```powershell
# 1. パスワードを config/auth.json に保存（永続的）
OpenDeck.exe --set-password
#    またはプロンプトなしで:
OpenDeck.exe --set-password "my-password"

# 2. 今回の実行のみパスワードを渡す（ディスクに書き込まれない）
OpenDeck.exe --password "my-password"

# 3. 環境変数
$env:OPEN_DECK_PASSWORD = "my-password"
```

インストール済みアプリには、そのための「パスワードを設定」ショートカットが
スタートメニューにあります。ファイル `config/auth.json` には **PBKDF2 ハッシュ
のみ**が保存されます（ランダムソルト、210,000 イテレーション）。ファイルを
削除すると、ログインは再び不要になります。`--no-auth` フラグはファイルと
パスワードを無視します（信頼できるネットワークのみ）。

`--password` のパスワードはディスクに書き込まれませんが、プロセス一覧
（`Get-Process` / タスクマネージャー）で見えます。永続的に使用する場合は
`--set-password` を推奨します: 起動時にメモリ内で 1 回ハッシュ化されます。

パスワードの最小長は **6 文字**です。制限: 256 文字以下、制御文字なし、先頭
および末尾の空白なし。

### 8.2. ログインの仕組み

1. クライアントが `/login.html` を開き、パスワードを入力します。
2. `POST /api/auth/login` が PBKDF2 ハッシュを検証します。成功するとセッション
   が作成されます（32 バイトのランダム値、12 時間の TTL、アクティビティで
   延長）。
3. サーバーは `open_deck_session` Cookie を `HttpOnly`、`SameSite=Lax` で設定
   します — JavaScript からは見えず、ブラウザが自動的に送信します。
4. ネイティブクライアントには、JSON 応答が `token` を返します。
   `Authorization: Bearer <token>` または WebSocket 用の `?token=` として
   渡すことができます。
5. `POST /api/auth/logout` がセッションを無効化し、Cookie をクリアします。

公開アクセス可能なのは次のみです:

| パス | 理由 |
| --- | --- |
| `/login.html`、`/js/login.js`、`/css/*`、`/img/*` | ログインページとそのスタイル |
| `/api/auth/status`、`/api/auth/login`、`/api/auth/logout` | ログイン自体 |
| `/api/health` | 「これはゲートウェイか?」チェックとパスワードフラグ |
| `/api/integrity` | UI 整合性チェック（ライセンス条件） |
| `/api/donation` | 作者サポートブロック（ライセンス条件） |
| `/license` | ライセンステキスト |

それ以外すべて — プロファイル、テレメトリ、コマンド、Android 設定、APK
ビルド、QR、`WS /ws` — はセッションを必要とします。セッションのないページは
`/login.html?next=…` へのリダイレクトで応答します。

### 8.3. ブルートフォース保護

- 60 秒以内に 1 つの IP から 5 回失敗 → 60 秒間ブロック（応答 `429` と
  `Retry-After`）。
- ハッシュ比較は `hmac.compare_digest`（定数時間）を使用します。
- 失敗した試行はアドレス付きでログに記録されますが、パスワードは記録され
  ません。

### 8.4. スマートフォンからの QR ログイン

パネルの「phone」ボタンが `POST /api/pair` をリクエストします（セッションが
必要）。ゲートウェイは 10 分間有効なワンタイムトークンを発行し、QR は
`http://<address>:<port>/?pair=<token>` をエンコードします。スマートフォンが
リンクを開くと、ゲートウェイはトークンを通常のセッションと交換し、Cookie を
設定して `/` にリダイレクトします。ペアリングトークン自体はセッションでは
ありません: Cookie や Bearer トークンとして `401` を返すため、交換後にリンク
を再利用することはできません。トークンの再利用は拒否されます。

## 9. 着陸・タキシーアシスト

ページ `/assist.html` と API `/api/assist*` が 2 つの補助ループを追加します。
これは**認証されたオートパイロットではありません**: パイロットが飛行を制御
し、いつでもアシストを無効化できます。

### 9.1. タキシー

- 地上でのみ有効化され、パーキングブレーキが解除され、速度が 35 kt 未満です。
- PI スロットルコントローラーで目標対地速度（3〜25 kt）を、P ラダー
  コントローラーで方位を保持します。パイロットは ±1°/±5° ボタンで方位を変更
  します。
- 「STOP」: スロットル 0、ラダー 0、パーキングブレーキ。
- 機体が離陸した場合、パーキングブレーキが作動した場合、または速度が 35 kt を
  超えた場合、自動的に解除されます。

### 9.2. 着陸

- ARM: `AP_MASTER` と `AP_APR_HOLD`（ILS アプローチ）を有効化します。少なく
  とも 40 kt の速度と、機体が空中にあることが必要です。
- 電波高度 60〜15 ft で、アシストはスロットルを 45 % から 0 まで線形に絞り
  ます。
- 接地時: スロットル 0、オートパイロットオフ。5 kt 未満に減速した後 —
  「ロールアウト完了」。
- TOGA: フルスロットル、AP と APR オフ（ゴーアラウンド）。
- アシストはエレベーターには触れません: アプローチとフレアは
  オートパイロット/パイロットに残ります。

状態と設定値: `GET /api/assist`。アクション — `POST /api/assist/taxi`
（`engage`、`disengage`、`stop`、`speed`、`heading`）と
`POST /api/assist/landing`（`arm`、`disarm`、`toga`）。すべてのリクエストは
セッションを必要とします。

## 10. API

ベース URL: `http://<host>:<port>`。すべての応答は JSON です。エラーは
`{"error": "…", "code": "…"}` の形式です。

| メソッド | パス | アクセス | 説明 |
| --- | --- | --- | --- |
| GET | `/api/health` | 公開 | ステータス、バージョン、レート、パスワードフラグ |
| GET | `/api/auth/status` | 公開 | `{required, authenticated}` |
| POST | `/api/auth/login` | 公開 | `{password}` → セッション + Cookie |
| POST | `/api/auth/logout` | 公開 | 現在のセッションを無効化 |
| POST | `/api/pair` | セッション必須 | ワンタイム QR トークン |
| GET | `/api/profiles` | セッション必須 | プロファイル一覧 |
| GET | `/api/profiles/{id}` | セッション必須 | 完全なプロファイル |
| PUT | `/api/profiles/{id}` | セッション必須 | プロファイルを保存（ボディの id = URL の id） |
| GET | `/api/telemetry` | セッション必須 | 最新フレーム |
| GET | `/api/telemetry/variables` | セッション必須 | 変数カタログ |
| POST | `/api/sim/command` | セッション必須 | `{key, value}` → 確認 |
| POST | `/api/sim/aircraft` | セッション必須 | `{profileId}` — 手動の機体選択 |
| GET | `/api/integrity` | 公開 | SHA-256 チェック結果 |
| GET | `/api/donation` | 公開 | 作者サポート詳細 |
| GET | `/api/connect` | セッション必須 | QR/ヒント用ゲートウェイアドレス |
| GET | `/api/qr.svg?text=…` | セッション必須 | QR コード付き SVG |
| GET/PUT | `/api/android/settings` | セッション必須 | APK ビルド設定 |
| GET/POST | `/api/android/build` | セッション必須 | APK ビルドの開始/状態 |
| GET | `/api/android/apk` | セッション必須 | APK をダウンロード |
| GET | `/api/assist` | セッション必須 | アシスト状態とテレメトリ |
| POST | `/api/assist/taxi` | セッション必須 | タキシーアシスト制御 |
| POST | `/api/assist/landing` | セッション必須 | ARM / DISARM / TOGA |
| WS | `/ws` | セッション必須 | テレメトリとコマンド |

ログインとリクエストの例:

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"my-password"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

コマンド:

```json
{"type": "command", "id": "c17", "key": "power.batteryMaster", "value": true}
```

応答: `{"type": "ack", "id": "c17", "ok": true, "value": true}` またはエラー
コード付きの `ok:false`。コマンドはクライアントごとに 1 秒あたり約 20 回に
制限されます。

## 11. インストールと起動

### 11.1. Windows インストーラー

`OpenDeck-Setup-<version>.exe` — 管理者権限なしのユーザー単位インストールで、
Python は不要です。ショートカットが作成されます: ゲートウェイの起動、ブラウザ
でのパネル、APK ビルドページ、「パスワードを設定」、アンインストール。

### 11.2. ソースから

```powershell
python -m msfs_gateway --sim auto          # 実際のフライト
python -m msfs_gateway --sim mock          # シミュレーターなしのデモ
python -m msfs_gateway --password "secret123"
```

| パラメーター | デフォルト | 目的 |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8760` | アドレスとポート |
| `--allow-host NAME` | — | Host 用の追加 DNS 名（パネルを名前で開く場合） |
| `--sim` | `auto` | `auto`、`mock`、`simconnect` |
| `--telemetry-hz` | `30` | フレームレート、1..60 |
| `--simconnect-dll` | 自動検出 | `SimConnect.dll` へのパス |
| `--simconnect-host` | `127.0.0.1` | SimConnect アドレス（リモートシミュレーター） |
| `--simconnect-port` | `19999` | SimConnect TCP ポート |
| `--profile-dir` | `profiles/` | プロファイルディレクトリ |
| `--password` | — | 今回の実行のパスワード |
| `--set-password [PWD]` | — | ハッシュを保存して終了 |
| `--auth-file` | `config/auth.json` | ハッシュファイル |
| `--web-dir` / `--profile-dir` | `web/` / `profiles/` | 静的ディレクトリとプロファイルディレクトリ |
| `--donation-config` | `config/donation.json` | 作者サポート詳細 |
| `--log-level` | `INFO` | `DEBUG`、`INFO`、`WARNING`、`ERROR` |
| `--discovery-port` / `--discovery-interval` | `8761` / `3` | UDP ビーコン: ポートと周期 |
| `--no-auth` | — | パスワードを無視 |
| `--no-wasm` | — | LVAR/RPN なし |
| `--no-discovery` | — | UDP ビーコンなし |
| `--build-apk [CONFIG]` | — | APK をビルドして終了 |

### 11.3. Android APK

インストールには Android ソースが含まれます。ビルド済み APK は
`android/dist/OpenDeck-Android-<version>.apk` に出力されます。ページ
`/android.html`（ログイン必須）では、名前、パッケージ ID、バージョン、デフォルト
のゲートウェイアドレスを変更し、その場で APK をビルドできます。JDK 17、
Android SDK、Gradle 8.x が必要です。リリースディストリビューションでは、APK は
すでに添付されています。

## 12. 診断

| 症状 | 確認事項 |
| --- | --- |
| スマートフォンからパネルが開かない | 同じ Wi-Fi、バナーのアドレス、Windows ファイアウォール（ポート 8760）、`--host 0.0.0.0` |
| 「パスワードログインが必要です」 | パスワードが設定されている。`/login.html` で入力する。QR トークンは 10 分間有効 |
| 「パスワードが正しくありません」 | キーボードレイアウト/大文字小文字。リセット: `config/auth.json` を削除するか `--no-auth` を使用 |
| 計器が「--」を表示 | SimConnect/WASM がない、mock が選択されている、機体にプロファイルがない、シミュレーターがまだメインメニューにある |
| プロファイルが切り替わらない | `sim.match` が名前/モデルと一致しない。手動で選択 |
| APK ビルドが開始しない | JDK/SDK/Gradle が見つからない。`/android.html` でパスを指定 |
| 「整合性違反」 | 重要ファイルが変更された。`python -m msfs_gateway.integrity --write` |
| `SimConnect_Open … 0x80004005` | ゲートウェイ自体が TCP `127.0.0.1:19999` を試みる。それでも解決しない場合 — `%APPDATA%\Microsoft Flight Simulator\SimConnect.cfg`（設定を上書きする）とフライトが読み込まれていることを確認。リモートシミュレーターの場合は `--simconnect-host/--simconnect-port` を設定 |

ログ: ゲートウェイコンソール（`--log-level DEBUG`）、ブラウザの「ネットワーク」
タブ、Android の場合は `adb logcat`（タグ `OpenDeckDiscovery`）。

## 13. セキュリティ

- パスワードは API とテレメトリを「Wi-Fi の隣人」から保護しますが、**トラフィック
  は TLS なしの HTTP 経由**です。信頼できる家庭内ネットワークでは許容されます。
  ゲストネットワークでは、別の VLAN または TLS 付きリバースプロキシを使用して
  ください。
- セッション Cookie は `HttpOnly` + `SameSite=Lax` です。CSRF リスクは軽減
  されます。URL トークンは WebSocket（`?token=`）とワンタイム QR（`?pair=`）
  にのみ使用されます。QR トークンは `/?pair=` 経由でのみ受け付けられ、セッション
  ではありません。
- ブラウザの POST/PUT と WebSocket に対する `Origin` チェック: 外部の
  `Origin` を持つリクエストは `403` を受け取ります。`Origin` のないクライアント
  は許可されます。
- ローカル名/IP に対する `Host` チェック: 未知の Host は `403` を受け取ります
  （DNS リバインディングへの保護）。
- ログイン試行はアドレスごとに 1 分あたり 5 回に制限されます。
- CORS は意図的に無効化されています: サードパーティのページは API 応答を読み
  取れません。
- パスワードが設定されていない場合、ゲートウェイはパネルとコマンドがローカル
  ネットワーク上の全員に利用可能であることをコンソールで明示的に警告します。
- UDP ビーコンは署名されていません: ネットワーク上の任意のホストがゲートウェイ
  を装うことができます。ゲートウェイをインターネットに公開しないでください。
- Android: WebView ナビゲーションの許可リスト、`file:`/`content:` へのアクセス
  は禁止、混合コンテンツは禁止。

## 14. 制限事項

- SimConnect/WASM のライブ実行には MSFS のインストールが必要です。リポジトリ
  ではロジックはエミュレーションで検証されています。
- APK はデバッグキーで署名されます。リリース署名はまだ自動化されていません。
- mDNS はありません: UDP ビーコンのみです。
- ポートごとに 1 つのアクティブなゲートウェイ。プロファイルはデータベースなし
  のファイルです。

## 15. 用語集

| 用語 | 意味 |
| --- | --- |
| **Gateway** | シミュレーターのある PC 上のプロセス: テレメトリを読み取り、クライアントに配信する |
| **Host** | ゲートウェイが動作するマシン（Android クライアントでは — 検出された PC） |
| **Profile** | 特定の機体用の計器とレイアウトを含む JSON ファイル |
| **Instrument / widget** | パネル要素: 姿勢指示器、ゲージ、スイッチなど |
| **Form factor** | 画面クラス: `phone`、`tablet-sm`、`tablet-lg` |
| **Aircraft** | シミュレーター内の特定の機体。プロファイルは `TITLE`/`ATC MODEL` で選択される |
| **Telemetry** | JSON フレーム内の SimVar と `custom.*` 値のストリーム |
| **Frame** | `seq`、`ts`、`sim`、`values` を持つ単一の `telemetry` メッセージ |
| **LVAR** | 機体のローカル変数（PMDG、Fenix、FBW など） |
| **RPN** | 逆ポーランド記法 — MSFS で値を計算するスクリプト |
| **WASM bridge** | MobiFlight/SimBridge モジュールの Client Data Area を介した LVAR/RPN 交換 |
| **Client Data Area** | データブロックを交換するための名前付き SimConnect エリア |
| **AP / APR / AT** | オートパイロット / ILS アプローチモード / オートスロットル |
| **Retard** | フレア中の滑らかなスロットル減少（着陸アシスト） |
| **TOGA** | Take Off / Go Around: フルスロットルとゴーアラウンド |
| **Pairing** | ワンタイム QR トークンを使用したスマートフォンからのログイン |
| **Session** | アクティブなログイン: Cookie/Bearer 内のトークン、TTL 12 時間 |
| **Integrity** | 重要 UI ファイルの SHA-256 とマニフェストとの比較 |
| **Air-gapped** | インターネットアクセスのないネットワーク。すべてのリソースがローカル |

## 16. フィードバックとサポート

- **作者:** Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)。
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。
- バグと提案 — GitHub の issue テンプレート経由（`.github/` を参照）。
- 脆弱性 — [security.md](security.md) に従って非公開で。
- セットアップの質問 — Discussions（有効な場合）または「Bug」テンプレートを
  使用した issue。
- ライセンスと必須の作者サポートブロック — [LICENSE](../../LICENSE)。

## 17. ライセンス

[GNU Affero General Public License v3.0](../../LICENSE) および
[追加条件 Section 7](../../COPYING.ADDITIONAL): ソースコードはオープンで、
改変版は AGPL の下で配布されます。作者サポートブロックと整合性チェックは必須で
あり、削除できません。
