# ✈️ Open Deck for MSFS

**Languages:** [English](README.md) · [Русский](README_RU.md) · [Deutsch](README_DE.md) · [中文](README_ZH.md) · [Español](README_ES.md) · [日本語](README_JA.md)


<img src="docs/pic1.jpg" alt="Open Deck for MSFS" width="220" />

**Приборные панели MSFS 2020/2024 на телефоне и планшете — по локальной сети,
без интернета.**

Шлюз на Windows читает телеметрию из Microsoft Flight Simulator через
SimConnect (включая LVAR/RPN через WASM-модуль) и раздаёт её веб-клиентам и
Android-приложению по HTTP + WebSocket. Панели описываются JSON-профилями
самолётов и рендерятся под три форм-фактора.

Проект полностью автономен: **ни одного внешнего CDN, шрифта или сервиса** —
всё работает в изолированной сети и на машине без доступа в интернет.

| | |
| --- | --- |
| Версия | 0.1.0 |
| Тесты | 250 Python + 35 Node.js |
| Платформа хоста | Windows 10/11 (Python 3.11+ или установщик) |
| Клиенты | браузер (любой современный), Android 8+ |
| Автор | Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck) |
| Donat | [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs) |
| Лицензия | [GNU AGPL-3.0](LICENSE) — свободное ПО с обязательным блоком поддержки автора (Section 7) |

## Скриншоты

| Телефон | Большой планшет |
| --- | --- |
| ![Панель на телефоне](docs/screenshots/phone.png) | ![Панель на планшете](docs/screenshots/tablet-lg.png) |

| Классическая «шестёрка» C172 | Редактор панелей |
| --- | --- |
| ![Six-pack](docs/screenshots/sixpack-phone.png) | ![Редактор](docs/screenshots/editor.png) |

![Вход по паролю с телефона](docs/screenshots/login.png)

![Ассистент посадки и руления](docs/screenshots/assist.png)

## Возможности

### Шлюз

- **Один порт** для статики, REST и WebSocket — достаточно одного правила
  брандмауэра; только стандартная библиотека Python, без `pip install`.
- **Сменный источник телеметрии**:
  - `simconnect` — нативный SimConnect через `ctypes`;
  - `mock` — процедурный «полёт» без симулятора (демо и тесты);
  - `auto` — SimConnect, при неудаче — mock.
- **Автоопределение борта**: профиль объявляет `sim.match.title` и
  `atcModel`, шлюз читает `TITLE`/`ATC MODEL` и сам переключает панель.
- **LVAR/RPN через WASM** (MobiFlight/SimBridge): Client Data Area,
  синхронный канал с таймаутами, запись LVAR через RPN.
- **Автообнаружение хоста** по UDP-бикону (для нативных клиентов), встроенный
  HTTP-сервер, JSON API, строгая валидация профилей и команд.

### Профили и приборы

- **6 профилей**: Cessna 172S, Cessna 172 Classic Six-Pack, Daher TBM 930,
  Airbus A320, Piper PA-28-181, LVAR-демо.
- **Приборы**: авиагоризонт, круговые шкалы, цифровые табло, тумблеры,
  галетник (жесты/колесо), табло-лампы, вариометр, высотомер с тремя
  стрелками, курсоуказатель с «жучком».
- Раскладка в долях панели + переопределения `layout.phone`,
  `layout.tablet-sm`, `layout.tablet-lg`; схема и валидация —
  [`docs/ru/profile-schema.md`](docs/ru/profile-schema.md).

### Клиенты

- **Веб-клиент** на vanilla ES-модулях: плавная анимация (rAF), сглаживание,
  жесты, командные виджеты, переподключение.
- **Три форм-фактора** с автоподбором по ширине экрана.
- **Комфорт в кокпите**: яркость панели 100/72/45 % (клавиша `B`) и режим
  киоска без интерфейса (`F`, выход `Esc`).
- **Подключение телефона по QR**: страница панели показывает QR-код адреса
  хоста и список сетевых адресов.
- **Android-клиент**: WebView-панель, UDP-обнаружение хоста, проверка
  целостности, экран подключения с ручным вводом адреса.

### Безопасность

- **Вход по паролю** (не короче 6 символов): PBKDF2-хеш, сессии в cookie
  `HttpOnly`, Bearer-токены для нативных клиентов, лимит попыток, QR-вход с
  телефона без ввода пароля. Одноразовый QR-токен действует только через
  `/?pair=` и не принимается как обычная сессия.
- **Same-origin и Host-защита**: браузерные POST/PUT и WebSocket с чужим
  `Origin`, а также запросы с неизвестным `Host` отклоняются (`403`). Это
  закрывает CSRF, cross-site WebSocket hijacking и DNS rebinding; клиенты без
  `Origin` (Android, curl) работают как раньше.
- Публично доступны только страница входа, проверка здоровья/целостности и
  блок поддержки автора — остальное (профили, телеметрия, команды, сборка APK)
  закрыто.

### Ассистент посадки и руления

- **Руление**: удержание заданной скорости (3–25 уз) и курса — тягу и руль
  направления считает шлюз; «СТОП» даёт тягу 0 и стояночный тормоз.
- **Посадка**: ARM включает AP и APR, на 60–15 футах ассистент плавно убирает
  тягу, на касании выключает автопилот; TOGA — уход на второй круг.
- Страница `/assist.html` (кнопка «Ассистент» в шапке панели); работает и на
  телефоне. Ассистент — вспомогательный контур, пилот контролирует полёт.

### Инструменты

- **Редактор панелей** `/editor.html`: drag-and-drop, изменение размеров,
  привязка к сетке 1 %, отмена/повтор (`Ctrl+Z` / `Ctrl+Y`), копирование
  раскладки между форм-факторами, сохранение профиля на хост.
- **Сборщик Android APK** прямо в дистрибутиве: страница `/android.html`
  меняет имя приложения, package id, версию и адрес шлюза, собирает APK и
  отдаёт его на скачивание; есть CLI `--build-apk`.
- **Установщик Windows** (NSIS, per-user, без прав администратора) с готовым
  APK и исходниками Android внутри.

### Лицензия и целостность

- Блок поддержки автора **неудаляем**; SHA-256 критичных файлов проверяется
  при старте хоста и в браузере, при расхождении интерфейс блокируется.

## Установка (Windows, без Python)

Скачайте `OpenDeck-Setup-<версия>.exe` из релизов, запустите и нажимайте
«Далее» — права администратора не нужны, Python и интернет не требуются.
Установка идёт в `%LOCALAPPDATA%\OpenDeck`, создаются ярлыки и запись
в «Программах и компонентах».

1. Запустите **Open Deck for MSFS** — откроется консоль с адресами панели.
2. Разрешите приложению доступ к частной сети в запросе брандмауэра.
3. Откройте панель на этом ПК или введите напечатанный адрес на телефоне,
   либо отсканируйте QR из панели (кнопка с телефоном).

Подробности сборки установщика — [`packaging/windows/README.md`](packaging/windows/README.md).

## Вход по паролю

Вход включается одним из способов:

```powershell
# сохранить пароль (PBKDF2-хеш) в config/auth.json
OpenDeck.exe --set-password            # спросит пароль в консоли
OpenDeck.exe --set-password "мой-пароль"

# или только на этот запуск
OpenDeck.exe --password "мой-пароль"
```

Минимум **6 символов**. Файл `config/auth.json` хранит только хеш; удалите его,
чтобы снова пускать без пароля. В меню «Пуск» установщик создаёт ярлык
«Задать пароль». Подробности — в [описании сервиса](docs/ru/service.md#8-аутентификация-паролем).

Подключённые клиенты:

- браузер — страница `/login.html`, затем панель (cookie на 12 часов);
- телефон — отсканируйте QR на панели: одноразовый токен войдёт без пароля
  (действует 10 минут);
- Android — панель сама покажет экран входа; сессия сохраняется в WebView.

## Запуск из исходников

Нужен **Python 3.11+**; Node.js — только для тестов клиента.

```powershell
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# демо-режим без симулятора: http://127.0.0.1:8760/
python -m msfs_gateway --sim mock

# реальный полёт: SimConnect, при неудаче — mock
python -m msfs_gateway --sim auto

# явный путь к DLL и 60 Гц
python -m msfs_gateway --sim simconnect --simconnect-dll C:\SDK\SimConnect.dll --telemetry-hz 60
```

Полезные параметры:

| Параметр | По умолчанию | Назначение |
| --- | --- | --- |
| `--host` | `0.0.0.0` | адрес прослушивания |
| `--allow-host NAME` | — | дополнительное DNS-имя для заголовка Host (можно повторять) |
| `--port` | `8760` | порт HTTP и WebSocket |
| `--sim` | `auto` | `auto` / `mock` / `simconnect` |
| `--telemetry-hz` | `30` | частота рассылки, 1..60 Гц |
| `--simconnect-host` / `--simconnect-port` | `127.0.0.1` / `19999` | адрес SimConnect (в т.ч. удалённый симулятор) |
| `--profile-dir` | `profiles/` | каталог JSON-профилей |
| `--password` / `--set-password` | — | пароль на запуск / сохранить хеш и выйти |
| `--auth-file` / `--no-auth` | `config/auth.json` | файл хеша / отключить вход |
| `--no-wasm` | — | отключить WASM-мост |
| `--no-discovery` | — | отключить UDP-автообнаружение |
| `--build-apk [CONFIG]` | — | собрать Android APK и выйти |

## Android APK из дистрибутива

В установленном приложении есть исходники Android (`android/`); готовый APK
собирается в `android/dist/OpenDeck-Android-<версия>.apk`, а в меню «Пуск» есть
«Собрать Android APK» (`http://127.0.0.1:8760/android.html`).

На странице задаются имя приложения, package id, версия и адрес шлюза по
умолчанию; кнопка «Собрать APK» запускает `gradle assembleDebug` на этом же
компьютере. Нужны **JDK 17**, **Android SDK** и **Gradle 8.x** (пути можно
указать на странице или задать через `JAVA_HOME` / `ANDROID_HOME` / `gradle` в
`PATH`). В релизном дистрибутиве готовый APK уже лежит в `android/dist`.

```powershell
OpenDeck.exe --build-apk                        # настройки из config/android-build.json
OpenDeck.exe --build-apk C:\path\settings.json
```

## Документация

Полный индекс — [docs/ru/README.md](docs/ru/README.md). Основное:

- [Описание сервиса: назначение, API, аутентификация, ассистент, эксплуатация](docs/ru/service.md)
- [Архитектура и зоны ответственности](docs/ru/architecture.md)
- [Сетевой протокол: REST, WebSocket, вход, QR, автообнаружение](docs/ru/protocol.md)
- [Каталог переменных телеметрии](docs/ru/telemetry.md) *(генерируется из кода)*
- [Каталог приборов и опций](docs/ru/widgets.md) *(генерируется из кода)*
- [Схема профиля самолёта](docs/ru/profile-schema.md)
- [Android-клиент: сборка, вход, отладка](android/README.md)
- [Сборка установщика](packaging/windows/README.md)
- [Стоимость подключённых сервисов vs локальные аналоги](docs/ru/pricing.md)
- [История изменений](CHANGELOG_RU.md)

## Структура репозитория

```
msfs_gateway/            # шлюз на Python (stdlib)
  sim/                   # провайдеры: mock, simconnect, client_data, wasm_bridge
  qr.py                  # собственный генератор QR (SVG)
  assist.py              # ассистент посадки и руления
  android_build.py       # сборка APK из дистрибутива
  http_api.py, hub.py, profiles.py, integrity.py, discovery.py, websocket.py
web/                     # веб-клиент и редактор (vanilla JS, без сборки)
profiles/                # JSON-профили самолётов
android/                 # Android-клиент (Kotlin, без AndroidX)
packaging/               # PyInstaller + NSIS: установщик Windows
scripts/                 # build-installer.ps1, check.ps1, verify_qr.py
tests/                   # unittest (Python) и node:test (JS)
docs/                    # архитектура, протокол, схема, скриншоты
config/                  # реквизиты автора, настройки сборки APK
integrity/               # SHA-256 манифест критичных файлов
```

## Тесты

```powershell
python -m unittest discover -s tests        # 250 тестов
node --test "tests/web/*.test.mjs"          # 29 тестов
python -m ruff check msfs_gateway tests scripts
```

Один запуск всех проверок:

```powershell
pwsh -File scripts/check.ps1
```

Покрыто: телеметрия и профили, WebSocket (RFC 6455), шина и команды,
mock-провайдер, WASM/Client Data, QR (структура + эталонная матрица),
сборщик APK, целостность, геометрия приборов и раскладки.

## Разработка

См. [`CONTRIBUTING_RU.md`](CONTRIBUTING_RU.md): стиль, тесты, как добавить профиль
или прибор. Вопросы безопасности — [`SECURITY_RU.md`](SECURITY_RU.md).

## Дорожная карта

1. **Живой прогон WASM-моста** с MSFS + MobiFlight/SimBridge (логика и
   эмуляция покрыты тестами).
2. **Release-подпись APK**: keystore/alias в настройках сборщика.
3. **mDNS (Bonjour)** как альтернатива UDP-бикону.
4. **Редактор**: направляющие выравнивания, мультивыделение.
5. **Android**: нативный Compose-рендеринг, foreground-service для киоска.
6. **Запись/повтор телеметрии** для демонстраций и профилирования.

## Безопасность

Проект рассчитан на **доверенную локальную сеть**: HTTP без TLS и
аутентификации, UDP-бикон не подписан. Не выставляйте шлюз в интернет.
Подробнее — [`SECURITY_RU.md`](SECURITY_RU.md).

## Поддержка / Donat

- **Donat:** [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
- **Автор:** Viktor Krasnikov
- **Репозиторий:** [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)

## Лицензия / License

Проект распространяется под лицензией **GNU Affero General Public License v3.0 (AGPL-3.0)** с дополнительными условиями в соответствии с **Разделом 7 (Section 7)**.

* Вы имеете право свободно использовать, изучать, модифицировать и распространять данный код при условии сохранения той же лицензии (AGPL-3.0) и открытия исходного кода любых модификаций (включая использование на сервере / по сети согласно Разделу 13).
* **Обязательное условие (Section 7(b) & Section 5(d)):** Во всех форках, сборках и модифицированных версиях **строго запрещено** удалять, скрывать или изменять упоминание оригинального автора (**Viktor Krasnikov**, [https://github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)) и активные ссылки на страницу поддержки (доната) разработчика в пользовательском интерфейсе программы и документации: [Donat — https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs).

Подробный юридический текст дополнительных условий приведен в файле [COPYING.ADDITIONAL](./COPYING.ADDITIONAL). Полный текст базовой лицензии находится в файле [LICENSE](./LICENSE).
