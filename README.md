# Trading Bot — Binance Futures Testnet (USDT-M)

A Python trading-bot core (CLI + REST API) with a Node.js/Express
gateway and a React UI on top. **The Python core is the graded
deliverable** for the assignment (which requires Python 3.x); the
Node/React layer is an additional web UI, added on request, that talks
to the *same* Python business logic — nothing is duplicated in JS.

```
Browser (React)  →  Node/Express gateway  →  Python FastAPI  →  Binance Futures Testnet
      :5173               :4000                  :8000
                                                     ↑
                                        pages/cli.py also calls this
                                        same components/ code directly
```
<img width="712" height="586" alt="image" src="https://github.com/user-attachments/assets/8e39793c-284c-4147-8c5e-af776f4f3a02" />
<img width="1103" height="852" alt="image" src="https://github.com/user-attachments/assets/f991d682-a81d-40e8-ac4f-51068053c1f7" />
<img width="1111" height="265" alt="image" src="https://github.com/user-attachments/assets/4eb4133c-6c26-4b0a-acc9-6aad11faa5db" />
<img width="1918" height="585" alt="image" src="https://github.com/user-attachments/assets/1684e15b-473e-4b2c-bed4-2532438135f6" />
<img width="1918" height="967" alt="image" src="https://github.com/user-attachments/assets/ce7d420d-a052-41de-ab65-0cfe7469e6b7" />
<img width="1918" height="952" alt="image" src="https://github.com/user-attachments/assets/c40a3d80-1362-4bb2-a4af-b594fbcbbe81" />
<img width="1918" height="915" alt="image" src="https://github.com/user-attachments/assets/0ac70306-d2f4-4608-b30a-5ad19f1e66e9" />
<img width="1913" height="521" alt="image" src="https://github.com/user-attachments/assets/332de0b1-5eec-4b2f-992a-c475862b09bf" />






## Why it's built this way

The assignment specifies **Language: Python 3.x** as a core requirement,
and grades on correctness of order placement, validation, and logging.
So `components/` (the actual order/validation/API logic) and
`pages/cli.py` (the CLI) are unchanged from the original Python
submission — that's what should be evaluated for the assignment itself.

On top of that, `api/main.py` is a thin FastAPI wrapper that exposes the
exact same `components/` code over HTTP, so a web UI can use it without
re-implementing anything. `server/` is a Node/Express gateway (mostly a
proxy + static file host for the built React app), and `client/` is the
React UI. No order validation, signing, or Binance-calling logic exists
in JavaScript — it all still happens once, in Python.

## Project Structure

```
trading_bot/
  components/          # Reusable Python logic (unchanged core)
    client.py            # Binance Futures REST client (HMAC signing, error handling)
    orders.py             # Order construction + placement
    validators.py         # Input validation, pure functions
    logging_config.py     # Rotating file + console logging
  pages/
    cli.py                # CLI entry point (required Python deliverable)
  api/
    main.py                # FastAPI wrapper exposing components/ over HTTP
  server/                # Node.js/Express gateway
    src/index.js
    package.json
  client/                # React UI (Vite)
    src/App.jsx
    src/index.css
    package.json
  logs/                  # Sample log files (MARKET, LIMIT, STOP orders)
  .env                   # Real env file with placeholder values (see below)
  .env.example
  requirements.txt
  README.md
```

## Setup

### 1. Get Binance Futures Testnet credentials

1. Go to <https://testnet.binancefuture.com> and log in (GitHub login).
2. Generate an API Key + Secret from the testnet dashboard.
3. Testnet funds are virtual — no real money involved.

### 2. Configure `.env`

A real `.env` file (with placeholder credential values) is included at
the project root — copy your own keys in:

```bash
# edit trading_bot/.env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
DRY_RUN=true          # set to false once real keys are in place
CORS_ORIGINS=http://localhost:5173,http://localhost:4000
NODE_PORT=4000
PYTHON_API_URL=http://localhost:8000
```

`DRY_RUN=true` ships as the default so the whole app runs safely out of
the box without real credentials — every order is validated and a
realistic response is simulated instead of calling Binance.

### 3. Install each part

**Python (core + API):**
```bash
cd trading_bot
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Node gateway:**
```bash
cd trading_bot/server
npm install
```

**React client:**
```bash
cd trading_bot/client
npm install
```

## How to Run

### Option A — CLI only (no web UI needed)

**Flag-based (scriptable):**
```bash
cd trading_bot
python pages/cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
python pages/cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 68000
python pages/cli.py --symbol ETHUSDT --side SELL --type STOP --quantity 0.5 --price 3300 --stop-price 3350
# add --dry-run to any of the above to simulate without live credentials
```

**Interactive (menus + step-by-step prompts):**
```bash
python pages/cli.py --interactive
# or just run it with no flags — it falls back to interactive mode automatically
python pages/cli.py
```
Walks you through symbol → side (menu) → order type (menu) → quantity →
price/stop-price (if applicable) → time-in-force (menu) → dry-run
toggle → a final confirmation summary before anything is submitted.
Each answer is validated immediately — an invalid symbol, negative
quantity, etc. gets rejected with a reason and re-prompted on the spot,
using the exact same `components/validators.py` rules as flag mode.

### Option B — Full web stack (three processes, one terminal each)

**1. Python API:**
```bash
cd trading_bot
uvicorn api.main:app --reload --port 8000
```

**2. Node/Express gateway:**
```bash
cd trading_bot/server
npm start
```

**3. React dev server:**
```bash
cd trading_bot/client
npm run dev
```

Then open **http://localhost:5173**. The Vite dev server proxies
`/api/*` and `/health` to the Node gateway on `:4000`, which proxies to
the Python API on `:8000`.

### Option C — Production-style single origin

```bash
cd trading_bot/client && npm run build     # outputs client/dist
cd ../server && npm start                  # serves client/dist + proxies /api
# (with the Python API also running on :8000 as in Option B)
```
Open **http://localhost:4000** — the Node server serves the built React
app and the API from the same origin.

## Using the Web UI

The order form ("New Order") lets you pick symbol, side, order type
(MARKET/LIMIT/STOP), quantity, price, stop price, time-in-force, and a
**Dry run** toggle. Submitted orders appear as ticket-style cards in the
"Order Tape" on the right, each showing order ID, status, executed
quantity, and average price — the same fields the CLI prints.

## Logging

Both the CLI and the API log through the same
`components/logging_config.py` setup, into
`trading_bot/logs/trading_bot.log` (rotating, 5 MB / 3 backups).
Every request, response, validation failure, and API/network error is
recorded; API secrets are redacted before being logged.

Included sample logs (generated via `--dry-run`, see Assumptions below):
- `logs/market_order_example.log`
- `logs/limit_order_example.log`
- `logs/stop_order_example.log` (bonus STOP/stop-limit order)
- `logs/interactive_mode_example.log` (bonus interactive CLI flow)

## Error Handling

- **Invalid input** — caught in `components/validators.py` before any
  network call; the CLI prints a message and exits non-zero, the API
  returns `400` with a `detail` message, and the React UI shows it in a
  banner.
- **API errors** (rejected orders, bad credentials) — caught in
  `components/client.py`, logged with the full response body, surfaced
  as `502` from the FastAPI layer.
- **Network errors** — caught and logged distinctly from API errors.
- **Unexpected errors** — caught at the top of the CLI and the API,
  logged with a full traceback, and reported cleanly rather than
  crashing.

## Assumptions

- Core order logic (`components/`) targets Binance's **USDT-M Futures**
  testnet REST API (`/fapi/v1/order`) via manual HMAC-SHA256 signing
  over `requests`, for full control over logging/error handling.
- Bonus order type: **STOP** (stop-limit), requiring both `price` and
  `stopPrice`.
- The sample logs in `logs/` were generated with `--dry-run` mode: it
  builds and validates the exact same payload a live call would send,
  and logs it identically — only the final HTTP call is replaced with a
  synthesized response, since this delivery environment doesn't have
  live testnet credentials. Running the same commands with real
  credentials and `--dry-run` omitted produces logs in the same format
  with real Binance responses.
- The included `.env` ships with placeholder credentials and
  `DRY_RUN=true` so the app is runnable immediately; it is not a real
  secret and is safe to include in the delivered zip/repo.
- Quantity/price precision (`stepSize`/`tickSize` per symbol) is not
  auto-corrected — Binance will reject out-of-precision values with a
  clear, logged error message.
- Leverage, margin type, and position mode are assumed already
  configured on the testnet account; this project focuses on order
  placement, not account configuration.

## Bonus Delivered

All three optional bonus items are implemented:

- **Third order type**: STOP (stop-limit) — `type=STOP`, requires `price` + `stopPrice`.
- **Enhanced CLI UX**: `pages/cli.py --interactive` (or just running with no
  flags) walks through numbered menus and prompts with inline validation
  and a confirmation step, instead of requiring everything as flags.
- **Lightweight UI**: React + Node/Express web UI on top of the Python core.
