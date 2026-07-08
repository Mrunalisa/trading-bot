#!/usr/bin/env python3
"""
CLI entry point for the simplified Binance Futures Testnet trading bot.

Two ways to use it:

1. Flag-based (scriptable, good for automation/CI):
    python pages/cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run

2. Interactive (menus + step-by-step prompts, good for humans):
    python pages/cli.py --interactive
    # or just run it with no flags at all — it falls back to interactive mode
    python pages/cli.py

Both modes funnel through the exact same components/ validation and
order-placement logic, so behavior is identical either way.
"""

import os
import sys

# pages/ and components/ are sibling folders under the project root, so
# add the project root to sys.path to import components as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import click
from dotenv import load_dotenv

from components.client import BinanceFuturesClient, BinanceFuturesClientError
from components.logging_config import setup_logging
from components.orders import OrderManager
from components.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
    validate_time_in_force,
)

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

_DEFAULT_LOG_FILE = os.path.join(_PROJECT_ROOT, "logs", "trading_bot.log")

ORDER_TYPE_MENU = [
    ("MARKET", "Market  — fill immediately at the best available price"),
    ("LIMIT", "Limit   — fill only at your price or better"),
    ("STOP", "Stop    — bonus: stop-limit, triggers at stopPrice then works as a limit order"),
]

TIF_MENU = [
    ("GTC", "Good Till Cancel — stays open until filled or cancelled"),
    ("IOC", "Immediate or Cancel — fills what it can immediately, cancels the rest"),
    ("FOK", "Fill or Kill — fills completely immediately, or not at all"),
]


# --------------------------------------------------------------------- #
# Interactive prompt helpers
# --------------------------------------------------------------------- #
def _prompt_loop(prompt_text, validator, **validator_kwargs):
    """Prompt repeatedly until `validator(value, **validator_kwargs)` succeeds."""
    while True:
        raw = click.prompt(prompt_text)
        try:
            return validator(raw, **validator_kwargs)
        except ValidationError as exc:
            click.secho(f"  ✗ {exc}", fg="red")


def _prompt_menu(title, options):
    """
    Render a numbered menu and return the selected key.
    `options` is a list of (key, description) tuples.
    """
    click.secho(f"\n{title}", fg="cyan", bold=True)
    for i, (key, desc) in enumerate(options, start=1):
        click.echo(f"  {i}) {desc}")
    valid_choices = [str(i) for i in range(1, len(options) + 1)]
    while True:
        choice = click.prompt("Select", type=click.Choice(valid_choices), show_choices=False)
        return options[int(choice) - 1][0]


def interactive_flow():
    """Walk the user through building an order step by step, with menus
    and inline validation at every step. Returns a dict of raw order params.
    """
    click.secho("=== Interactive Order Builder ===", fg="cyan", bold=True)
    click.echo("Answer each prompt; invalid input is rejected immediately with a reason.\n")

    symbol = _prompt_loop("Symbol (e.g. BTCUSDT)", validate_symbol)

    side = _prompt_menu("Side", [("BUY", "Buy"), ("SELL", "Sell")])
    side = validate_side(side)

    order_type = _prompt_menu("Order type", ORDER_TYPE_MENU)
    order_type = validate_order_type(order_type)

    quantity = _prompt_loop(f"Quantity ({symbol}, base asset)", validate_quantity)

    price = None
    stop_price = None
    time_in_force = "GTC"

    if order_type in {"LIMIT", "STOP"}:
        price = _prompt_loop("Limit price", validate_price, order_type=order_type)
        tif_key = _prompt_menu("Time in force", TIF_MENU)
        time_in_force = validate_time_in_force(tif_key)

    if order_type == "STOP":
        stop_price = _prompt_loop("Stop (trigger) price", validate_stop_price, order_type=order_type)

    dry_run = click.confirm(
        "\nDry run? (simulate only, no live order sent)", default=True
    )

    # --- confirmation summary before doing anything ---
    click.secho("\n=== Confirm Order ===", fg="yellow", bold=True)
    click.echo(f"Symbol       : {symbol}")
    click.echo(f"Side         : {side}")
    click.echo(f"Type         : {order_type}")
    click.echo(f"Quantity     : {quantity}")
    if price is not None:
        click.echo(f"Price        : {price}")
    if stop_price is not None:
        click.echo(f"Stop Price   : {stop_price}")
    click.echo(f"Time in Force: {time_in_force}")
    click.echo(f"Mode         : {'DRY RUN (simulated)' if dry_run else 'LIVE (testnet)'}")

    if not click.confirm("\nSubmit this order?", default=True):
        click.secho("Cancelled — no order was submitted.", fg="yellow")
        sys.exit(0)

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "stop_price": stop_price,
        "time_in_force": time_in_force,
        "dry_run": dry_run,
    }


# --------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------- #
@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--symbol", default=None, help="Trading pair, e.g. BTCUSDT")
@click.option(
    "--side",
    default=None,
    type=click.Choice(["BUY", "SELL"], case_sensitive=False),
    help="Order side.",
)
@click.option(
    "--type",
    "order_type",
    default=None,
    type=click.Choice(["MARKET", "LIMIT", "STOP"], case_sensitive=False),
    help="Order type. STOP is a bonus stop-limit order.",
)
@click.option("--quantity", default=None, type=float, help="Order quantity in base asset.")
@click.option("--price", default=None, type=float, help="Limit price. Required for LIMIT and STOP orders.")
@click.option("--stop-price", default=None, type=float, help="Trigger price. Required for STOP orders.")
@click.option("--time-in-force", default="GTC", show_default=True, help="GTC, IOC, or FOK.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate the order locally without calling the Binance API (no credentials needed).",
)
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Force the interactive menu/prompt flow, even if flags are also given.",
)
@click.option(
    "--log-file",
    default=_DEFAULT_LOG_FILE,
    show_default=True,
    help="Path to the log file that captures requests/responses/errors.",
)
def main(symbol, side, order_type, quantity, price, stop_price, time_in_force, dry_run, interactive, log_file):
    """Place a MARKET, LIMIT, or STOP order on Binance Futures Testnet (USDT-M).

    Runs interactively (menus + prompts) if --interactive is passed, or if
    the required flags (--symbol/--side/--type/--quantity) are not all
    supplied. Otherwise runs directly off the flags you gave.
    """
    logger = setup_logging(log_file=log_file)

    required_flags_given = all([symbol, side, order_type, quantity is not None])

    if interactive or not required_flags_given:
        try:
            built = interactive_flow()
        except (click.Abort, KeyboardInterrupt):
            click.secho("\nAborted.", fg="yellow")
            sys.exit(130)
        symbol = built["symbol"]
        side = built["side"]
        order_type = built["order_type"]
        quantity = built["quantity"]
        price = built["price"]
        stop_price = built["stop_price"]
        time_in_force = built["time_in_force"]
        dry_run = built["dry_run"] or dry_run

    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

    if not dry_run and (not api_key or not api_secret):
        click.secho(
            "Missing BINANCE_API_KEY / BINANCE_API_SECRET.\n"
            "Either create a .env file with your testnet credentials, "
            "or re-run with --dry-run to try the bot without them.",
            fg="red",
        )
        sys.exit(1)

    client = BinanceFuturesClient(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
        dry_run=dry_run,
    )
    manager = OrderManager(client)

    order_type_upper = order_type.upper()
    side_upper = side.upper()

    click.secho("\n=== Order Request Summary ===", fg="cyan", bold=True)
    click.echo(f"Symbol       : {symbol.upper()}")
    click.echo(f"Side         : {side_upper}")
    click.echo(f"Type         : {order_type_upper}")
    click.echo(f"Quantity     : {quantity}")
    if order_type_upper in {"LIMIT", "STOP"}:
        click.echo(f"Price        : {price}")
    if order_type_upper == "STOP":
        click.echo(f"Stop Price   : {stop_price}")
    click.echo(f"Time in Force: {time_in_force.upper()}")
    click.echo(f"Mode         : {'DRY RUN (simulated)' if dry_run else 'LIVE (testnet)'}")
    click.echo(f"Log file     : {log_file}")

    try:
        params, response = manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )
    except ValidationError as exc:
        click.secho(f"\n✗ Validation error: {exc}", fg="red", bold=True)
        logger.error("Validation error: %s", exc)
        sys.exit(1)
    except BinanceFuturesClientError as exc:
        click.secho(f"\n✗ Order failed: {exc}", fg="red", bold=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - top-level safety net for the CLI
        click.secho(f"\n✗ Unexpected error: {exc}", fg="red", bold=True)
        logger.exception("Unexpected error while placing order")
        sys.exit(1)

    click.secho("\n=== Order Response ===", fg="green", bold=True)
    click.echo(f"Order ID       : {response.get('orderId')}")
    click.echo(f"Status         : {response.get('status')}")
    click.echo(f"Executed Qty   : {response.get('executedQty')}")
    click.echo(f"Avg Price      : {response.get('avgPrice')}")
    click.secho("\n✓ Order placed successfully.\n", fg="green", bold=True)


if __name__ == "__main__":
    main()
