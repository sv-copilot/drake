#!/usr/bin/env bash
#
# Cut a release.
#
# Release management here means: the adoption chain is tested before the tag, and the
# published artifact is tested after it. A tag that a stranger cannot adopt is not a
# release, and finding that out at tag time is the cheap moment to find it out.
#
#   scripts/cut_release.sh v0.2.3 [notes-file]
#
# Steps:
#   1  refuse to start unless main is clean, level with origin, and green in CI
#   2  rehearse the adoption chain on this tree (fail here and nothing is tagged)
#   3  tag, push the tag, create the GitHub release
#   4  clone the published tag and run its gate phase there (the artifact must pass
#      its own gate, including the adoption chain, from a cold clone)
#
# The same verification runs automatically in .github/workflows/release-verify.yml on
# every tag push, so a release cut by hand is still verified.
#
set -uo pipefail

version="${1:-}"
notes_file="${2:-}"
if [ -z "$version" ]; then
  echo "usage: scripts/cut_release.sh <version> [notes-file]" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root" || exit 1
python_bin="${PYTHON:-python3}"

fail() { echo "cut_release: FAILED — $1" >&2; exit 1; }
step() { printf '\n== %s\n' "$1"; }

step "1/5 preconditions"
branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] || fail "must be on main, currently on $branch"
git fetch -q origin || fail "could not fetch origin"
[ -z "$(git status --porcelain)" ] || fail "working tree is dirty:
$(git status --porcelain)"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || fail "main is not level with origin/main"
if git rev-parse -q --verify "refs/tags/$version" >/dev/null; then
  fail "tag $version already exists"
fi
echo "branch: main at $(git rev-parse --short HEAD)"

if command -v gh >/dev/null 2>&1; then
  ci_state="$(gh run list --branch main --limit 1 --json status,conclusion \
    -q '.[0] | "\(.status) \(.conclusion)"' 2>/dev/null || echo "unknown")"
  case "$ci_state" in
    "completed success") echo "CI on main: $ci_state" ;;
    unknown)             echo "CI on main: could not read it (continuing)" ;;
    *)                   fail "CI on main is '$ci_state'; wait for a green run before tagging" ;;
  esac
else
  echo "gh not available: skipping the CI-on-main check"
fi

step "2/5 the documentation pins the version being released"
# The README quick start and the whitepaper name the release they were verified against. They
# drifted two releases behind once, so a stranger following the documented path cloned an old tag
# without anyone noticing. Enforce it here: cutting a release requires the docs to name it.
unpinned=""
stale=""

# Only the PIN SITES matter: a version mentioned in prose or a Node toolchain version is not a pin.
# The first version of this check matched every vX.Y.Z in the files, which flagged Node's v22.20.0.
pin_check() {
  # $1 doc, $2 an ERE that matches a pin site INCLUDING the version digits.
  # Two traps are baked into these patterns, both found by running them against the real files:
  #   * in an extended regex '(' opens a group, so a literal parenthesis must be escaped - an
  #     unescaped 'semantic tags (v0.2.12' matched nothing;
  #   * `grep -o` prints only the matched text, so a pattern that stops before the version yields no
  #     digits to check. (An earlier version used -F prefixes and silently matched nothing.)
  local doc="$1" pattern="$2" found only
  found="$(grep -oE -e "$pattern" "$doc" 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sort -u | tr '\n' ' ')"
  [ -z "$found" ] && { unpinned="$unpinned $doc"; return; }
  only="$(printf '%s' "$found" | tr ' ' '\n' | grep -v -- "^$version$" | sort -u | tr '\n' ' ')"
  [ -n "$only" ] && stale="$stale
  $doc pins: $only"
}

pin_check README.md '--branch v[0-9]+\.[0-9]+\.[0-9]+'
pin_check README.md 'cleanroom-run\.sh "\$room" v[0-9]+\.[0-9]+\.[0-9]+'
pin_check docs/whitepaper.md 'semantic tags \(v[0-9]+\.[0-9]+\.[0-9]+'
pin_check docs/whitepaper.md '\| Release \| \*\*v[0-9]+\.[0-9]+\.[0-9]+\*\*'
pin_check docs/whitepaper.md 'cleanroom-run\.sh "\$room" v[0-9]+\.[0-9]+\.[0-9]+'

if [ -n "$unpinned" ]; then
  fail "these files do not pin $version:$unpinned - update the pinned version (README quick start and clean-room command, whitepaper release line) and re-run"
fi
if [ -n "$stale" ]; then
  fail "these files still pin an older release:$(printf "$stale") - every pin must name $version"
fi

echo "documentation names $version"

step "3/5 adoption chain on this tree"
chain_work="$(mktemp -d)"
if ! RETEST_WORK="$chain_work" bash scripts/adoption_chain_retest.sh "$version" chain; then
  fail "the adoption chain failed; nothing was tagged (artifacts in $chain_work)"
fi

step "4/5 tag and publish"
git tag -a "$version" -m "$version" || fail "could not create the tag"
git push origin "$version" || fail "could not push the tag"
if [ -n "$notes_file" ]; then
  [ -f "$notes_file" ] || fail "notes file not found: $notes_file"
  gh release create "$version" --title "$version" --notes-file "$notes_file" || fail "could not create the release"
else
  gh release create "$version" --title "$version" --generate-notes || fail "could not create the release"
fi
echo "published: $(gh release view "$version" --json url -q .url 2>/dev/null || echo "$version")"

step "5/5 verify the published artifact"
remote="$(git remote get-url origin)"
verify_dir="$(mktemp -d)/drake"
bash -c "git clone -q --branch '$version' --depth 1 '$remote' '$verify_dir'" \
  || fail "could not clone the published tag"
if ( cd "$verify_dir" && bash scripts/adoption_chain_retest.sh "$version" gate ); then
  echo
  echo "cut_release: $version verified — the published tag passes its own gate, the"
  echo "             adoption chain, and the harness matrix from a cold clone."
else
  fail "$version is tagged and published, but the cold-clone verification FAILED — investigate before announcing it"
fi
