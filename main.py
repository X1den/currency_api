import httpx 
import sqlite3
import logging
from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

DB_PATH = "currency.db"

def get_connection(db_path: str | None = None):
    if db_path is None:
        db_path = DB_PATH
    return sqlite3.connect(db_path)

scheduler = AsyncIOScheduler()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DB_PATH)
    
    scheduler.add_job(collect_rates, "interval", hours=24)
    scheduler.start()
    yield
    scheduler.shutdown()
    
app = FastAPI(lifespan=lifespan)

CURRENCY_PAIRS = [
    ('EUR', 'USD'),
    ('EUR', 'RUB'),
    ('USD', 'RUB'),
]

def init_db(db_path: str):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS rate_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            base TEXT NOT NULL,
            quote TEXT NOT NULL,
            rate DECIMAL(10, 4) NOT NULL,
            UNIQUE (date, base, quote)
        )
        '''
    )
    conn.commit()
    conn.close()

@app.get("/")
def get_status():
    return {"message": "Currency API"}

async def fetch_rate(base: str, quote: str):
    base = base.upper()
    quote = quote.upper()
    
    url = f"https://api.frankfurter.dev/v2/rate/{base}/{quote}"
    
    if len(base) != 3 or len(quote) != 3:
        raise HTTPException(
            status_code=400,
            detail="Currency codes must contain 3 characters"
            )
        
    if not base.isalpha() or not quote.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Currency codes must contain only letters"
        )
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail="External API returned an error"
            )
    
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="External API is unavailable"
        )
    
    data = response.json()
    return data

def save_rate(date: str, base: str, quote: str, rate: float):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO rate_history (date, base, quote, rate)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date, base, quote) DO NOTHING
            ''', 
            (date, base.upper(), quote.upper(), rate)
                   )
    
@app.get("/rate/{base}/{quote}")
async def get_rate(base: str, quote: str):
    data = await fetch_rate(base, quote)
    save_rate(data["date"], base, quote, data["rate"])
    return {
        "date": data["date"],
        "base": base.upper(),
        "quote": quote.upper(),
        "rate": data["rate"]
    }

@app.get("/convert/{base}/{quote}")
async def convert(base: str, quote:str, amount: float, precision: int = 2):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Bad request")
    
    if precision < 0 or precision > 6:
        raise HTTPException(
            status_code=400,
            detail="Precision must be between 0 and 6"
                )
        
    data = await fetch_rate(base, quote)
    return {
        "date": data["date"],
        "base": base.upper(),
        "quote": quote.upper(),
        "amount": amount,
        "rate": data["rate"],
        "result": round(data["rate"] * amount, precision)
    }
    
@app.get("/history")
def get_history(date: str | None = None, base: str | None = None, quote: str | None = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
            
        if base:
            conditions.append("base = ?")
            params.append(base.upper())
            
        if quote:
            conditions.append("quote = ?")
            params.append(quote.upper())
        
        query = """
            SELECT id, date, base, quote, rate
            FROM rate_history
        """
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "date": row[1],
                "base": row[2],
                "quote": row[3],
                "rate": row[4]
            }
            for row in rows]
        
async def collect_rates():
    for base, quote in CURRENCY_PAIRS:
        try:
            data = await fetch_rate(base, quote)
            save_rate(data["date"], base, quote, data["rate"])
            logger.info(
                "Saved rate for %s/%s: %s (%s)",
                        base,
                        quote,
                        data["rate"],
                        data["date"]
                    )
        except HTTPException as e:
            logger.error(
                "Failed to collect rate for %s/%s: %s",
                base,
                quote,
                e.detail
            )