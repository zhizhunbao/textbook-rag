# ngrok Local Deployment

This is the GO-DEPLOY path for demo and early paid trials: run Payload and Engine locally, expose Payload through ngrok, and keep Engine private on localhost.

## Architecture

```text
User browser
  -> https://<ngrok-domain>
  -> localhost:3001 Payload / Next.js
  -> localhost:8001 Engine API
  -> local PostgreSQL / ChromaDB / uploads
```

Only Payload is public. Engine stays on `127.0.0.1:8001`; the browser calls Engine through configured client URLs where existing real-time query flows require it.

## Prerequisites

- ngrok account and authtoken configured locally.
- PostgreSQL, ChromaDB storage, and uploads available through the existing local setup.
- `.env` contains real secrets: `PAYLOAD_SECRET`, Stripe keys, model keys, and database URL.

## Environment

Copy `.env.ngrok.example` to `.env.ngrok` for notes, then set these values in `.env`:

```dotenv
PAYLOAD_URL=http://localhost:3001
PAYLOAD_PUBLIC_SERVER_URL=https://<ngrok-domain>
NEXT_PUBLIC_ENGINE_URL=http://localhost:8001
ENGINE_URL=http://localhost:8001
CORS_ORIGINS=http://localhost:3001,https://<ngrok-domain>
```

For Stripe local webhooks, set the webhook endpoint in Stripe to:

```text
https://<ngrok-domain>/api/stripe/webhooks
```

## Launch

Start Engine:

```powershell
uv run python -m uvicorn engine_v2.api.app:app --reload --host 127.0.0.1 --port 8001
```

Start Payload:

```powershell
npm run dev -- --port 3001
```

Start ngrok:

```powershell
ngrok http 3001
```

Use the HTTPS forwarding URL as the public product URL.

## Health Checks

Check local services:

```powershell
Invoke-WebRequest http://localhost:8001/engine/health
Invoke-WebRequest http://localhost:3001
```

Check the public tunnel:

```powershell
Invoke-WebRequest https://<ngrok-domain>
Invoke-WebRequest https://<ngrok-domain>/pricing
```

## Operational Notes

- Free ngrok URLs rotate; update `.env`, Stripe webhook URLs, sitemap URLs, and any demo links after restarting ngrok.
- For a stable demo URL, use a reserved ngrok domain.
- Keep the machine awake during demos; this path has no cloud restart policy.
- Logs stay in the local Engine and Payload terminals. Capture terminal output for debugging payment or query failures.

## Pre-Demo Checklist

- Engine terminal is running on `127.0.0.1:8001`.
- Payload terminal is running on `localhost:3001`.
- ngrok terminal shows an HTTPS forwarding URL.
- `.env` uses the current ngrok URL in `PAYLOAD_PUBLIC_SERVER_URL` and `CORS_ORIGINS`.
- Stripe webhook endpoint uses the current ngrok URL.
- `/`, `/register`, `/pricing`, `/terms`, and `/privacy` load through ngrok.
- One authenticated query succeeds from the ngrok URL.

## Common Failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Browser CORS error | Current ngrok URL missing from `CORS_ORIGINS` | Add the HTTPS ngrok URL, then restart Engine |
| Stripe webhook fails | Dashboard still points to an old ngrok URL | Update webhook endpoint and secret |
| Public URL returns 502 | Payload is not running on port 3001 | Restart Payload, then refresh ngrok URL |
| Engine calls fail | Engine is not running or port changed | Restart Engine on `127.0.0.1:8001` |
| Login cookie behaves oddly | Public URL changed mid-session | Clear browser cookies for the ngrok domain and sign in again |
