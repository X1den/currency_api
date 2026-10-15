from fastapi import FastAPI, HTTPException

app = FastAPI()

currencies = {
    "USD": 81.42,
    "EUR": 95.17,
    "CNY": 11.35
}

@app.get("/")
def get_health():
    return {"message": "Currency API"}

@app.get("/currencies")
def get_currencies():
    return [{"code": code, "rate": rate} for code, rate in currencies.items()]
    
@app.get("/currencies/{code}")
def get_currency(code: str):
    if code not in currencies:
        raise HTTPException(status_code=404, detail="Currency not found")
    return {"code": code, "rate": currencies[code]}

@app.get("/currencies/{code}/convert")
def convert_currency(code: str, amount: float, precision: int = 2):
    if code not in currencies:
        raise HTTPException(status_code=404, detail="Currency not found")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Bad request")
    if precision < 0 or precision > 6:
        raise HTTPException(status_code=400, detail="Precision must be between 0 and 6")
    return {"currency": code, "amount": amount, "result": round(amount * currencies[code], precision)}