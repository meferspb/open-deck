# 開発への参加

ご協力ありがとうございます! プロジェクトは小さく、意図的にシンプルです:
依存関係のない Python、ビルドツールのないバニラ JS、素の SDK/Kotlin による
Android。

## 開発者向けクイックスタート

```powershell
# 1. リポジトリをクローン
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# 2. デモモードでゲートウェイを起動（MSFS 不要）
python -m msfs_gateway --sim mock

# 3. http://127.0.0.1:8760/ を開く
```

要件: **Python 3.11+**。クライアントテストには **Node.js 20+**。
Android APK のビルドには **JDK 17**、**Android SDK**、**Gradle 8.x**。

## PR 前のチェック

```powershell
pwsh -File scripts/check.ps1
```

スクリプトは次を実行します:

- Python の `ruff check` と `ruff format --check`。
- `python -m unittest discover -s tests`（249 テスト）。
- Node.js がインストールされている場合、
  `node --test "tests/web/*.test.mjs"`（29 テスト）。

リンターツールのインストール: `python -m pip install ruff`。

## コードスタイル

- **Python**: PEP 8、`ruff format` による整形、行長 100。標準ライブラリのみ —
  新しい依存関係は追加しません。
- **JS**: ES モジュール、フレームワークや外部 CDN なし。構文チェック —
  `node --check`、テスト — `node --test`。
- **Kotlin**: Android SDK と Kotlin stdlib のみ、AndroidX とサードパーティ
  ライブラリなし。
- コメントとドキュメント — ロシア語。コード内の名前 — 英語。
- すべてのユーザー向け文字列は**オフライン**で動作しなければなりません:
  外部フォント、画像、API は禁止です。

## 改善できること

[`README.md`](../../README_JA.md#ロードマップ) と
[`architecture.md`](architecture.md) を参照してください。良い方向性:

- 新しい機体プロファイル（`profiles/*.json`）— 歓迎します。
- 新しい計器タイプ（`web/js/widgets/`、レジストリ `registry.js`）と、
  `msfs_gateway/profiles.py`（`WIDGET_TYPES`、`REQUIRED_BINDINGS`）への登録。
- テスト: 純粋なロジック（計器のジオメトリ、プロファイル、プロトコル）を
  優先。
- ドキュメント: コードと `docs/` の不一致はバグと見なされます。

## 機体プロファイル

1. `profiles/` から既存のプロファイルをコピーし、`id`、`name`、`sim.match` を
   変更します。
2. 検証を確認します:
   `python -c "from msfs_gateway.profiles import ProfileStore; ..."` —
   または単にゲートウェイを起動します: 壊れたプロファイルは警告付きでスキップ
   されます。
3. バインディングは `GET /api/telemetry/variables` から取得します（エディターは
   それらを一覧で表示します）。
4. PR に、どのアドオンで検証したかの説明を添付してください。

## コミットと PR

- アトミックなコミット、命令形のメッセージ: `add A320 profile`、
  `fix QR mask`。
- PR には、何を変更したか、なぜか、どのように検証したか（テスト/スクリーン
  ショット）を含めます。
- インターフェースの変更には `docs/screenshots/` にスクリーンショットを添付
  してください。

## 貢献のライセンス

PR を送信することで、あなたの貢献がプロジェクトのライセンス
（[LICENSE](../../LICENSE)）の下で配布されることに同意したものと見なされます。
作者サポートブロックと整合性チェックを削除または置き換えないでください —
これはライセンス条件です。
