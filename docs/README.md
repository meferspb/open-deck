# 📚 Документация Open Deck for MSFS

<img src="pic1.jpg" alt="Open Deck for MSFS" width="180" />

Здесь собраны все документы проекта. Начните с README в корне — он даёт
общую картину и быстрый старт; этот индекс поможет найти детали.

## С чего начать

| Если вы… | Читайте по порядку |
| --- | --- |
| пилот, ставите панель «для себя» | [README](../README.md) → [service.md](service.md) |
| хотите понять устройство | [architecture.md](architecture.md) → [protocol.md](protocol.md) |
| пишете клиент или интеграцию | [protocol.md](protocol.md) → [telemetry.md](telemetry.md) |
| меняете код | [development.md](development.md) → [architecture.md](architecture.md) |
| делаете профиль самолёта | [profile-schema.md](profile-schema.md) → [widgets.md](widgets.md) |
| собираете установщик/APK | [packaging/windows/README.md](../packaging/windows/README.md) → [android/README.md](../android/README.md) |
| проверяете безопасность | [SECURITY.md](../SECURITY.md) |

## Документы

| Документ | О чём | Аудитория |
| --- | --- | --- |
| [service.md](service.md) | Полное описание сервиса: назначение, модель работы, телеметрия, профили, клиенты, сеть, аутентификация, ассистент, API, установка, диагностика, безопасность, лицензия | все |
| [architecture.md](architecture.md) | Внутреннее устройство: модули, потоки данных, WASM-мост, ключевые решения и границы MVP | разработчики |
| [protocol.md](protocol.md) | HTTP REST, WebSocket, вход по паролю и QR, автообнаружение, коды ошибок и примеры | интеграторы |
| [telemetry.md](telemetry.md) | Каталог всех переменных: типы, единицы, SimVar, события, `custom.*` — генерируется из кода | разработчики клиентов, профилей |
| [widgets.md](widgets.md) | Каталог приборов: обязательные привязки, `command`, опции, примеры JSON — генерируется из кода | авторы профилей |
| [profile-schema.md](profile-schema.md) | Схема JSON-профиля: поля, раскладки, валидация, совместимость, полный пример | авторы профилей |
| [development.md](development.md) | Как менять код: карта модулей, добавление переменной/прибора/профиля/провайдера/страницы, тесты, релиз | контрибьюторы |
| [pricing.md](pricing.md) | Сравнение «подключаемые сервисы vs локальные аналоги» для air-gapped сценария | те, кто выбирает стек |
| [../android/README.md](../android/README.md) | Android-клиент: сборка, архитектура, вход, отладка | Android-разработчики |
| [../packaging/windows/README.md](../packaging/windows/README.md) | Установщик: состав, сборка, ярлыки, удаление, тихие флаги | релиз-инженеры |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Как участвовать: стиль, тесты, профили, PR | контрибьюторы |
| [../SECURITY.md](../SECURITY.md) | Модель угроз, что защищено, как сообщить об уязвимости | все |
| [../CHANGELOG.md](../CHANGELOG.md) | История версий | все |

## Скриншоты

`docs/screenshots/` — панель на телефоне и планшете, six-pack, редактор,
страница входа и ассистент. Используются в README и в описании сервиса.

## Актуальность

Два документа **генерируются из кода** и проверяются тестом:

```powershell
python -m msfs_gateway.docsgen --check   # telemetry.md и widgets.md
python -m msfs_gateway.docsgen --write   # обновить после правок реестров
```

Если меняли `telemetry.py`, `profiles.py` или веб-приборы — обновите
документацию и прогоните `pwsh -File scripts/check.ps1`.

## Как писать документацию

- Пишите по-русски, короткими абзацами, с примерами JSON/команд.
- Ссылки — относительные, чтобы работали и на GitHub, и локально.
- Не дублируйте схему: профиль — в `profile-schema.md`, переменные — в
  `telemetry.md`, приборы — в `widgets.md`, сеть — в `protocol.md`.
- Меняете поведение — обновите README/сервис и `CHANGELOG.md`.
