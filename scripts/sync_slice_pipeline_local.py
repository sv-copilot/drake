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

# Assets copied verbatim from this repository's own scripts/. The runner config
# this script generates points sliceSelectorCommand at
# `scripts/select_next_automation_slice.py`, so an adopter's repository needs the
# selector AND the module it imports; without them the first `run-next` fails with
# ModuleNotFoundError.
REPO_SCRIPTS_TO_INSTALL = (
    "select_next_automation_slice.py",
    "slice_lifecycle.py",
)

# Framework-owned assets: this tooling is executed, not edited. On install they are
# refreshed to match the framework, because leaving a stale copy means the runner
# keeps executing old code while the config, the docs and CI all describe new code.
# Everything else (AGENTS.md, prompts, agents, conventions) is adopter-owned and is
# never overwritten without --overwrite-existing.
MANAGED_PATHS = frozenset(
    {
        "scripts/select_next_automation_slice.py",
        "scripts/slice_lifecycle.py",
        "scripts/sync_slice_execution_docs.py",
        ".drake/runs/.gitignore",
        ".cursor/hooks/block-task-tool.sh",
        ".cursor/hooks/block-subagent.sh",
    }
)
TEMPLATE_ROOT = REPO_ROOT / "templates" / "slice-pipeline-local"

# Canonical, harness-neutral assets. Everything below works whichever coding
# harness the adopter runs; per-harness entry points are generated *views* of
# these files, never a second copy to keep in sync.
TEMPLATE_FILES = (
    "AGENTS.md",
    ".docs/git_workflow.md",
    ".drake/skills/slice-pipeline-local/SKILL.md",
    ".drake/agents/slice-preflight.md",
    ".drake/agents/slice-implementer.md",
    ".drake/agents/pr-babysitter.md",
    ".docs/agent_prompts/slice-pipeline-automation.md",
    ".docs/agent_prompts/slice-pipeline-handoff-contract.md",
    ".docs/agent_automation_execution_policy.md",
    ".docs/agent_automations.md",
    ".docs/branch_conventions.md",
    ".drake/slice-pipeline.config.json",
    ".drake/runs/.gitignore",
    "scripts/sync_slice_execution_docs.py",
    "scripts/harness_stub.sh",
)

CANONICAL_AGENT_DIR = ".drake/agents"
AGENT_NAMES = ("slice-preflight", "slice-implementer", "pr-babysitter")
CLAUDE_AGENT_DEST = ".claude/agents"

# Harness ids the installer knows. Mirrors
# tools/slice-agent-runner/src/harnesses.ts and docs/harnesses.md;
# tests/test_harness_catalogue.py fails when the three drift apart.
HARNESS_IDS = ("claude", "codex", "cursor", "cline", "aider", "generic")
DEFAULT_HARNESSES = "cline"

# Harness-neutral config locations, mirroring tools/slice-agent-runner/src/slice-config.ts.
CONFIG_FILE = ".drake/slice-pipeline.config.json"
LEGACY_CONFIG_FILE = ".cursor/slice-pipeline-local.config.json"

# Per-harness entry points, as (template source, destination) pairs. Sources are
# read from the bundle; destinations are repo-relative in the target repository.
HARNESS_VIEW_FILES: dict[str, tuple[tuple[str, str], ...]] = {
    "cursor": (
        (".drake/agents/slice-preflight.md", ".cursor/agents/slice-preflight.md"),
        (".drake/agents/slice-implementer.md", ".cursor/agents/slice-implementer.md"),
        (".drake/agents/pr-babysitter.md", ".cursor/agents/pr-babysitter.md"),
        (
            ".drake/skills/slice-pipeline-local/SKILL.md",
            ".cursor/skills/slice-pipeline-local/SKILL.md",
        ),
        (".cursor/hooks/block-task-tool.sh", ".cursor/hooks/block-task-tool.sh"),
        (".cursor/hooks/block-subagent.sh", ".cursor/hooks/block-subagent.sh"),
    ),
    "claude": (("harness-views/claude/CLAUDE.md", "CLAUDE.md"),),
    "cline": (("harness-views/cline/.clinerules", ".clinerules"),),
}

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
    parser.add_argument("--integration-branch", default="dev")
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
    parser.add_argument(
        "--harnesses",
        default=None,
        help=(
            "Comma-separated harnesses to install for; the first becomes the "
            f"primary harness in the runner config. Known: {', '.join(HARNESS_IDS)}. "
            f"Default: {DEFAULT_HARNESSES} on install; on check, whatever the target "
            "already records."
        ),
    )
    parser.add_argument(
        "--harness-model",
        help="Model passed to the harness (default: the harness's own model).",
    )
    parser.add_argument(
        "--harness-command",
        help='Shell command for the "generic" harness (the BYO-command path).',
    )
    parser.add_argument(
        "--sdk-model",
        help="Deprecated alias for --harness-model (no SDK is required any more).",
    )
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


def installed_harness_block(target: Path) -> dict:
    """Harness settings already recorded in the target, for check mode.

    ``check`` compares the target against the flags it is given. The harness id,
    model and command are pass-through values that the installed config already
    holds, so re-reading them removes a trap: install with ``--harness-command``,
    then run ``check`` without it, and the config would be reported stale for no
    real reason — which trains people to ignore the report.
    """
    for rel_path in (CONFIG_FILE, LEGACY_CONFIG_FILE):
        path = target / rel_path
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        block = data.get("harness")
        if isinstance(block, str):
            return {"id": block}
        if isinstance(block, dict):
            return block
        return {}
    return {}


def selected_harnesses(
    args: argparse.Namespace, target: Path | None = None
) -> list[str]:
    raw = args.harnesses
    installed = (
        installed_harness_block(target)
        if target is not None and args.mode == "check"
        else {}
    )
    if raw is None and installed.get("id"):
        raw = str(installed["id"])
    if raw is None:
        raw = DEFAULT_HARNESSES

    ids = [part.strip() for part in raw.split(",") if part.strip()]
    if not ids:
        raise SystemExit("--harnesses must list at least one harness")
    unknown = [harness for harness in ids if harness not in HARNESS_IDS]
    if unknown:
        raise SystemExit(
            f"unknown harness(es): {', '.join(unknown)}; known: {', '.join(HARNESS_IDS)}"
        )

    deduped: list[str] = []
    for harness in ids:
        if harness not in deduped:
            deduped.append(harness)

    # In check mode, also cover the harness views that are actually present, so a
    # target installed for several harnesses is checked as installed rather than as
    # one harness plus whatever the flags happened to say.
    if target is not None and args.mode == "check":
        for harness, marker in (
            ("claude", Path(".claude") / "agents"),
            ("cursor", Path(".cursor") / "agents"),
        ):
            if (target / marker).is_dir() and harness not in deduped:
                deduped.append(harness)

    return deduped


def installed_paths_for(harnesses: list[str]) -> set[str]:
    """Every repo-relative path an install writes for the given harness selections.

    Kept next to HARNESS_VIEW_FILES so the tests can assert the managed set is a
    subset of what an install actually produces, for every harness combination.
    """
    paths = set(TEMPLATE_FILES)
    paths.update(f"scripts/{name}" for name in REPO_SCRIPTS_TO_INSTALL)
    for harness in harnesses:
        for _source, dest in HARNESS_VIEW_FILES.get(harness, ()):
            paths.add(dest)
        if harness == "claude":
            paths.update(f"{CLAUDE_AGENT_DEST}/{name}.md" for name in AGENT_NAMES)
        if harness == "cursor":
            paths.add(HOOK_POLICY_TEMPLATE)
    return paths


def claude_agent_view(canonical: str) -> str:
    """Claude Code subagent definition generated from a canonical agent prompt.

    Same body as every other harness reads; the frontmatter keeps only the fields
    Claude Code documents for subagents (name, description, optional tools). The
    model line is dropped so the subagent inherits the session model instead of a
    harness-specific alias.
    """
    if not canonical.startswith("---"):
        return canonical
    end = canonical.find("\n---", 3)
    if end == -1:
        return canonical
    keep = {"name", "description", "tools"}
    front = [
        line
        for line in canonical[3:end].strip().splitlines()
        if line.split(":", 1)[0].strip() in keep
    ]
    return "---\n" + "\n".join(front) + "\n---" + canonical[end + 4 :]


def sync_harness_view(
    harness: str, args: argparse.Namespace, target: Path, tokens: dict[str, str]
) -> list[WriteResult]:
    """Install the entry points one harness needs, generated from canonical assets."""
    results: list[WriteResult] = []

    for source, dest in HARNESS_VIEW_FILES.get(harness, ()):
        content = render_template(source, tokens)
        results.append(
            write_text_if_needed(
                target,
                dest,
                content,
                mode=args.mode,
                dry_run=args.dry_run,
                overwrite_existing=(
                    args.overwrite_existing or dest in MANAGED_PATHS
                ),
            )
        )

    if harness == "claude":
        for name in AGENT_NAMES:
            source = f"{CANONICAL_AGENT_DIR}/{name}.md"
            content = claude_agent_view(render_template(source, tokens))
            results.append(
                write_text_if_needed(
                    target,
                    f"{CLAUDE_AGENT_DEST}/{name}.md",
                    content,
                    mode=args.mode,
                    dry_run=args.dry_run,
                    overwrite_existing=args.overwrite_existing,
                )
            )

    if harness == "cursor":
        results.append(merge_hooks_json(target, mode=args.mode, dry_run=args.dry_run))

    return results


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
    installed = installed_harness_block(target) if args.mode == "check" else {}
    harnesses = selected_harnesses(args, target)
    harness_model = args.harness_model or args.sdk_model or installed.get("model")
    harness_command = (
        args.harness_command
        if args.harness_command is not None
        else installed.get("command")
    )
    if args.mode == "check" and args.harnesses is None and installed:
        print(
            f"note: --harnesses not given; checking the harness recorded in the target "
            f"({', '.join(harnesses)})"
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
        "HARNESS_ID": harnesses[0],
        "HARNESS_IDS_LIST": ", ".join(harnesses),
        "HARNESS_MODEL_JSON": json.dumps(harness_model or None),
        "HARNESS_COMMAND_JSON": json.dumps(harness_command or None),
        "HARNESS_MODEL": harness_model or "",
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
            return WriteResult(
                rel_path,
                "stale",
                "content differs (check compares against the flags you pass, so "
                "re-run with the same --project-name/--github-slug/--validation-commands "
                "you installed with)",
            )
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
    # This lands in the adopter's repository, so it must not carry an internal fixture name: the
    # first tree someone sees saying "SMOKE-AUTOMATION-001" is a bad first impression. It also
    # carries the current schema's fields explicitly rather than relying on the v1->v2 normalizer.
    placeholder_id = "SLICE-1"
    backlog_path = tokens["SLICE_BACKLOG_PATH"]
    dependency_tree_path = tokens["DEPENDENCY_TREE_PATH"]
    slice_detail_dir = tokens["SLICE_DETAIL_DIR"].rstrip("/")
    dependency_tree = {
        "schema_version": 2,
        "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
        "source_backlog_path": backlog_path,
        "default_fanout_limit": 1,
        "notes": [
            "Placeholder dependency tree for slice-pipeline-local bootstrap.",
            "Replace with project-specific slices before enabling unattended automation.",
        ],
        "slices": [
            {
                "slice_id": placeholder_id,
                "slice_number": 1,
                "group": "technical",
                "title": "Replace this placeholder slice with real work",
                "state": "ready",
                "status": "ready",
                "dependencies": [],
                "blocks": [],
                "operator_gates": [],
                "checkpoint": "low-risk",
                "automation_eligible": True,
                "priority": 1,
                "last_known_pr": None,
                "risk": "low",
                "effort": "small",
                "tier": "P1",
            }
        ],
    }
    return {
        backlog_path: f"""# Slice Backlog

Use this file as the human-readable planning surface. Keep it synchronized with `{dependency_tree_path}`.

| Rank | Slice ID | Status | Summary | Validation | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `{placeholder_id}` | Ready | Placeholder slice - replace it with real work before enabling unattended runs. | Run repo validation commands. | Seeded by the installer. |
""",
        dependency_tree_path: json.dumps(dependency_tree, indent=2) + "\n",
        f"{slice_detail_dir}/README.md": """# Slice Details

Store one target slice detail document per automation-ready slice.

The reusable slice-pipeline-local assets expect Path B payloads to point at a
detail doc under this directory when the project uses detailed slice specs.
""",
    }


def missing_bundle_assets() -> list[str]:
    """Report bundle assets referenced by this script that do not exist.

    A missing asset used to raise FileNotFoundError mid-install, which reads as a
    crash rather than as a packaging defect. Check up front and say so.
    """
    missing: list[str] = []
    for rel_path in TEMPLATE_FILES:
        if not (TEMPLATE_ROOT / rel_path).is_file():
            missing.append(f"templates/slice-pipeline-local/{rel_path}")
    for views in HARNESS_VIEW_FILES.values():
        for source, _dest in views:
            if not (TEMPLATE_ROOT / source).is_file():
                missing.append(f"templates/slice-pipeline-local/{source}")
    for name in REPO_SCRIPTS_TO_INSTALL:
        if not (REPO_ROOT / "scripts" / name).is_file():
            missing.append(f"scripts/{name}")
    return missing


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
                overwrite_existing=(
                    args.overwrite_existing or rel_path in MANAGED_PATHS
                ),
            )
        )
    for name in REPO_SCRIPTS_TO_INSTALL:
        rel_path = f"scripts/{name}"
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        results.append(
            write_text_if_needed(
                target,
                rel_path,
                content,
                mode=args.mode,
                dry_run=args.dry_run,
                overwrite_existing=(
                    args.overwrite_existing or rel_path in MANAGED_PATHS
                ),
            )
        )
    for harness in selected_harnesses(args, target):
        results.extend(sync_harness_view(harness, args, target, tokens))
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
    missing = missing_bundle_assets()
    if missing:
        print(
            "slice-pipeline-local bundle is incomplete; these assets are missing:",
            file=sys.stderr,
        )
        for rel_path in missing:
            print(f"  - {rel_path}", file=sys.stderr)
        return 2

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
