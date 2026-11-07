# 📊 Каталог переменных телеметрии

> Файл сгенерирован из `msfs_gateway/telemetry.py`; не редактируйте вручную.
> Обновить: `python -m msfs_gateway.docsgen --write`.

Реестр — единственный источник правды: по этим ключам профили панелей
привязывают приборы, а шлюз читает SimVar и отправляет команды.

## Как читать таблицу

- **Ключ** — имя переменной в кадре телеметрии и в `bindings` профиля.
- **Тип** — `number`, `bool` или `string`; `bool` в JSON приходит как
  `true/false`, числа — как `float`.
- **Чтение** — SimVar, из которого шлюз берёт значение (для `custom.*`
  источника нет: их читает WASM-мост по описанию из профиля).
- **Команда** — SimConnect-событие, которым переменная меняется;
  прочерк означает «только чтение».

## Переменные по группам

### Электрика и питание

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `power.batteryMaster` | bool | — | ELECTRICAL MASTER BATTERY | TOGGLE_MASTER_BATTERY | Выключатель аккумулятора |
| `power.avionicsMaster` | bool | — | AVIONICS MASTER SWITCH | TOGGLE_AVIONICS_MASTER | Питание авионики |
| `power.busVolts` | number | V | ELECTRICAL MAIN BUS VOLTAGE | — | Напряжение основной шины |

### Двигатель

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `engine.rpm` | number | RPM | GENERAL ENG RPM:1 | — | Обороты двигателя |
| `engine.fuelFlowGph` | number | GPH | ENG FUEL FLOW GPH:1 | — | Часовой расход топлива |
| `engine.torquePct` | number | % | TURB ENG MAX TORQUE PERCENT:1 | — | Момент турбовинтового двигателя |
| `engine.ittC` | number | °C | TURB ENG ITT:1 | — | Температура ИТТ |
| `engine.propRpm` | number | RPM | PROP RPM:1 | — | Обороты воздушного винта |
| `engine.n1Pct` | number | % | TURB ENG N1:1 | — | N1 двигателя №1 |
| `engine.n1Pct2` | number | % | TURB ENG N1:2 | — | N1 двигателя №2 |

### Пространственное положение

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `attitude.pitchDeg` | number | ° | PLANE PITCH DEGREES | — | Тангаж |
| `attitude.bankDeg` | number | ° | PLANE BANK DEGREES | — | Крен |

### Высота

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `altitude.indicatedFt` | number | FT | INDICATED ALTITUDE | — | Приборная высота |

### Скорость

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `speed.iasKt` | number | KT | AIRSPEED INDICATED | — | Приборная скорость |

### Вариометр

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `verticalSpeed.fpm` | number | FPM | VERTICAL SPEED | — | Вертикальная скорость |

### Курс

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `heading.magneticDeg` | number | ° | PLANE HEADING DEGREES MAGNETIC | — | Магнитный курс |

### Механизация крыла

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `flaps.percent` | number | % | TRAILING EDGE FLAPS LEFT PERCENT | — | Положение закрылков |

### Топливо

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `fuel.leftGal` | number | GAL | FUEL LEFT QUANTITY | — | Топливо в левом баке |
| `fuel.rightGal` | number | GAL | FUEL RIGHT QUANTITY | — | Топливо в правом баке |
| `fuel.totalGal` | number | GAL | — | — | Всего топлива |

### Автопилот

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `autopilot.headingBugDeg` | number | ° | AUTOPILOT HEADING LOCK DIR | HEADING_BUG_SET | Заданный курс (heading bug) |
| `autopilot.master` | bool | — | AUTOPILOT MASTER | AP_MASTER | Автопилот включён |
| `autopilot.approachHold` | bool | — | AUTOPILOT APPROACH HOLD | AP_APR_HOLD | Режим APR — команда включения |
| `autopilot.approach` | bool | — | AUTOPILOT APPROACH HOLD | — | Режим APR активен |

### Состояние воздушного судна

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `aircraft.onGround` | bool | — | SIM ON GROUND | — | Самолёт на земле |
| `aircraft.radioAltitudeFt` | number | FT | RADIO HEIGHT | — | Радиовысота над ВПП |
| `aircraft.title` | string | — | TITLE | — | Название борта в симуляторе |

### Руление

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `groundSpeed.kt` | number | KT | GPS GROUND SPEED | — | Путевая скорость |

### Навигация (ILS)

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `nav.localizer` | number | ° | NAV LOCALIZER | — | Отклонение от курсового маяка |
| `nav.glideSlope` | number | ° | NAV GLIDE SLOPE | — | Отклонение от глиссады |
| `nav.locFlag` | bool | — | NAV LOC FLAG | — | Курсовой маяк захвачен |
| `nav.gsFlag` | bool | — | NAV GS FLAG | — | Глиссада захвачена |

### Органы управления

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `controls.throttlePct` | number | % | GENERAL ENG THROTTLE LEVER POSITION:1 | THROTTLE_SET | Положение РУД (команда ассистента) |
| `controls.rudder` | number | % | RUDDER POSITION | RUDDER_SET | Руль направления (команда ассистента) |

### Тормоза

| Ключ | Тип | Ед. | Чтение (SimVar) | Команда | Описание |
| --- | --- | --- | --- | --- | --- |
| `brakes.parking` | bool | — | BRAKE PARKING POSITION | PARKING_BRAKES | Стояночный тормоз |

## Переменные с командами

Эти ключи можно менять через `POST /api/sim/command` и WebSocket
`command`. Значение приводится к типу переменной; для событий с
параметром оно масштабируется (например, проценты → 0..16383).

| Ключ | Событие | Параметр | Масштаб |
| --- | --- | --- | --- |
| `power.batteryMaster` | `TOGGLE_MASTER_BATTERY` | нет | 1.0 |
| `power.avionicsMaster` | `TOGGLE_AVIONICS_MASTER` | нет | 1.0 |
| `autopilot.headingBugDeg` | `HEADING_BUG_SET` | да | 1.0 |
| `autopilot.master` | `AP_MASTER` | нет | 1.0 |
| `autopilot.approachHold` | `AP_APR_HOLD` | нет | 1.0 |
| `controls.throttlePct` | `THROTTLE_SET` | да | 163.83 |
| `controls.rudder` | `RUDDER_SET` | да | 163.83 |
| `brakes.parking` | `PARKING_BRAKES` | нет | 1.0 |

## Пользовательские переменные `custom.*`

Профиль может объявить свои LVAR/RPN в блоке `variables`; ключ обязан
начинаться со строчного сегмента (обычно `custom.`) и не совпадать со
встроенными. Такой ключ появляется в кадре как обычная переменная.

Допустимые виды: bool, number, string; источники: lvar, rpn. Формат ключа: `^[a-z][a-z0-9]*(\.[A-Za-z0-9][A-Za-z0-9-]*)+$`.

Пример:

```json
{ "key": "custom.apuBleed", "kind": "bool", "source": "lvar",
  "name": "APU_BLEED", "initial": false }
```

Подробности — в [profile-schema.md](profile-schema.md#6-пользовательские-переменные-lvar--rpn).
