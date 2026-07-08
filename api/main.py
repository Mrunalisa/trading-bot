"""
FastAPI wrapper around the existing Python trading-bot core.

This is intentionally thin: it does NOT reimplement any order logic.
Every request is validated and executed through the exact same
`components/` modules used by `pages/cli.py` — so the CLI and the web
UI are guaranteed to behave identically, and there is a single source
of truth for validation, signing, and logging.

Run:
    uvicorn api.main:app --reload --port 8000
"""

import os
import sys

# Allow `import components...` when running from the project root or elsewhere.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from components.client import BinanceFuturesClient, BinanceFuturesClientError
from components.logging_config import setup_logging
from components.orders import OrderManager
from components.validators import ValidationError

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

logger = setup_logging(log_file=os.path.join(_PROJECT_ROOT, "logs", "trading_bot.log"))

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BASE_URL = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")
DRY_RUN_DEFAULT = os.getenv("DRY_RUN", "false").lower() == "true"

app = FastAPI(
    title="Trading Bot API",
    description="REST API in front of the Binance Futures Testnet trading bot core.",
    version="1.0.0",
)

# The Node/Express gateway (and, in dev, the Vite dev server) call this API
# from a different origin, so CORS must be open to those origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrderRequest(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    side: str = Field(..., examples=["BUY"])
    order_type: str = Field(..., alias="type", examples=["MARKET"])
    quantity: float = Field(..., examples=[0.01])
    price: Optional[float] = Field(None, examples=[68000])
    stop_price: Optional[float] = Field(None, alias="stopPrice", examples=[68500])
    time_in_force: str = Field("GTC", alias="timeInForce")
    dry_run: Optional[bool] = Field(None, alias="dryRun")

    class Config:
        populate_by_name = True


def _get_client(dry_run: bool) -> BinanceFuturesClient:
    return BinanceFuturesClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        base_url=BASE_URL,
        dry_run=dry_run,
    )


@app.get("/health")
def health():
    return {"status": "ok", "dry_run_default": DRY_RUN_DEFAULT, "base_url": BASE_URL}


@app.post("/api/orders")
def place_order(order: OrderRequest):
    dry_run = order.dry_run if order.dry_run is not None else (DRY_RUN_DEFAULT or not (API_KEY and API_SECRET))

    client = _get_client(dry_run=dry_run)
    manager = OrderManager(client)

    try:
        params, response = manager.place_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            time_in_force=order.time_in_force,
        )
    except ValidationError as exc:
        logger.error("Validation error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except BinanceFuturesClientError as exc:
        logger.error("Order failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error while placing order")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")

    return {
        "request": params,
        "response": response,
        "dryRun": dry_run,
    }
