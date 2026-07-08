"""
Order construction and placement logic.

This layer sits between the CLI and the raw API client: it validates
input, assembles the exact parameter set Binance expects for each
order type, and logs the outcome. Keeping it separate from client.py
means the HTTP/signing details can change without touching order
business logic, and vice versa.
"""

import logging

from .client import BinanceFuturesClientError
from .validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
    validate_time_in_force,
)

logger = logging.getLogger("trading_bot.orders")


class OrderManager:
    """Builds and places MARKET, LIMIT, and STOP (stop-limit) orders."""

    def __init__(self, client):
        self.client = client

    def build_order_params(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None,
        stop_price=None,
        time_in_force="GTC",
    ) -> dict:
        """Validate raw input and return a Binance-ready parameter dict."""
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_order_type(order_type)
        quantity = validate_quantity(quantity)
        price = validate_price(price, order_type)
        stop_price = validate_stop_price(stop_price, order_type)
        time_in_force = validate_time_in_force(time_in_force)

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        # LIMIT and STOP (stop-limit) orders need a limit price + TIF.
        if order_type in {"LIMIT", "STOP"}:
            params["price"] = price
            params["timeInForce"] = time_in_force

        # STOP (stop-limit) additionally needs the trigger price.
        if order_type == "STOP":
            params["stopPrice"] = stop_price

        return params

    def place_order(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None,
        stop_price=None,
        time_in_force="GTC",
    ):
        """
        Validate, place, and log an order.

        Returns
        -------
        (params, response) : tuple[dict, dict]
            The request parameters actually sent, and the raw API response.

        Raises
        ------
        ValidationError
            If the input fails validation (never reaches the network).
        BinanceFuturesClientError
            If the API call fails (network error, bad credentials, rejected order, etc).
        """
        params = self.build_order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )

        logger.info("Submitting order: %s", params)
        try:
            response = self.client.place_order(**params)
        except BinanceFuturesClientError as exc:
            logger.error("Order submission failed: %s", exc)
            raise

        logger.info(
            "Order accepted: orderId=%s status=%s executedQty=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
        )
        return params, response
