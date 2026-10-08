from fastapi import FastAPI, HTTPException

app = FastAPI()

currencies = {
    "USD": 81.42,
    "EUR": 95.17,
    "CNY": 11.35
}

@app.get("/")
def get_health():
    return {"message": "Currensy API"}

@app.get("/currencies")
def get_currencies():
    return [{"code": code, "rate": rate} for code, rate in currencies.items()]
    
@app.get("/currencies/{code}")
def get_currency(code: str):
    if code not in currencies:
        raise HTTPException(status_code=404, detail="Currency not found")
    return {"code": code, "rate": currencies[code]}