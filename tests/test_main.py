from fastapi.testclient import TestClient
import main
import sqlite3
import pytest
import httpx
from unittest.mock import AsyncMock, patch

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_currency.db"
    monkeypatch.setattr(main, "DB_PATH", str(db_path))
    main.init_db(str(db_path))
    return db_path

@pytest.fixture
def client(test_db):
    with TestClient(main.app) as test_client:
        yield test_client
        
def test_get_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Currency API"}

def test_get_history(client):
    response = client.get("/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_history_by_base(client, test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    cursor.execute(
        """
        INSERT INTO rate_history (date, base, quote, rate)
        VALUES (?, ?, ?, ?)
        """,
        ("2026-10-01", "EUR", "USD", 1.10)
    )
    
    cursor.execute(
        """
        INSERT INTO rate_history (date, base, quote, rate)
        VALUES (?, ?, ?, ?)
        """,
        ("2026-10-01", "USD", "RUB", 80.00)
    )
    
    conn.commit()
    conn.close()
    
    response = client.get("/history?base=EUR")
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["base"] == "EUR"
    assert data[0]["quote"] == "USD"
    assert data[0]["rate"] == 1.1

def test_history_empty(client):
    response = client.get("/history")
    
    assert response.status_code == 200
    assert response.json() == []

def test_get_history_by_quote(client, test_db):
    with sqlite3.connect(test_db) as conn:
        conn.executemany(
            """
            INSERT INTO rate_history (date, base, quote, rate)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("2026-10-01", "EUR", "USD", 1.10),
                ("2026-10-01", "USD", "RUB", 80.00),
            ],
        )
        
    response = client.get("/history?quote=RUB")
    
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["base"] == "USD"
    assert data[0]["quote"] == "RUB"
    
def test_get_history_by_date(client, test_db):
    with sqlite3.connect(test_db) as conn:
        conn.executemany(
            """
            INSERT INTO rate_history (date, base, quote, rate)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("2026-10-01", "EUR", "USD", 1.10),
                ("2026-10-02", "USD", "RUB", 80.00),
            ],
        )

    response = client.get("/history?date=2026-10-01")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-10-01"


def test_save_rate(test_db):
    main.save_rate("2026-10-01", "EUR", "USD", 1.10)
    main.save_rate("2026-10-01", "EUR", "USD", 1.10)
    
    with sqlite3.connect(test_db) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM rate_history
            WHERE date = ? AND base = ? AND quote = ?
            """,
            ("2026-10-01", "EUR", "USD"),
        ).fetchone()[0]
        
        assert count == 1
        
def test_convert_rejects_zero(client):
    response = client.get("convert/EUR/USD?amount=0")
    assert response.status_code == 400
    
def test_convert_rejects_invalid(client):
    response = client.get("/convert/EUR/USD?amount=10&precision=7")
    
    assert response.status_code == 400
    
def test_get_rate_success(client):
    response_data = {
        "date": "2026-10-01",
        "base": "EUR",
        "quote": "USD",
        "rate": 1.10,
    }
    
    mock_response = httpx.Response(
        200,
        json=response_data,
        request=httpx.Request("GET", "https://api.frankfurter.dev"),
    )
    
    with patch("main.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        response = client.get("/rate/EUR/USD")

    assert response.status_code == 200
    assert response.json()["base"] == "EUR"
    assert response.json()["quote"] == "USD"
    assert response.json()["rate"] == pytest.approx(1.10)
    
def test_get_rate_external_api_error(client):
    mock_response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=httpx.Request("GET", "https://api.frankfurter.dev"),
    )

    with patch("main.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        response = client.get("/rate/EUR/XXX")

    assert response.status_code == 404
    assert response.json()["detail"] == "External API returned an error"
    
