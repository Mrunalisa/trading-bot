import { useEffect, useState } from "react";

const ORDER_TYPES = ["MARKET", "LIMIT", "STOP"];

function emptyForm() {
  return {
    symbol: "BTCUSDT",
    side: "BUY",
    type: "MARKET",
    quantity: "0.01",
    price: "",
    stopPrice: "",
    timeInForce: "GTC",
    dryRun: true,
  };
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function App() {
  const [form, setForm] = useState(emptyForm());
  const [tickets, setTickets] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [apiOnline, setApiOnline] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/health")
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) setApiOnline(Boolean(data?.pythonApi?.status === "ok"));
      })
      .catch(() => {
        if (!cancelled) setApiOnline(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function needsPrice(type) {
    return type === "LIMIT" || type === "STOP";
  }

  function needsStopPrice(type) {
    return type === "STOP";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const payload = {
      symbol: form.symbol.trim().toUpperCase(),
      side: form.side,
      type: form.type,
      quantity: Number(form.quantity),
      price: needsPrice(form.type) && form.price !== "" ? Number(form.price) : null,
      stopPrice: needsStopPrice(form.type) && form.stopPrice !== "" ? Number(form.stopPrice) : null,
      timeInForce: form.timeInForce,
      dryRun: form.dryRun,
    };

    try {
      const res = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Order failed.");
        setTickets((t) => [
          {
            id: `err-${Date.now()}`,
            time: new Date(),
            error: data.detail || "Order failed.",
            request: payload,
          },
          ...t,
        ]);
        return;
      }

      setTickets((t) => [
        { id: `ok-${data.response.orderId}-${Date.now()}`, time: new Date(), ...data },
        ...t,
      ]);
    } catch (err) {
      setError(`Could not reach the gateway: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Order Desk</h1>
          <div className="subtitle">Binance Futures Testnet · USDT-M</div>
        </div>
        <div className={`status-pill ${apiOnline === null ? "" : apiOnline ? "online" : "offline"}`}>
          <span className="status-dot" />
          {apiOnline === null ? "checking API…" : apiOnline ? "API online" : "API unreachable"}
        </div>
      </header>

      <div className="layout">
        <form className="panel" onSubmit={handleSubmit}>
          <h2>New Order</h2>
          <div className="panel-eyebrow">fapi/v1/order</div>

          {error && <div className="error-banner">{error}</div>}

          <div className="field">
            <label htmlFor="symbol">Symbol</label>
            <input
              id="symbol"
              value={form.symbol}
              onChange={(e) => update("symbol", e.target.value.toUpperCase())}
              placeholder="BTCUSDT"
              required
            />
          </div>

          <div className="field">
            <label>Side</label>
            <div className="side-toggle">
              <button
                type="button"
                className={`buy ${form.side === "BUY" ? "active" : ""}`}
                onClick={() => update("side", "BUY")}
              >
                Buy
              </button>
              <button
                type="button"
                className={`sell ${form.side === "SELL" ? "active" : ""}`}
                onClick={() => update("side", "SELL")}
              >
                Sell
              </button>
            </div>
          </div>

          <div className="field">
            <label>Order Type</label>
            <div className="type-toggle">
              {ORDER_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={form.type === t ? "active" : ""}
                  onClick={() => update("type", t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="quantity">Quantity</label>
            <input
              id="quantity"
              type="number"
              step="any"
              min="0"
              value={form.quantity}
              onChange={(e) => update("quantity", e.target.value)}
              required
            />
          </div>

          {needsPrice(form.type) && (
            <div className="field">
              <label htmlFor="price">Price</label>
              <input
                id="price"
                type="number"
                step="any"
                min="0"
                value={form.price}
                onChange={(e) => update("price", e.target.value)}
                required
              />
            </div>
          )}

          {needsStopPrice(form.type) && (
            <div className="field">
              <label htmlFor="stopPrice">Stop Price (trigger)</label>
              <input
                id="stopPrice"
                type="number"
                step="any"
                min="0"
                value={form.stopPrice}
                onChange={(e) => update("stopPrice", e.target.value)}
                required
              />
            </div>
          )}

          {needsPrice(form.type) && (
            <div className="field">
              <label htmlFor="tif">Time in Force</label>
              <select id="tif" value={form.timeInForce} onChange={(e) => update("timeInForce", e.target.value)}>
                <option value="GTC">GTC — Good Till Cancel</option>
                <option value="IOC">IOC — Immediate or Cancel</option>
                <option value="FOK">FOK — Fill or Kill</option>
              </select>
            </div>
          )}

          <div className="dry-run-row">
            <div>
              <div>Dry run</div>
              <div className="hint">Simulate without hitting Binance</div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={form.dryRun}
                onChange={(e) => update("dryRun", e.target.checked)}
              />
              <span className="track" />
            </label>
          </div>

          <button
            type="submit"
            className={`submit-btn ${form.side === "BUY" ? "buy" : "sell"}`}
            disabled={submitting}
          >
            {submitting ? "Submitting…" : `${form.side} ${form.symbol || ""}`}
          </button>
        </form>

        <section>
          <div className="tape-header">
            <h2>Order Tape</h2>
            <span className="count">{tickets.length} ticket{tickets.length === 1 ? "" : "s"}</span>
          </div>

          <div className="tape">
            {tickets.length === 0 && (
              <div className="empty-tape">No orders yet — submit one from the ticket on the left.</div>
            )}

            {tickets.map((t) => (
              <Ticket key={t.id} ticket={t} />
            ))}
          </div>
        </section>
      </div>

      <footer className="app-footer">
        React → Node/Express gateway → Python FastAPI → Binance Futures Testnet. Same validation &amp; order
        logic as the CLI.
      </footer>
    </div>
  );
}

function Ticket({ ticket }) {
  if (ticket.error) {
    return (
      <div className="ticket">
        <div className="notches" />
        <div className="ticket-side sell">
          ERR
          <span className="type-label">{ticket.request?.type}</span>
        </div>
        <div className="ticket-body">
          <div className="symbol-row">
            <span className="symbol">{ticket.request?.symbol}</span>
            <span className="order-id">rejected</span>
          </div>
          <div className="ticket-grid">
            <span className="k">reason</span>
            <span className="v" style={{ gridColumn: "span 2" }}>
              {ticket.error}
            </span>
          </div>
        </div>
        <div className="ticket-status">
          <span className="status-badge error">FAILED</span>
          <span className="timestamp">{formatTime(ticket.time)}</span>
        </div>
      </div>
    );
  }

  const { request, response, dryRun } = ticket;
  const statusClass = response.status === "FILLED" ? "filled" : "new";

  return (
    <div className="ticket">
      <div className="notches" />
      <div className={`ticket-side ${request.side === "BUY" ? "buy" : "sell"}`}>
        {request.side}
        <span className="type-label">{request.type}</span>
      </div>
      <div className="ticket-body">
        {dryRun && <span className="testnet-stamp">DRY-RUN</span>}
        <div className="symbol-row">
          <span className="symbol">{request.symbol}</span>
          <span className="order-id">#{response.orderId}</span>
        </div>
        <div className="ticket-grid">
          <span className="k">qty</span>
          <span className="v">{response.executedQty ?? request.quantity}</span>
          <span />
          {request.price !== undefined && (
            <>
              <span className="k">price</span>
              <span className="v">{request.price}</span>
              <span />
            </>
          )}
          <span className="k">avg</span>
          <span className="v">{response.avgPrice}</span>
          <span />
        </div>
      </div>
      <div className="ticket-status">
        <span className={`status-badge ${statusClass}`}>{response.status}</span>
        <span className="timestamp">{formatTime(ticket.time)}</span>
      </div>
    </div>
  );
}
