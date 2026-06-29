# Hosted API scaffold

FastAPI scaffold for the hosted operations control plane. This slice only
implements a local boot check at `GET /health` and a read-only GitHub sync
surface for fixture-safe registry/tree ingestion.

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

## GitHub read sync

The internal sync endpoint reads a portfolio registry and dependency trees from
GitHub contents API into an in-memory cache:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sync \
  -H 'content-type: application/json' \
  -d '{
    "registry_repo": "example-org/example-portfolio",
    "registry_ref": "ai-dev",
    "registry_path": ".docs/projects-registry.json"
  }'
```

Status is available at:

```bash
curl http://127.0.0.1:8000/api/v1/sync/status
```

Live GitHub reads may use `GH_TOKEN` or `GITHUB_TOKEN` from the environment.
Only env var names belong in committed docs; never commit token values.

## Current non-goals

- No dispatch controls.
- No secrets broker.
- No authentication.
- No database.
- No UI.
- No live registry data or private runtime artifacts.
