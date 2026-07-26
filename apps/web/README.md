# Hosted web scaffold

Next.js scaffold for Drake hosted operations. This slice only adds a read-only
app shell, placeholder routes, a typed API client, and local validation setup.

## Local setup

```bash
cd apps/web
npm install
cp .env.example .env.local
```

`NEXT_PUBLIC_API_URL` points at the FastAPI service. The example value is:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Run locally

```bash
cd apps/web
npm run dev
```

Then open `http://127.0.0.1:3000`.

## Validate

```bash
cd apps/web
npm run typecheck
npm run test
npm run build
```

## Current non-goals

- No registry sync.
- No feature screens beyond shell and placeholders.
- No dispatch controls.
- No auth or RBAC.
- No production deploy.
- No secret values or private registry data.
