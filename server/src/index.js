import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import express from "express";
import cors from "cors";
import fetch from "node-fetch";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
dotenv.config({ path: path.join(PROJECT_ROOT, ".env") });

const PORT = process.env.NODE_PORT || 4000;
const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

const app = express();
app.use(cors());
app.use(express.json());

// Simple request logger so gateway traffic shows up in the console too.
app.use((req, _res, next) => {
  console.log(`[gateway] ${new Date().toISOString()} ${req.method} ${req.path}`);
  next();
});

app.get("/health", async (_req, res) => {
  try {
    const upstream = await fetch(`${PYTHON_API_URL}/health`);
    const data = await upstream.json();
    res.json({ gateway: "ok", pythonApi: data });
  } catch (err) {
    res.status(502).json({ gateway: "ok", pythonApi: "unreachable", error: err.message });
  }
});

app.post("/api/orders", async (req, res) => {
  try {
    const upstream = await fetch(`${PYTHON_API_URL}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await upstream.json();
    res.status(upstream.status).json(data);
  } catch (err) {
    console.error("[gateway] Failed to reach Python API:", err.message);
    res.status(502).json({ detail: `Could not reach Python API at ${PYTHON_API_URL}: ${err.message}` });
  }
});

// In production, serve the built React app from the same origin as the API.
const clientDist = path.join(PROJECT_ROOT, "client", "dist");
app.use(express.static(clientDist));
app.get("*", (req, res, next) => {
  if (req.path.startsWith("/api") || req.path === "/health") return next();
  res.sendFile(path.join(clientDist, "index.html"), (err) => {
    if (err) next();
  });
});

app.listen(PORT, () => {
  console.log(`[gateway] Trading bot gateway listening on http://localhost:${PORT}`);
  console.log(`[gateway] Proxying order requests to Python API at ${PYTHON_API_URL}`);
});
