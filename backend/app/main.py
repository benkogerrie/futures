from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Quant Trading Dashboard API",
    version="0.1.0",
    description="Mock backend for the NDQ ALN trading dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def get_dashboard_snapshot() -> dict:
    return {
        "accountOverview": {
            "cashBalance": 5_100_000,
            "bondCollateralLtv90": 12_280_000,
            "totalMarginAvailable": 17_380_000,
            "totalAccountValue": 24_100_000,
        },
        "risk": {
            "instrument": "NDQ",
            "allowedProducts": ["E-mini NASDAQ-100 Futures", "NDQ Listed Options"],
            "currentLongFutures": 34,
            "hardLimit": 50,
            "bondInventoryMode": "collateral_only",
        },
        "chart": {
            "symbol": "NDQ",
            "overlays": ["Asia High", "Asia Low", "London High", "London Low", "New York High", "New York Low", "VWAP"],
        },
    }
