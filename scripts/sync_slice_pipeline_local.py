#!/usr/bin/env python3
"""Install or check the reusable slice-pipeline-local capability.

The script is intentionally conservative:
- check mode reports missing or stale assets without writing;
- install mode creates missing files and merges the hook allowlist;
- existing non-empty files are not overwritten unless --overwrite-existing is set.
"""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from sync_mcp_environment_profile import sync_mcp_environment_profile_scaffold


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "templates" / "slice-pipeline-local"

TEMPLATE_FILES = (
    ".cursor/skills/slice-pipeline-local/SKILL.md",
    ".cursor/agents/slice-preflight.md",
    ".cursor/agents/slice-implementer.md",
    ".cursor/agents/pr-babysitter.md",
    ".docs/agent_prompts/slice-pipeline-automation.md",
    ".docs/agent_prompts/slice-pipeline-handoff-contract.md",
    ".docs/agent_automation_execution_policy.md",
    ".docs/agent_automations.md",
    ".docs/branch_conventions.md",
    ".cursor/hooks/block-task-tool.sh",
    ".cursor/hooks/block-subagent.sh",
    ".cursor/slice-pipeline-local.config.json",
    ".cursor/automation-runs/.gitignore",
    "scripts/sync_slice_execution_docs.py",
)

HOOK_POLICY_TEMPLATE = ".cursor/hooks.json"
HOOK_SCRIPT_PATHS = {
    ".cursor/hooks/block-task-tool.sh",
    ".cursor/hooks/block-subagent.sh",
}

DEFAULT_APPROVED_SUBAGENTS = "slice-preflight, slice-implementer, pr-babysitter"


@dataclass(frozen=True)
class WriteResult:
    path: str
    status: str
    detail: str


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or check reusable slice-pipeline-local assets."
    )
    parser.add_argument("--target", required=True, help="Target repository path.")
    parser.add_argument(
        "--mode",
        choices=("check", "install"),
        default="check",
        help="check reports drift; install creates missing assets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned writes without changing the target repository.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Replace stale existing managed files. Use only after reviewing diffs.",
    )
    parser.add_argument("--project-name", help="Human-readable project name.")
    parser.add_argument("--project-id", help="Kebab-case project id.")
    parser.add_argument("--github-slug", default="OWNER/REPO")
    parser.add_argument("--local-path")
    parser.add_argument("--integration-branch", default="ai-dev")
    parser.add_argument(
        "--feature-branch-prefix",
        default="agent/",
        help="Preferred feature branch prefix for new agent work (must end with /).",
    )
    parser.add_argument(
        "--legacy-feature-branch-prefixes",
        default="cursor/",
        help="Comma-separated legacy prefixes accepted during migration.",
    )
    parser.add_argument(
        "--dependency-tree-path", default=".docs/slice_dependency_tree.json"
    )
    parser.add_argument("--slice-backlog-path", default=".docs/slice_backlog.md")
    parser.add_argument("--slice-detail-dir", default=".docs/slices")
    parser.add_argument("--slice-selector-command")
    parser.add_argument("--docs-sync-command", default="not configured")
    parser.add_argument("--validation-commands", default="not configured")
    parser.add_argument("--sdk-model", default="composer-2.5")
    parser.add_argument(
        "--portfolio-webhook-url-env",
        default="PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_URL",
    )
    parser.add_argument(
        "--portfolio-webhook-token-env",
        default="PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_TOKEN",
    )
    parser.add_argument(
        "--local-webhook-url-env",
        default="PLAN_NEXT_SLICE_WEBHOOK_URL",
    )
    parser.add_argument(
        "--local-webhook-token-env",
        default="PLAN_NEXT_SLICE_WEBHOOK_TOKEN",
    )
    parser.add_argument(
        "--approved-subagents", default=DEFAULT_APPROVED_SUBAGENTS
    )
    parser.add_argument(
        "--skip-mcp-profile",
        action="store_true",
        help="Do not install or check MCP environment profile scaffold assets.",
    )
    return parser.parse_args()


def normalize_branch_prefix(value: str, label: str) -> str:
    prefix = value.strip()
    if not prefix.endswith("/"):
        raise SystemExit(f"{label} must end with '/': {value}")
    if "*" in prefix or " " in prefix:
        raise SystemExit(f"{label} must not contain '*' or spaces: {value}")
    return prefix


def parse_legacy_prefixes(value: str) -> list[str]:
    prefixes = [
        normalize_branch_prefix(part, "legacy feature branch prefix")
        for part in value.split(",")
        if part.strip()
    ]
    if not prefixes:
        raise SystemExit("legacy feature branch prefixes must not be empty")
    return prefixes


def token_map(args: argparse.Namespace, target: Path) -> dict[str, str]:
    project_name = args.project_name or target.name
    project_id = args.project_id or slugify(project_name)
    local_path = args.local_path or str(target)
    feature_prefix = normalize_branch_prefix(
        args.feature_branch_prefix, "feature branch prefix"
    )
    legacy_prefixes = parse_legacy_prefixes(args.legacy_feature_branch_prefixes)
    legacy_doc = ", ".join(f"`{prefix}*`" for prefix in legacy_prefixes)
    selector = (
        args.slice_selector_command
        or f"python3 scripts/select_next_automation_slice.py --tree {args.dependency_tree_path}"
    )
    return {
        "PROJECT_NAME": project_name,
        "PROJECT_ID": project_id,
        "GITHUB_SLUG": args.github_slug,
        "LOCAL_PATH": local_path,
        "INTEGRATION_BRANCH": args.integration_branch,
        "FEATURE_BRANCH_PREFIX": feature_prefix,
        "LEGACY_FEATURE_BRANCH_PREFIXES": legacy_doc,
        "LEGACY_FEATURE_BRANCH_PREFIXES_JSON": json.dumps(legacy_prefixes),
        "DEPENDENCY_TREE_PATH": args.dependency_tree_path,
        "SLICE_BACKLOG_PATH": args.slice_backlog_path,
        "SLICE_DETAIL_DIR": args.slice_detail_dir,
        "SLICE_SELECTOR_COMMAND": selector,
        "DOCS_SYNC_COMMAND": args.docs_sync_command,
        "VALIDATION_COMMANDS": args.validation_commands,
        "SDK_MODEL": args.sdk_model,
        "APPROVED_SUBAGENTS": args.approved_subagents,
        "PORTFOLIO_WEBHOOK_URL_ENV": args.portfolio_webhook_url_env,
        "PORTFOLIO_WEBHOOK_TOKEN_ENV": args.portfolio_webhook_token_env,
        "LOCAL_WEBHOOK_URL_ENV": args.local_webhook_url_env,
        "LOCAL_WEBHOOK_TOKEN_ENV": args.local_webhook_token_env,
    }


def validate_repo_relative_path(value: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"{label} must be a repo-relative path without '..': {value}")


def render_template(rel_path: str, tokens: dict[str, str]) -> str:
    text = (TEMPLATE_ROOT / rel_path).read_text(encoding="utf-8")
    for key, value in tokens.items():
        text = text.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
    if unresolved:
        raise SystemExit(f"unresolved template tokens in {rel_path}: {unresolved}")
    return text


def write_text_if_needed(
    target: Path,
    rel_path: str,
    content: str,
    *,
    mode: str,
    dry_run: bool,
    overwrite_existing: bool,
) -> WriteResult:
    dest = target / rel_path
    if dest.exists():
        current = dest.read_text(encoding="utf-8")
        if current == content:
            return WriteResult(rel_path, "ok", "already current")
        if mode == "check":
            return WriteResult(rel_path, "stale", "content differs")
        if current.strip() and not overwrite_existing:
            return WriteResult(
                rel_path,
                "skipped",
                "exists and differs; use --overwrite-existing after review",
            )
        if dry_run:
            return WriteResult(rel_path, "would_update", "content differs")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return WriteResult(rel_path, "updated", "content replaced")

    if mode == "check":
        return WriteResult(rel_path, "missing", "file is absent")
    if dry_run:
        return WriteResult(rel_path, "would_create", "file is absent")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return WriteResult(rel_path, "created", "file installed")


def write_placeholder_if_missing(
    target: Path,
    rel_path: str,
    content: str,
    *,
    mode: str,
    dry_run: bool,
) -> WriteResult:
    dest = target / rel_path
    if dest.exists():
        return WriteResult(rel_path, "ok", "project-provided file present")
    if mode == "check":
        return WriteResult(rel_path, "missing", "placeholder file is absent")
    if dry_run:
        return WriteResult(rel_path, "would_create", "placeholder file is absent")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return WriteResult(rel_path, "created", "placeholder file installed")


def make_hook_scripts_executable(target: Path, dry_run: bool) -> list[WriteResult]:
    results: list[WriteResult] = []
    for rel_path in sorted(HOOK_SCRIPT_PATHS):
        path = target / rel_path
        if not path.exists() or dry_run:
            continue
        mode = path.stat().st_mode
        if mode & stat.S_IXUSR:
            results.append(WriteResult(rel_path, "ok", "executable bit present"))
            continue
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        results.append(WriteResult(rel_path, "updated", "made executable"))
    return results


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc


def hook_entry_exists(entries: list[dict], desired: dict) -> bool:
    command = desired.get("command")
    matcher = desired.get("matcher")
    for entry in entries:
        if entry.get("command") != command:
            continue
        if matcher is None or entry.get("matcher") == matcher:
            return True
    return False


def merge_hooks_json(
    target: Path,
    *,
    mode: str,
    dry_run: bool,
) -> WriteResult:
    rel_path = HOOK_POLICY_TEMPLATE
    desired = json.loads((TEMPLATE_ROOT / rel_path).read_text(encoding="utf-8"))
    dest = target / rel_path
    current = load_json(dest)

    if not current:
        content = json.dumps(desired, indent=2) + "\n"
        return write_text_if_needed(
            target,
            rel_path,
            content,
            mode=mode,
            dry_run=dry_run,
            overwrite_existing=True,
        )

    merged = json.loads(json.dumps(current))
    merged.setdefault("version", desired.get("version", 1))
    merged_hooks = merged.setdefault("hooks", {})
    changed = False

    for hook_name, desired_entries in desired.get("hooks", {}).items():
        current_entries = merged_hooks.setdefault(hook_name, [])
        for entry in desired_entries:
            if not hook_entry_exists(current_entries, entry):
                current_entries.append(entry)
                changed = True

    if not changed:
        return WriteResult(rel_path, "ok", "hook allowlist already present")
    if mode == "check":
        return WriteResult(rel_path, "stale", "missing slice-pipeline hook entries")
    if dry_run:
        return WriteResult(rel_path, "would_update", "would merge hook entries")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return WriteResult(rel_path, "updated", "merged hook entries")


def placeholder_docs(tokens: dict[str, str]) -> dict[str, str]:
    smoke_id = "SMOKE-AUTOMATION-001"
    backlog_path = tokens["SLICE_BACKLOG_PATH"]
    dependency_tree_path = tokens["DEPENDENCY_TREE_PATH"]
    slice_detail_dir = tokens["SLICE_DETAIL_DIR"].rstrip("/")
    dependency_tree = {
        "schema_version": 1,
        "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
        "source_backlog_path": backlog_path,
        "default_fanout_limit": 1,
        "notes": [
            "Placeholder dependency tree for slice-pipeline-local bootstrap.",
            "Replace with project-specific slices before enabling unattended automation.",
        ],
        "slices": [
            {
                "slice_id": smoke_id,
                "slice_number": 1,
                "title": "Automation smoke slice",
                "status": "ready",
                "dependencies": [],
                "blocks": [],
                "operator_gates": [],
                "checkpoint": "low-risk",
                "automation_eligible": True,
                "priority": 1,
                "last_known_pr": None,
            }
        ],
    }
    return {
        backlog_path: f"""# Slice Backlog

Use this file as the human-readable planning surface. Keep it synchronized with `{dependency_tree_path}`.

| Rank | Slice ID | Status | Summary | Validation | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `{smoke_id}` | Ready | Harmless automation smoke slice. | Run repo validation commands. | Replace or refine before unattended automation. |
""",
        dependency_tree_path: json.dumps(dependency_tree, indent=2) + "\n",
        f"{slice_detail_dir}/README.md": """# Slice Details

Store one target slice detail document per automation-ready slice.

The reusable slice-pipeline-local assets expect Path B payloads to point at a
detail doc under this directory when the project uses detailed slice specs.
""",
    }


def sync_templates(args: argparse.Namespace, target: Path, tokens: dict[str, str]) -> list[WriteResult]:
    results: list[WriteResult] = []
    for rel_path in TEMPLATE_FILES:
        content = render_template(rel_path, tokens)
        results.append(
            write_text_if_needed(
                target,
                rel_path,
                content,
                mode=args.mode,
                dry_run=args.dry_run,
                overwrite_existing=args.overwrite_existing,
            )
        )
    results.append(merge_hooks_json(target, mode=args.mode, dry_run=args.dry_run))
    for rel_path, content in placeholder_docs(tokens).items():
        results.append(
            write_placeholder_if_missing(
                target,
                rel_path,
                content,
                mode=args.mode,
                dry_run=args.dry_run,
            )
        )
    if not args.skip_mcp_profile:
        mcp_results = sync_mcp_environment_profile_scaffold(
            target,
            mode=args.mode,
            dry_run=args.dry_run,
            overwrite_existing=args.overwrite_existing,
            project_name=tokens["PROJECT_NAME"],
            project_id=tokens["PROJECT_ID"],
        )
        results.extend(mcp_results)
    results.extend(make_hook_scripts_executable(target, args.dry_run))
    return results


def print_results(results: list[WriteResult]) -> None:
    for result in results:
        print(f"{result.status:13} {result.path} - {result.detail}")


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()

    if not TEMPLATE_ROOT.is_dir():
        raise SystemExit(f"template root not found: {TEMPLATE_ROOT}")
    if args.mode == "check" and not target.exists():
        raise SystemExit(f"target path does not exist: {target}")
    if args.mode == "install" and not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    tokens = token_map(args, target)
    validate_repo_relative_path(tokens["DEPENDENCY_TREE_PATH"], "dependency tree path")
    validate_repo_relative_path(tokens["SLICE_BACKLOG_PATH"], "slice backlog path")
    validate_repo_relative_path(tokens["SLICE_DETAIL_DIR"], "slice detail dir")
    results = sync_templates(args, target, tokens)
    print_results(results)

    blocking = {"missing", "stale", "skipped"}
    if args.mode == "check" and any(result.status in blocking for result in results):
        return 1
    if args.mode == "install" and any(result.status == "skipped" for result in results):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
