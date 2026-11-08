# 📱 Open Deck for MSFS — Android 客户端

原生 Android 应用（Kotlin，无第三方库），可将手机或平板变成 MSFS 仪表板：

- 通过 UDP 信标（端口 8761）**自动发现** Windows 主机，并支持手动输入 IP；
- **面板渲染**——WebView 从主机加载 Web 客户端，因此 Android 版本会自动获得所有配置文件、仪表、编辑器和 UI 更新；
- 根据屏幕尺寸（`smallestScreenWidthDp`）选择**三种形态因素**：phone / tablet-sm / tablet-lg；
- 在显示面板前进行**完整性检查**（许可证关于保护作者支持区块的条件）；
- **密码登录**：如果网关启用了密码，WebView 会显示登录页面；会话存储在 WebView cookie 中，并在应用重启后保留；受密码保护的主机会标记为锁形图标 🔒；
- **kiosk 模式**：全屏沉浸式、屏幕常亮、旋转时不重新加载面板；
- 连接屏幕上的**作者支持区块**（信息来自主机）；
- **捐赠：** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)。

## 构建要求

| 组件 | 版本 |
| --- | --- |
| JDK | 17+ |
| Android SDK | platform 35、build-tools 35.x |
| Gradle | 8.9+（项目基于 8.10.2 构建） |
| Android Gradle Plugin | 8.7.3 |
| Kotlin | 2.0.21 |

`minSdk 26`（Android 8.0），`targetSdk 35`。

## 构建

已在此仓库中验证：**JDK 17.0.20.1（Temurin）、Gradle 8.10.2、AGP 8.7.3、Kotlin 2.0.21、Android SDK platform 35 / build-tools 35.0.0**。`assembleDebug` 和 `lintDebug` 均通过：**0 个错误**，3 条信息性警告（本地网络明文、过度绘制、备份规则）。

```bash
cd android

# SDK 路径可以通过 ANDROID_HOME 或 local.properties 设置：
#   echo "sdk.dir=/path/to/android-sdk" > local.properties

# 选项 1：Android Studio——打开 android/ 目录并点击 Run

# 选项 2：命令行（Gradle 8.9+）
gradle wrapper --gradle-version 8.10.2   # 仅一次，生成 gradlew
./gradlew assembleDebug
# APK：app/build/outputs/apk/debug/app-debug.apk

# 安装到设备
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

构建完成后，调试版 APK 会出现在 `android/dist/OpenDeck-Android-<版本>.apk`（调试签名——用于安装到自己的设备；发布需要 release 密钥）。

> **关于 air-gapped 构建。** 应用不使用第三方库：仅 Android SDK 和 Kotlin 标准库。但 Gradle 仍会从 Maven 下载 AGP 和 Kotlin 插件。如果构建机器是隔离的，请从已执行过构建的机器复制 Gradle 缓存（`~/.gradle/caches`），或预先构建 APK 并以文件形式分发。在网关发行版中（`android/` + 已构建的 APK），可以从 `/android.html` 页面进行构建。

## 工作原理

```
MainActivity
├── DiscoveryClient  → UDP 8761, 主机 JSON 信标（名称、IP、端口、配置文件、auth）
├── HostStore        → SharedPreferences: 最后的主机
├── HostApi          → GET /api/health, /api/integrity, /api/donation
└── WebView          → http://<host>:<port>/?device=<preset>&frame=0
```

启动顺序：

1. 应用启动 UDP 接收器并显示发现的主机（有密码的主机带锁形图标）。
2. 用户选择主机，或在网络阻止广播时手动输入地址。
3. 在显示面板前执行 `GET /api/integrity`：如果主机报告界面完整性违规——面板会被阻止并显示消息。
4. 面板在 WebView 中打开。如果网关要求密码，WebView 会显示 `/login.html`；登录后 cookie 会被保存，再次打开面板无需重新输入。
5. 面板标题栏中的“辅助”按钮会打开 `/assist.html`（着陆和滑行）；在手机上也可用。

## 结构

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
        │   ├── MainActivity.kt     # 屏幕、WebView、完整性阻断、
        │   │                       # 登录 cookie、打开辅助
        │   ├── DiscoveryClient.kt  # UDP 信标接收器（线程代际）
        │   ├── HostApi.kt          # HTTP 检查和捐赠信息
        │   └── HostStore.kt        # SharedPreferences 中的最后主机
        └── res/
            ├── layout/activity_main.xml, view_setup.xml
            ├── values/strings.xml, colors.xml, themes.xml
            ├── drawable/…          # open_deck_logo.png、卡片、捐赠横幅
            └── xml/network_security_config.xml
```

## 调试

- **找不到主机**：手机和 PC 在同一子网，PC 防火墙允许专用网络和端口 8760；信标发往 UDP 8761。手动输入地址（`192.168.1.10:8760`）。
- **“需要登录”**：网关启用了密码——在登录页面输入；面板上的二维码可免密码登录（10 分钟）。
- **完整性检查未通过**：主机上的界面文件已被修改——重建清单（`python -m msfs_gateway.integrity --write`）。
- **日志**：`adb logcat -s OpenDeckDiscovery OpenDeck`，WebView 日志——通过 Chrome DevTools（`chrome://inspect`）。
- **安装 APK**：允许从未知来源安装；release 构建需要自己的签名。

## 安全

- 无 TLS 的 HTTP：网络是本地且可信的，`usesCleartextTraffic` 是有意启用的；密码保护登录，但不加密流量。
- WebView：导航允许列表，禁止 `file:`/`content:`，禁止混合内容，cookie——仅限网关的 `HttpOnly` 会话。
- 捐赠信息来自主机；该区块不可移除（许可证条件）。

## 限制与后续步骤

- 面板由主机的 Web 客户端渲染：这带来 100 % 的功能对等，但需要 WebView（任何 Android 8+ 都有）。
- 完全原生的 Compose 仪表渲染是另一个独立引擎；协议（`/api/profiles`、`/ws`）已为其准备就绪。
- 没有前台服务：长时间最小化时 Android 可能会暂停 WebView——对于 kiosk 用途，请保持应用在前台。
