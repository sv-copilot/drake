# MCP hosting (path-routed)

Drake is designed to be exposed as an MCP server at a predictable path under a
shared MCP gateway. The recommended pattern uses path-based routing rather than
per-service subdomains.

## Recommended topology

```
mcp.yourdomain.com/drake           Drake orchestration MCP (production)
mcp.yourdomain.com/staging/drake   Drake MCP (staging)
```

## Environment variable name

| Variable | Purpose | Example |
| --- | --- | --- |
| `DRAKE_MCP_BASE_URL` | Base URL for the Drake MCP endpoint | `https://mcp.yourdomain.com/drake` |

Set `DRAKE_MCP_BASE_URL` in your deployment environment. Clients and consuming
tools (including personal operator Cockpits) connect through this URL.

## Relationship to Cockpit

Drake is a bare orchestration MCP. A personal operator Cockpit (such as Simon's
private Cockpit UI/API at `cockpit.yourdomain.com`) may consume Drake as one of
its MCP tools. Drake does **not** own Cockpit UI/API hostnames or `COCKPIT_*`
environment variables. See the [Drake-Cockpit boundary doc](../.docs/examples/README.md)
in this repo and the portfolio governance repo's
[`drake_cockpit_boundary.md`](https://github.com/sv-copilot/simon-projects/blob/ai-dev/.docs/drake_cockpit_boundary.md)
for the separation of concerns.

## Path routing vs subdomain routing

| Pattern | Example | Drake recommendation |
| --- | --- | --- |
| Path-routed (preferred) | `mcp.example.com/{service}` | Use this |
| Subdomain-routed (legacy) | `{service}.mcp.example.com` | Avoid for new deployments |

Path routing simplifies TLS certificate management and allows a single MCP
gateway to serve multiple services.
