# 🧩 Каталог приборов

> Файл сгенерирован из `msfs_gateway/profiles.py` (типы и обязательные
> привязки) и веб-клиента (опции). Обновить:
> `python -m msfs_gateway.docsgen --write`.

Каждый прибор — элемент массива `widgets[]` профиля. Полная схема
профиля — в [profile-schema.md](profile-schema.md).

## Общая структура

```json
{
  "id": "attitude-main",
  "type": "attitude",
  "label": "Авиагоризонт",
  "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" },
  "layout": {
    "base": { "x": 0.02, "y": 0.03, "w": 0.36, "h": 0.62 },
    "phone": { "x": 0.03, "y": 0.02, "w": 0.94, "h": 0.3 }
  },
  "options": { "unit": "FT", "decimals": 0 }
}
```

- `id` — уникальный slug (`[a-z0-9][a-z0-9-]`), используется в редакторе
  и для привязки событий.
- `layout` — координаты в долях панели; обязателен `base`, опциональны
  `phone`, `tablet-sm`, `tablet-lg`.
- `options` — необязательный объект, зависит от типа.
- `command` — обязателен для тумблера и галетника (см. ниже).

## Типы приборов

| Тип | Прибор | Обязательные bindings | `command` | Основные options |
| --- | --- | --- | --- | --- |
| `attitude` | Авиагоризонт | `pitch`, `bank` | — | — |
| `gauge.radial` | Круговая шкала | `value` | — | `min`*, `max`*, `redline`, `zones`, `majorTicks`, `minorTicks`, `decimals`, `unit` |
| `readout` | Цифровое табло | `value` | — | `unit`, `decimals`, `caption`, `alarm` |
| `switch.toggle` | Тумблер | `state` | обязателен | `caption`, `onLabel`, `offLabel` |
| `knob.rotary` | Галетник / энкодер | `value` | обязателен | `min`, `max`, `step`, `wrap`, `unit`, `decimals`, `caption` |
| `annunciator` | Табло-лампы | `active` | — | `caption`, `tone`, `invert` |
| `vsi` | Вариометр | `value` | — | `limit` |
| `altimeter` | Высотомер | `value` | — | — |
| `heading` | Курсоуказатель | `heading` | — | — |

`*` у опции — обязательна. Остальные опции имеют разумные значения по
умолчанию и нужны для настройки внешнего вида.

## Описание типов

### `attitude` — Авиагоризонт

Авиагоризонт: тангаж и крен по `pitch`/`bank`, шкала крена, метка нуля. Дополнительных опций нет.

Минимальный пример:

```json
{ "id": "attitude", "type": "attitude", "bindings": { "pitch": "attitude.pitchDeg", "bank": "attitude.bankDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `gauge.radial` — Круговая шкала

Круговая стрелочная шкала: значение `value` в диапазоне `min..max`, деления, красная зона, подпись и единицы.

| Опция | Значение | Обязательна |
| --- | --- | --- |
| `min` | минимум шкалы | да |
| `max` | максимум шкалы | да |
| `redline` | красная зона (в диапазоне min..max) | нет |
| `zones` | дополнительные цветные зоны | нет |
| `majorTicks` | число больших делений | нет |
| `minorTicks` | число малых делений | нет |
| `decimals` | знаков после запятой | нет |
| `unit` | единицы подписи | нет |

Минимальный пример:

```json
{ "id": "speed", "type": "gauge.radial", "bindings": { "value": "speed.iasKt" }, "options": { "min": 0, "max": 200, "unit": "KT", "redline": 160 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `readout` — Цифровое табло

Цифровое табло: форматирует `value` с заданным числом знаков, единицами и подписью; умеет подсвечивать аварийный порог.

| Опция | Значение | Обязательна |
| --- | --- | --- |
| `unit` | единицы | нет |
| `decimals` | знаков после запятой | нет |
| `caption` | подпись над значением | нет |
| `alarm` | порог аварийной подсветки | нет |

Минимальный пример:

```json
{ "id": "alt", "type": "readout", "bindings": { "value": "altitude.indicatedFt" }, "options": { "caption": "ALT", "unit": "FT", "decimals": 0 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `switch.toggle` — Тумблер

Тумблер: показывает логическое `state` и отправляет команду `command.key`; действие `set` посылает противоположное значение, `toggle` — событие-переключатель.

| Опция | Значение | Обязательна |
| --- | --- | --- |
| `caption` | подпись тумблера | нет |
| `onLabel` | текст включённого состояния | нет |
| `offLabel` | текст выключенного состояния | нет |

Минимальный пример:

```json
{ "id": "battery", "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" }, "command": { "key": "power.batteryMaster", "action": "set" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `knob.rotary` — Галетник / энкодер

Галетник/энкодер: вращение и свайпы меняют `value` на `step` в диапазоне `min..max`, отправляя команду с новым значением.

| Опция | Значение | Обязательна |
| --- | --- | --- |
| `min` | минимум | нет |
| `max` | максимум | нет |
| `step` | шаг изменения | нет |
| `wrap` | зацикливать значение | нет |
| `unit` | единицы | нет |
| `decimals` | знаков после запятой | нет |
| `caption` | подпись | нет |

Минимальный пример:

```json
{ "id": "hdg", "type": "knob.rotary", "bindings": { "value": "autopilot.headingBugDeg" }, "command": { "key": "autopilot.headingBugDeg", "action": "set" }, "options": { "min": 0, "max": 359, "step": 1, "wrap": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `annunciator` — Табло-лампы

Табло-лампы: горит при истинном `active`; подпись, тон и инверсия настраиваются опциями.

| Опция | Значение | Обязательна |
| --- | --- | --- |
| `caption` | подпись лампы | нет |
| `tone` | цвет/тон свечения | нет |
| `invert` | инвертировать логику | нет |

Минимальный пример:

```json
{ "id": "bus", "type": "annunciator", "bindings": { "active": "power.busVolts" }, "options": { "caption": "BUS OFF", "invert": true }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `vsi` — Вариометр

Вариометр: стрелка вертикальной скорости, шкала ограничена `limit`, подписи в fpm.

| Опция | Значение | Обязательна |
| --- | --- | --- |
| `limit` | предел шкалы, fpm | нет |

Минимальный пример:

```json
{ "id": "vsi", "type": "vsi", "bindings": { "value": "verticalSpeed.fpm" }, "options": { "limit": 2000 }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `altimeter` — Высотомер

Высотомер с тремя стрелками (сотни/тысячи/десятки тысяч футов) по значению `value`.

Минимальный пример:

```json
{ "id": "altimeter", "type": "altimeter", "bindings": { "value": "altitude.indicatedFt" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

### `heading` — Курсоуказатель

Курсоуказатель с вращающейся картушкой и «жучком»; значение — магнитный курс в градусах.

Минимальный пример:

```json
{ "id": "heading", "type": "heading", "bindings": { "heading": "heading.magneticDeg" }, "layout": { "base": { "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2 } } }
```

## Команды с тумблера и галетника

Блок `command` описывает, что отправить на шлюз:

| Поле | Значение |
| --- | --- |
| `key` | переменная с признаком «принимает команды» (см. каталог телеметрии) |
| `action` | `set` — отправить новое значение; `toggle` — событие-переключатель |
| `value` | для `set`: `true/false`/число; по умолчанию противоположное текущему |

Пример тумблера:

```json
{ "type": "switch.toggle", "bindings": { "state": "power.batteryMaster" },
  "command": { "key": "power.batteryMaster", "action": "set" } }
```

## Валидация

- Тип обязан входить в список выше; неизвестный тип редактор не сохранит.
- Обязательные роли `bindings` должны ссылаться на существующие ключи
  телеметрии.
- `layout.base` и переопределения обязаны быть прямоугольниками в
  пределах `0..1` (см. схему профиля).
