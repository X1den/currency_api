import httpx 
from fastapi import FastAPI, HTTPException
import sqlite3

app = FastAPI()

conn = sqlite3.connect("currency.db")
cursor = conn.cursor()
cursor.execute('''
             CREATE TABLE IF NOT EXISTS rate_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base TEXT NOT NULL,
                quote TEXT NOT NULL,
                rate DECIMAL(10, 4) NOT NULL
            )
            ''')

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

def save_rate(base: str, quote: str, rate: float):
    with sqlite3.connect("currency.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO rate_history (base, quote, rate)
                       VALUES (?, ?, ?)
                   ''', 
                   (base.upper(), quote.upper(), rate)
                   )
    
@app.get("/rate/{base}/{quote}")
async def get_rate(base: str, quote: str):
    data = await fetch_rate(base, quote)
    save_rate(base, quote, data["rate"])
    return {
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
        "base": base.upper(),
        "quote": quote.upper(),
        "amount": amount,
        "rate": data["rate"],
        "result": round(data["rate"] * amount, precision)
    }
    
@app.get("/history")
def get_history():
    with sqlite3.connect("currency.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT id, base, quote, rate
                       FROM rate_history
                       ORDER BY id DESC
                       ''')
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "base": row[1],
                "quote": row[2],
                "rate": row[3]
            }
            for row in rows]