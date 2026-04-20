import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def get_allowed_origins() -> list[str]:
    """
    FRONTEND_ORIGIN supports comma-separated values, for example:
    https://your-app.vercel.app,https://your-custom-domain.com,http://localhost:3000
    """
    raw = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Quant Trading Dashboard API",
    version="0.2.0",
    description="Backend for the NDQ ALN trading dashboard with Saxo integration and hard risk rules.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _first_numeric_by_keys(payload: Any, keys: list[str]) -> float | None:
    """
    Recursively find the first numeric value for one of the provided keys.
    """
    normalized_keys = {key.lower() for key in keys}

    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in normalized_keys and isinstance(value, (int, float)):
                return float(value)

        for value in payload.values():
            nested = _first_numeric_by_keys(value, keys)
            if nested is not None:
                return nested

    if isinstance(payload, list):
        for item in payload:
            nested = _first_numeric_by_keys(item, keys)
            if nested is not None:
                return nested

    return None


def _sum_option_market_value(payload: Any) -> float:
    """
    Recursively sum market values of option positions only.
    """
    if isinstance(payload, dict):
        total = 0.0
        asset_type = str(payload.get("AssetType", payload.get("assetType", ""))).lower()
        if "option" in asset_type:
            value = _first_numeric_by_keys(
                payload,
                ["marketvalue", "positionvalue", "netmarketvalue", "currentvalue"],
            )
            if value is not None:
                total += value

        for value in payload.values():
            total += _sum_option_market_value(value)

        return total

    if isinstance(payload, list):
        return sum(_sum_option_market_value(item) for item in payload)

    return 0.0


def _get_saxo_headers() -> dict[str, str]:
    token = get_saxo_access_token()
    return {"Authorization": f"Bearer {token}"}


def _build_saxo_url(path_env: str, fallback: str) -> str:
    base_url = os.getenv("SAXO_OPENAPI_BASE_URL", "https://gateway.saxobank.com/sim/openapi").strip().rstrip("/")
    endpoint_path = os.getenv(path_env, fallback).strip()
    if not endpoint_path.startswith("/"):
        endpoint_path = f"/{endpoint_path}"
    return f"{base_url}{endpoint_path}"


_SAXO_TOKEN_CACHE: dict[str, float | str] = {
    "token": "",
    "expires_at": 0.0,
}


def _get_float_env(name: str, default: float) -> float:
    """
    Parse float env var safely; empty/invalid values fall back to default.
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip()
    if not value:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def get_saxo_access_token() -> str:
    """
    Resolve access token in this order:
    1) Static SAXO_ACCESS_TOKEN (manual token)
    2) OAuth token endpoint using SAXO_APP_KEY/SAXO_APP_SECRET
    """
    static_token = os.getenv("SAXO_ACCESS_TOKEN", "").strip()
    if static_token:
        return static_token

    cached_token = str(_SAXO_TOKEN_CACHE.get("token", ""))
    expires_at = float(_SAXO_TOKEN_CACHE.get("expires_at", 0.0))
    now = time.time()

    # Small safety buffer before real expiry.
    if cached_token and now < (expires_at - 30):
        return cached_token

    client_id = os.getenv("SAXO_APP_KEY", "").strip()
    client_secret = os.getenv("SAXO_APP_SECRET", "").strip()
    token_url = os.getenv("SAXO_TOKEN_URL", "https://sim.logonvalidation.net/token").strip()
    grant_type = os.getenv("SAXO_OAUTH_GRANT_TYPE", "client_credentials").strip()
    timeout = _get_float_env("SAXO_TIMEOUT_SECONDS", 12.0)

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail=(
                "Geen Saxo credentials gevonden. Zet SAXO_ACCESS_TOKEN "
                "of gebruik SAXO_APP_KEY + SAXO_APP_SECRET (+ SAXO_TOKEN_URL)."
            ),
        )

    body: dict[str, str] = {"grant_type": grant_type}
    scope = os.getenv("SAXO_OAUTH_SCOPE", "").strip()
    if scope:
        body["scope"] = scope

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(token_url, data=body, auth=(client_id, client_secret))
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Saxo token request mislukt: {exc}",
        ) from exc

    access_token = str(payload.get("access_token", "")).strip()
    expires_in_raw = payload.get("expires_in", 0)
    try:
        expires_in = int(expires_in_raw)
    except (ValueError, TypeError):
        expires_in = 0

    if not access_token:
        raise HTTPException(
            status_code=502,
            detail="Saxo token endpoint gaf geen access_token terug.",
        )

    _SAXO_TOKEN_CACHE["token"] = access_token
    _SAXO_TOKEN_CACHE["expires_at"] = now + max(expires_in, 60)

    return access_token


def fetch_saxo_account_overview() -> dict[str, float]:
    headers = _get_saxo_headers()
    balances_url = _build_saxo_url("SAXO_BALANCES_PATH", "/port/v1/balances")
    positions_url = _build_saxo_url("SAXO_POSITIONS_PATH", "/port/v1/positions")
    timeout = _get_float_env("SAXO_TIMEOUT_SECONDS", 12.0)

    try:
        with httpx.Client(timeout=timeout, headers=headers) as client:
            balances_response = client.get(balances_url)
            balances_response.raise_for_status()
            balances_payload = balances_response.json()

            positions_response = client.get(positions_url)
            positions_response.raise_for_status()
            positions_payload = positions_response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Saxo OpenAPI request mislukt: {exc}",
        ) from exc

    cash_balance = _first_numeric_by_keys(
        balances_payload,
        ["cashbalance", "cash", "availablefunds", "amount", "value"],
    )

    if cash_balance is None:
        raise HTTPException(
            status_code=502,
            detail="Kon geen cash-balans uit Saxo response halen.",
        )

    options_market_value = _sum_option_market_value(positions_payload)

    bond_collateral_ltv90 = _get_float_env("BOND_COLLATERAL_LTV90", 12_280_000.0)
    total_margin_available = cash_balance + bond_collateral_ltv90
    total_account_value = cash_balance + options_market_value + bond_collateral_ltv90

    return {
        "cashBalance": cash_balance,
        "bondCollateralLtv90": bond_collateral_ltv90,
        "totalMarginAvailable": total_margin_available,
        "totalAccountValue": total_account_value,
        "openOptionsValue": options_market_value,
    }


class TradeCheckRequest(BaseModel):
    product_type: str
    side: str
    quantity: int
    current_long_futures: int = 0


class TradeCheckResponse(BaseModel):
    allowed: bool
    reason: str
    projected_long_futures: int
    hard_limit: int


HARD_LIMIT_CONTRACTS = 50
BLOCKED_PRODUCT_TYPES = {"bond", "bonds", "obligatie", "obligaties"}


def enforce_trading_rules(payload: TradeCheckRequest) -> TradeCheckResponse:
    product = payload.product_type.strip().lower()
    side = payload.side.strip().lower()

    if payload.quantity <= 0:
        return TradeCheckResponse(
            allowed=False,
            reason="Quantity moet groter zijn dan 0.",
            projected_long_futures=payload.current_long_futures,
            hard_limit=HARD_LIMIT_CONTRACTS,
        )

    if product in BLOCKED_PRODUCT_TYPES:
        return TradeCheckResponse(
            allowed=False,
            reason="Obligaties zijn collateral-only en niet tradebaar.",
            projected_long_futures=payload.current_long_futures,
            hard_limit=HARD_LIMIT_CONTRACTS,
        )

    projected = payload.current_long_futures
    if side == "buy":
        projected += payload.quantity
    elif side == "sell":
        projected = max(0, projected - payload.quantity)
    else:
        return TradeCheckResponse(
            allowed=False,
            reason="Side moet buy of sell zijn.",
            projected_long_futures=payload.current_long_futures,
            hard_limit=HARD_LIMIT_CONTRACTS,
        )

    if projected > HARD_LIMIT_CONTRACTS:
        return TradeCheckResponse(
            allowed=False,
            reason=f"Hard limit van {HARD_LIMIT_CONTRACTS} contracten overschreden.",
            projected_long_futures=projected,
            hard_limit=HARD_LIMIT_CONTRACTS,
        )

    return TradeCheckResponse(
        allowed=True,
        reason="Trade voldoet aan backend-risicoregels.",
        projected_long_futures=projected,
        hard_limit=HARD_LIMIT_CONTRACTS,
    )


@app.get("/api/dashboard")
def get_dashboard_snapshot() -> dict:
    account_overview = fetch_saxo_account_overview()

    return {
        "accountOverview": account_overview,
        "risk": {
            "instrument": "NDQ",
            "allowedProducts": ["E-mini NASDAQ-100 Futures", "NDQ Listed Options"],
            "currentLongFutures": 34,
            "hardLimit": HARD_LIMIT_CONTRACTS,
            "bondInventoryMode": "collateral_only",
        },
        "chart": {
            "symbol": "NDQ",
            "overlays": ["Asia High", "Asia Low", "London High", "London Low", "New York High", "New York Low", "VWAP"],
        },
    }


@app.post("/api/rules/check-trade", response_model=TradeCheckResponse)
def check_trade(payload: TradeCheckRequest) -> TradeCheckResponse:
    return enforce_trading_rules(payload)
