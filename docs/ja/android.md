# 📱 Open Deck for MSFS — Android クライアント

サードパーティライブラリなしのネイティブ Android アプリケーション（Kotlin）で、
スマートフォンやタブレットを MSFS の計器パネルに変えます:

- **自動検出** — UDP ビーコン（ポート 8761）による Windows ホストの検出と、
  手動 IP 入力。
- **パネルレンダリング** — WebView がホストから Web クライアントを読み込むため、
  Android 版はすべてのプロファイル、計器、エディター、UI 更新を自動的に取得
  します。
- **3 つのフォームファクタ**を画面サイズ（`smallestScreenWidthDp`）で選択:
  phone / tablet-sm / tablet-lg。
- **整合性チェック** — パネル表示前（作者サポートブロック保護に関するライセンス
  条件）。
- **パスワードログイン**: ゲートウェイでパスワードが有効な場合、WebView は
  ログインページを表示します。セッションは WebView Cookie に保存され、アプリの
  再起動後も維持されます。パスワード付きホストはロック 🔒 でマークされます。
- **キオスクモード**: 全画面 immersive、画面は消灯せず、パネルを再読み込みせずに
  回転できます。
- **作者サポートブロック**を接続画面に表示（詳細はホストから取得）。
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。

## ビルド要件

| コンポーネント | バージョン |
| --- | --- |
| JDK | 17+ |
| Android SDK | platform 35、build-tools 35.x |
| Gradle | 8.9+（プロジェクトは 8.10.2 でビルド） |
| Android Gradle Plugin | 8.7.3 |
| Kotlin | 2.0.21 |

`minSdk 26`（Android 8.0）、`targetSdk 35`。

## ビルド

このリポジトリで検証済み: **JDK 17.0.20.1（Temurin）、Gradle 8.10.2、
AGP 8.7.3、Kotlin 2.0.21、Android SDK platform 35 / build-tools 35.0.0**。
`assembleDebug` と `lintDebug` は成功します: **エラー 0**、情報警告 3 件
（ローカルネットワークの cleartext、overdraw、backup-rules）。

```bash
cd android

# SDK へのパスは ANDROID_HOME または local.properties で指定できます:
#   echo "sdk.dir=/path/to/android-sdk" > local.properties

# 方法 1: Android Studio — android/ ディレクトリを開いて Run をクリック

# 方法 2: コマンドライン（Gradle 8.9+）
gradle wrapper --gradle-version 8.10.2   # 1 回だけ実行、gradlew を作成
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk

# デバイスへのインストール
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

ビルド後、debug APK は `android/dist/OpenDeck-Android-<バージョン>.apk` に
現れます（debug 署名 — 自分のデバイスへのインストール用。公開にはリリース
キーが必要です）。

> **エアギャップビルドについて。** アプリケーションはサードパーティ
> ライブラリを使用しません: Android SDK と Kotlin stdlib のみです。ただし
> Gradle は AGP と Kotlin プラグインを Maven からダウンロードします。ビルド
> マシンが分離されている場合は、ビルドをすでに実行したマシンから Gradle
> キャッシュ（`~/.gradle/caches`）を移動するか、APK を事前にビルドして
> ファイルで配布してください。ゲートウェイのディストリビューション
> （`android/` + ビルド済み APK）では、`/android.html` ページからビルドでき
> ます。

## 仕組み

```
MainActivity
├── DiscoveryClient  → UDP 8761、ホストの JSON ビーコン（名前、IP、ポート、プロファイル、auth）
├── HostStore        → SharedPreferences: 最後のホスト
├── HostApi          → GET /api/health, /api/integrity, /api/donation
└── WebView          → http://<host>:<port>/?device=<preset>&frame=0
```

起動順序:

1. アプリケーションが UDP 受信機を起動し、見つかったホストを表示します
   （パスワード付きホストはロック付き）。
2. ユーザーがホストを選択するか、ネットワークがブロードキャストを遮断して
   いる場合はアドレスを手動で入力します。
3. パネル表示前に `GET /api/integrity` を実行します: ホストがインターフェース
   の整合性違反を報告した場合、パネルはメッセージとともにブロックされます。
4. パネルが WebView で開きます。ゲートウェイがパスワードを要求する場合、
   WebView は `/login.html` を表示します。ログイン後、Cookie が保存され、
   再度入力せずにパネルが開きます。
5. パネルヘッダーの「アシスタント」ボタンが `/assist.html`（着陸とタキシー）
   を開きます。スマートフォンでも動作します。

## 構造

```
android/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle.properties
├── gradle/wrapper/gradle-wrapper.properties
└── app/
    ├── build.gradle.kts
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/opendeck/msfs/
        │   ├── MainActivity.kt     # 画面、WebView、整合性ブロック、
        │   │                       # ログイン Cookie、アシストを開く
        │   ├── DiscoveryClient.kt  # UDP ビーコン受信機（スレッド世代）
        │   ├── HostApi.kt          # HTTP チェックとドネーション詳細
        │   └── HostStore.kt        # SharedPreferences 内の最後のホスト
        └── res/
            ├── layout/activity_main.xml, view_setup.xml
            ├── values/strings.xml, colors.xml, themes.xml
            ├── drawable/…          # open_deck_logo.png、カード、ドネーションパネル
            └── xml/network_security_config.xml
```

## デバッグ

- **ホストが見つからない**: スマートフォンと PC が同じサブネットにあること、
  PC でプライベートネットワークとポート 8760 のファイアウォールが許可されて
  いること。ビーコンは UDP 8761 に送信されます。アドレスを手動で入力して
  ください（`192.168.1.10:8760`）。
- **「ログインが必要です」**: ゲートウェイでパスワードが有効です — ログイン
  ページで入力してください。パネルの QR コードはパスワードなしでログインします
  （10 分）。
- **整合性チェックが失敗する**: ホスト上のインターフェースファイルが変更されて
  います — マニフェストを再ビルドしてください
  （`python -m msfs_gateway.integrity --write`）。
- **ログ**: `adb logcat -s OpenDeckDiscovery OpenDeck`、WebView ログは Chrome
  DevTools（`chrome://inspect`）経由。
- **APK のインストール**: 不明なソースからのインストールを許可してください。
  リリースビルドには独自の署名が必要です。

## セキュリティ

- TLS なしの HTTP: ネットワークはローカルで信頼されており、
  `usesCleartextTraffic` は意図的に有効化されています。パスワードはログインを
  保護しますが、トラフィックを暗号化しません。
- WebView: ナビゲーションの許可リスト、`file:`/`content:` は禁止、混合
  コンテンツは禁止、Cookie はゲートウェイの `HttpOnly` セッションのみ。
- ドネーション詳細はホストから取得されます。ブロックは削除できません
  （ライセンス条件）。

## 制限事項と次のステップ

- パネルはホストの Web クライアントをレンダリングします: これにより機能の
  100 % の同等性が得られますが、WebView が必要です（Android 8+ には搭載）。
- 計器の完全にネイティブな Compose レンダリングは別のエンジンです。プロトコル
  （`/api/profiles`、`/ws`）はすでに準備されています。
- フォアグラウンドサービスはありません: 長時間最小化すると Android が WebView
  を一時停止する可能性があります — キオスクではアプリを画面に表示したままに
  してください。
