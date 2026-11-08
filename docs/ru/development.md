# 🛠️ Разработка и внутреннее устройство

Документ для тех, кто меняет код: где что лежит, как добавить переменную,
прибор, профиль, провайдера или страницу, как проверять и выпускать.
Пользовательская документация — в [service.md](service.md), протокол — в
[protocol.md](protocol.md).

## 1. Требования

- Windows 10/11 (шлюз использует `ctypes` для SimConnect; остальное
  кроссплатформенно).
- Python **3.11+**; сторонних зависимостей нет — только стандартная
  библиотека.
- Node.js **20+** — для тестов веб-клиента (сам клиент сборки не требует).
- JDK 17 + Android SDK + Gradle 8.x — только для сборки APK.
- PyInstaller и NSIS — только для установщика.

## 2. Карта кода

```
msfs_gateway/
  app.py            сборка зависимостей, жизненный цикл, CLI-режимы
  settings.py       аргументы CLI, пути, значения по умолчанию
  telemetry.py      реестр переменных (ключи, типы, SimVar, события)
  hub.py            шина: кадр, подписки, команды, автоопределение борта
  http_api.py       HTTP: статика, REST, WebSocket-upgrade, авторизация
  websocket.py      RFC 6455: кадры, ping/pong, close, очередь отправки
  auth.py           пароль, PBKDF2, сессии, QR-токены, лимит попыток
  assist.py         ассистенты руления и посадки (10 Гц)
  profiles.py       валидация, хранение, атомарное сохранение профилей
  legacy.py         адаптер старого формата профиля v0
  integrity.py      SHA-256 манифест критичных файлов
  discovery.py      UDP-бикон автообнаружения
  qr.py             генератор QR (SVG) на stdlib
  android_build.py  настройки, поиск инструментов, запуск Gradle
  docsgen.py        генерация docs/telemetry.md и docs/widgets.md
  sim/              провайдеры: mock, simconnect, client_data, wasm_bridge
web/                панель, редактор, вход, ассистент (vanilla ES-модули)
profiles/           JSON-профили самолётов
android/            Kotlin-клиент (WebView + UDP-поиск)
packaging/windows/  PyInstaller + NSIS
scripts/            build-installer.ps1, check.ps1, verify_qr.py
tests/              unittest (Python) и node:test (JS)
docs/               эта и остальная документация
```

## 3. Как добавить переменную телеметрии

1. Откройте `msfs_gateway/telemetry.py`, добавьте `Variable(...)` в
   `_VARIABLES`: ключ, тип, подпись, `sim_var`/`sim_unit`, при необходимости
   `sim_event`, `sim_event_param`, `sim_event_scale`.
2. Проверьте имя SimVar по документации MSFS SDK (регистр и единицы важны).
3. Обновите каталог: `python -m msfs_gateway.docsgen --write`.
4. Прогоните `python -m unittest tests.test_telemetry` и весь набор.
5. Если переменная управляющая — убедитесь, что событие действительно меняет
   состояние (сравнение `bool` идёт по текущему значению).

## 4. Как добавить прибор

1. Создайте `web/js/widgets/my-widget.js`: класс с `update(state)` и
   `destroy()` (см. `base.js` и соседние приборы). Отрисовка — canvas или DOM.
2. Зарегистрируйте тип в `web/js/widgets/registry.js`.
3. Добавьте тип в `WIDGET_TYPES`, обязательные роли в `REQUIRED_BINDINGS` и,
   если нужны, проверки опций в `msfs_gateway/profiles.py`.
4. Опишите прибор в `msfs_gateway/docsgen.py` (`WIDGET_ORDER`,
   `WIDGET_TITLES`, `WIDGET_DESCRIPTIONS`, `WIDGET_OPTIONS`, пример) и
   выполните `python -m msfs_gateway.docsgen --write`.
5. Проверьте на всех трёх форм-факторах (телефон/малый/большой планшет) и в
   редакторе; добавьте тест геометрии в `tests/web/`.

## 5. Как добавить профиль самолёта

1. Скопируйте близкий профиль из `profiles/`, поменяйте `id`, `name`, `icao`,
   `sim.match` (glob по `TITLE`/`ATC MODEL`).
2. Проверьте валидацию: `python -m unittest tests.test_profiles`.
3. Соберите раскладки `base` + отличия для форм-факторов; следите, чтобы
   прямоугольники не выходили за `0..1`.
4. Проверьте в редакторе `/editor.html` и на реальном борту (если есть MSFS).
5. Добавьте профиль в README (список) и в CHANGELOG.

## 6. Как добавить провайдер телеметрии

1. Унаследуйте `SimProvider` (`sim/base.py`) и реализуйте `start`, `stop`,
   `read`, `apply_command`, `connected`; при необходимости —
   `select_aircraft`, `aircraft_title`, `atc_model`.
2. Зарегистрируйте выбор в `sim/__init__.py:create_sim()` и добавьте значение
   в `SIM_CHOICES` (`settings.py`).
3. Потокобезопасность: `read()` и `apply_command()` могут вызываться из разных
   потоков — используйте блокировку.
4. Добавьте тесты с фейковым транспортом (см. `tests/test_mock_sim.py`).

## 7. Как добавить endpoint

1. Разберите путь в `_handle_api_get/post/put` (`http_api.py`).
2. Решите, публичный он или под сессией: публичные — только в
   `PUBLIC_API_PATHS`; остальные автоматически закрыты.
3. Отвечайте через `_send_json`/`ApiError`; ошибки — с машинным `code`.
4. Опишите endpoint в `docs/protocol.md` (таблица + пример) и в
   `docs/service.md` (раздел API).
5. Добавьте тест в `tests/` (unit + при необходимости HTTP-интеграцию).

## 8. Как добавить страницу

1. Положите HTML в `web/`, JS — в `web/js/`, стили — в `web/css/`.
2. Страница по умолчанию **закрыта** (кроме `/login.html` и её файлов);
   без сессии сервер отдаст `302` на вход.
3. Ссылку добавьте в шапку панели (`web/index.html`), затем пересоберите
   манифест: `python -m msfs_gateway.integrity --write`.
4. Проверьте на телефоне (`?device=phone`) и в киоске.

## 9. Тесты и проверки

```powershell
pwsh -File scripts/check.ps1       # ruff + format + 248 Python + 35 JS
python -m unittest discover -s tests
node --test "tests/web/*.test.mjs"
python -m msfs_gateway.docsgen --check
python -m msfs_gateway.integrity
```

Тестовая стратегия:

- **Чистая логика** (валидация, профили, QR, контроллеры ассистента,
  аутентификация) — unit-тесты без сети и MSFS.
- **HTTP/WebSocket** — поднимаем `GatewayApplication.start_background()` на
  `127.0.0.1:0` и ходим `http.client`/сырыми сокетами.
- **SimConnect/WASM** — фейковый DLL/транспорт; живой полёт проверяется вручную.
- **Веб** — `node:test` для чистых функций (раскладка, `isConnectionStale`).

## 10. Документация

- `docs/telemetry.md` и `docs/widgets.md` **генерируются** из кода; ручные
  правки будут затёрты. Меняйте `docsgen.py` и запускайте `--write`.
- Остальные документы — вручную; при изменении поведения обновляйте
  `service.md`, `protocol.md`, `profile-schema.md` и `CHANGELOG.md`.
- Проверка актуальности встроена в `scripts/check.ps1` (docsgen --check).
- Индекс — [docs/README.md](README.md).

## 11. Сборка и релиз

1. Обновите версию (`msfs_gateway/__init__.py`, `config/android-build.json`,
   `packaging/windows/README.md`).
2. `python -m msfs_gateway.integrity --write` (если менялись критичные файлы).
3. `pwsh -File scripts/build-installer.ps1 -Version <x.y.z> -NsisPath <NSIS>`.
4. Проверьте установку/удаление и `--set-password` на чистой машине.
5. Соберите APK (`android/gradle assembleDebug`) и положите в `android/dist`.
6. Обновите `CHANGELOG.md`, закоммитьте, поставьте тег `v<x.y.z>`.

## 12. Соглашения

- Python: только stdlib, форматирование `ruff format`, длина строки 100.
- JS: ES-модули, без CDN и сборки; `node --check` и `node:test`.
- Kotlin: только SDK и stdlib, без AndroidX.
- Комментарии и документация — по-русски; идентификаторы — по-английски.
- Не добавляйте внешние зависимости без крайней необходимости: проект
  рассчитан на air-gapped установку.
