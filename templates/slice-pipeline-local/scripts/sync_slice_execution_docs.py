#!/usr/bin/env python3
"""Sync execution docs after one or more slice PRs merge.

Canonical version lives in the portfolio governance repo at
templates/slice-pipeline-local/scripts/sync_slice_execution_docs.py.

Updates canonical planning files so automation selection advances:
  - .docs/slice_dependency_tree.json (status=done, last_known_pr)
  - .docs/slice_backlog.md (Planned -> Completed + PR ref, authoritative next)
  - .docs/roadmap.md (next-slice pointers when --authoritative-next is set)

Auto-promotes the authoritative-next slice from "planned" to "ready" when
all its dependencies are done, so the next automation cycle picks it up.

Usage:
  python3 scripts/sync_slice_execution_docs.py \
    --merge SLICE-ALPHA-1:100 \
    --merge SLICE-BETA-1:101 \
    --authoritative-next SLICE-GAMMA-1

Customization needed per repo:
  - ROADMAP_PATH points to .docs/roadmap.md (default) or custom path.
  - _update_roadmap() has hardcoded section patterns. Override or edit
    the regex patterns to match your repo's roadmap format.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TREE_PATH = Path(".docs/slice_dependency_tree.json")
BACKLOG_PATH = Path(".docs/slice_backlog.md")
ROADMAP_PATH = Path(".docs/roadmap.md")


def _parse_merge(value: str) -> tuple[str, int]:
    if ":" not in value:
        raise argparse.ArgumentTypeError(
            f"expected SLICE-ID:PR_NUMBER, got {value!r}"
        )
    slice_id, pr_raw = value.rsplit(":", 1)
    slice_id = slice_id.strip()
    if not slice_id.startswith("SLICE-"):
        raise argparse.ArgumentTypeError(f"invalid slice id: {slice_id!r}")
    try:
        pr_number = int(pr_raw.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid PR number: {pr_raw!r}") from exc
    return slice_id, pr_number


def _load_tree(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _slice_row(tree: dict, slice_id: str) -> dict:
    for row in tree["slices"]:
        if row["slice_id"] == slice_id:
            return row
    raise KeyError(f"slice not found in dependency tree: {slice_id}")


def _update_dependency_tree(tree: dict, merges: list[tuple[str, int]]) -> list[str]:
    changes: list[str] = []
    for slice_id, pr_number in merges:
        row = _slice_row(tree, slice_id)
        if row.get("status") != "done" or row.get("last_known_pr") != pr_number:
            row["status"] = "done"
            row["state"] = "validated"
            row["last_known_pr"] = pr_number
            changes.append(
                f"dependency tree: {slice_id} -> done (PR #{pr_number})"
            )
    return changes


def _backlog_row_pattern(rank: int) -> re.Pattern[str]:
    return re.compile(rf"^\| {rank}\s+\|")


def _update_backlog_row(
    lines: list[str],
    rank: int,
    pr_number: int,
) -> bool:
    pattern = _backlog_row_pattern(rank)
    for index, line in enumerate(lines):
        if not pattern.match(line):
            continue
        if "**Completed:**" in line and f"PR #{pr_number}" in line:
            return False
        updated = line.replace("**Planned:**", "**Completed:**")
        if f"(PR #{pr_number})" not in updated:
            parts = updated.split("|")
            if len(parts) >= 5:
                desc = parts[4].strip()
                if desc.endswith("."):
                    desc = desc[:-1].rstrip()
                parts[4] = f" {desc} (PR #{pr_number}). "
                updated = "|".join(parts)
        lines[index] = updated
        return True
    raise KeyError(f"backlog row not found for rank {rank}")


def _authoritative_next_line(next_slice_id: str, next_rank: int) -> str:
    return (
        f"**Authoritative next implementation slice:** rank **{next_rank}** "
        f"`{next_slice_id}`."
    )


def _update_authoritative_next_backlog(
    text: str,
    next_slice_id: str,
    next_rank: int,
) -> tuple[str, bool]:
    target = _authoritative_next_line(next_slice_id, next_rank)
    if target in text:
        return text, False
    updated = re.sub(
        r"\*\*Authoritative next implementation slice:\*\* rank \*\*\d+\*\* `[^`]+`\.",
        target,
        text,
        count=1,
    )
    return updated, updated != text


def _recommended_next_triplet(
    tree: dict,
    start_rank: int,
) -> list[tuple[int, str]]:
    by_rank = {row["slice_number"]: row for row in tree["slices"]}
    picks: list[tuple[int, str]] = []
    for rank in range(start_rank, start_rank + 20):
        row = by_rank.get(rank)
        if row is None:
            break
        if row.get("status") == "done":
            continue
        picks.append((rank, row["slice_id"]))
        if len(picks) == 3:
            break
    if len(picks) < 1:
        raise ValueError(f"no runnable slice at or after rank {start_rank}")
    return picks


def _format_recommended_next_3(picks: list[tuple[int, str]]) -> str:
    chunks = [
        f"`{slice_id}` ({rank})" for rank, slice_id in picks
    ]
    return ", ".join(f"({index + 1}) {chunk}" for index, chunk in enumerate(chunks))


def _update_roadmap(
    text: str,
    *,
    done_through_rank: int,
    done_prs: list[int],
    next_rank: int,
    next_slice_id: str,
    recommended: list[tuple[int, str]],
) -> str:
    """Update roadmap next-slice pointers.

    NOTE: This function uses repo-specific regex patterns. When porting to a
    new repo, edit the regex patterns and replacement templates to match the
    target repo's .docs/roadmap.md format. The patterns below are from the
    reference implementation (example-app) and will fail on a different
    roadmap format unless customized.
    """
    pr_list = ", ".join(f"#{pr}" for pr in done_prs)
    rec = _format_recommended_next_3(recommended)

    # REPO-SPECIFIC: edit regex/replacement to match your roadmap format
    text = re.sub(
        r"\*\*Ranks \d+–\d+ are complete\*\* \(PRs [^)]+\)\. "
        r"\*\*Next slice:\*\* rank \*\*\d+\*\* `[^`]+`\.",
        (
            f"**Ranks –{done_through_rank} are complete** (PRs {pr_list}). "
            f"**Next slice:** rank **{next_rank}** `{next_slice_id}`."
        ),
        text,
        count=1,
    )

    # REPO-SPECIFIC: edit regex/replacement to match your roadmap format
    text = re.sub(
        r"\*\*Recommended next 3 on `ai-dev` \(strict linear.*?\):\*\* "
        r"\(1\) `[^`]+` \(\d+\), "
        r"\(2\) `[^`]+` \(\d+\), "
        r"\(3\) `[^`]+` \(\d+\)\.",
        f"**Recommended next 3 on `ai-dev` (strict linear):** {rec}.",
        text,
        count=1,
    )

    changelog = (
        "- **Roadmap sync:** mirrored completion through rank "
        f"**{done_through_rank}** (includes PRs {pr_list}); advanced "
        f"`Next Slice` and `Recommended next 3` to rank **{next_rank}** "
        f"`{next_slice_id}`; refreshed `.docs/slice_dependency_tree.json` statuses.\n"
    )
    marker = "## Change log for this canonical roadmap\n\n"
    if marker in text and changelog not in text:
        text = text.replace(marker, marker + changelog)

    return text


def sync_execution_docs(
    merges: list[tuple[str, int]],
    *,
    authoritative_next: str | None = None,
    tree_path: Path = TREE_PATH,
    backlog_path: Path = BACKLOG_PATH,
    roadmap_path: Path = ROADMAP_PATH,
    dry_run: bool = False,
) -> dict:
    """Run one sync cycle: mark merges done, update backlog, auto-promote next."""

    tree = _load_tree(tree_path)
    changes: list[str] = []
    changes.extend(_update_dependency_tree(tree, merges))

    backlog_lines = backlog_path.read_text(encoding="utf-8").splitlines()
    for slice_id, pr_number in merges:
        rank = _slice_row(tree, slice_id)["slice_number"]
        if _update_backlog_row(backlog_lines, rank, pr_number):
            changes.append(f"backlog: rank {rank} -> Completed (PR #{pr_number})")

    next_rank: int | None = None
    if authoritative_next:
        next_row = _slice_row(tree, authoritative_next)
        next_rank = next_row["slice_number"]
        backlog_text = "\n".join(backlog_lines) + "\n"
        backlog_text, backlog_next_changed = _update_authoritative_next_backlog(
            backlog_text,
            authoritative_next,
            next_rank,
        )
        backlog_lines = backlog_text.splitlines()
        if backlog_next_changed:
            changes.append(
                f"backlog: authoritative next -> rank {next_rank} {authoritative_next}"
            )

        # Auto-promote authoritative-next from planned to ready if deps met.
        if next_row.get("status") == "planned":
            dep_nums = next_row.get("dependencies", [])
            by_num = {row["slice_number"]: row for row in tree["slices"]}
            all_deps_done = all(
                by_num[dep]["status"] == "done" for dep in dep_nums
            )
            if all_deps_done:
                merged_ids = [sid for sid, _ in merges]
                next_row["status"] = "ready"
                changes.append(
                    f"dependency tree: {authoritative_next} -> ready "
                    f"(auto-promoted after {', '.join(merged_ids)} done)"
                )
                for index, line in enumerate(backlog_lines):
                    if not _backlog_row_pattern(next_rank).match(line):
                        continue
                    updated = line.replace("**Planned:**", "**Ready:**")
                    if updated != line:
                        backlog_lines[index] = updated
                        changes.append(
                            f"backlog: rank {next_rank} -> Ready (auto-promoted)"
                        )
                    break

        merged_ranks = sorted(
            _slice_row(tree, slice_id)["slice_number"] for slice_id, _ in merges
        )
        done_through_rank = merged_ranks[-1]
        done_prs = [pr for _, pr in merges]
        recommended = _recommended_next_triplet(tree, next_rank)
        roadmap_text = roadmap_path.read_text(encoding="utf-8")
        next_marker = f"**Next slice:** rank **{next_rank}** `{authoritative_next}`."
        if next_marker not in roadmap_text:
            roadmap_text = _update_roadmap(
                roadmap_text,
                done_through_rank=done_through_rank,
                done_prs=done_prs,
                next_rank=next_rank,
                next_slice_id=authoritative_next,
                recommended=recommended,
            )
            if not dry_run:
                roadmap_path.write_text(roadmap_text, encoding="utf-8")
            changes.append(f"roadmap: next slice -> rank {next_rank}")

    if not dry_run:
        tree_path.write_text(
            json.dumps(tree, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        backlog_path.write_text(
            "\n".join(backlog_lines) + "\n",
            encoding="utf-8",
        )

    return {"changes": changes, "dry_run": dry_run}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--merge",
        action="append",
        type=_parse_merge,
        default=[],
        metavar="SLICE-ID:PR",
        help="Slice id and merged PR number (repeatable)",
    )
    parser.add_argument(
        "--authoritative-next",
        help="Slice id for the next automation target (updates backlog + roadmap)",
    )
    parser.add_argument(
        "--tree",
        type=Path,
        default=TREE_PATH,
    )
    parser.add_argument(
        "--backlog",
        type=Path,
        default=BACKLOG_PATH,
    )
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=ROADMAP_PATH,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    args = parser.parse_args(argv)

    if not args.merge:
        print("at least one --merge SLICE-ID:PR is required", file=sys.stderr)
        return 2

    merges = sorted(args.merge, key=lambda item: _slice_row(_load_tree(args.tree), item[0])["slice_number"])
    result = sync_execution_docs(
        merges,
        authoritative_next=args.authoritative_next,
        tree_path=args.tree,
        backlog_path=args.backlog,
        roadmap_path=args.roadmap,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
