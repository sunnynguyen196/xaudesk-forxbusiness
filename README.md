# XAUDesk Cloud — MT5 -> web dashboard

This is a deployable package, **not a published website**. No live MT5 access or cloud account access was available during packaging.

## 1. Publish cloud server (Render)

1. Upload this folder to a **private GitHub repository** (exclude `.venv`, credentials and snapshots).
2. On Render, choose **New > Blueprint**, select the repo and apply `render.yaml`. The `starter` plan is used to reduce sleep risk; check current hosting charges.
3. Copy the resulting `https://...onrender.com` URL. Open it and enter the username `xaudesk` and the generated `XAU_DASH_PASSWORD` from Render environment variables.
4. Copy `XAU_INGEST_TOKEN` from Render environment variables. **Never put this token into HTML, Git, screenshots or a public URL.**

Note: `/tmp` storage is **ephemeral**; after a restart the most recent snapshot is lost until the Windows agent uploads again. For durable historical data, add a managed database in a later iteration. The dashboard itself is password protected with HTTP Basic Auth; for production use a stronger identity solution (SSO/MFA) and rate limiting.

## 2. Start Windows MT5 agent

1. Keep FPG MT5 logged in and `XAUUSD.c` visible; ensure Python 3.14 has MetaTrader5 installed, or use the `.venv` from the previous project.
2. Copy `market.py`, `mt5_agent.py`, `start-agent.cmd` to a Windows folder.
3. In CMD **in that folder**, set variables for that CMD session:

```bat
set "XAU_CLOUD_URL=https://YOUR-SERVICE.onrender.com"
set "XAU_INGEST_TOKEN=PASTE_SECRET_FROM_RENDER"
start-agent.cmd
```

4. Expected output: `Uploaded XAUUSD.c quote_utc ... ok True`.
5. Visit the HTTPS dashboard URL from any device, authenticate, and check the timestamp. On weekends, the quote may show `STALE` even when uploads succeed.

### Testing locally

```bash
export XAU_INGEST_TOKEN='a-long-random-token-at-least-20-chars'
export XAU_DASH_USER='xaudesk'
export XAU_DASH_PASSWORD='a-long-random-password-at-least-20-chars'
python cloud_server.py
```

Visit http://127.0.0.1:8765 locally. For public access use HTTPS provided by a hosting service, not a bare HTTP port.

## Security

- Read-only price/candles; **no trading and no MT5 account credentials**.
- Ingestion endpoint requires a secret header; dashboard requires a separate username/password.
- Rotate secrets if exposed; do not publish secrets in client-side JS.
- Cloud host must support persistent Python processes and HTTPS.
- Cloud server only receives data pushed by the Windows agent. It cannot connect to the user's MT5 on its own.
