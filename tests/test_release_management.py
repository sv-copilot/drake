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
import re
import subprocess

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


def test_cutting_a_release_requires_the_documentation_to_name_it(tmp_path: Path) -> None:
    """A release must not be cut while the documentation pins a different version.

    Behavioural on purpose: the pin check is extracted from cut_release.sh and run against fixture
    documents, so this test survives the check being rewritten (its first version flagged Node's
    v22.20.0 and a historical v0.1.0 mention, and failed a good release for the wrong reason).
    """
    source = (pathlib.Path(__file__).resolve().parents[1] / "scripts" / "cut_release.sh").read_text(
        encoding="utf-8"
    )
    function = re.search(r"^pin_check\(\) \{.*?^\}", source, re.S | re.M)
    assert function, "cut_release.sh must keep a pin_check function"

    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "git clone --branch v0.2.12 --depth 1 https://example.invalid/repo.git\n"
        "curl -fsSL https://nodejs.org/dist/v22.20.0/node-v22.20.0-linux-x64.tar.xz\n"
        "Version v0.1.0 was the first release.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "whitepaper.md").write_text(
        "released under semantic tags (v0.2.12 at the time of writing\n"
        "| Release | **v0.2.12**, Apache-2.0 |\n",
        encoding="utf-8",
    )

    script = rf"""
set -uo pipefail
cd {tmp_path}
version="v0.2.12"
unpinned=""
stale=""
{function.group(0)}
pin_check README.md '--branch v[0-9.]+'
pin_check docs/whitepaper.md 'semantic tags \(v[0-9.]+'
pin_check docs/whitepaper.md '\| Release \| \*\*v[0-9.]+\*\*'
printf 'unpinned=[%s] stale=[%s]' "$unpinned" "$stale"
"""
    clean = subprocess.run(["bash", "-c", script], text=True, capture_output=True, check=False)
    assert clean.returncode == 0, clean.stderr
    # Node's v22.20.0 and the historical v0.1.0 are not pin sites: neither may be reported.
    assert clean.stdout == "unpinned=[] stale=[]", clean.stdout

    (tmp_path / "README.md").write_text("git clone --branch v0.2.11 --depth 1 x\n", encoding="utf-8")
    stale_result = subprocess.run(["bash", "-c", script], text=True, capture_output=True, check=False)
    assert "v0.2.11" in stale_result.stdout, "a stale pin must be reported"

    assert "do not pin" in source and "still pin an older release" in source


def test_the_pin_check_reads_PATTERNS_starting_with_dashes(tmp_path: Path) -> None:
    """The check greps for '--branch ...', which grep parses as an option unless -e is used."""
    source = (pathlib.Path(__file__).resolve().parents[1] / "scripts" / "cut_release.sh").read_text(
        encoding="utf-8"
    )
    assert 'grep -oE -e "$pattern"' in source
