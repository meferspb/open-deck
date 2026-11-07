# 🔌 Сетевой протокол RUD Panel Gateway

Всё общение идёт по одному TCP-порту (по умолчанию `8760`):

- **HTTP-статика** — файлы `web/` (панель, редактор, вход, ассистент);
- **REST API** — профили, телеметрия, команды, ассистент, сборка APK;
- **WebSocket `/ws`** — поток телеметрии и подтверждения команд.

## 0. Соглашения

- Базовый URL: `http://<хост>:<порт>`; все пути относительные.
- JSON — UTF-8, `Content-Type: application/json; charset=utf-8`.
- Ответы API: `Cache-Control: no-store`; статика: `no-cache`.
- **CORS намеренно выключен**: API рассчитано на same-origin клиентов,
  сторонняя страница не может прочитать ответы.
- **Same-origin защита**: если браузер прислал `Origin`, его хост и effective-порт
  должны совпадать с `Host`. Иначе `POST`/`PUT` и WebSocket получают `403`
  `origin_not_allowed`. Клиенты без `Origin` (Android, curl) допускаются.
- **Host allowlist**: `Host` должен указывать на localhost, имя машины, FQDN,
  локальный IP или имя из `--allow-host`; иначе `403 host_not_allowed`.
  Это защита от DNS rebinding.
- Лимит тела запроса — **2 МиБ**; неизвестный `Content-Length` → `411`.
- Пароль (если включён) и сессии описаны в разделе 2.
- Версия протокола в биконе автообнаружения — `protocol: 1`.

---

## 1. Доступ: публично и под сессией

Если пароль не настроен, доступно всё. Если настроен, без сессии открыты
только страница входа, её файлы и служебные данные, нужные лицензии:

| Путь | Доступ | Назначение |
| --- | --- | --- |
| `/login.html`, `/js/login.js`, `/css/*`, `/img/*` | публично | страница входа и оформление |
| `/api/auth/status`, `/api/auth/login`, `/api/auth/logout` | публично | вход/выход |
| `/api/health` | публично | «это шлюз?», версия, признак пароля |
| `/api/integrity` | публично | проверка SHA-256 интерфейса |
| `/api/donation` | публично | блок поддержки автора |
| `/license` | публично | текст лицензии |
| всё остальное | под сессией | профили, телеметрия, команды, QR, APK, ассистент, `/ws` |

Без сессии:

- API отвечает `401` с `{"error","code":"unauthorized"}` и
  `WWW-Authenticate: Bearer realm="rud-panel"`;
- HTML-страницы отвечают `302` на `/login.html?next=<путь>`;
- WebSocket handshake отклоняется с `401` (браузер покажет ошибку соединения).

---

## 2. Аутентификация

Пароль — от 6 символов, хранится как PBKDF2-хеш в `config/auth.json`
(210 000 итераций, случайная соль). Сессия — 32 случайных байта, TTL 12 часов,
продлевается при обращении.

Токен принимается тремя способами:

| Способ | Где | Кому |
| --- | --- | --- |
| Cookie `rud_session` | `HttpOnly; SameSite=Lax` | браузер и Android WebView |
| `Authorization: Bearer <token>` | заголовок | нативные клиенты |
| `?token=<token>` | только `/ws` | WebSocket без cookie |

### `GET /api/auth/status`

```json
{ "required": true, "authenticated": false }
```

### `POST /api/auth/login`

```json
{ "password": "секрет" }
```

Успех — `200`, cookie и токен:

```json
{ "ok": true, "required": true, "token": "<43 символа>", "expiresIn": 43200 }
```

Ошибки:

| Статус | `code` | Когда |
| --- | --- | --- |
| `400` | `missing_password` | нет `password` |
| `401` | `bad_password` | неверный пароль |
| `429` | `rate_limited` | после 5 неудач с адреса; есть `Retry-After` |

Если пароль не настроен, ответ `{"ok":true,"required":false}`.

### `POST /api/auth/logout`

Отзывает текущую сессию и очищает cookie: `{"ok": true}`.

### `POST /api/pair`

Только с сессией. Одноразовый токен для входа с телефона:

```json
{ "url": "http://192.168.1.10:8760/?pair=…", "token": "…", "expiresIn": 600, "required": true }
```

Переход по `url` обменивает токен на обычную сессию (cookie) и редиректит на
`/`; повторное использование даёт `/login.html?error=pair`.

---

## 3. REST API

Ниже `{id}` — идентификатор профиля (`[a-z0-9][a-z0-9-]{1,63}`).

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "authRequired": true,
  "sim": {
    "provider": "simconnect",
    "connected": true,
    "aircraftTitle": "Cessna Skyhawk G1000 Asobo",
    "profileId": "cessna-172-g1000"
  }
}
```

### `GET /api/profiles`

```json
{ "profiles": [
  { "id": "cessna-172-skyhawk", "name": "Cessna 172S Skyhawk", "icao": "C172",
    "revision": 3, "widgetCount": 11 }
] }
```

### `GET /api/profiles/{id}`

Полный профиль (см. [profile-schema.md](profile-schema.md)).
`404 not_found` — нет файла; `422 invalid_profile` — не проходит валидацию.

### `PUT /api/profiles/{id}`

Тело — полный JSON-профиль; `id` в теле обязан совпадать с URL
(`400 id_mismatch`). Ответ `{"ok": true, "profile": {…}}`.

### `GET /api/telemetry`

Последний кадр (тот же формат, что `telemetry` в WebSocket).
`seq` растёт; `values` содержит все ключи реестра.

### `GET /api/telemetry/variables`

Каталог переменных:

```json
{ "variables": [
  { "key": "speed.iasKt", "label": "Indicated airspeed", "kind": "number",
    "unit": "KT", "writable": false, "simVar": "AIRSPEED INDICATED", "simEvent": null }
] }
```

Полный человекочитаемый каталог — [telemetry.md](telemetry.md).

### `GET /api/integrity`

```json
{ "verified": true, "checkedAt": "2026-11-01T…", "manifestPresent": true,
  "files": { "web/index.html": "<sha256>" }, "errors": [] }
```

### `GET /api/donation`

Реквизиты поддержки автора из `config/donation.json` (единственный источник —
конфигурация на хосте).

### `GET /api/connect`

Адреса для телефона/планшета:

```json
{
  "host": "FLIGHTSIM-PC",
  "primaryUrl": "http://192.168.1.10:8760/",
  "phoneUrl": "http://192.168.1.10:8760/?device=phone",
  "urls": [
    { "url": "http://192.168.1.10:8760/", "host": "192.168.1.10",
      "private": true, "loopback": false, "linkLocal": false }
  ],
  "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
  "qr": { "scale": 6, "border": 4, "maxTextLength": 512 }
}
```

Сортировка: `192.168.*`, затем `10.*`, `172.16–31.*`, link-local, loopback.

### `GET /api/qr.svg?text=…&scale=6&border=4`

SVG с QR-кодом (до 512 символов; генерируется на хосте, без библиотек).
`400 missing_text` — нет `text`; `400` (код `error`) — `scale`/`border` не
числа; `422 qr_too_long` — текст не помещается в поддерживаемые версии QR.

### `POST /api/sim/command`

```json
{ "key": "power.batteryMaster", "value": true }
```

Успех — `200` с `{"type":"ack","id":…,"key":…,"ok":true,"value":…}`.
Ошибки: `400` с `code` = `invalid_key`, `not_writable`, `invalid_value`,
`rate_limited` или `sim_error`; `409 sim_rejected` — симулятор отказал.
Для переменных с событием-параметром значение масштабируется
(проценты → 0..16383).

### `POST /api/sim/aircraft`

```json
{ "profileId": "cessna-172-sixpack" }
```

Ответ: `{"ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false}`.
`pinned: true` — провайдер не умеет менять борт (SimConnect), выбор закреплён
до смены самолёта в симуляторе. `404` — профиля нет.

### Ассистент

`GET /api/assist` — состояние контуров:

```json
{
  "telemetry": {
    "onGround": true, "radioAltitudeFt": 0, "groundSpeedKt": 12.3,
    "iasKt": 0, "headingDeg": 274, "localizerDeg": 0.0,
    "glideSlopeDeg": 0.0, "locValid": false, "gsValid": false,
    "autopilotMaster": false, "approach": false,
    "throttlePct": 18.4, "rudderPct": -3.2, "parkingBrake": false
  },
  "taxi": { "engaged": true, "targetSpeedKt": 12, "targetHeadingDeg": 274,
            "throttlePct": 18.4, "rudderPct": -3.2, "message": "…" },
  "landing": { "phase": "off", "message": "…", "throttlePct": 0, "active": false },
  "limits": { "taxiSpeedMinKt": 3, "taxiSpeedMaxKt": 25,
              "flareStartFt": 60, "flareIdleFt": 15 }
}
```

`POST /api/assist/taxi`:

| `action` | Поля | Смысл |
| --- | --- | --- |
| `engage` | — | включить удержание скорости/курса (только на земле) |
| `disengage` | — | выключить |
| `stop` | — | тяга 0, стояночный тормоз |
| `speed` | `value` (3…25) | задать скорость руления |
| `heading` | `delta` (±) | повернуть заданный курс |

`POST /api/assist/landing`: `action` = `arm` (AP + APR), `disarm`, `toga`.

Ответ: `{"ok": true|false, "message": "…", "status": {…}}`.
`200` — действие выполнено; `409` — отказ (не на земле, мала скорость,
нет связи с MSFS, неизвестное действие).

### Сборка Android APK

- `GET /api/android/settings` — `{settings, toolchain, apk, prebuiltApk}`.
- `PUT /api/android/settings` — сохранить настройки (имя, package id, версия,
  адрес шлюза, пути к инструментам). `422 invalid_settings`.
- `GET /api/android/build` — статус задачи:
  `{jobId, state, running, log, apk, error}` (`state`: `idle|running|success|failed`).
- `POST /api/android/build` — запуск; `202` с `jobId`, `409 build_running`,
  `422 invalid_settings`.
- `GET /api/android/apk` — скачать APK (`application/vnd.android.package-archive`);
  если сборки нет — готовый APK из дистрибутива, иначе `404 apk_missing`.

### Статика и служебные страницы

- `GET /` — панель (`index.html`), `GET /editor.html` — редактор,
  `GET /android.html` — сборка APK, `GET /assist.html` — ассистент,
  `GET /login.html` — вход.
- `GET /license` — текст лицензии.
- `HEAD` — только для статики; для `/api/*` — `405`.
- `OPTIONS` — `204` без CORS-заголовков.

---

## 4. WebSocket `/ws`

Handshake — RFC 6455, версия 13. Только текстовые сообщения; бинарные
закрываются с `1002`.

### 4.1. Авторизация

Токен берётся из cookie, `Authorization: Bearer` или `?token=` (для `/ws`).
Без действующей сессии — HTTP `401`, upgrade не выполняется. Одноразовый
pairing-токен здесь недействителен: он принимается только через `/?pair=`.
При несовпадении `Origin` и `Host` — HTTP `403`, upgrade не выполняется.

### 4.2. Сервер → клиент

#### `hello` — первое сообщение

```json
{
  "type": "hello",
  "clientId": "a1b2c3d4",
  "server": { "name": "RUD Panel Gateway", "version": "0.1.0",
              "telemetryHz": 30.0, "uptimeSec": 1.2 },
  "profiles": [ … ],
  "state": { /* полный кадр telemetry */ }
}
```

#### `telemetry` — периодически (`telemetryHz` раз в секунду)

```json
{
  "type": "telemetry",
  "seq": 1234,
  "ts": 1762340000000,
  "sim": { "provider": "mock", "connected": true,
           "aircraftTitle": "…", "profileId": "…" },
  "values": { "speed.iasKt": 108.0, "altitude.indicatedFt": 4520.0, … }
}
```

- `seq` монотонен — по нему видно потери кадров;
- `values` всегда содержит все ключи реестра. `null` означает «данных нет»:
  SimVar не принят SimConnect или телеметрия устарела. Клиент показывает
  прочерк, а не подставляет ноль.

#### `aircraft`

```json
{ "type": "aircraft", "profileId": "cessna-172-sixpack", "aircraftTitle": "…" }
```

Приходит после смены борта/автоопределения, чтобы клиент переключил профиль.

#### `ack`

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong`

Ответ на `ping`: `{ "type": "pong", "t": <эхо>, "ts": <unix ms> }`.

#### `error`

`{ "type": "error", "code": "bad_json"|"unknown_type", "error": "…" }`.

### 4.3. Клиент → сервер

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` произвольный; сервер вернёт его в `ack`.

### 4.4. Коды `ack`

| `code` | Смысл |
| --- | --- |
| `invalid_key` | пустой/неизвестный ключ |
| `not_writable` | переменная только для чтения |
| `invalid_value` | значение не приводится к типу |
| `rate_limited` | больше 30 команд в секунду с WebSocket-клиента или IP для REST |
| `sim_rejected` | симулятор отклонил команду |
| `sim_error` | внутренняя ошибка провайдера |

### 4.5. Лимиты и поведение

- Максимальный размер сообщения — 256 КиБ; больше — `1002`.
- На клиента — очередь 8 кадров телеметрии; при переполнении старые
  выбрасываются (медленный клиент не тормозит остальных).
- Управляющие фреймы (ping/pong/close) не фрагментируются и ≤125 байт.
- Идле-таймаут чтения — 90 с; клиент шлёт `ping` каждые 20 с.
- Закрытие: `1000` — нормальное, `1002` — нарушение протокола.

### 4.6. Рекомендации клиенту

- Визуальное состояние — по `telemetry.values`, не по `ack`.
- Реконнект с backoff (500 мс → 8 с, jitter); если сообщений нет 45 с —
  считать соединение «полуоткрытым» и переподключаться.
- Не блокировать UI: показать «ожидание», откатить при `ok:false`/таймауте.

---

## 5. Вход по QR (pairing)

```
Телефон (нет сессии)                    Шлюз
        │  GET /?pair=<одноразовый токен> │
        ├────────────────────────────────►│
        │                                 │ проверка токена (10 мин, один раз)
        │  302 / + Set-Cookie rud_session  │
        │◄────────────────────────────────┤
        │  GET / (с cookie)               │
        └────────────────────────────────►│ панель
```

QR-код рисует сам шлюз (`/api/qr.svg`); токен создаёт `POST /api/pair`
(нужна сессия). Так телефон входит без ввода пароля. Токен одноразовый и
не является сессией: попытка использовать его как cookie или Bearer даёт
`401`, а TTL не продлевается.

---

## 6. Автообнаружение (UDP broadcast)

Хост рассылает JSON-бикон на UDP-порт `8761` каждые 3 секунды (для Android и
нативных клиентов; браузер UDP не умеет).

```json
{
  "type": "rud-panel-gateway",
  "protocol": 1,
  "name": "FLIGHTSIM-PC",
  "version": "0.1.0",
  "httpPort": 8760,
  "telemetryHz": 30.0,
  "profiles": ["cessna-172-skyhawk", "piper-pa28-archer-ii"],
  "auth": true,
  "ts": 1762340000
}
```

| Поле | Описание |
| --- | --- |
| `type` | всегда `rud-panel-gateway` |
| `protocol` | версия схемы бикона |
| `name` | имя хоста |
| `httpPort` | порт HTTP/WebSocket |
| `telemetryHz` | частота телеметрии |
| `profiles` | доступные профили |
| `auth` | есть только при включённом пароле (`true`) |
| `ts` | unix-время |

Проверка вручную:

```powershell
python -m msfs_gateway.discovery --listen
```

---

## 7. Ошибки HTTP

Формат: `{"error": "текст", "code": "машинный_код"}`.

| Статус | Типичные коды |
| --- | --- |
| `400` | `bad_request`, `bad_json`, `invalid_value`, `id_mismatch`, `missing_password` |
| `401` | `unauthorized`, `bad_password` |
| `404` | `not_found`, `apk_missing` |
| `409` | `build_running`, `sim_rejected`, отказы ассистента |
| `411` | `length_required` |
| `413` | `too_large` |
| `422` | `invalid_profile`, `invalid_settings`, `qr_too_long` |
| `429` | `rate_limited` |
| `501` | неподдерживаемый HTTP-метод (stdlib) |

---

## 8. Примеры

### Вход и запрос профилей

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"password":"секрет"}' http://127.0.0.1:8760/api/auth/login

curl -b cookies.txt http://127.0.0.1:8760/api/profiles
```

### Bearer вместо cookie

```bash
TOKEN=$(curl -s -H "Content-Type: application/json" \
  -d '{"password":"секрет"}' http://127.0.0.1:8760/api/auth/login | jq -r .token)

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/telemetry
```

### Команда

```bash
curl -b cookies.txt -H "Content-Type: application/json" \
     -d '{"key":"power.batteryMaster","value":true}' \
     http://127.0.0.1:8760/api/sim/command
```

### WebSocket (Python, без библиотек)

```python
import json, socket, base64, os
sock = socket.create_connection(("127.0.0.1", 8760))
key = base64.b64encode(os.urandom(16)).decode()
sock.sendall((
    "GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "Cookie: rud_session=<токен>\r\n\r\n"
).encode())
# далее — чтение кадров RFC 6455 (см. msfs_gateway/websocket.py)
```

---

## 9. Совместимость

- Схема профиля — `schemaVersion: 1`; старый формат `v0` адаптируется
  `legacy.py` при чтении.
- Бикон — `protocol: 1`; новые необязательные поля (`auth`) клиенты обязаны
  игнорировать.
- API не версионируется в URL: ломающие изменения — только в новой мажорной
  версии шлюза.
