# 📄 Схема JSON-профиля самолёта

Профиль — один файл `profiles/{id}.json`, описывающий приборную панель
декларативно. Хост валидирует его строго (`msfs_gateway/profiles.py`), клиент
рендерит «на лету».

Все размеры и координаты — **доли панели (0..1)**, а не пиксели: один профиль
работает на телефоне и на большом планшете.

```json
{
  "schemaVersion": 1,
  "id": "cessna-172-skyhawk",
  "name": "Cessna 172S Skyhawk SP",
  "icao": "C172",
  "revision": 3,
  "description": "…",
  "sim": { "match": { "title": "Cessna Skyhawk*", "atcModel": "C172" } },
  "panel": { "background": "#0b1117", "gridSize": 8, "footer": "C172S · OPEN DECK" },
  "widgets": [ … ]
}
```

---

## 1. Поля верхнего уровня

| Поле | Тип | Обязательно | Описание |
| --- | --- | --- | --- |
| `schemaVersion` | int | да | всегда `1` |
| `id` | slug | да | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `name` | string | да | название для UI |
| `icao` | string | нет | код 2–4 символа (напр. `C172`) |
| `revision` | int ≥ 1 | нет | версия профиля |
| `description` | string | нет | пояснение |
| `sim.match` | object | нет | правила автоопределения борта |
| `panel` | object | да | фон, сетка, подпись |
| `widgets` | array 1..64 | да | приборы |
| `variables` | array 0..64 | нет | пользовательские LVAR/RPN (см. §6) |

`sim.match.title` — glob по названию ВС в симуляторе (регистронезависимо),
например `"Cessna Skyhawk*"` подхватит любой ливер и вариант названия.
`sim.match.atcModel` — glob по модели ATC (`C172`), срабатывает, если название
не совпало. Клиент подхватывает профиль автоматически, как только шлюз
прочитает `TITLE` и `ATC MODEL` через SimConnect; ручной выбор из списка
действует, пока в симуляторе не загрузили другой самолёт.

---

## 2. `panel`

| Поле | Тип | Описание |
| --- | --- | --- |
| `background` | цвет `#RGB(A)` / `#RRGGBB(AA)` | фон панели |
| `gridSize` | int | шаг фоновой сетки в «единицах» (опционально) |
| `footer` | string | подпись внизу панели |

---

## 3. `widgets[]` — общая структура

```json
{
  "id": "battery-switch",
  "type": "switch.toggle",
  "label": "Аккумулятор",
  "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" },
  "options": { "caption": "BATTERY", "onLabel": "ON", "offLabel": "OFF" },
  "layout": {
    "base": { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
    "phone": { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 }
  }
}
```

| Поле | Назначение |
| --- | --- |
| `id` | уникальный slug прибора |
| `type` | тип из таблицы ниже |
| `label` | aria-метка / подпись |
| `bindings` | привязки к каноническим ключам телеметрии |
| `command` | для управляющих приборов — как менять переменную |
| `options` | типозависимые настройки (шкалы, подписи, тона) |
| `layout` | геометрия (см. §4) |

### Привязки `bindings`

Ключи — из канонического реестра `msfs_gateway/telemetry.py` (плоские, с
точками): `power.batteryMaster`, `attitude.pitchDeg`, `engine.rpm`,
`speed.iasKt`, `autopilot.headingBugDeg` и т. д. Сервер отвергает неизвестные
ключи при валидации. Полный список с типами и единицами —
[telemetry.md](telemetry.md); описание типов приборов и опций —
[widgets.md](widgets.md).

---

## 4. `layout` — адаптивность под форм-факторы

```json
"layout": {
  "base":       { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "phone":      { "x": 0.03, "y": 0.675, "w": 0.44, "h": 0.125 },
  "tablet-sm":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 },
  "tablet-lg":  { "x": 0.4, "y": 0.37, "w": 0.17, "h": 0.15 }
}
```

- `base` — обязателен; `phone` / `tablet-sm` / `tablet-lg` — необязательные
  **переопределения**, которые сливаются поверх `base` (можно указать только
  отличающиеся поля).
- `x`, `y` — левый верхний угол; `w`, `h` — ширина/высота. Все в долях 0..1,
  `w,h > 0`, прямоугольник не выходит за границы панели.
- Значения `x,y,w,h` могут быть и «дополнительными» — клиент сам задаёт
  размер текста от габаритов прибора через CSS-переменные `--w`/`--h`.

---

## 5. Типы приборов

| `type` | Что делает | `bindings` (обязательные роли) | `command` | Ключевые `options` |
| --- | --- | --- | --- | --- |
| `attitude` | авиагоризонт (canvas) | `pitch`, `bank` | — | — |
| `gauge.radial` | круговая шкала со стрелкой | `value` | — | `min`, `max`, `redline`, `unit`, `decimals`, `majorTicks`, `minorTicks`, `zones[]` |
| `readout` | цифровое табло | `value` | — | `caption`, `unit`, `decimals`, `alarm.{below,above}` |
| `switch.toggle` | тумблер | `state` | `{key, action: set|toggle}` | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | галетник (свайп/колесо/стрелки) | `value` | `{key, action: set}` | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | табло-лампа | `active` | — | `caption`, `tone: ok|warn|danger`, `invert` |
| `vsi` | вариометр (canvas) | `value` | — | `limit` (по умолчанию 2000 FPM) |
| `altimeter` | высотомер с тремя стрелками | `value` | — | — |
| `heading` | курсоуказатель с картушкой и «жучком» | `heading` (опц. `bug`) | — | — |

### `options` по типам

- **`gauge.radial`**: `min`/`max` — диапазон шкалы; `redline` — красная дуга от
  `redline` до `max`; `zones` — массив `{from, to, tone}` для цветных секторов
  (`ok`/`warn`/`danger`); `majorTicks`/`minorTicks` — деления; `decimals` — знаки
  в цифровом значении; `unit` — подпись единицы.
- **`readout`**: `caption` — заголовок; `unit` — единица; `decimals`; `alarm` —
  пороги подсветки `{below, above}`.
- **`switch.toggle`**: `caption`, `onLabel`/`offLabel` — тексты состояний;
  `command.action = "toggle"` — отправить переключение без явного значения.
- **`knob.rotary`**: `min`/`max`/`step`/`wrap` — диапазон и шаг; `unit`,
  `decimals` — отображение; `wrap = true` — зациклить диапазон (например 0–359°).
- **`annunciator`**: `tone` — цвет лампы; `invert = true` — гореть при ложном
  значении (индикатор «BUS OFF» при выключенном питании).
- **`vsi`**: `limit` — предел шкалы в футах/мин (по умолчанию 2000); стрелка
  уходит на ±90° при достижении предела.
- **`heading`**: необязательная привязка `bug` рисует заданный курс
  (`autopilot.headingBugDeg`) отдельным указателем.
- **`attitude`**: опций нет; подпись берётся из `label` прибора.
- Неизвестные опции не отвергаются (для совместимости), но и не используются
  клиентом — сверяйтесь с [widgets.md](widgets.md).

### `command`

```json
"command": { "key": "power.batteryMaster", "action": "set" }
```

`key` обязан быть **записываемой** переменной (у которой есть `sim_event`).
`action`: `set` — установить значение из `value`; `toggle` — переключить.

---

## 6. Пользовательские переменные: LVAR / RPN

Дефолтные SimVar покрывают Cessna 172 и большинство простых ВС, но PMDG,
Fenix, FlyByWire и iniBuilds держат состояние в собственных переменных.
Профиль может объявить их блоком `variables`, а виджеты — ссылаться на
получившиеся ключи (`custom.*`) как на обычные.

```json
"variables": [
  {
    "key": "custom.fuelLbs",
    "kind": "number",
    "source": "lvar",
    "name": "PMDG_FUEL_LBS",
    "label": "Топливо (фунты)",
    "unit": "LBS",
    "initial": 1200
  },
  {
    "key": "custom.apuOn",
    "kind": "bool",
    "source": "lvar",
    "name": "PMDG_APU_ON"
  },
  {
    "key": "custom.cabinAlt",
    "kind": "number",
    "source": "rpn",
    "expression": "(A:CABIN ALTITUDE, feet)"
  }
]
```

| Поле | Описание |
| --- | --- |
| `key` | ключ вида `custom.fuelLbs` (первый сегмент строчный, дальше camelCase); не может совпадать со встроенной переменной |
| `kind` | `number` / `bool` / `string` |
| `source` | `lvar` — чтение LVAR через WASM-мост; `rpn` — вычисление RPN-скриптом |
| `name` | имя LVAR (для `source: lvar`), до 127 байт UTF-8 |
| `expression` | RPN-скрипт (для `source: rpn`), ответ парсится в число/флаг |
| `initial` | стартовое значение для mock-режима (без MSFS) |
| `label`, `unit` | подписи для редактора |

Привязки виджетов валидируются против **встроенных + объявленных** ключей:

```json
{ "id": "fuel", "type": "readout", "bindings": { "value": "custom.fuelLbs" } }
```

Как это работает:

- в **mock-режиме** провайдер подставляет `initial` — панель оживает без MSFS;
- в **реальном полёте** значения читает `WasmBridge` (`read_specs`) через
  WASM-модуль MobiFlight/SimBridge; шина опрашивает их не чаще 4 раз в секунду
  и кэширует между кадрами;
- если мост не подключён, ключи просто отсутствуют в кадре — приборы покажут
  «--» (подставлять 0.0 было бы враньём).

Пример профиля: [`profiles/demo-lvar-panel.json`](../profiles/demo-lvar-panel.json).

---

## 7. Полный пример (Cessna 172S)

См. [`profiles/cessna-172-skyhawk.json`](../profiles/cessna-172-skyhawk.json) —
11 приборов: авиагоризонт, скорость/высота/шина (readout), тахометр и топливо
(gauge), тумблеры батареи/авионики, лампа BUS OFF, закрылки, задатчик курса
(knob). Второй пример — `profiles/piper-pa28-archer-ii.json` (только `layout.base`,
проверка fallback-раскладки).

---

## 8. Обратная совместимость с форматом v0

Исходный формат из ТЗ (`bindings[]` с пиксельными `position` и `sim_var`)
поддерживается через адаптер `msfs_gateway/legacy.py`: он транслируется во
внутренний формат при загрузке, а координаты пересчитываются из пикселей в доли
панели (канвас по умолчанию 1280×800 или из `layout.canvas`/`target_aspect_ratio`).
Сохранение через `PUT /api/profiles/{id}` записывает уже внутренний формат.
