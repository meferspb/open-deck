# Windows 用インストーラー

単一ファイル `OpenDeck-Setup-<バージョン>.exe`: ダブルクリック → 「次へ」 →
完了。管理者権限は不要で、Python もインターネットも必要ありません。

## インストール時に何が起こるか

| | |
|---|---|
| ディレクトリ | `%LOCALAPPDATA%\OpenDeck`（ユーザープロファイル内、UAC なし） |
| 内容 | `OpenDeck.exe` — Python 3.13 と標準ライブラリを内蔵したゲートウェイ |
| | `web/` — Web クライアント（パネルとエディター）、`profiles/` — 機体プロファイル |
| | `config/donation.json` — 作者情報、`integrity/` — 整合性マニフェスト |
| | `android/` — Android ソースと、ビルド後の完成 APK（`android/dist/OpenDeck-Android-<バージョン>.apk`）、`config/android-build.json` — APK ビルド設定 |
| | `docs/` — 完全なドキュメント（サービス、プロトコル、変数、計器、プロファイルスキーマ） |
| ショートカット | デスクトップ、スタートメニュー（起動、ブラウザでのパネル、Android APK のビルド、「パスワードを設定」、アンインストール） |
| アンインストール | 「プログラムと機能」または「アンインストール」ショートカット |

データは `.exe` の隣にあるため、プロファイルと作者情報は再インストールせずに
編集できます（保護されたファイルを編集した後は、マニフェストを再ビルドする
必要があります。ルート README を参照）。

## ビルド（開発マシン上、インターネットは 1 回だけ必要）

要件:

- Python 3.11+ と PyInstaller: `python -m pip install pyinstaller`
- NSIS 3.x: `makensis.exe` が `PATH` にあるか、`NSIS_HOME`、または `-NsisPath`

```powershell
# リポジトリのルートから
pwsh -File scripts/build-installer.ps1 -Version 0.1.0 -NsisPath "C:\Program Files (x86)\NSIS"
```

スクリプトの手順: 整合性マニフェストを再ビルド → テストを実行 →
`build/pyinstaller/dist/OpenDeck` をビルド（PyInstaller、onedir）→
`web/`、`profiles/`、`config/`、`integrity/` を隣に配置 → `.exe` が起動する
ことを確認（`--help`）→ インストーラーを
`dist/OpenDeck-Setup-<バージョン>.exe` にコンパイル。

フラグ: `-SkipTests`、`-NsisPath <フォルダー>`、`-Version 0.2.0`。

スクリプトはインストーラーがビルドされたことも確認し、最終パスとサイズを
表示します。手順の完全な一覧は `scripts/build-installer.ps1` の冒頭にあります。

パスワードログイン: 「パスワードを設定」ショートカットが
`OpenDeck.exe --set-password` を起動し、コンソールでパスワードを尋ねます。
ハッシュは `.exe` の隣の `config/auth.json` に保存されます。ファイルを削除
すると、再びログインなしでアクセスできるようになります。

## 公開前の確認

1. `config/donation.json` を確認: 作者 Viktor Krasnikov、Donat リンク —
   `https://taps.uz/open_deck_fs`。
2. マニフェストを再ビルド: `python -m msfs_gateway.integrity --write`
   （ビルドスクリプト自体がこれを行いますが、確認しても損はありません）。
3. クリーンなマシンでインストーラーを実行: 管理者なしのインストール、起動、
   同じネットワーク上のスマートフォンからのパネルアクセス、アンインストール。

## サイレントインストール / 展開

```bat
OpenDeck-Setup-0.1.0.exe /S /D=C:\Tools\OpenDeck
Uninstall.exe /S
```

`/D=` は最後に置き、引用符なしで指定する必要があります（NSIS の制限）。

## 制限事項

- インストーラーは署名されていません: SmartScreen が「不明な発行元」と警告する
  場合があります — 「詳細」→「実行」を選択してください。リリースにはコード
  署名証明書（EV/OV）が必要です。
- ファイアウォールルールは追加されません（管理者権限が必要）。初回起動時に
  Windows がネットワークアクセスについて尋ねます — プライベートネットワークで
  許可してください。そうしないとクライアントが接続できません。
- ユーザー単位のインストール: アプリは現在のユーザーにのみ表示されます。
- レジストリ/ショートカットは `HKCU` に作成されます — 厳格なポリシーのある
  マシン（AppLocker、プロファイルへの書き込み禁止）ではインストールがブロック
  される場合があります。その場合はポータブル版を使用してください:
  `build/pyinstaller/dist/OpenDeck` ディレクトリを展開し、そこから `.exe` を
  実行します。
