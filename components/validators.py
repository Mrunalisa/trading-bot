"""
Input validation for order parameters.

Kept separate from the API/client layer so validation rules can be
unit-tested in isolation and reused by both the CLI and any future
interface (e.g. a web UI).
"""

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}  # STOP = bonus stop-limit order
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK"}

# Binance Futures symbols are uppercase alphanumeric, typically 6-12 chars
# (e.g. BTCUSDT, ETHUSDT). We keep the check permissive but sane.
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(Exception):
    """Raised when user-supplied order input fails validation."""


def validate_symbol(symbol: str) -> str:
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol is required, e.g. 'BTCUSDT'.")
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected an uppercase alphanumeric "
            f"pair like 'BTCUSDT' (5-20 characters)."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required (MARKET, LIMIT, or STOP).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if qty <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return qty


def validate_price(price, order_type: str):
    """Price is mandatory for LIMIT/STOP orders, ignored for MARKET."""
    if order_type in {"LIMIT", "STOP"}:
        if price is None:
            raise ValidationError(f"Price is required for {order_type} orders.")
        try:
            p = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a number, got '{price}'.")
        if p <= 0:
            raise ValidationError("Price must be greater than 0.")
        return p
    return None


def validate_stop_price(stop_price, order_type: str):
    """Stop price is mandatory for STOP orders only (bonus order type)."""
    if order_type == "STOP":
        if stop_price is None:
            raise ValidationError("stop_price is required for STOP orders.")
        try:
            sp = float(stop_price)
        except (TypeError, ValueError):
            raise ValidationError(f"stop_price must be a number, got '{stop_price}'.")
        if sp <= 0:
            raise ValidationError("stop_price must be greater than 0.")
        return sp
    return None


def validate_time_in_force(tif: str) -> str:
    tif = (tif or "GTC").strip().upper()
    if tif not in VALID_TIME_IN_FORCE:
        raise ValidationError(f"Invalid timeInForce '{tif}'. Must be one of {sorted(VALID_TIME_IN_FORCE)}.")
    return tif
