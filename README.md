# SMOG Bot — TradingView Webhook Handler

Automated trading bot for MEXC futures. Receives TradingView alerts via webhook, applies filter logic (RSI, BTC-tracking), and manages positions.

## Architecture

- **Webhook receiver:** FastAPI server
- **Filters:** RSI, BTC tracking, signal aggregator
- **Broker:** MEXC futures API
- **Deployment:** Docker container with Traefik reverse proxy

## Setup

1. Create `.env` from `.env.example`
2. Fill in secrets (AUTH_TOKEN, MEXC_API_KEY, etc.)
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn src.main:app --reload`

## Project Structure

```
smog-bot/
├── src/
│   ├── main.py          - FastAPI app entry point
│   ├── config.py        - Environment & settings loader
│   ├── models.py        - Pydantic request/response models
│   └── routes/webhook.py - Webhook endpoint handlers
├── tests/               - Unit tests (placeholder)
├── requirements.txt     - Exact Python dependencies
├── .env.example         - Environment variables template
├── Dockerfile           - Container definition (skeleton)
└── pyproject.toml       - Package metadata
```

## Status

[PRIO 3] — Skeleton phase. No trading logic yet.

---
*Created: 2026-04-29 by Botman*
