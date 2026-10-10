# Сервис статистики устройств

REST API на FastAPI для приёма показаний `{ "x": float, "y": float, "z": float }` и анализа каждого показателя по идентификатору устройства.

## Запуск в Docker

Из вашего каталога, при запущенном Docker Desktop с Linux-контейнерами:

```sh
docker compose up --build -d
docker compose ps
```

API: http://localhost:8000, интерактивная документация: http://localhost:8000/docs, OpenAPI: http://localhost:8000/openapi.json.

В PowerShell можно запустить `./start.ps1`: скрипт собирает контейнеры, ожидает готовности сервисов и выводит ссылку на Swagger UI. При запуске через Uvicorn ссылка также выводится в лог приложения; для фонового Docker-запуска лог доступен через `docker compose logs api`.

PostgreSQL 17 запускается отдельным сервисом `db`. API ожидает успешного healthcheck БД. Данные хранятся в именованном томе `postgres_data` и сохраняются при пересоздании контейнеров. Остановка: `docker compose down`. Команда `docker compose down -v` удаляет также данные.

По умолчанию PostgreSQL доступен внутри Docker по адресу `db:5432`, порт БД на Windows не публикуется. База называется `app_db`, таблица показаний — `app_data`. Открыть SQL-консоль: `docker compose exec db psql -U postgres -d app_db`. Просмотр записей: `SELECT * FROM app_data ORDER BY id DESC LIMIT 20;`.

Для подключения из pgAdmin/DBeaver или запуска API вне Docker включите дополнительный файл: `docker compose -f compose.yaml -f compose.local.yaml up -d db`. Хост `localhost`, порт `15432`, база `app_db`, пользователь `postgres`, пароль `postgres`. Это настройки для локального задания. Порт можно изменить переменной `POSTGRES_PORT` (и использовать выбранный порт в строках подключения ниже). Если Windows сообщает об ошибке публикации порта, обычный запуск через `docker compose up --build -d` не требует публикации порта БД.

## Локальный запуск

Python 3.10 или новее (Docker использует 3.12). Из каталога проекта:

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose -f compose.yaml -f compose.local.yaml up -d db
$env:DATABASE_URL = 'postgresql://postgres:postgres@localhost:15432/app_db'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Linux/macOS:

```sh
.venv/bin/python -m pip install -r requirements.txt
docker compose -f compose.yaml -f compose.local.yaml up -d db
export DATABASE_URL='postgresql://postgres:postgres@localhost:15432/app_db'
.venv/bin/python -m uvicorn app.main:app --reload
```

Подключение задаётся обязательной переменной окружения `DATABASE_URL`. Можно использовать свой PostgreSQL вместо контейнера: заранее создайте базу и пользователя с правом создания таблиц. Таблица `app_data` и индекс создаются автоматически при запуске API. Локального файла БД больше нет; SQLite не используется. Перенос старых SQLite-данных не выполняется.

## API

### Добавление показаний

`POST /devices/{device_id}/readings` возвращает `201 Created`, идентификатор записи, устройство, координаты и время UTC.

```json
{
  "x": 1.5,
  "y": -2.0,
  "z": 3.0,
  "timestamp": "2026-01-01T12:00:00+03:00"
}
```

`timestamp` необязателен: при отсутствии или `null` используется время сервера. Переданное время должно содержать часовой пояс. Идентификатор устройства: от 1 до 128 латинских букв, цифр, символов `_` или `-`; предварительная регистрация не требуется. Координаты обязательны, принимаются JSON-числа (включая целые), но не строки, булевы значения, NaN или бесконечности. Диапазон каждой координаты ограничен ±1e100 для безопасного расчёта суммы и медианы. Лишние поля отклоняются. Повторная отправка создаёт новое измерение, даже при совпадении времени.

Пример PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/devices/sensor-1/readings' -ContentType 'application/json' -Body '{"x":1.5,"y":-2.0,"z":3.0}'
Invoke-RestMethod 'http://localhost:8000/devices/sensor-1/statistics'
```

### Анализ

`GET /devices/{device_id}/statistics`

Необязательные параметры `start` и `end` задают включительные границы периода в ISO 8601 с часовым поясом. Без обоих параметров анализируется вся история; можно задать только одну границу. В URL знак `+` в часовом поясе кодируется как `%2B`; удобнее использовать UTC с суффиксом `Z`.

Пример: `/devices/sensor-1/statistics?start=2026-01-01T00:00:00Z&end=2026-01-31T23:59:59.999999Z`.

Для каждой координаты возвращаются `min`, `max`, `count`, `sum`, `median`. Для чётного количества медиана — среднее двух центральных значений. Например, после одного измерения выше:

```json
{
  "device_id": "sensor-1",
  "start": null,
  "end": null,
  "x": {"min": 1.5, "max": 1.5, "count": 1, "sum": 1.5, "median": 1.5},
  "y": {"min": -2.0, "max": -2.0, "count": 1, "sum": -2.0, "median": -2.0},
  "z": {"min": 3.0, "max": 3.0, "count": 1, "sum": 3.0, "median": 3.0}
}
```

Для пустого периода или неизвестного устройства возвращается `200`: `count=0`, `sum=0`, остальные характеристики `null`. Ошибки формата и обратный период (`start > end`) возвращают `422`.

`GET /health` проверяет доступность таблицы БД; используется Docker healthcheck.

## Архитектура и ограничения

Приложение использует слоистую архитектуру: HTTP-маршруты → сервис → репозиторий → PostgreSQL. Сервис не зависит от FastAPI, а репозиторий не обрабатывает HTTP-запросы.

```text
app/
├── main.py          # создание приложения и связывание слоёв
├── schemas.py       # модели Pydantic для входных данных и результатов
├── routes.py        # HTTP-маршруты и преобразование ошибок в ответы
├── services.py      # проверка периода и расчёт статистики
├── repository.py    # SQL-запросы: сохранение и чтение показаний
└── database.py      # соединения, транзакции и создание таблицы
```

`main.py` создаёт подключение, репозиторий и сервис, затем передаёт сервис маршрутам. При запуске создаются таблица и индекс, если их ещё нет. Используется PostgreSQL и драйвер Psycopg 3 без ORM. Запросы параметризованы. Время хранится в `TIMESTAMPTZ`, координаты — в `DOUBLE PRECISION`, идентификатор — `BIGINT IDENTITY`. Индекс `(device_id, timestamp)` ускоряет выборку. Каждое обращение использует отдельное соединение, которое закрывается после завершения транзакции; при исключении изменения откатываются. Таймаут подключения — 10 секунд.

Обработчики синхронные и выполняются FastAPI в пуле потоков. Анализ рассчитывается непосредственно в HTTP-запросе. Для точной медианы выбранные показания загружаются в память; расход памяти O(n), сортировка для медианы O(n log n).
