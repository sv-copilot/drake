# MCP environment profiles

A profile declares which MCP servers a worker may reach in each environment, and
which credentials those servers may resolve. One file per repository:
`.docs/mcp_environment_profile.json`, validated against
`.docs/mcp_environment_profile.schema.json`.

## Tiers

| Tier | Purpose | Credential policy |
| --- | --- | --- |
| `dev` | Local development. Filesystem, shell, and read-only GitHub servers. | No credentials in this tier (`forbidden_in_tiers`). |
| `staging` | Remote verification against a real deployment. | Credentials by reference only. |
| `production` | Reserved. Enabling it is a human gate (`human_gate_tiers`). | Credentials by reference only, never inline. |

## Rules

- Credentials are always **references by name**, never values. The profile is
  committed, so anything in it is public.
- A tier lists the servers it allows; a server that is absent from the tier is not
  reachable, which is the point of the boundary.
- Agents move between environments; credentials do not. A worker that runs in
  `staging` does not inherit `production` credentials.

## Tooling

```bash
python3 scripts/mcp_environment_profile.py           # generate a placeholder profile
python3 scripts/validate_mcp_environment_profile.py  # validate the committed profile
```

The validator runs in `scripts/ci_preflight.sh`, so a profile that names a
credential value rather than a reference fails the gate.
