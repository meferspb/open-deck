# 変更履歴

形式: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/)、
バージョン — [SemVer](https://semver.org/lang/ru/)。

## [Unreleased]

### 変更

- **Open Deck for MSFS** への完全なリブランディング: 製品名、Web インターフェース、
  Android アプリケーション（`com.opendeck.msfs`）、実行ファイル、インストーラー、
  ドキュメント、機体プロファイル。
- `docs/pic1.jpg` から生成されたロゴとアプリアイコン。ファイル
  `web/img/open-deck-mark.jpg`、`web/favicon.ico`、Android drawable、
  `packaging/windows/open-deck.ico`。

### 追加

- **Donat** リンク — [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) —
  を Web パネル、エディター、ログイン画面、アシスト、Android インターフェース、
  README、ドキュメントに追加。
- 作者 **Viktor Krasnikov** とリポジトリ
  [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) を明記。

### 修正

- SimConnect: `SIMCONNECT_RECV_SIMOBJECT_DATA` のフィールド順序を
  `SimConnect.h`（`dwFlags`/`dwEntryNumber`/`dwOutOf`/`dwDefineCount`）に合わせた
  — これがないとライブの数値テレメトリが更新されなかった。
- SimConnect: コマンドはディスパッチスレッドで実行される。イベント ID は
  再接続時にリセットされる。失敗した `AddToDataDefinition` が他のデータムの
  インデックスをずらさなくなった。
- WASM/Client Data: タイムアウト後のサーキットブレーカーと LVAR ブロック ≤ 56
  要素により、WASM モジュールがない場合でもテレメトリスレッドがブロックされ
  ない。
- QR トークンが通常のセッションとして受け付けられなくなり、TTL も延長されなく
  なった。
- ブラウザの POST/PUT と WebSocket に対する `Origin` チェック、およびローカル
  名/IP に対する `Host` チェックを追加（DNS リバインディングを防ぐ）。独自の
  DNS 名でアクセスするための `--allow-host` を追加。
- `login.js` の `next` 内のバックスラッシュを介したオープンリダイレクトを修正。
- リクエストボディのエラーが keep-alive 接続を非同期状態のままにしなくなった。
  同時接続数の制限を追加。
- `pair`/`token` トークンはリクエストログ内で編集される。
- アシスト: 高度/速度/方位の欠如がゼロで置き換えられない。APR が有効になら
  なかった場合、AP はロールバックされる。通信が失われるとループがオフになる。
  `stop` はコマンドが送信されなかった場合にエラーを報告する。
- テレメトリ: SimConnect 定義にない、または古い組み込み SimVar は `null` として
  返される（UI は `--` を表示）。
- SimVar の精度: `TURB ENG MAX TORQUE PERCENT:1`（最大値に対する現在のトルク
  の %）と、対地高度の代わりに `RADIO HEIGHT`。
- QR ダイアログは開いたときと TTL 切れのときにワンタイムトークンを再生成する。
- エディターはプロファイル変更時に履歴をクリアし、未保存の変更を警告する。
- Android ビルダー: `extraGradleArgs` の許可リスト、型チェック、ドライブ相対
  `outputDir` の禁止、安全な `appName`。
- Android: ポート付きの完全な URL が手動入力で再び受け付けられる。
- SimConnect: 再接続が一時設定の `OSError` に耐える。スレッドの停止がより
  堅牢になった。
- 自動検出ビーコンはオーバーフロー時にプロファイル一覧なしで送信され、完全に
  スキップされることはない。
- インメモリリミッターの増加を制限。REST コマンドに IP ごとのレート制限を追加。
- パスワードが無効な場合、コンソールは LAN へのオープンアクセスについて警告
  する。

## [0.1.0] — 2026-11-01

最初の公開リリース。

### 追加

- **着陸・タキシーアシスト**: 地上での速度/方位保持、ILS アプローチ用の
  ARM/DISARM/TOGA、60〜15 フィートでの自動 retard、接地時の AP 解除。ページ
  `/assist.html` と API `/api/assist*`。
- **パスワードログイン**（6 文字以上）: `config/auth.json` の PBKDF2 ハッシュ、
  `HttpOnly` Cookie の 12 時間セッション、Bearer トークン、スマートフォンからの
  ワンタイム QR ログイン、試行回数制限とブルートフォース保護。
- Python 製ゲートウェイ（stdlib のみ）: 単一ポートの HTTP + WebSocket
  （RFC 6455）、UDP 自動検出、JSON スキーマと検証を備えた機体プロファイル。
- テレメトリプロバイダー: `simconnect`（ctypes、文字列データム `TITLE` と
  `ATC MODEL`）、`mock`、自動フォールバック `auto`。
- SimConnect Client Data Area を介した LVAR/RPN WASM ブリッジ
  （MobiFlight/SimBridge）: リクエストチャネル、タイムアウト、再接続、RPN 経由の
  LVAR 書き込み。
- フレームワークなしの Web クライアント: 姿勢指示器、円形スケール、表示、
  トグルスイッチ、ロータリーセレクター、VSI、高度計、方位指示器。3 つの
  フォームファクタ。
- パネルエディター: ドラッグ&ドロップ、元に戻す/やり直し、グリッド、フォーム
  ファクタ間のレイアウトコピー、ホストへの保存。
- 名前と ATC モデルによる機体の自動検出。手動選択はシミュレーターで機体が
  変わるまで固定される。
- スマートフォンの迅速な接続: QR コード（stdlib 上の独自ジェネレーター）と
  ネットワークアドレスの一覧。
- Android クライアント: WebView パネル、UDP 検出、整合性チェック。
- ディストリビューション内の Android APK ビルダー: アプリ設定（名前、
  パッケージ ID、バージョン、ゲートウェイアドレス）、`/android.html` Web ページ
  と CLI `--build-apk` からのビルド。
- Windows インストーラー（NSIS、ユーザー単位、管理者権限なし）、完成 APK と
  Android ソースを同梱。
- コックピットの快適性: 3 段階のパネル輝度、キオスクモード。
- プロファイル: Cessna 172S、Cessna 172 Six-Pack、Daher TBM 930、Airbus A320、
  Piper PA-28、LVAR デモ。

### 修正

- 遅い、またはハングしたクライアントがテレメトリのブロードキャストを停止させ
  なくなった: 各接続には独自のキュー（8 フレーム）と送信スレッドがあり、古い
  フレームはバスのブロックではなく破棄される。
- WebSocket はプロトコル違反（マークなし、フラグメント化、大きすぎる制御
  フレーム）でコード 1002 でクローズされる。
- ゲートウェイの停止はハングしたクライアントを待たない: close フレームは
  タイムアウト付きで送信され、ソケットはどのような場合でも閉じられる。
- POST/PUT は常にリクエストボディを読み取る — APK ビルド開始後に keep-alive
  接続が壊れなくなった。
- APK ビルダー: タイムアウトウォッチドッグは、Gradle がハングして何も出力
  しなくても作動する。アプリ名では制御文字が禁止されている。
- Android: ホスト検索の迅速な再起動時の競合が新しい UDP 受信機を停止させ
  なくなった。
- エディター: 保存エラー時にリビジョンがロールバックされる。再クリックで並行
  保存が開始されない。
- 静的ファイル: NUL バイトを含むパスは例外ではなく 404 を返す。HEAD はボディを
  重複しない。クライアントによる接続切断がトレースバックでログを汚さない。

- SimConnect: ユーザーの `SimConnect.cfg` が存在しないチャネルを指している場合
  （`0x80004005` エラーのよくある原因）、ゲートウェイは自動的に TCP
  `127.0.0.1:19999` — MSFS 2020/2024 がリッスンするポート — で再接続を再試行
  する。アドレスとポートは `--simconnect-host` / `--simconnect-port` で設定
  できる。

### ドキュメント

- 完全なドキュメント索引 `docs/README.md`。開発者ガイド
  `docs/development.md`（コードマップ、変数/計器/プロファイル/プロバイダー/
  ページの追加、テスト、リリース）。
- `docs/telemetry.md` と `docs/widgets.md` のカタログはコードから生成される
  （`python -m msfs_gateway.docsgen --write`）。テストと CI が最新性と相対
  リンクを検証する。
- `docs/protocol.md` を完全に書き直し: アクセス、パスワードと QR、すべての
  エンドポイント、WebSocket、アシスト、APK ビルド、エラーコード、例。
- `docs/architecture.md`、`docs/service.md`（用語集、サポート）、
  `docs/profile-schema.md`、README、`android/README.md`、
  `packaging/windows/README.md` を更新。ドキュメントはインストーラーに含まれる。

### セキュリティ

- 起動時とブラウザ内での重要インターフェースファイルの SHA-256 チェック。
- CSP `default-src 'self'`、外部リソースの禁止、Android WebView のナビゲーション
  許可リスト。
