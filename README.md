# Currency API

REST API на FastAPI для конвертации, хранения и сбора истории курсов валют в SQLite.

## Стек

- Python
- FastAPI
- HTTPX
- SQLite
- APScheduler
- Pytest

## Endpoints
| GET | `/` |
| GET | `/rate/{base}/{quote}` |
| GET | `/convert/{base}/{quote}?amount=100` |
| GET | `/history` |
| GET | `/history?base=EUR` |
| GET | `/history?quote=USD` |
| GET | `/history?date=2026-10-01` |

## Running Tests

```bash
uv run python -m pytest -v
```