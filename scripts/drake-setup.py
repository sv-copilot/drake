#!/usr/bin/env python3
"""drake-setup — architect a governance programme in a target repository.

The adopter should not have to read a 25-flag installer and a design document before they can see
this framework work. This script inspects the repository, asks only what it could not detect,
proposes an adoption level, installs, and then *proves* what it did — or says exactly what is
missing.

    python3 scripts/drake-setup.py --target ../my-product              # plan (writes nothing)
    python3 scripts/drake-setup.py --target ../my-product --apply      # install
    python3 scripts/drake-setup.py --target ../my-product --level L2 --apply

Levels are stopping points, not a ladder:

    L0  plan only        config, canonical assets, a seeded dependency tree, slice detail docs.
                         Nothing executes until you wire a harness.
    L1  one slice        L0 + a harness wired and verified with --dry-run. Human-triggered runs.
    L2  unattended       L1 + the schedule to run one slice per tick, with logs and exit codes.
    L3  portfolio        L2 + the multi-repository path.

Exit codes: 0 the requested level is reached · 1 error · 2 the requested level was not reached
(the reason is printed, and it is always something you can fix).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DRAKE_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = DRAKE_ROOT / "scripts" / "sync_slice_pipeline_local.py"
VALIDATOR = DRAKE_ROOT / "scripts" / "validate_slice_dependency_tree.py"
RUNNER = DRAKE_ROOT / "tools" / "slice-agent-runner" / "dist" / "index.js"

LEVELS = ("L0", "L1", "L2", "L3")
LEVEL_NEEDS_HARNESS = {"L1", "L2", "L3"}

# A harness is a child process, so "is it available" is just "is it on PATH". The catalogue
# (`adapters/harnesses.json`) is the behavioural source of truth; this is only detection.
HARNESS_BINARIES = {
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor-agent",
    "cline": "cline",
    "aider": "aider",
}

# npm script names worth running, in the order a repository usually means them. Keep these per
# manifest: matching a Makefile target against an npm script key silently produces `make test` for
# a JavaScript repo.
NPM_SCRIPTS = (("test", "npm test"), ("lint", "npm run lint"), ("build", "npm run build"))


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def git(target: Path, *args: str) -> str:
    result = run(["git", "-C", str(target), *args])
    return result.stdout.strip() if result.returncode == 0 else ""


# --------------------------------------------------------------------------------------------
# 1. Inspect


def detect(target: Path) -> dict:
    """Everything the wizard can find out for itself, with the evidence for each finding."""
    found: dict = {"evidence": {}, "assumptions": []}

    found["is_git"] = bool(git(target, "rev-parse", "--show-toplevel"))
    found["branch"] = git(target, "rev-parse", "--abbrev-ref", "HEAD") or ""

    remote = git(target, "remote", "get-url", "origin")
    slug = ""
    match = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", remote)
    if match:
        slug = f"{match.group(1)}/{match.group(2)}"
    found["github_slug"] = slug
    if remote:
        found["evidence"]["remote"] = remote

    manifests = []
    for candidate in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "Makefile"):
        if (target / candidate).is_file():
            manifests.append(candidate)
    found["manifests"] = manifests
    if manifests:
        found["evidence"]["manifests"] = ", ".join(manifests)

    nested = [
        p.relative_to(target).as_posix()
        for pattern in ("*/package.json", "*/pyproject.toml")
        for p in target.glob(pattern)
        if "node_modules" not in p.parts
    ]
    found["monorepo"] = len(nested) > 0
    if nested:
        found["evidence"]["nested_manifests"] = ", ".join(sorted(nested)[:5])

    commands: list[str] = []
    package_json = target / "package.json"
    if package_json.is_file():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {}) or {}
        except json.JSONDecodeError:
            scripts = {}
            found["assumptions"].append("package.json could not be parsed; test command not detected")
        for key, command in NPM_SCRIPTS:
            if key in scripts:
                commands.append(command)
    if (target / "pyproject.toml").is_file() and (target / "tests").is_dir():
        commands.append("python3 -m pytest -q")
    if (target / "Makefile").is_file() and "make test" not in commands:
        makefile = (target / "Makefile").read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^test:", makefile, re.MULTILINE):
            commands.append("make test")
    found["validation_commands"] = list(dict.fromkeys(commands))
    if commands:
        found["evidence"]["validation"] = ", ".join(found["validation_commands"])
    else:
        found["assumptions"].append(
            "no test command detected — set validationCommands in .drake/slice-pipeline.config.json; "
            "a slice with no way to prove itself is not a slice"
        )

    workflows = sorted(p.name for p in (target / ".github" / "workflows").glob("*.y*ml")) if (target / ".github" / "workflows").is_dir() else []
    found["ci"] = workflows
    if workflows:
        found["evidence"]["ci"] = ", ".join(workflows)

    available = {name: shutil.which(binary) for name, binary in HARNESS_BINARIES.items()}
    found["harnesses_on_path"] = {name: path for name, path in available.items() if path}
    if found["harnesses_on_path"]:
        found["evidence"]["harnesses"] = ", ".join(found["harnesses_on_path"])
    else:
        found["assumptions"].append(
            "no harness CLI found on PATH — install the agent you already use (or pass "
            "--harness generic --harness-command) before moving past L0"
        )
    return found


# --------------------------------------------------------------------------------------------
# 2/3. Resolve the plan


def resolve(args, target: Path, found: dict) -> dict:
    project_id = args.project_id or re.sub(r"[^a-z0-9]+", "-", target.name.lower()).strip("-")
    settings = {
        "project_id": project_id,
        "project_name": args.project_name or target.name.replace("-", " ").title(),
        "github_slug": args.github_slug or found["github_slug"] or f"OWNER/{project_id}",
        "integration_branch": args.integration_branch or ("main" if not found["branch"] else found["branch"]),
        "validation_commands": args.validation_commands
        if args.validation_commands is not None
        else "; ".join(found["validation_commands"]),
        "level": args.level,
    }

    if args.harness:
        settings["harness"] = args.harness
    elif found["harnesses_on_path"]:
        settings["harness"] = next(iter(found["harnesses_on_path"]))
    else:
        # Cline is the documented default and installs a complete set of views without needing a
        # command. "generic" is deliberately NOT the fallback: generic without a command is a
        # broken install by design, and a wizard should not hand someone one of those.
        settings["harness"] = "cline"
    settings["harness_command"] = args.harness_command or ""

    problems = []
    if not found["is_git"]:
        problems.append(f"{target} is not a git repository — Drake is repo-native, so git is the floor")
    if settings["level"] in LEVEL_NEEDS_HARNESS and not settings["harness_command"]:
        harness = settings["harness"]
        if harness != "generic" and harness not in found["harnesses_on_path"]:
            problems.append(
                f"level {settings['level']} needs a harness: '{HARNESS_BINARIES.get(harness, harness)}' is not on PATH. "
                f"Install it, or run with --harness generic --harness-command '<your command with {{prompt_file}}>'"
            )
        if harness == "generic":
            problems.append("the generic harness needs --harness-command (use {prompt_file}, {prompt} or {model})")
    settings["problems"] = problems
    return settings


def installer_base(target: Path, settings: dict) -> list[str]:
    flags = [
        sys.executable,
        str(INSTALLER),
        "--target",
        str(target),
        "--project-name",
        settings["project_name"],
        "--project-id",
        settings["project_id"],
        "--github-slug",
        settings["github_slug"],
        "--integration-branch",
        settings["integration_branch"],
        "--harnesses",
        settings["harness"],
        "--skip-mcp-profile",
    ]
    if settings["validation_commands"]:
        flags += ["--validation-commands", settings["validation_commands"]]
    if settings["harness_command"]:
        flags += ["--harness-command", settings["harness_command"]]
    return flags


# --------------------------------------------------------------------------------------------
# 4. Apply


def seed_tree(target: Path, settings: dict, found: dict) -> tuple[Path, list[Path]]:
    """Seed a three-slice tree and its detail docs, if there is no tree yet."""
    docs = target / ".docs"
    tree_path = docs / "slice_dependency_tree.json"
    detail_dir = docs / "slices"

    if tree_path.exists():
        return tree_path, []

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prefix = re.sub(r"[^A-Z0-9]+", "-", settings["project_id"].upper()).strip("-") or "PROJECT"
    slices = [
        {
            "slice_id": f"{prefix}-1",
            "slice_number": 1,
            "group": "technical",
            "title": f"First real slice in {settings['project_name']} (replace this one)",
            "state": "ready",
            "status": "ready",
            "dependencies": [],
            "blocks": [2],
            "operator_gates": [],
            "checkpoint": "low-risk",
            "automation_eligible": True,
            "priority": 1,
            "last_known_pr": None,
            "risk": "low",
            "effort": "small",
            "tier": "P0",
        },
        {
            "slice_id": f"{prefix}-2",
            "slice_number": 2,
            "group": "technical",
            "title": "Something with a dependency (replace this one)",
            "state": "shaped",
            "status": "planned",
            "dependencies": [1],
            "blocks": [],
            "operator_gates": [],
            "checkpoint": "low-risk",
            "automation_eligible": True,
            "priority": 2,
            "last_known_pr": None,
            "risk": "medium",
            "effort": "medium",
            "tier": "P1",
        },
        {
            "slice_id": f"{prefix}-3",
            "slice_number": 3,
            "group": "product",
            "title": "A decision only you can make (replace this one)",
            "state": "gated",
            "status": "blocked",
            "dependencies": [],
            "blocks": [],
            "operator_gates": ["operator decides whether this is worth doing"],
            "checkpoint": "human",
            "automation_eligible": False,
            "priority": 3,
            "last_known_pr": None,
            "risk": "high",
            "effort": "small",
            "tier": "P0",
        },
    ]
    tree = {
        "schema_version": 2,
        "generated_at": now,
        "source_backlog_path": ".docs/slice_backlog.md",
        "default_fanout_limit": 1,
        "notes": [
            f"Seeded by scripts/drake-setup.py for {settings['project_name']}.",
            "Replace these three slices with your own work: slice 2 shows a dependency, slice 3 "
            "shows a slice that waits for a human decision, which the selector will not dispatch.",
        ],
        "slices": slices,
    }

    written: list[Path] = []
    docs.mkdir(parents=True, exist_ok=True)
    tree_path.write_text(json.dumps(tree, indent=2) + "\n", encoding="utf-8")
    written.append(tree_path)

    detail_dir.mkdir(parents=True, exist_ok=True)
    for row in slices:
        detail = detail_dir / f"{row['slice_id']}.md"
        detail.write_text(
            f"""# {row['slice_id']} — {row['title']}

| Field | Value |
| --- | --- |
| Slice ID | `{row['slice_id']}` |
| Group | {row['group']} |
| State | {row['state']} |
| Risk | {row['risk']} |
| Effort | {row['effort']} |

## Goal

Describe what changes for the user when this slice is done. If you cannot say it in two
sentences, the slice is too large — split it.

## Acceptance criteria

- [ ] The behaviour is observable by someone who did not write the code
- [ ] The validation commands in `.drake/slice-pipeline.config.json` pass
- [ ] Any new behaviour has a test that fails without it

## Manual test checklist

- [ ] Run the validation commands and paste the output into the evidence record
- [ ] Confirm the change is on one branch and one pull request

## Notes

Seeded by `drake-setup`. Replace this file with the real plan for the real slice.
""",
            encoding="utf-8",
        )
        written.append(detail)

    if found["monorepo"]:
        settings.setdefault("notes", []).append(
            "monorepo detected: confirm the validation commands run at the right level before the first slice"
        )
    return tree_path, written


def runbook_text(target: Path, settings: dict, found: dict, level: str) -> str:
    harness = settings["harness"]
    binary = HARNESS_BINARIES.get(harness)
    return f"""# SETUP.md — what `drake-setup` configured

Written {datetime.now(timezone.utc).strftime("%Y-%m-%d")} by `scripts/drake-setup.py` from the Drake
repository. Delete this file once you have read it.

## Level reached: **{level}**

| Level | Meaning |
| --- | --- |
| L0 | Plan only — config, canonical assets, a seeded tree, slice detail docs. Nothing runs. |
| L1 | One slice, human-triggered, with a wired harness. |
| L2 | Unattended: one slice per tick, with logs and exit codes. |
| L3 | Portfolio: several repositories. |

## What was detected (with the evidence)

| Fact | Value |
| --- | --- |
| Repository | `{target}` |
| Project id / name | `{settings['project_id']}` / {settings['project_name']} |
| GitHub slug | `{settings['github_slug']}` |
| Integration branch | `{settings['integration_branch']}` |
| Manifests | {found['evidence'].get('manifests', '— none found —')} |
| Validation commands | {settings['validation_commands'] or '— none detected —'} |
| CI workflows | {found['evidence'].get('ci', '— none found —')} |
| Harness CLIs on PATH | {found['evidence'].get('harnesses', '— none found —')} |
| Chosen harness | `{harness}`{f" (`{binary}`)" if binary else ''} |

## What was assumed

{chr(10).join(f"- {item}" for item in found['assumptions']) or "- nothing: everything above was detected"}

{f"- {chr(10).join(settings['notes'])}" if settings.get('notes') else ""}

## What to do next

```bash
# 1. Validate the plan
python3 {DRAKE_ROOT}/scripts/validate_slice_dependency_tree.py --tree .docs/slice_dependency_tree.json

# 2. See what would run, without running anything
node {DRAKE_ROOT}/tools/slice-agent-runner/dist/index.js run-next --repo . --dry-run

# 3. Run one slice for real (this calls your agent CLI)
node {DRAKE_ROOT}/tools/slice-agent-runner/dist/index.js run-next --repo .
```

Exit codes from the runner are the contract: **0** ran · **1** configuration error · **2** the
harness failed · **3** nothing runnable. Exit 3 is normal in a healthy repository.

{'## Running it unattended' + chr(10) + chr(10) + 'Add one line to your crontab (or a systemd timer — see ' + str(DRAKE_ROOT / 'docs' / 'scheduling.md') + '):' + chr(10) + chr(10) + '```cron' + chr(10) + f'*/30 7-20 * * 1-5  cd {target} && {DRAKE_ROOT}/scripts/slice-cron.sh --repo {target}' + chr(10) + '```' + chr(10) + chr(10) + 'It runs one slice per tick, refuses to overlap a run already in flight, and writes a log per run.' if level in ('L2', 'L3') else ''}

{'## Several repositories' + chr(10) + chr(10) + 'Each repository gets its own config and tree. Selection across them belongs to a dispatcher you own — the framework deliberately does not ship one. `docs/example-configuration.md` describes the registry shape.' if level == 'L3' else ''}

## Files this wrote

- `.drake/slice-pipeline.config.json` — the single source of truth for this repository
- `.drake/` canonical assets, with the entry points generated for `{harness}`
- `.docs/slice_dependency_tree.json` — three placeholder slices; replace them
- `.docs/slices/*.md` — one detail doc per slice
- `SETUP.md` — this file

Managed files (the ones Drake executes) refresh when you re-run the installer. Your files —
`AGENTS.md`, prompts, conventions — are never overwritten without `--overwrite-existing`.
"""


def apply_plan(target: Path, settings: dict, found: dict, *, apply: bool) -> dict:
    """Do the work. Without `apply`, everything here is reported and nothing is written."""
    report: dict = {"writes": [], "steps": []}

    if not apply:
        planned = run(installer_base(target, settings) + ["--mode", "install", "--dry-run"])
        report["steps"].append(("install (dry run)", planned.returncode, planned.stdout.strip()))
        report["writes"].append(".drake/ (config and assets, from the installer — not written)")
        report["writes"].append(".docs/slice_dependency_tree.json (seeded tree — not written)")
        report["writes"].append(".docs/slices/*.md (detail docs — not written)")
        report["writes"].append("SETUP.md (runbook — not written)")
        return report

    # Seed the plan FIRST: the installer ships a placeholder tree, and it leaves a
    # project-provided tree alone. Seeding second means the adopter gets the placeholder instead
    # of their own plan.
    before = set(git(target, "status", "--porcelain").splitlines())
    tree_path, seeded = seed_tree(target, settings, found)
    report["writes"].extend(str(p.relative_to(target)) for p in seeded)

    installed = run(installer_base(target, settings) + ["--mode", "install"])
    report["steps"].append(("install", installed.returncode, installed.stdout.strip() or installed.stderr.strip()))
    if installed.returncode != 0:
        report["install_failed"] = (installed.stdout + installed.stderr).strip()
        return report

    # Report what actually appeared, rather than what we expected to appear.
    after = set(git(target, "status", "--porcelain").splitlines())
    report["created_by_installer"] = sorted(line[3:] for line in after - before if line.strip())

    runbook = target / "SETUP.md"
    existing = runbook.read_text(encoding="utf-8") if runbook.is_file() else ""
    new_runbook = runbook_text(target, settings, found, settings["level"])
    if existing != new_runbook:
        runbook.write_text(new_runbook, encoding="utf-8")
        report["writes"].append("SETUP.md")

    report["tree"] = tree_path
    return report


# --------------------------------------------------------------------------------------------
# 5. Prove it


def verify(target: Path, settings: dict, report: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    tree = report.get("tree") or (target / ".docs" / "slice_dependency_tree.json")
    if tree.is_file():
        validated = run([sys.executable, str(VALIDATOR), "--tree", str(tree)])
        ok &= validated.returncode == 0
        notes.append(
            ("ok" if validated.returncode == 0 else "FAIL")
            + f"  dependency tree validates ({tree.relative_to(target)})"
            + ("" if validated.returncode == 0 else f": {validated.stdout.strip() or validated.stderr.strip()}")
        )
    else:
        ok = False
        notes.append("FAIL  no dependency tree — nothing to run")

    checked = run(installer_base(target, settings) + ["--mode", "check"])
    check_ok = checked.returncode == 0
    message = (checked.stdout + checked.stderr).strip().splitlines()
    detail = message[0] if message else ""
    if check_ok:
        notes.append("ok    installer check passes on the target")
    elif settings["level"] == "L0":
        notes.append(f"note  installer check reports the harness is not wired yet — expected at L0: {detail}")
    else:
        ok = False
        notes.append(f"FAIL  installer check: {detail}")

    if settings["level"] in LEVEL_NEEDS_HARNESS:
        if RUNNER.is_file():
            dry = run(["node", str(RUNNER), "run-next", "--repo", str(target), "--dry-run"])
            dry_ok = dry.returncode == 0
            ok &= dry_ok
            first = (dry.stdout or dry.stderr).strip().splitlines()
            notes.append(
                ("ok" if dry_ok else "FAIL")
                + "  dry run renders the task packet without calling a model"
                + ("" if dry_ok else f": {first[0] if first else ''}")
            )
        else:
            notes.append(f"note  runner not built at {RUNNER} — build it with: npm --prefix tools/slice-agent-runner ci && npm --prefix tools/slice-agent-runner run build")
    return ok, notes


# --------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--target", type=Path, required=True, help="the repository to configure")
    parser.add_argument("--level", choices=LEVELS, default="L1", help="how far to take adoption (default: L1)")
    parser.add_argument("--apply", action="store_true", help="write changes; without this, only plan")
    parser.add_argument("--project-name")
    parser.add_argument("--project-id")
    parser.add_argument("--github-slug")
    parser.add_argument("--integration-branch")
    parser.add_argument("--validation-commands", default=None)
    parser.add_argument("--harness", choices=sorted(HARNESS_BINARIES) + ["generic"])
    parser.add_argument("--harness-command", default="")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    target = args.target.resolve()
    if not target.is_dir():
        print(f"drake-setup: no such directory: {target}", file=sys.stderr)
        return 1

    found = detect(target)
    settings = resolve(args, target, found)

    # A plan run shows the plan and names what is blocking; an apply run refuses, because the
    # point of the level is that it is actually reached rather than nearly reached.
    if settings["problems"] and args.apply:
        for problem in settings["problems"]:
            print(f"drake-setup: {problem}", file=sys.stderr)
        print(
            "\nNothing was changed. Run at --level L0 to install the plan without a harness, fix the "
            "above and re-run, or run without --apply to see the plan anyway.",
            file=sys.stderr,
        )
        return 2

    report = apply_plan(target, settings, found, apply=args.apply)

    if report.get("install_failed"):
        print("drake-setup: the installer failed — nothing else was attempted", file=sys.stderr)
        print(report["install_failed"], file=sys.stderr)
        return 1

    ok, notes = verify(target, settings, report) if args.apply else (True, ["note  plan only: nothing was written (pass --apply)"])

    if args.json:
        print(json.dumps({"level": settings["level"], "applied": args.apply, "detected": found, "report": report, "notes": notes}, indent=2, default=str))
    else:
        print(f"drake-setup: {settings['project_name']} → level {settings['level']}"
              f"{' (applied)' if args.apply else ' (plan only — nothing written)'}\n")
        print("detected")
        for key in ("manifests", "validation", "ci", "harnesses"):
            if key in found["evidence"]:
                print(f"  {key:<12} {found['evidence'][key]}")
        for assumption in found["assumptions"]:
            print(f"  assumed      {assumption}")
        if settings["problems"]:
            print("\nblocked by")
            for problem in settings["problems"]:
                print(f"  {problem}")
        print("\nwrote" if args.apply else "\nwould write")
        for item in report["writes"] or ["(nothing)"]:
            print(f"  {item}")
        for item in report.get("created_by_installer", []):
            print(f"  {item} (installer)")
        print("\nverified")
        for note in notes:
            print(f"  {note}")
        if settings["level"] in ("L2", "L3"):
            print("\nnext")
            print(f"  add one line to cron (see SETUP.md), or a systemd timer from {DRAKE_ROOT / 'docs' / 'scheduling.md'}")

    if not args.apply:
        return 0
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
