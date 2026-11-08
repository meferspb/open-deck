# ✈️ Open Deck for MSFS

**Languages:** [English](README.md) · [Русский](README_RU.md) · [Deutsch](README_DE.md) · [中文](README_ZH.md) · [Español](README_ES.md) · [日本語](README_JA.md)


<img src="docs/pic1.jpg" alt="Open Deck for MSFS" width="220" />

**MSFS 2020/2024 の計器パネルを、スマートフォンやタブレットで — ローカル
ネットワーク経由、インターネットなしで。**

Windows 向けゲートウェイが、SimConnect（WASM モジュール経由の LVAR/RPN を
含む）を通じて Microsoft Flight Simulator からテレメトリを読み取り、HTTP +
WebSocket で Web クライアントと Android アプリに配信します。パネルは機体の
JSON プロファイルで記述され、3 つのフォームファクタ向けにレンダリングされます。

プロジェクトは完全に自己完結しています。**外部 CDN、フォント、サービスは
一切ありません** — すべてが分離されたネットワーク上、およびインターネット
接続のないマシン上で動作します。

| | |
| --- | --- |
| バージョン | 0.1.0 |
| テスト | Python 248 + Node.js 35 |
| ホストプラットフォーム | Windows 10/11（Python 3.11+ またはインストーラー） |
| クライアント | ブラウザ（任意のモダンブラウザ）、Android 8+ |
| 作者 | Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) |
| Donat | [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) |
| ライセンス | [GNU AGPL-3.0](LICENSE) — 作者サポートブロック（Section 7）を必須とする自由ソフトウェア |

## スクリーンショット

| スマートフォン | 大型タブレット |
| --- | --- |
| ![スマートフォン上のパネル](docs/screenshots/phone.png) | ![タブレット上のパネル](docs/screenshots/tablet-lg.png) |

| クラシックな C172 シックスパック | パネルエディター |
| --- | --- |
| ![シックスパック](docs/screenshots/sixpack-phone.png) | ![エディター](docs/screenshots/editor.png) |

![スマートフォンからのパスワードログイン](docs/screenshots/login.png)

![着陸・タキシーアシスト](docs/screenshots/assist.png)

## 機能

### ゲートウェイ

- **単一ポート**で静的ファイル、REST、WebSocket を提供 — ファイアウォール
  ルール 1 つで十分です。Python 標準ライブラリのみで動作し、`pip install` は
  不要です。
- **交換可能なテレメトリソース**:
  - `simconnect` — `ctypes` 経由のネイティブ SimConnect。
  - `mock` — シミュレーターなしの手続き型「フライト」（デモとテスト用）。
  - `auto` — SimConnect、失敗時は mock にフォールバック。
- **機体の自動検出**: プロファイルが `sim.match.title` と `atcModel` を宣言し、
  ゲートウェイが `TITLE`/`ATC MODEL` を読み取ってパネルを自動的に切り替えます。
- **WASM 経由の LVAR/RPN**（MobiFlight/SimBridge）: Client Data Area、
  タイムアウト付きの同期チャネル、RPN 経由の LVAR 書き込み。
- **ホストの自動検出**（UDP ビーコン、ネイティブクライアント向け）、組み込み
  HTTP サーバー、JSON API、プロファイルとコマンドの厳格な検証。

### プロファイルと計器

- **6 プロファイル**: Cessna 172S、Cessna 172 Classic Six-Pack、Daher TBM 930、
  Airbus A320、Piper PA-28-181、LVAR デモ。
- **計器**: 姿勢指示器、円形ゲージ、デジタル表示、トグルスイッチ、ロータリー
  セレクター（ジェスチャー/ホイール）、アナンシエーターライト、VSI、三針
  高度計、バグ付き方位指示器。
- パネル比率によるレイアウト + オーバーライド `layout.phone`、
  `layout.tablet-sm`、`layout.tablet-lg`。スキーマと検証 —
  [`docs/ja/profile-schema.md`](docs/ja/profile-schema.md)。

### クライアント

- **Web クライアント**はバニラ ES モジュール: 滑らかなアニメーション（rAF）、
  スムージング、ジェスチャー、コマンドウィジェット、再接続。
- **3 つのフォームファクタ**を画面幅に応じて自動選択。
- **コックピットの快適性**: パネル輝度 100/72/45 %（キー `B`）と UI なしの
  キオスクモード（`F`、`Esc` で終了）。
- **QR によるスマートフォン接続**: パネルページにホストアドレスの QR コードと
  ネットワークアドレスの一覧を表示。
- **Android クライアント**: WebView パネル、UDP ホスト検出、整合性チェック、
  手動アドレス入力付きの接続画面。

### セキュリティ

- **パスワードログイン**（6 文字以上）: PBKDF2 ハッシュ、`HttpOnly` Cookie の
  セッション、ネイティブクライアント向け Bearer トークン、試行回数制限、
  パスワード入力なしのスマートフォンからの QR ログイン。ワンタイム QR
  トークンは `/?pair=` 経由でのみ有効で、通常のセッションとしては受け付け
  られません。
- **同一オリジンおよび Host 保護**: 外部の `Origin` を持つブラウザの POST/PUT
  および WebSocket リクエスト、ならびに未知の `Host` を持つリクエストは拒否
  されます（`403`）。これにより CSRF、クロスサイト WebSocket ハイジャック、
  DNS リバインディングを防ぎます。`Origin` のないクライアント（Android、
  curl）は従来どおり動作します。
- 公開されるのはログインページ、ヘルス/整合性チェック、作者サポートブロック
  のみです — それ以外（プロファイル、テレメトリ、コマンド、APK ビルド）は
  すべて閉じられています。

### 着陸・タキシーアシスト

- **タキシー**: 目標速度（3〜25 kt）と方位を保持 — ゲートウェイがスロットルと
  ラダーを計算します。「STOP」はスロットル 0 とパーキングブレーキです。
- **着陸**: ARM で AP と APR を有効化し、60〜15 ft でアシストがスロットルを
  滑らかに絞り、接地時にオートパイロットを解除します。TOGA — ゴーアラウンド。
- ページ `/assist.html`（パネルヘッダーの「Assist」ボタン）。スマートフォンでも
  動作します。アシストは補助ループであり、飛行の制御はパイロットに残ります。

### ツール

- **パネルエディター** `/editor.html`: ドラッグ&ドロップ、リサイズ、
  1 % グリッドスナップ、元に戻す/やり直し（`Ctrl+Z` / `Ctrl+Y`）、フォーム
  ファクタ間のレイアウトコピー、プロファイルのホストへの保存。
- **Android APK ビルダー**がディストリビューション内に: ページ `/android.html`
  でアプリ名、パッケージ ID、バージョン、ゲートウェイアドレスを変更し、APK を
  ビルドしてダウンロードできます。CLI の `--build-apk` もあります。
- **Windows インストーラー**（NSIS、ユーザー単位、管理者権限不要）。ビルド済み
  APK と Android ソースを同梱。

### ライセンスと整合性

- 作者サポートブロックは**削除できません**。重要ファイルの SHA-256 はホスト
  起動時とブラウザ内で検証され、不一致の場合は UI がブロックされます。

## インストール（Windows、Python 不要）

リリースから `OpenDeck-Setup-<version>.exe` をダウンロードして実行し、
「次へ」をクリックします — 管理者権限は不要で、Python もインターネットも
必要ありません。インストール先は `%LOCALAPPDATA%\OpenDeck` で、ショートカット
と「プログラムと機能」のエントリが作成されます。

1. **Open Deck for MSFS** を起動します — パネルアドレスが表示されたコンソールが
   開きます。
2. ファイアウォールのプロンプトで、アプリにプライベートネットワークへのアクセス
   を許可します。
3. この PC でパネルを開くか、スマートフォンに表示されたアドレスを入力するか、
   パネルの QR（スマートフォンボタン）をスキャンします。

インストーラーのビルド詳細 — [`docs/ja/packaging.md`](docs/ja/packaging.md)。

## パスワードログイン

ログインは次のいずれかの方法で有効化できます:

```powershell
# パスワード（PBKDF2 ハッシュ）を config/auth.json に保存
OpenDeck.exe --set-password            # コンソールでパスワードの入力を求めます
OpenDeck.exe --set-password "my-password"

# または今回の実行のみ
OpenDeck.exe --password "my-password"
```

最小 **6 文字**。ファイル `config/auth.json` にはハッシュのみが保存されます。
削除すると、再びパスワードなしでアクセスできるようになります。スタートメニュー
には、インストーラーが「パスワードを設定」ショートカットを作成します。詳細 —
[サービス説明](docs/ja/service.md#8-パスワード認証)。

接続済みクライアント:

- ブラウザ — ページ `/login.html`、その後パネル（Cookie は 12 時間有効）。
- スマートフォン — パネルの QR をスキャン: ワンタイムトークンでパスワード入力
  なしにログイン（有効期間 10 分）。
- Android — パネル自体がログイン画面を表示し、セッションは WebView に保存
  されます。

## ソースからの実行

**Python 3.11+** が必要です。Node.js はクライアントテストのみで必要です。

```powershell
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# シミュレーターなしのデモモード: http://127.0.0.1:8760/
python -m msfs_gateway --sim mock

# 実際のフライト: SimConnect、失敗時は mock にフォールバック
python -m msfs_gateway --sim auto

# 明示的な DLL パスと 60 Hz
python -m msfs_gateway --sim simconnect --simconnect-dll C:\SDK\SimConnect.dll --telemetry-hz 60
```

便利なパラメーター:

| パラメーター | デフォルト | 用途 |
| --- | --- | --- |
| `--host` | `0.0.0.0` | リッスンアドレス |
| `--allow-host NAME` | — | Host ヘッダー用の追加 DNS 名（繰り返し指定可） |
| `--port` | `8760` | HTTP および WebSocket ポート |
| `--sim` | `auto` | `auto` / `mock` / `simconnect` |
| `--telemetry-hz` | `30` | ブロードキャストレート、1..60 Hz |
| `--simconnect-host` / `--simconnect-port` | `127.0.0.1` / `19999` | SimConnect アドレス（リモートシミュレーターを含む） |
| `--profile-dir` | `profiles/` | JSON プロファイルディレクトリ |
| `--password` / `--set-password` | — | 実行時のパスワード / ハッシュを保存して終了 |
| `--auth-file` / `--no-auth` | `config/auth.json` | ハッシュファイル / ログイン無効化 |
| `--no-wasm` | — | WASM ブリッジを無効化 |
| `--no-discovery` | — | UDP 自動検出を無効化 |
| `--build-apk [CONFIG]` | — | Android APK をビルドして終了 |

## ディストリビューションからの Android APK

インストール済みアプリには Android ソース（`android/`）が含まれます。ビルド
済み APK は `android/dist/OpenDeck-Android-<version>.apk` に出力され、スタート
メニューには「Build Android APK」（`http://127.0.0.1:8760/android.html`）が
あります。

ページではアプリ名、パッケージ ID、バージョン、デフォルトのゲートウェイ
アドレスを設定します。「Build APK」ボタンは同じコンピューター上で
`gradle assembleDebug` を実行します。**JDK 17**、**Android SDK**、**Gradle 8.x**
が必要です（パスはページで指定するか、`JAVA_HOME` / `ANDROID_HOME` /
`PATH` 内の `gradle` で設定できます）。リリースディストリビューションでは、
ビルド済み APK がすでに `android/dist` にあります。

```powershell
OpenDeck.exe --build-apk                        # config/android-build.json の設定
OpenDeck.exe --build-apk C:\path\settings.json
```

## ドキュメント

完全な索引は [docs/ja/README.md](docs/ja/README.md) です。主なドキュメント:

- [サービス説明: 目的、API、認証、アシスト、運用](docs/ja/service.md)
- [アーキテクチャと責務](docs/ja/architecture.md)
- [ネットワークプロトコル: REST、WebSocket、ログイン、QR、自動検出](docs/ja/protocol.md)
- [テレメトリ変数カタログ](docs/ja/telemetry.md) *(コードから生成)*
- [計器とオプションのカタログ](docs/ja/widgets.md) *(コードから生成)*
- [機体プロファイルスキーマ](docs/ja/profile-schema.md)
- [Android クライアント: ビルド、ログイン、デバッグ](docs/ja/android.md)
- [インストーラーのビルド](docs/ja/packaging.md)
- [接続サービスのコストとローカル代替の比較](docs/ja/pricing.md)
- [変更履歴](docs/ja/changelog.md)

## リポジトリ構成

```
msfs_gateway/            # Python ゲートウェイ（stdlib）
  sim/                   # プロバイダー: mock、simconnect、client_data、wasm_bridge
  qr.py                  # 組み込み QR ジェネレーター（SVG）
  assist.py              # 着陸・タキシーアシスト
  android_build.py       # ディストリビューションからの APK ビルド
  http_api.py, hub.py, profiles.py, integrity.py, discovery.py, websocket.py
web/                     # Web クライアントとエディター（バニラ JS、ビルド手順なし）
profiles/                # 機体 JSON プロファイル
android/                 # Android クライアント（Kotlin、AndroidX なし）
packaging/               # PyInstaller + NSIS: Windows インストーラー
scripts/                 # build-installer.ps1、check.ps1、verify_qr.py
tests/                   # unittest（Python）と node:test（JS）
docs/                    # アーキテクチャ、プロトコル、スキーマ、スクリーンショット
config/                  # 作者情報、APK ビルド設定
integrity/               # 重要ファイルの SHA-256 マニフェスト
```

## テスト

```powershell
python -m unittest discover -s tests        # 250 テスト
node --test "tests/web/*.test.mjs"          # 29 テスト
python -m ruff check msfs_gateway tests scripts
```

すべてのチェックを一度に実行:

```powershell
pwsh -File scripts/check.ps1
```

対象: テレメトリとプロファイル、WebSocket（RFC 6455）、バスとコマンド、
mock プロバイダー、WASM/Client Data、QR（構造 + 参照マトリックス）、
APK ビルダー、整合性、計器のジオメトリ、レイアウト。

## 開発

[`docs/ja/contributing.md`](docs/ja/contributing.md) を参照: スタイル、テスト、
プロファイルや計器の追加方法。セキュリティに関する質問 —
[`docs/ja/security.md`](docs/ja/security.md)。

## ロードマップ

1. **WASM ブリッジのライブ実行**（MSFS + MobiFlight/SimBridge。ロジックと
   エミュレーションはテストでカバー済み）。
2. **APK のリリース署名**: ビルダー設定の keystore/alias。
3. **mDNS（Bonjour）** を UDP ビーコンの代替として。
4. **エディター**: 配置ガイド、複数選択。
5. **Android**: ネイティブ Compose レンダリング、キオスクモード用フォアグラウンド
   サービス。
6. **テレメトリの記録/再生**（デモとプロファイリング用）。

## セキュリティ

プロジェクトは**信頼できるローカルネットワーク**向けに設計されています:
TLS なしの HTTP と認証、署名なしの UDP ビーコン。ゲートウェイをインターネット
に公開しないでください。詳細 — [`docs/ja/security.md`](docs/ja/security.md)。

## サポート / Donat

- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
- **作者:** Viktor Krasnikov
- **リポジトリ:** [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)

## ライセンス

プロジェクトは **GNU Affero General Public License v3.0（AGPL-3.0）** および
**Section 7** に基づく追加条件の下で配布されます。

* 同じライセンス（AGPL-3.0）が保持され、改変のソースコードが利用可能にされる
  限り（Section 13 に従ったサーバー上/ネットワーク経由の利用を含む）、この
  コードを使用、調査、改変、配布する自由があります。
* **必須条件（Section 7(b) & Section 5(d)）:** すべてのフォーク、ビルド、改変版
  において、元の作者（**Viktor Krasnikov**、
  [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)）
  への言及と、プログラムのユーザーインターフェースおよびドキュメント内の
  開発者サポート（ドネーション）ページへの有効なリンクを、削除、非表示、
  または改変することは**厳格に禁止**されています:
  [Donat — https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。

追加条件の詳細な法的文言はファイル [COPYING.ADDITIONAL](./COPYING.ADDITIONAL)
に記載されています。基本ライセンスの全文はファイル [LICENSE](./LICENSE) に
あります。
