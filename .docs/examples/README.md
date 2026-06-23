# Product-repo doc examples

Copy or adapt these into a **product repository** under `.docs/` after bootstrap or
course-correct. They are portfolio-side samples only — not runtime config for this repo.

| Example file | Target path in product repo | Purpose |
| --- | --- | --- |
| [project_intake.example.json](project_intake.example.json) | `.docs/project_intake.json` | Machine-readable product/UX directive, defaults, human gates, validation, and automation readiness |
| [stack_decisions.example.md](stack_decisions.example.md) | `.docs/stack_decisions.md` | Record scaffold inputs, stack choices, rejected alternatives, and deviations |
| [frontend_stack.example.md](frontend_stack.example.md) | `.docs/frontend_stack.md` | Frontend profile, router, styling, data access, CMS, and validation commands |
| [deployment.example.md](deployment.example.md) | `.docs/deployment.md` | UAT and production ownership, deploy/rollback, env var names |

Canonical portfolio rules:

- [new_project_practices.md](../new_project_practices.md)
- [project_factory_contract.md](../project_factory_contract.md)
- [project_bootstrap_scaffold_contract.md](../project_bootstrap_scaffold_contract.md)
- [frontend_scaffold_practices.md](../frontend_scaffold_practices.md)
- [automation_ci_deploy_practices.md](../automation_ci_deploy_practices.md)

When promoting a pattern into `project-bootstrap` templates, use the
[cascade-practices](../../.cursor/skills/cascade-practices/SKILL.md) skill.

Replace placeholder project IDs, paths, and stack choices with repo-specific values.
Do not commit real secrets or private data in decision records.
