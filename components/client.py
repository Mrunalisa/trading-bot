"""
Thin wrapper around the Binance Futures (USDT-M) REST API.

Implemented with `requests` + manual HMAC signing rather than the
`python-binance` package so that request/response handling, retries,
and logging are fully explicit and easy to audit.

This module knows nothing about CLI arguments or business validation;
it only knows how to talk to Binance. That separation keeps it
reusable and unit-testable in isolation (see orders.py for the layer
that builds order parameters and validators.py for input checks).
"""

import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds


class BinanceFuturesClientError(Exception):
    """Raised for any API, network, or protocol-level failure."""


class BinanceFuturesClient:
    """
    Minimal REST client for Binance USDT-M Futures.

    Parameters
    ----------
    api_key, api_secret : str
        Credentials generated from the Binance Futures Testnet UI.
    base_url : str
        API root. Defaults to the testnet endpoint.
    dry_run : bool
        If True, no network calls are made; a plausible response is
        synthesized instead. Useful for demos / CI / offline testing
        without live credentials.
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        dry_run: bool = False,
    ):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.dry_run = dry_run

        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------ #
    # Low-level request plumbing
    # ------------------------------------------------------------------ #
    def _sign(self, params: dict) -> str:
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _redact(params: dict) -> dict:
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***REDACTED***"
        return redacted

    def _request(self, method: str, path: str, params: dict = None, signed: bool = True) -> dict:
        params = dict(params or {})
        url = f"{self.base_url}{path}"

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params.setdefault("recvWindow", 5000)
            params["signature"] = self._sign(params)

        logger.info("REQUEST  %s %s | params=%s", method, url, self._redact(params))

        if self.dry_run:
            response_data = self._simulate_response(params)
            logger.info("RESPONSE (dry-run, no network call made) | %s", response_data)
            return response_data

        try:
            response = self.session.request(method, url, params=params, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error("NETWORK ERROR  %s %s | %s", method, url, exc)
            raise BinanceFuturesClientError(f"Network error calling {path}: {exc}") from exc

        try:
            data = response.json()
        except ValueError:
            logger.error(
                "INVALID RESPONSE  %s %s | status=%s body=%s",
                method, url, response.status_code, response.text[:500],
            )
            raise BinanceFuturesClientError(
                f"Non-JSON response from {path} (status {response.status_code})"
            )

        if response.status_code >= 400:
            logger.error(
                "API ERROR  %s %s | status=%s body=%s", method, url, response.status_code, data
            )
            code = data.get("code", response.status_code)
            msg = data.get("msg", "Unknown error")
            raise BinanceFuturesClientError(f"Binance API error {code}: {msg}")

        logger.info("RESPONSE  %s %s | status=%s body=%s", method, url, response.status_code, data)
        return data

    _DRY_RUN_REFERENCE_PRICES = {
        "BTCUSDT": 65000.0,
        "ETHUSDT": 3400.0,
    }

    def _simulate_response(self, params: dict) -> dict:
        """Synthesize a realistic order response for --dry-run mode."""
        import random

        order_id = random.randint(1_000_000, 9_999_999)
        order_type = params.get("type", "MARKET")
        symbol = params.get("symbol", "")
        qty = str(params.get("quantity", "0"))
        status = "FILLED" if order_type == "MARKET" else "NEW"

        if order_type == "MARKET":
            ref_price = self._DRY_RUN_REFERENCE_PRICES.get(symbol, 100.0)
            avg_price = str(round(ref_price * random.uniform(0.999, 1.001), 2))
            price = "0"  # Binance market orders don't carry a limit price
        else:
            price = str(params.get("price", "0"))
            avg_price = "0"  # NEW limit/stop orders have no fills yet

        return {
            "orderId": order_id,
            "symbol": symbol,
            "status": status,
            "clientOrderId": f"dryrun_{order_id}",
            "price": price,
            "avgPrice": avg_price,
            "origQty": qty,
            "executedQty": qty if status == "FILLED" else "0",
            "side": params.get("side"),
            "type": order_type,
            "timeInForce": params.get("timeInForce", "GTC"),
        }

    # ------------------------------------------------------------------ #
    # Public API surface
    # ------------------------------------------------------------------ #
    def place_order(self, **order_params) -> dict:
        """POST /fapi/v1/order"""
        return self._request("POST", "/fapi/v1/order", params=order_params)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """GET /fapi/v1/order"""
        return self._request("GET", "/fapi/v1/order", params={"symbol": symbol, "orderId": order_id})

    def get_account(self) -> dict:
        """GET /fapi/v2/account"""
        return self._request("GET", "/fapi/v2/account", params={})

    def ping(self) -> dict:
        """GET /fapi/v1/ping (unsigned connectivity check)"""
        return self._request("GET", "/fapi/v1/ping", params={}, signed=False)
