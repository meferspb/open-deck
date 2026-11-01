# 🔌 Сетевой протокол RUD Panel Gateway

Всё общение идёт на одном TCP-порту (по умолчанию `8760`).

- **REST** — профили, команды, служебные метрики (JSON).
- **WebSocket** `/ws` — push телеметрии и подтверждения команд.
- **HTTP-статика** — файлы `web/` для браузерного клиента.

Контент-тип JSON — `application/json; charset=utf-8`, все ответы без кэша.
Заголовки CORS выставлены открыто (`*`) — локальная сеть, авторизация не в
объёме MVP.

---

## 1. REST API

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptimeSec": 42.1,
  "clients": 1,
  "telemetryHz": 30.0,
  "sim": { "provider": "mock", "connected": true, "aircraftTitle": "…", "profileId": "…" }
}
```

### `GET /api/profiles`

```json
{ "profiles": [ { "id": "cessna-172-skyhawk", "name": "…", "icao": "C172", "revision": 3, "widgetCount": 11 } ] }
```

### `GET /api/profiles/{id}`

Полный профиль (см. [profile-schema.md](profile-schema.md)). `404` — нет профиля,
`422` — файл не проходит валидацию.

### `PUT /api/profiles/{id}`

Сохранение профиля (будущий редактор панелей). Тело — полный JSON-профиль,
`id` в теле обязан совпадать с `{id}` в URL. Ответ:

```json
{ "ok": true, "profile": { "id": "…", "name": "…" } }
```

### `GET /api/telemetry`

Последний кадр телеметрии (тот же формат, что и WebSocket-сообщение
`telemetry`). Полезно для отладки и polling-клиентов.

### `GET /api/telemetry/variables`

Каталог канонических переменных телеметрии (для редактора панелей и нативных
клиентов): `{ "variables": [ { "key", "label", "kind", "unit", "writable", "simVar", "simEvent" } ] }`.

### `GET /api/integrity`

Результат SHA-256 проверки критичных файлов:

```json
{ "verified": true, "checkedAt": "2026-10-30T…", "files": { … }, "errors": [] }
```

### `GET /api/connect`

Адреса для быстрого подключения телефона/планшета:

```json
{
  "host": "FLIGHTSIM-PC",
  "primaryUrl": "http://192.168.31.189:8760/",
  "phoneUrl": "http://192.168.31.189:8760/?device=phone",
  "urls": [
    { "url": "http://192.168.31.189:8760/", "host": "192.168.31.189",
      "private": true, "loopback": false, "linkLocal": false }
  ],
  "devicePresets": ["phone", "tablet-sm", "tablet-lg"],
  "qr": { "scale": 6, "border": 4, "maxTextLength": 512 }
}
```

Адреса отсортированы: сначала домашние сети `192.168.x`, затем `10.x`,
`172.16-31.x`, потом link-local и loopback. Клиент показывает их списком —
если телефон в другой подсети, адрес можно выбрать вручную.

### `GET /api/qr.svg?text=…&scale=6&border=4`

SVG с QR-кодом переданного текста (до 512 символов). Генерируется на хосте
(`msfs_gateway/qr.py`, без внешних библиотек), отдаётся с `Cache-Control:
no-store`. `400` — нет `text`/некорректные числа; `422` — текст не помещается
в поддерживаемые версии.

### `GET /api/donation`

Реквизиты поддержки автора (из `config/donation.json`). Единственный источник —
конфигурация автора на хосте.

### `POST /api/sim/command`

Выполнить команду на симуляторе:

```json
{ "key": "power.batteryMaster", "value": true }
```

Ответ `200` — подтверждение `{type:"ack", id, key, ok, value}`; `400` — неверное
значение/ключ; `409` — симулятор отклонил команду.

### `POST /api/sim/aircraft`

Выбор борта (панели):

```json
{ "profileId": "cessna-172-sixpack" }
```

Ответ `200`: `{ "ok": true, "profileId": "…", "aircraftTitle": "…", "pinned": false }`.
`pinned: true` — провайдер не умеет менять самолёт (SimConnect), поэтому выбор
закреплён как ручной и действует, пока в симуляторе не загрузили другой борт.
`404` — профиля нет.

---

## 2. WebSocket `/ws`

Handshake — стандартный (Upgrade: websocket, версия 13). Сервер шлёт **текстовые**
JSON-сообщения; бинарные фреймы не поддерживаются.

### 2.1. Сервер → клиент

#### `hello` (первое сообщение после подключения)

```json
{
  "type": "hello",
  "clientId": "a1b2c3d4",
  "server": { "name": "RUD Panel Gateway", "version": "0.1.0", "telemetryHz": 30.0, "uptimeSec": 1.2 },
  "profiles": [ … ],
  "state": { /* кадр telemetry */ }
}
```

#### `telemetry` (периодически, `telemetryHz` раз в секунду)

```json
{
  "type": "telemetry",
  "seq": 1234,
  "ts": 1762340000000,
  "sim": { "provider": "mock", "connected": true, "aircraftTitle": "…", "profileId": "…" },
  "values": {
    "power.batteryMaster": true,
    "power.busVolts": 24.197,
    "attitude.pitchDeg": 2.5,
    "speed.iasKt": 108.0
  }
}
```

- `seq` монотонно растёт — клиент может считать потерянные кадры;
- `values` всегда содержит полный набор ключей из реестра телеметрии.

#### `profiles` / `aircraft`

Рассылаются после перезагрузки каталога профилей или смены борта, чтобы
клиенты обновили выпадающий список и активный профиль.

#### `ack` (подтверждение команды)

```json
{ "type": "ack", "id": "c1", "key": "power.batteryMaster", "ok": true, "value": true }
{ "type": "ack", "id": "c1", "key": "…", "ok": false, "code": "not_writable", "error": "…" }
```

#### `pong` / `error`

`pong` отвечает на клиентский `ping`; `error` сигнализирует о нераспознанном
сообщении (`bad_json`, `unknown_type`).

### 2.2. Клиент → сервер

```json
{ "type": "ping", "t": 12345.6 }
{ "type": "command", "id": "c1", "key": "power.batteryMaster", "value": true }
```

`id` команды произвольный — сервер вернёт его в `ack`, чтобы клиент сопоставил
ответ с запросом.

### 2.3. Коды ошибок `ack`

| code | Смысл |
| --- | --- |
| `invalid_key` | пустой/несуществующий ключ |
| `not_writable` | переменная не принимает команды |
| `invalid_value` | значение не прошло приведение типа |
| `rate_limited` | превышен лимит команд клиента |
| `sim_rejected` | симулятор отклонил команду |

---

## 3. Поведение клиента (рекомендации)

- **Подтверждение по телеметрии**, а не по `ack`: визуальное состояние
  тумблера следует за `telemetry.values`, `ack` лишь сигнализирует о приёме.
- **Реконнект с backoff** (напр. 500 мс → 8 с, jitter) и `ping` каждые 20 с.
- **Не блокировать UI** на команде: оптимистично показать «pending», откатить
  при `ack.ok == false` или таймауте.
- **Потеря кадров некритична**: последний кадр всегда актуален, стрелки
  сглаживаются на клиенте.

---

## 4. Автообнаружение (UDP broadcast)

Хост рассылает JSON-бикон по UDP broadcast на порт `8761` (по умолчанию)
каждые 3 секунды. Это для нативных клиентов (Android): браузер UDP не умеет.

```json
{
  "type": "rud-panel-gateway",
  "protocol": 1,
  "name": "FLIGHTSIM-PC",
  "version": "0.1.0",
  "httpPort": 8760,
  "telemetryHz": 30.0,
  "profiles": ["cessna-172-skyhawk", "piper-pa28-archer-ii"],
  "ts": 1762340000
}
```

| Поле | Описание |
| --- | --- |
| `type` | всегда `rud-panel-gateway` (фильтр «свой/чужой») |
| `protocol` | версия схемы бикона |
| `name` | имя хоста (`socket.gethostname()`) |
| `httpPort` | порт HTTP/WebSocket шлюза |
| `telemetryHz` | частота телеметрии |
| `profiles` | доступные профили самолётов |
| `ts` | unix-время отправки |

Клиент подключается к `http://<ip-источника>:<httpPort>/`. Проверить вручную:

```powershell
python -m msfs_gateway.discovery --listen
```
