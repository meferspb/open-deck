# 🛠️ 開発と内部設計

コードを変更する人向けのドキュメント: どこに何があるか、変数、計器、
プロファイル、プロバイダー、ページを追加する方法、テストとリリースの方法。
ユーザー向けドキュメントは [service.md](service.md)、プロトコルは
[protocol.md](protocol.md) にあります。

## 1. 要件

- Windows 10/11（ゲートウェイは SimConnect に `ctypes` を使用します。それ
  以外はクロスプラットフォームです）。
- Python **3.11+**。サードパーティの依存関係はありません — 標準ライブラリの
  みです。
- Node.js **20+** — Web クライアントのテスト用（クライアント自体はビルドを
  必要としません）。
- JDK 17 + Android SDK + Gradle 8.x — APK のビルドのみ。
- PyInstaller と NSIS — インストーラーのみ。

## 2. コードマップ

```
msfs_gateway/
  app.py            dependency assembly, lifecycle, CLI modes
  settings.py       CLI arguments, paths, defaults
  telemetry.py      variable registry (keys, types, SimVars, events)
  hub.py            bus: frame, subscriptions, commands, aircraft autodetection
  http_api.py       HTTP: static files, REST, WebSocket upgrade, authorization
  websocket.py      RFC 6455: frames, ping/pong, close, send queue
  auth.py           password, PBKDF2, sessions, QR tokens, attempt limiting
  assist.py         taxi and landing assists (10 Hz)
  profiles.py       validation, storage, atomic profile saving
  legacy.py         adapter for the old v0 profile format
  integrity.py      SHA-256 manifest of critical files
  discovery.py      autodiscovery UDP beacon
  qr.py             QR generator (SVG) on stdlib
  android_build.py  settings, tool lookup, Gradle launch
  docsgen.py        generation of docs/telemetry.md and docs/widgets.md
  sim/              providers: mock, simconnect, client_data, wasm_bridge
web/                panel, editor, login, assist (vanilla ES modules)
profiles/           aircraft JSON profiles
android/            Kotlin client (WebView + UDP discovery)
packaging/windows/  PyInstaller + NSIS
scripts/            build-installer.ps1, check.ps1, verify_qr.py
tests/              unittest (Python) and node:test (JS)
docs/               this and other documentation
```

## 3. テレメトリ変数の追加方法

1. `msfs_gateway/telemetry.py` を開き、`_VARIABLES` に `Variable(...)` を追加
   します: キー、型、ラベル、`sim_var`/`sim_unit`、必要に応じて `sim_event`、
   `sim_event_param`、`sim_event_scale`。
2. MSFS SDK ドキュメントに対して SimVar 名を確認します（大文字小文字と単位が
   重要です）。
3. カタログを更新します: `python -m msfs_gateway.docsgen --write`。
4. `python -m unittest tests.test_telemetry` と完全なスイートを実行します。
5. 変数が制御用の場合 — イベントが実際に状態を変更することを確認します
   （`bool` 比較は現在の値を使用します）。

## 4. 計器の追加方法

1. `web/js/widgets/my-widget.js` を作成します: `update(state)` と `destroy()`
   を持つクラス（`base.js` と隣接する計器を参照）。レンダリングは canvas また
   は DOM。
2. `web/js/widgets/registry.js` にタイプを登録します。
3. `WIDGET_TYPES` にタイプを、`REQUIRED_BINDINGS` に必須ロールを追加し、
   必要に応じて `msfs_gateway/profiles.py` にオプションチェックを追加します。
4. `msfs_gateway/docsgen.py` に計器を記述し（`WIDGET_ORDER`、`WIDGET_TITLES`、
   `WIDGET_DESCRIPTIONS`、`WIDGET_OPTIONS`、例）、
   `python -m msfs_gateway.docsgen --write` を実行します。
5. 3 つのフォームファクタ（phone/small/large tablet）すべてとエディターで
   確認します。`tests/web/` にジオメトリテストを追加します。

## 5. 機体プロファイルの追加方法

1. `profiles/` から類似のプロファイルをコピーし、`id`、`name`、`icao`、
   `sim.match`（`TITLE`/`ATC MODEL` に対する glob）を変更します。
2. 検証を確認します: `python -m unittest tests.test_profiles`。
3. `base` レイアウト + フォームファクタの差分を構築します。矩形が `0..1` を
   超えないようにします。
4. エディター `/editor.html` と実際の機体で確認します（MSFS が利用可能な場合）。
5. README（一覧）と CHANGELOG にプロファイルを追加します。

## 6. テレメトリプロバイダーの追加方法

1. `SimProvider`（`sim/base.py`）をサブクラス化し、`start`、`stop`、`read`、
   `apply_command`、`connected` を実装します。必要に応じて
   `select_aircraft`、`aircraft_title`、`atc_model`。
2. `sim/__init__.py:create_sim()` に選択肢を登録し、値を `SIM_CHOICES`
   （`settings.py`）に追加します。
3. スレッドセーフティ: `read()` と `apply_command()` は異なるスレッドから
   呼ばれる可能性があるため、ロックを使用します。
4. フェイクトランスポートでテストを追加します（`tests/test_mock_sim.py` を
   参照）。

## 7. エンドポイントの追加方法

1. `_handle_api_get/post/put`（`http_api.py`）でパスを処理します。
2. 公開かセッション保護かを決定します: 公開は `PUBLIC_API_PATHS` のみ。
   それ以外は自動的に閉じられます。
3. `_send_json`/`ApiError` を通じて応答します。エラーは機械可読な `code` を
   持ちます。
4. `docs/protocol.md`（表 + 例）と `docs/service.md`（API セクション）に
   エンドポイントを文書化します。
5. `tests/` にテストを追加します（必要に応じてユニット + HTTP 統合）。

## 8. ページの追加方法

1. HTML を `web/`、JS を `web/js/`、スタイルを `web/css/` に置きます。
2. ページはデフォルトで**閉じられています**（`/login.html` とそのファイルを
   除く）。セッションがない場合、サーバーはログインへ `302` を返します。
3. パネルヘッダー（`web/index.html`）にリンクを追加し、マニフェストを再ビルド
   します: `python -m msfs_gateway.integrity --write`。
4. スマートフォン（`?device=phone`）とキオスクモードで確認します。

## 9. テストとチェック

```powershell
pwsh -File scripts/check.ps1       # ruff + format + Python 252 + JS 41
python -m unittest discover -s tests
node --test "tests/web/*.test.mjs"
python -m msfs_gateway.docsgen --check
python -m msfs_gateway.integrity
```

テスト戦略:

- **純粋なロジック**（検証、プロファイル、QR、アシストコントローラー、認証）
  — ネットワークや MSFS なしのユニットテスト。
- **HTTP/WebSocket** — `127.0.0.1:0` で
  `GatewayApplication.start_background()` を起動し、`http.client`/生ソケットを
  使用します。
- **SimConnect/WASM** — フェイク DLL/トランスポート。ライブフライトは手動で
  検証します。
- **Web** — 純粋な関数（レイアウト、`isConnectionStale`）に対する `node:test`。

## 10. ドキュメント

- `docs/telemetry.md` と `docs/widgets.md` はコードから**生成**されます。
  手動編集は上書きされます。`docsgen.py` を変更して `--write` を実行します。
- その他のドキュメントは手動です。動作が変わった場合は、`service.md`、
  `protocol.md`、`profile-schema.md`、`CHANGELOG.md` を更新します。
- 最新性のチェックは `scripts/check.ps1` に組み込まれています
  （docsgen --check）。
- 索引 — [docs/README.md](README.md)。

## 11. ビルドとリリース

1. バージョンを更新します（`msfs_gateway/__init__.py`、
   `config/android-build.json`、`packaging/windows/README.md`）。
2. `python -m msfs_gateway.integrity --write`（重要ファイルが変更された場合）。
3. `pwsh -File scripts/build-installer.ps1 -Version <x.y.z> -NsisPath <NSIS>`。
4. クリーンなマシンでインストール/アンインストールと `--set-password` を確認
   します。
5. APK をビルドし（`android/gradle assembleDebug`）、`android/dist` に置きます。
6. `CHANGELOG.md` を更新し、コミットして `v<x.y.z>` をタグ付けします。

## 12. 規約

- Python: stdlib のみ、`ruff format` による整形、行長 100。
- JS: ES モジュール、CDN やビルド手順なし。`node --check` と `node:test`。
- Kotlin: SDK と stdlib のみ、AndroidX なし。
- コメントとドキュメント — 英語。識別子 — 英語。
- 絶対に必要な場合を除いて外部依存関係を追加しないでください: プロジェクトは
  エアギャップインストール向けに設計されています。
