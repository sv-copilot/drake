"""Release management must keep testing the adoption chain.

The adoption chain is a permanent part of releasing: the gate runs it on every push and
pull request, the release script rehearses it before tagging and verifies the published
tag afterwards, and a tag push triggers the cold-clone verification.

Those are easy to lose — to a refactor, or to an export from another tree that owns the
same files. Losing them is silent: releases still go out, just unverified. This test
makes that loss loud, in CI, before anyone tags anything.
"""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PREFLIGHT = REPO_ROOT / "scripts" / "ci_preflight.sh"
RETEST = REPO_ROOT / "scripts" / "adoption_chain_retest.sh"
CUT_RELEASE = REPO_ROOT / "scripts" / "cut_release.sh"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
VERIFY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-verify.yml"


def read(path: pathlib.Path) -> str:
    assert path.is_file(), f"missing {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def test_every_push_and_pull_request_runs_the_adoption_chain() -> None:
    """The gate is the deployment signal; the chain has to be inside it."""
    preflight = read(PREFLIGHT)

    assert "bash scripts/adoption_chain_retest.sh" in preflight, (
        "ci_preflight.sh no longer rehearses the adoption chain: every deployment would "
        "ship without testing the path a stranger takes"
    )
    assert " chain" in preflight, "the gate must run the chain phase of the rehearsal"

    # The other halves of the release rehearsal must stay in the gate too.
    assert "scripts/harness_matrix_smoke.sh" in preflight
    assert "scripts/validate_run_artifacts.py" in preflight
    assert "scripts/adoption_smoke.sh" in preflight


def test_the_chain_phase_runs_against_the_tree_it_lives_in() -> None:
    """CI has no tag to clone, so the chain phase must work on the working tree."""
    retest = read(RETEST)

    assert 'RETEST_CLONE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)' in retest, (
        "the chain phase no longer defaults to its own repository"
    )


def test_the_chain_phase_cannot_recurse_into_the_gate() -> None:
    """The gate runs the chain; if the chain ran the gate, CI would never finish.

    The gate may only be *run* inside the gate phase's guarded region. A quoted mention
    (the fixture app's validation command) is not an invocation.
    """
    import re

    retest = read(RETEST)
    guard_end = retest.index("fi  # end phase != chain")

    invocation = re.compile(
        r"^(\(|\{)?\s*(cd [^)]*&&\s*)?bash scripts/ci_preflight\.sh", re.MULTILINE
    )

    assert invocation.search(retest[:guard_end]), "the rehearsal no longer runs the gate at all"

    offenders = [
        line.strip()
        for line in retest[guard_end:].splitlines()
        if invocation.match(line.strip())
    ]
    assert not offenders, (
        f"the rehearsal runs the gate outside the gate phase ({offenders}); the chain "
        "phase would call the gate back and CI would never finish"
    )


def test_the_release_script_rehearses_before_tagging_and_verifies_after() -> None:
    cut = read(CUT_RELEASE)

    assert "adoption_chain_retest.sh" in cut, "the release script no longer rehearses the chain"

    chain_index = cut.index('bash scripts/adoption_chain_retest.sh "$version" chain')
    tag_index = cut.index("git tag -a")
    assert chain_index < tag_index, (
        "the chain must be rehearsed BEFORE the tag is created, or a broken adoption path "
        "still reaches a published release"
    )

    assert '"$version" gate' in cut, (
        "the release script no longer verifies the published tag by cold clone"
    )
    assert "completed success" in cut, (
        "the release script no longer requires a green CI run on main before tagging"
    )


def test_a_tag_push_verifies_the_published_artifact() -> None:
    workflow = read(VERIFY_WORKFLOW)

    assert '"v*"' in workflow or "'v*'" in workflow, "the workflow no longer triggers on tags"
    assert "adoption_chain_retest.sh" in workflow
    assert " gate" in workflow, "the tag verification must run the gate phase"
    assert "env -u PYTHONPATH" in workflow, (
        "the verification should model a stranger's shell, without an inherited PYTHONPATH"
    )


def test_ci_still_runs_the_gate() -> None:
    assert "bash scripts/ci_preflight.sh" in read(CI_WORKFLOW)


def test_the_chain_retest_does_not_hardcode_matrix_counts() -> None:
    """The retest failed a good release by asserting an exact scenario count.

    A verification script may assert a floor and zero failures; it may not assert the exact
    number, because every added scenario then breaks the verification of an unrelated release.
    """
    retest = (pathlib.Path(__file__).resolve().parents[1] / "scripts" / "adoption_chain_retest.sh").read_text(
        encoding="utf-8"
    )

    assert "harness matrix: 14 passed" not in retest
    assert "matrix_passed" in retest and "-ge 14" in retest


def test_cutting_a_release_requires_the_documentation_to_name_it() -> None:
    """The README quick start and the whitepaper pin a version, and they drifted two releases
    behind: a stranger following the documented path cloned an old tag. The release path now
    refuses to tag unless those documents name the version being released.
    """
    source = (pathlib.Path(__file__).resolve().parents[1] / "scripts" / "cut_release.sh").read_text(
        encoding="utf-8"
    )

    assert "for doc in README.md docs/whitepaper.md" in source
    assert "do not name" in source
    # A doc that names the new version once and pins an older tag elsewhere is still wrong.
    assert "still pin an older release" in source
