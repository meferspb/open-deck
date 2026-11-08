# 📱 Open Deck for MSFS — Android-клиент

Нативное Android-приложение (Kotlin, без сторонних библиотек), которое
превращает телефон или планшет в приборную панель MSFS:

- **автообнаружение** Windows-хоста по UDP-бикону (порт 8761) и ручной ввод IP;
- **рендеринг панели** — WebView загружает веб-клиент с хоста, поэтому
  Android-версия автоматически получает все профили, приборы, редактор и
  обновления UI;
- **три форм-фактора** выбираются по размеру экрана (`smallestScreenWidthDp`):
  phone / tablet-sm / tablet-lg;
- **проверка целостности** перед показом панели (условие лицензии о защите
  блока поддержки автора);
- **вход по паролю**: если на шлюзе включён пароль, WebView показывает
  страницу входа; сессия хранится в cookie WebView и переживает перезапуск
  приложения; хосты с паролем помечены замком 🔒;
- **киоск-режим**: полноэкранный immersive, экран не гаснет, поворот без
  перезагрузки панели;
- **блок поддержки автора** на экране подключения (реквизиты приходят с хоста);
- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

## Требования для сборки

| Компонент | Версия |
| --- | --- |
| JDK | 17+ |
| Android SDK | platform 35, build-tools 35.x |
| Gradle | 8.9+ (проект собран под 8.10.2) |
| Android Gradle Plugin | 8.7.3 |
| Kotlin | 2.0.21 |

`minSdk 26` (Android 8.0), `targetSdk 35`.

## Сборка

Проверено на этом репозитории: **JDK 17.0.20.1 (Temurin), Gradle 8.10.2,
AGP 8.7.3, Kotlin 2.0.21, Android SDK platform 35 / build-tools 35.0.0**.
`assembleDebug` и `lintDebug` проходят: **0 ошибок**, 3 информационных
предупреждения (cleartext в локальной сети, overdraw, backup-rules).

```bash
cd android

# путь к SDK можно задать через ANDROID_HOME или local.properties:
#   echo "sdk.dir=/path/to/android-sdk" > local.properties

# вариант 1: Android Studio — открыть каталог android/ и нажать Run

# вариант 2: командная строка (Gradle 8.9+)
gradle wrapper --gradle-version 8.10.2   # один раз, создаст gradlew
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk

# установка на устройство
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

После сборки debug-APK появляется в `android/dist/OpenDeck-Android-<версия>.apk`
(debug-подпись — для установки на своё устройство; для публикации нужен
release-ключ).

> **Про air-gapped сборку.** Приложение не использует сторонних библиотек:
> только Android SDK и Kotlin stdlib. Но Gradle всё равно скачивает AGP и
> Kotlin-плагин из Maven. Если сборочная машина изолирована, перенесите
> Gradle-кэш (`~/.gradle/caches`) с машины, где сборка уже выполнялась, или
> соберите APK заранее и распространяйте файлом. В дистрибутиве шлюза
> (`android/` + собранный APK) сборка доступна со страницы `/android.html`.

## Как это работает

```
MainActivity
├── DiscoveryClient  → UDP 8761, JSON-бикон хоста (имя, IP, порт, профили, auth)
├── HostStore        → SharedPreferences: последний хост
├── HostApi          → GET /api/health, /api/integrity, /api/donation
└── WebView          → http://<host>:<port>/?device=<preset>&frame=0
```

Порядок запуска:

1. Приложение поднимает UDP-приёмник и показывает найденные хосты
   (у хостов с паролем — замок).
2. Пользователь выбирает хост или вводит адрес вручную, если сеть режет
   broadcast.
3. Перед показом панели выполняется `GET /api/integrity`: если хост сообщает
   о нарушении целостности интерфейса — панель блокируется с сообщением.
4. Панель открывается в WebView. Если шлюз требует пароль, WebView
   показывает `/login.html`; после входа cookie сохраняется, и панель
   открывается без повторного ввода.
5. Кнопка «Ассистент» в шапке панели открывает `/assist.html` (посадка и
   руление); работает и на телефоне.

## Структура

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
        │   ├── MainActivity.kt     # экраны, WebView, блокировка целостности,
        │   │                       # cookie входа, открытие ассистента
        │   ├── DiscoveryClient.kt  # UDP-приёмник биконов (поколения потоков)
        │   ├── HostApi.kt          # HTTP-проверки и реквизиты доната
        │   └── HostStore.kt        # последний хост в SharedPreferences
        └── res/
            ├── layout/activity_main.xml, view_setup.xml
            ├── values/strings.xml, colors.xml, themes.xml
            ├── drawable/…          # open_deck_logo.png, карточки, плашка доната
            └── xml/network_security_config.xml
```

## Отладка

- **Хост не находится**: телефон и ПК в одной подсети, на ПК разрешён
  брандмауэр для частных сетей и порт 8760; бикон идёт на UDP 8761.
  Введите адрес вручную (`192.168.1.10:8760`).
- **«Требуется вход»**: на шлюзе включён пароль — введите его на странице
  входа; QR-код с панели входит без пароля (10 минут).
- **Проверка целостности не проходит**: файлы интерфейса на хосте изменены —
  пересоберите манифест (`python -m msfs_gateway.integrity --write`).
- **Логи**: `adb logcat -s OpenDeckDiscovery OpenDeck`, логи WebView — через Chrome
  DevTools (`chrome://inspect`).
- **Установка APK**: разрешите установку из неизвестных источников; для
  release-сборки нужна своя подпись.

## Безопасность

- HTTP без TLS: сеть локальная и доверенная, `usesCleartextTraffic` включён
  осознанно; пароль защищает вход, но не шифрует трафик.
- WebView: allow-list навигации, `file:`/`content:` запрещены, смешанный
  контент запрещён, cookie — только `HttpOnly`-сессия шлюза.
- Реквизиты доната приходят с хоста; блок нельзя удалить (условие лицензии).

## Ограничения и следующие шаги

- Панель рендерит веб-клиент хоста: это даёт 100 % паритет функций, но требует
  WebView (есть на любом Android 8+).
- Полностью нативный Compose-рендеринг приборов — отдельный движок; протокол
  (`/api/profiles`, `/ws`) для него уже готов.
- Нет foreground-service: при долгом сворачивании Android может приостановить
  WebView — для киоска держите приложение на экране.