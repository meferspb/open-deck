# 📚 Open Deck for MSFS ドキュメント

**Languages:** [English](../README.md) · [Русский](../ru/README.md) · [Deutsch](../de/README.md) · [中文](../zh/README.md) · [Español](../es/README.md) · [日本語](README.md)


<img src="../pic1.jpg" alt="Open Deck for MSFS" width="180" />

ここにはプロジェクトのすべてのドキュメントがまとめられています。まず
リポジトリルートの README から始めてください — 全体像とクイックスタートを
提供します。この索引は詳細を見つけるのに役立ちます。

## どこから始めるか

| あなたが… | 読む順序 |
| --- | --- |
| 「自分のために」パネルをセットアップするパイロット | [README](../../README_JA.md) → [service.md](service.md) |
| 仕組みを理解したい人 | [architecture.md](architecture.md) → [protocol.md](protocol.md) |
| クライアントや連携機能を書く人 | [protocol.md](protocol.md) → [telemetry.md](telemetry.md) |
| コードを変更する人 | [development.md](development.md) → [architecture.md](architecture.md) |
| 機体プロファイルを作る人 | [profile-schema.md](profile-schema.md) → [widgets.md](widgets.md) |
| インストーラー/APK をビルドする人 | [packaging.md](packaging.md) → [android.md](android.md) |
| セキュリティをレビューする人 | [security.md](security.md) |

## ドキュメント

| ドキュメント | 内容 | 対象読者 |
| --- | --- | --- |
| [service.md](service.md) | 完全なサービス説明: 目的、運用モデル、テレメトリ、プロファイル、クライアント、ネットワーク、認証、アシスト、API、インストール、診断、セキュリティ、ライセンス | 全員 |
| [architecture.md](architecture.md) | 内部設計: モジュール、データフロー、WASM ブリッジ、主要な決定、MVP の境界 | 開発者 |
| [protocol.md](protocol.md) | HTTP REST、WebSocket、パスワードおよび QR ログイン、自動検出、エラーコード、例 | 連携開発者 |
| [telemetry.md](telemetry.md) | すべての変数のカタログ: 型、単位、SimVar、イベント、`custom.*` — コードから生成 | クライアントおよびプロファイル開発者 |
| [widgets.md](widgets.md) | 計器カタログ: 必須バインディング、`command`、オプション、JSON 例 — コードから生成 | プロファイル作成者 |
| [profile-schema.md](profile-schema.md) | JSON プロファイルスキーマ: フィールド、レイアウト、検証、互換性、完全な例 | プロファイル作成者 |
| [development.md](development.md) | コードの変更方法: モジュールマップ、変数/計器/プロファイル/プロバイダー/ページの追加、テスト、リリース | コントリビューター |
| [pricing.md](pricing.md) | エアギャップ環境向けの「接続サービス vs ローカル代替」の比較 | スタックを選ぶ人 |
| [android.md](android.md) | Android クライアント: ビルド、アーキテクチャ、ログイン、デバッグ | Android 開発者 |
| [packaging.md](packaging.md) | インストーラー: 内容、ビルド、ショートカット、アンインストール、サイレントフラグ | リリースエンジニア |
| [contributing.md](contributing.md) | 参加方法: スタイル、テスト、プロファイル、PR | コントリビューター |
| [security.md](security.md) | 脅威モデル、保護対象、脆弱性の報告方法 | 全員 |
| [changelog.md](changelog.md) | バージョン履歴 | 全員 |

## スクリーンショット

`docs/screenshots/` — スマートフォンとタブレット上のパネル、シックスパック、
エディター、ログインページ、アシスト。README とサービス説明で使用されています。

## ドキュメントを最新に保つ

2 つのドキュメントは**コードから生成**され、テストでチェックされます:

```powershell
python -m msfs_gateway.docsgen --check   # telemetry.md と widgets.md
python -m msfs_gateway.docsgen --write   # レジストリ変更後に更新
```

`telemetry.py`、`profiles.py`、または Web 計器を変更した場合は、ドキュメントを
更新して `pwsh -File scripts/check.ps1` を実行してください。

## ドキュメントの書き方

- 英語で、短い段落と JSON/コマンドの例を使って書きます。
- リンクは相対パスにして、GitHub 上でもローカルでも動作するようにします。
- スキーマを重複させないでください: プロファイルは `profile-schema.md`、
  変数は `telemetry.md`、計器は `widgets.md`、ネットワークは `protocol.md` に
  あります。
- 動作を変更した場合は、README/サービス説明と `CHANGELOG.md` を更新します。
