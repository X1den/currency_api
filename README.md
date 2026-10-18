# Currency API

REST API на FastAPI для конвертации, хранения и сбора истории курсов валют в SQLite.

## Стек

- Python
- FastAPI
- HTTPX
- SQLite
- APScheduler
- Pytest

## Эндпойнты
| Метод | Эндпойнт | Описание |
|---|---|---|
| GET | `/` | Проверка |
| GET | `/rate/{base}/{quote}` | Получение курсов |
| GET | `/convert/{base}/{quote}?amount=100` | Конвертация |
| GET | `/history` | История запросов |
| GET | `/history?base=EUR` | Фильтр по первой валюте |
| GET | `/history?quote=USD` | Фильтр по второй валюте |
| GET | `/history?date=2026-10-01` | Фильтр по дате |

## Запуск

```bash
uv sync
uv run uvicorn main:app --reload
```

## Запуск тестов

```bash
uv run python -m pytest -v
```