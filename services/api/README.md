# Hosted API scaffold

FastAPI scaffold for the hosted operations control plane. This slice only
implements a local boot check at `GET /health`.

## Local setup

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Run locally

```bash
cd services/api
python3 -m uvicorn hosted_api.main:app --reload --host 127.0.0.1 --port 8000
```

Then call:

```bash
curl http://127.0.0.1:8000/health
```

Expected JSON:

```json
{
  "status": "ok",
  "service": "hosted-api",
  "version": "0.1.0"
}
```

## Test

```bash
cd services/api
pytest -q
```

## Current non-goals

- No GitHub sync.
- No dispatch controls.
- No secrets broker.
- No authentication.
- No database.
- No UI.
- No live registry data or private runtime artifacts.
