# Temporary hosted IP staging

Use this path when the hosted operations UI needs a shared staging smoke test
before DNS and TLS are ready. This is not a production deployment path.

## Scope

- Web runs at `http://<staging-host>:3000`.
- API runs at `http://<staging-host>:8000`.
- The API remains read-only except for the explicit GitHub sync endpoint.
- No auth, TLS, database, or secrets broker is introduced by this path.

## Operator prerequisites

1. Provision a temporary host or VM.
2. Open inbound TCP only for the reviewers who need access:
   - `3000` for the web UI.
   - `8000` for the API.
3. Install the repo runtime prerequisites already used by local development:
   - Python 3.
   - Node.js and npm.
   - Python and npm dependencies for `services/api` and `apps/web`.
4. Optionally provide `GH_TOKEN` or `GITHUB_TOKEN` in the host secret store if
   live GitHub read sync is needed. Do not write token values to repository
   files or command history.

## Validate configuration

From the repository root on the staging host:

```bash
STAGING_HOST=<server-ip> bash scripts/hosted-ip-staging.sh --check
```

The check prints the browser URL, API URL, CORS origin, and a reminder that this
mode is HTTP-only and unauthenticated.

To print the exact launch command without starting services:

```bash
STAGING_HOST=<server-ip> bash scripts/hosted-ip-staging.sh --print-launch
```

To print smoke-test commands without contacting the host:

```bash
STAGING_HOST=<server-ip> bash scripts/hosted-ip-staging.sh --print-smoke
```

## Run

```bash
STAGING_HOST=<server-ip> bash scripts/hosted-ip-staging.sh --run
```

`--run` defaults to `HOSTED_STAGING_MODE=production`: it starts the FastAPI API,
builds the Next.js app with `NEXT_PUBLIC_API_URL`, then serves it with
`next start`. For temporary debugging only, use `HOSTED_STAGING_MODE=dev`.

Equivalent explicit environment:

```bash
STAGING_HOST=<server-ip> \
HOSTED_API_HOST=0.0.0.0 \
HOSTED_API_PORT=8000 \
HOSTED_WEB_HOST=0.0.0.0 \
HOSTED_WEB_PORT=3000 \
HOSTED_WEB_ORIGIN=http://<server-ip>:3000 \
NEXT_PUBLIC_API_URL=http://<server-ip>:8000 \
HOSTED_STAGING_MODE=production \
bash scripts/hosted-ip-staging.sh --run
```

## Smoke checks

From a reviewer machine allowed by the firewall:

```bash
STAGING_HOST=<server-ip> bash scripts/hosted-ip-staging.sh --smoke
```

The smoke check verifies:

- `GET /health` returns `status=ok` for `hosted-api`.
- `GET /api/v1/portfolio` returns a portfolio object with `repo_count`.
- The web shell responds on `http://<server-ip>:3000`.

Then manually open:

```text
http://<server-ip>:3000
```

Verify the Portfolio, Slice Board, Workers, Dispatches, and Runs pages load. If
live sync is enabled, use the API sync endpoint with a staging-scoped GitHub read
token from the host environment.

## Rollback and shutdown

- Stop the foreground `scripts/hosted-ip-staging.sh --run` process.
- Close inbound ports `3000` and `8000`.
- Remove any staging-scoped token values from the host secret store if this was a
  one-off smoke.

## Promotion gate

Before replacing this temporary path with real staging, document the stable host,
DNS, TLS, process manager, deploy owner, rollback command, and secret owner in
the deployment runbook.
