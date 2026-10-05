#!/usr/bin/env bash
#
# Provision an "empty machine" for the from-scratch test.
#
# The room ends up with: base OS utilities (git, curl, tar, coreutils) and nothing else
# that matters — no Node, no npm packages, no Python toolchain, no caches. Node and
# Python are installed from their own sources *into the room*, exactly as the README
# tells a new user to do.
#
# Bootstrap note (learned the hard way): the installers need a working PATH, so the
# room's bin goes FIRST rather than replacing PATH. The isolation claim is then checked
# at the end by resolving node/npm/python3/uv inside a fully scrubbed environment.
#
set -uo pipefail

room="${1:?usage: cleanroom-setup.sh <room-dir>}"
mkdir -p "$room/bin" "$room/src" "$room/work" "$room/home"
export HOME="$room/home"
# room first, then the base system: a user's shell during installation
export PATH="$room/bin:/usr/bin:/bin"

echo "room: $room"

# --- base OS utilities the room is allowed to have ---------------------------
BASE_TOOLS="bash sh env tar gzip xz curl unzip git ls cat mkdir rmdir cp mv rm chmod ln date sleep \
find grep sed awk sort head tail wc dirname basename realpath tee xargs which tr cut uniq diff \
touch id whoami printf seq stat df du file mktemp"

for tool in $BASE_TOOLS; do
  for dir in /usr/bin /bin; do
    if [ -x "$dir/$tool" ] && [ ! -e "$room/bin/$tool" ]; then
      /usr/bin/ln -s "$dir/$tool" "$room/bin/$tool"
      break
    fi
  done
done

missing=""
count=0
for tool in $BASE_TOOLS; do
  if [ -e "$room/bin/$tool" ]; then count=$((count + 1)); else missing="$missing $tool"; fi
done
echo "base utilities linked: $count of $(echo "$BASE_TOOLS" | /usr/bin/wc -w) (missing:$missing)"

# --- Node, from the official tarball -----------------------------------------
NODE_VERSION="v22.20.0"
if [ ! -e "$room/bin/node" ]; then
  echo "installing Node $NODE_VERSION from nodejs.org"
  /usr/bin/curl -fsSL "https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-linux-x64.tar.xz" \
    -o "$room/src/node.tar.xz" || { echo "node download failed" >&2; exit 1; }
  "$room/bin/tar" -xJf "$room/src/node.tar.xz" -C "$room/src" || exit 1
  for binary in node npm npx; do
    /usr/bin/ln -s "$room/src/node-$NODE_VERSION-linux-x64/bin/$binary" "$room/bin/$binary"
  done
fi

# --- Python, from uv's standalone builds --------------------------------------
if [ ! -e "$room/bin/python3" ]; then
  echo "installing uv, then Python 3.12"
  /usr/bin/curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz" \
    -o "$room/src/uv.tar.gz" || { echo "uv download failed" >&2; exit 1; }
  "$room/bin/tar" -xzf "$room/src/uv.tar.gz" -C "$room/src" || exit 1
  /usr/bin/ln -sf "$room/src/uv-x86_64-unknown-linux-gnu/uv" "$room/bin/uv"
  "$room/bin/uv" python install 3.12 || exit 1
  python_path="$("$room/bin/uv" python find 3.12)" || exit 1
  /usr/bin/ln -sf "$python_path" "$room/bin/python3"
fi

echo
echo "the room now provides:"
for tool in node npm python3 uv git curl tar xz; do
  printf '  %-8s %s\n' "$tool" "$(command -v "$tool" 2>/dev/null || echo ABSENT)"
done
printf '  node    %s\n' "$("$room/bin/node" --version 2>/dev/null)"
printf '  npm     %s\n' "$("$room/bin/npm" --version 2>/dev/null)"
printf '  python  %s\n' "$("$room/bin/python3" --version 2>/dev/null)"
printf '  git     %s\n' "$("$room/bin/git" --version 2>/dev/null)"

# --- isolation check: nothing from the host may be reachable -----------------
leaks="$(env -i "PATH=$room/bin" HOME="$room/home" bash -c 'command -v node npm python3 uv' 2>/dev/null | grep -v "^$room/" || true)"
if [ -n "$leaks" ]; then
  echo "LEAK: these resolve outside the room:" >&2
  echo "$leaks" >&2
  exit 1
fi
echo "isolation check: with PATH=$room/bin only, node/npm/python3/uv resolve inside the room"
echo "python3 -m venv available: $(env -i "PATH=$room/bin" HOME="$room/home" bash -c 'python3 -m venv --help >/dev/null 2>&1 && echo yes || echo no')"
