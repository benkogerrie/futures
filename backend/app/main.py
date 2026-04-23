import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Laadt backend/.env bij lokale uvicorn (Railway/Vercel gebruiken al echte env vars).
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


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


def _hard_limit_contracts() -> int:
    raw = os.getenv("SAXO_NDQ_HARD_LIMIT", "50").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 50


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


def _futures_long_from_netpositions(netpositions: Any) -> int:
    """Som van netto long futures-contracten uit /port/v1/netpositions/me (SIM)."""
    if not isinstance(netpositions, dict):
        return 0
    total = 0.0
    for row in netpositions.get("Data") or []:
        if not isinstance(row, dict):
            continue
        base = row.get("NetPositionBase")
        if not isinstance(base, dict):
            continue
        if base.get("AssetType") != "Futures":
            continue
        try:
            amount = float(base.get("Amount") or 0)
        except (TypeError, ValueError):
            continue
        direction = base.get("OpeningDirection")
        if direction == "Sell":
            total -= amount
        else:
            total += amount
    return max(0, int(round(total)))


def _futures_breakdown_from_netpositions(netpositions: Any, *, limit: int = 12) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(netpositions, dict):
        return rows
    for row in (netpositions.get("Data") or [])[:limit]:
        if not isinstance(row, dict):
            continue
        base = row.get("NetPositionBase")
        if not isinstance(base, dict) or base.get("AssetType") != "Futures":
            continue
        view = row.get("NetPositionView") if isinstance(row.get("NetPositionView"), dict) else {}
        disp = row.get("DisplayAndFormat") if isinstance(row.get("DisplayAndFormat"), dict) else {}
        symbol = (
            disp.get("Symbol")
            or disp.get("Description")
            or row.get("NetPositionId")
            or str(base.get("Uic") or "")
        )
        direction = base.get("OpeningDirection")
        try:
            amount = float(base.get("Amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        current_price = _as_float(view.get("CurrentPrice"))
        exposure = _as_float(view.get("Exposure"))
        pnl = _as_float(view.get("ProfitLossOnTrade"))
        rows.append(
            {
                "symbol": str(symbol)[:64],
                "contracts": amount,
                "direction": str(direction or ""),
                "currentPrice": current_price,
                "exposure": exposure,
                "profitLossOnTrade": pnl,
            }
        )
    return rows


def _positions_summary(positions: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"positionRowCount": 0, "totalMarketValueListed": None}
    if not isinstance(positions, dict):
        return out
    count = positions.get("__count")
    if isinstance(count, (int, float)):
        out["positionRowCount"] = int(count)
    else:
        data = positions.get("Data")
        if isinstance(data, list):
            out["positionRowCount"] = len(data)
    total_mv = 0.0
    data = positions.get("Data") if isinstance(positions.get("Data"), list) else []
    for row in data:
        if not isinstance(row, dict):
            continue
        mv = _first_numeric_by_keys(row, ["marketvalue", "netmarketvalue", "positionvalue", "value"])
        if mv is not None:
            total_mv += float(mv)
    if total_mv != 0.0 or out["positionRowCount"]:
        out["totalMarketValueListed"] = total_mv
    return out


def _flatten_initial_margin(balances: dict[str, Any]) -> dict[str, float]:
    im = balances.get("InitialMargin")
    if not isinstance(im, dict):
        return {}
    keys = (
        ("MarginAvailable", "initialMarginAvailable"),
        ("MarginUsedByCurrentPositions", "initialMarginUsedByPositions"),
        ("MarginUtilizationPct", "initialMarginUtilizationPct"),
        ("NetEquityForMargin", "initialMarginNetEquity"),
    )
    out: dict[str, float] = {}
    for src, dst in keys:
        v = _as_float(im.get(src))
        if v is not None:
            out[dst] = v
    return out


def _copy_balance_numerics(balances: dict[str, Any]) -> dict[str, float]:
    """
    Extra numerieke velden uit /balances/me (SIM) — camelCase voor JSON.
    """
    spec: list[tuple[str, str]] = [
        ("CashAvailableForTrading", "cashAvailableForTrading"),
        ("CashBlocked", "cashBlocked"),
        ("CollateralAvailable", "collateralAvailable"),
        ("MarginAvailableForTrading", "marginAvailableForTradingRaw"),
        ("MarginCollateralNotAvailable", "marginCollateralNotAvailable"),
        ("MarginNetExposure", "marginNetExposure"),
        ("MarginUtilizationPct", "marginUtilizationPct"),
        ("MarginAndCollateralUtilizationPct", "marginAndCollateralUtilizationPct"),
        ("NetEquityForMargin", "netEquityForMargin"),
        ("NonMarginPositionsValue", "nonMarginPositionsValue"),
        ("OpenPositionsCount", "openPositionsCount"),
        ("NetPositionsCount", "netPositionsCount"),
        ("OrdersCount", "ordersCount"),
        ("TriggerOrdersCount", "triggerOrdersCount"),
        ("SettlementValue", "settlementValue"),
        ("TotalValue", "totalValueRaw"),
        ("TransactionsNotBooked", "transactionsNotBooked"),
        ("UnrealizedMarginProfitLoss", "unrealizedMarginProfitLoss"),
        ("UnrealizedPositionsValue", "unrealizedPositionsValue"),
        ("CostToClosePositions", "costToClosePositions"),
        ("FundsAvailableForSettlement", "fundsAvailableForSettlement"),
        ("FundsReservedForSettlement", "fundsReservedForSettlement"),
        ("CorporateActionUnrealizedAmounts", "corporateActionUnrealizedAmounts"),
        ("OptionPremiumsMarketValue", "optionPremiumsMarketValue"),
    ]
    out: dict[str, float] = {}
    for saxo_key, json_key in spec:
        v = _as_float(balances.get(saxo_key))
        if v is not None:
            out[json_key] = v
    out.update(_flatten_initial_margin(balances))
    return out


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


def _build_saxo_query_params() -> dict[str, str]:
    """
    Optional account context for Saxo endpoints that require explicit keys.
    """
    params: dict[str, str] = {}
    client_key = os.getenv("SAXO_CLIENT_KEY", "").strip()
    account_key = os.getenv("SAXO_ACCOUNT_KEY", "").strip()

    if client_key:
        params["ClientKey"] = client_key
    if account_key:
        params["AccountKey"] = account_key

    return params


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
    2) Cached token (from previous OAuth call)
    3) Refresh token flow (SAXO_REFRESH_TOKEN)
    4) Client credentials flow (SAXO_APP_KEY/SAXO_APP_SECRET)
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
    refresh_token = os.getenv("SAXO_REFRESH_TOKEN", "").strip()
    refresh_file = os.getenv("SAXO_REFRESH_TOKEN_FILE", "").strip()
    if not refresh_token and refresh_file:
        try:
            with open(refresh_file, encoding="utf-8") as handle:
                refresh_token = handle.read().strip()
        except OSError:
            refresh_token = ""
    timeout = _get_float_env("SAXO_TIMEOUT_SECONDS", 12.0)

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail=(
                "Geen Saxo credentials gevonden. Zet SAXO_ACCESS_TOKEN "
                "of gebruik SAXO_APP_KEY + SAXO_APP_SECRET (+ SAXO_TOKEN_URL)."
            ),
        )

    resolved_grant_type = grant_type
    body: dict[str, str] = {"grant_type": resolved_grant_type}
    scope = os.getenv("SAXO_OAUTH_SCOPE", "").strip()
    if refresh_token:
        resolved_grant_type = "refresh_token"
        body = {
            "grant_type": resolved_grant_type,
            "refresh_token": refresh_token,
        }
        redirect_uri = os.getenv("SAXO_REDIRECT_URI", "").strip()
        if redirect_uri:
            body["redirect_uri"] = redirect_uri
    elif scope:
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

    # Keep the newest refresh token if Saxo rotates it.
    refreshed_refresh_token = str(payload.get("refresh_token", "")).strip()
    if refreshed_refresh_token:
        os.environ["SAXO_REFRESH_TOKEN"] = refreshed_refresh_token
        if refresh_file:
            try:
                tmp = f"{refresh_file}.{os.getpid()}.tmp"
                with open(tmp, "w", encoding="utf-8") as handle:
                    handle.write(refreshed_refresh_token)
                os.replace(tmp, refresh_file)
            except OSError:
                pass

    return access_token


def fetch_saxo_dashboard_sources() -> tuple[dict[str, Any], int, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Haalt balances, positions en netpositions in één Saxo-sessie op (SIM).

    Returns:
        (account_overview, futures_long_contracts, balances_json, positions_json, netpositions_json)
    """
    headers = _get_saxo_headers()
    balances_url = _build_saxo_url("SAXO_BALANCES_PATH", "/port/v1/balances/me")
    positions_url = _build_saxo_url("SAXO_POSITIONS_PATH", "/port/v1/positions/me")
    netpositions_url = _build_saxo_url("SAXO_NETPOSITIONS_PATH", "/port/v1/netpositions/me")
    timeout = _get_float_env("SAXO_TIMEOUT_SECONDS", 12.0)

    query_params = _build_saxo_query_params()
    net_q: dict[str, str] = dict(query_params) if query_params else {}
    net_q["$top"] = os.getenv("SAXO_NETPOSITIONS_TOP", "200").strip() or "200"
    net_q["FieldGroups"] = "NetPositionBase,NetPositionView,DisplayAndFormat"

    def _request_json(
        client: httpx.Client,
        url: str,
        *,
        extra_params: dict[str, str] | None = None,
    ) -> Any:
        merged: dict[str, str] | None = None
        if query_params or extra_params:
            merged = {}
            if query_params:
                merged.update(query_params)
            if extra_params:
                merged.update(extra_params)
        try:
            response = client.get(url, params=merged)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text.strip()
            body_suffix = f" | body: {body[:800]}" if body else ""
            raise HTTPException(
                status_code=502,
                detail=f"Saxo OpenAPI request mislukt: {exc}{body_suffix}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Saxo OpenAPI request mislukt: {exc}",
            ) from exc

    with httpx.Client(timeout=timeout, headers=headers) as client:
        balances_payload = _request_json(client, balances_url)
        positions_payload = _request_json(client, positions_url)
        netpositions_payload = _request_json(client, netpositions_url, extra_params=net_q)

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

    other_collateral = balances_payload.get("OtherCollateral") if isinstance(balances_payload, dict) else None
    if isinstance(other_collateral, (int, float)) and float(other_collateral) >= 0:
        bond_collateral_ltv90 = float(other_collateral)
    else:
        bond_collateral_ltv90 = _get_float_env("BOND_COLLATERAL_LTV90", 12_280_000.0)

    if not isinstance(balances_payload, dict):
        balances_payload = {}

    margin_saxo = _as_float(balances_payload.get("MarginAvailableForTrading"))
    total_val_saxo = _as_float(balances_payload.get("TotalValue"))
    total_margin_available = (
        float(margin_saxo) if margin_saxo is not None else cash_balance + bond_collateral_ltv90
    )
    total_account_value = (
        float(total_val_saxo)
        if total_val_saxo is not None
        else cash_balance + options_market_value + bond_collateral_ltv90
    )

    cd_raw = balances_payload.get("CurrencyDecimals")
    try:
        currency_decimals = int(cd_raw) if cd_raw is not None else 2
    except (TypeError, ValueError):
        currency_decimals = 2

    overview: dict[str, Any] = {
        "currency": str(balances_payload.get("Currency") or "USD"),
        "currencyDecimals": currency_decimals,
        "cashBalance": cash_balance,
        "bondCollateralLtv90": bond_collateral_ltv90,
        "totalMarginAvailable": total_margin_available,
        "totalAccountValue": total_account_value,
        "openOptionsValue": options_market_value,
    }
    overview.update(_copy_balance_numerics(balances_payload))
    pos_summary = _positions_summary(positions_payload)
    overview["positionsListedCount"] = float(pos_summary["positionRowCount"])
    if pos_summary.get("totalMarketValueListed") is not None:
        overview["positionsTotalMarketValue"] = float(pos_summary["totalMarketValueListed"])

    futures_long = _futures_long_from_netpositions(netpositions_payload)
    return overview, futures_long, balances_payload, positions_payload, netpositions_payload


def _anchor_price_from_futures_netpositions(netpositions: Any) -> float | None:
    if not isinstance(netpositions, dict):
        return None
    for row in netpositions.get("Data") or []:
        if not isinstance(row, dict):
            continue
        base = row.get("NetPositionBase")
        if not isinstance(base, dict) or base.get("AssetType") != "Futures":
            continue
        view = row.get("NetPositionView") if isinstance(row.get("NetPositionView"), dict) else {}
        cp = _as_float(view.get("CurrentPrice"))
        if cp is not None and cp > 0:
            return cp
    return None


def _position_rows_sample(positions: Any, *, limit: int = 12) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(positions, dict):
        return out
    for row in (positions.get("Data") or [])[:limit]:
        if not isinstance(row, dict):
            continue
        pb = row.get("PositionBase") if isinstance(row.get("PositionBase"), dict) else {}
        disp = row.get("DisplayAndFormat") if isinstance(row.get("DisplayAndFormat"), dict) else {}
        sym = disp.get("Symbol") or disp.get("Description") or pb.get("NetPositionId") or ""
        asset = pb.get("AssetType") or row.get("AssetType")
        amt = _as_float(pb.get("AmountOpen") or pb.get("Size") or row.get("AmountOpen"))
        out.append(
            {
                "symbol": str(sym)[:80],
                "assetType": str(asset) if asset is not None else None,
                "amountOpen": amt,
            }
        )
    return out


def _build_risk_payload(
    balances: dict[str, Any],
    netpositions: dict[str, Any],
    futures_long: int,
    hard_limit: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "instrument": "NDQ",
        "allowedProducts": ["E-mini NASDAQ-100 Futures", "NDQ Listed Options"],
        "currentLongFutures": futures_long,
        "hardLimit": hard_limit,
        "bondInventoryMode": "collateral_only",
        "marginUtilizationPct": _as_float(balances.get("MarginUtilizationPct")),
        "marginAndCollateralUtilizationPct": _as_float(balances.get("MarginAndCollateralUtilizationPct")),
        "openPositionsCount": _as_int(balances.get("OpenPositionsCount")),
        "netPositionsCount": _as_int(balances.get("NetPositionsCount")),
        "ordersCount": _as_int(balances.get("OrdersCount")),
        "triggerOrdersCount": _as_int(balances.get("TriggerOrdersCount")),
        "unrealizedMarginProfitLoss": _as_float(balances.get("UnrealizedMarginProfitLoss")),
        "unrealizedPositionsValue": _as_float(balances.get("UnrealizedPositionsValue")),
        "marginNetExposure": _as_float(balances.get("MarginNetExposure")),
        "futuresBreakdown": _futures_breakdown_from_netpositions(netpositions),
    }
    return {k: v for k, v in payload.items() if v is not None or k in ("futuresBreakdown", "allowedProducts")}


def _build_chart_payload(balances: dict[str, Any], netpositions: dict[str, Any]) -> dict[str, Any]:
    anchor = _anchor_price_from_futures_netpositions(netpositions)
    data = netpositions.get("Data") if isinstance(netpositions.get("Data"), list) else []
    return {
        "symbol": "NDQ",
        "overlays": [
            "Asia High",
            "Asia Low",
            "London High",
            "London Low",
            "New York High",
            "New York Low",
            "VWAP",
        ],
        "currency": str(balances.get("Currency") or "USD"),
        "environment": "saxo-sim",
        "anchorPrice": anchor,
        "calculationReliability": balances.get("CalculationReliability"),
        "netPositionsReturned": len(data),
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


BLOCKED_PRODUCT_TYPES = {"bond", "bonds", "obligatie", "obligaties"}


def enforce_trading_rules(payload: TradeCheckRequest) -> TradeCheckResponse:
    product = payload.product_type.strip().lower()
    side = payload.side.strip().lower()
    hard_limit = _hard_limit_contracts()

    if payload.quantity <= 0:
        return TradeCheckResponse(
            allowed=False,
            reason="Quantity moet groter zijn dan 0.",
            projected_long_futures=payload.current_long_futures,
            hard_limit=hard_limit,
        )

    if product in BLOCKED_PRODUCT_TYPES:
        return TradeCheckResponse(
            allowed=False,
            reason="Obligaties zijn collateral-only en niet tradebaar.",
            projected_long_futures=payload.current_long_futures,
            hard_limit=hard_limit,
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
            hard_limit=hard_limit,
        )

    if projected > hard_limit:
        return TradeCheckResponse(
            allowed=False,
            reason=f"Hard limit van {hard_limit} contracten overschreden.",
            projected_long_futures=projected,
            hard_limit=hard_limit,
        )

    return TradeCheckResponse(
        allowed=True,
        reason="Trade voldoet aan backend-risicoregels.",
        projected_long_futures=projected,
        hard_limit=hard_limit,
    )


@app.get("/api/dashboard")
def get_dashboard_snapshot() -> dict:
    account_overview, futures_long, balances, positions, netpositions = fetch_saxo_dashboard_sources()
    hard_limit = _hard_limit_contracts()

    return {
        "meta": {
            "environment": "saxo-sim",
            "saxoOpenApi": True,
        },
        "accountOverview": account_overview,
        "risk": _build_risk_payload(balances, netpositions, futures_long, hard_limit),
        "chart": _build_chart_payload(balances, netpositions),
        "positionsSample": _position_rows_sample(positions),
    }


@app.post("/api/rules/check-trade", response_model=TradeCheckResponse)
def check_trade(payload: TradeCheckRequest) -> TradeCheckResponse:
    return enforce_trading_rules(payload)
