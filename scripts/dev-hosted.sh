#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
api_host="${HOSTED_API_HOST:-127.0.0.1}"
api_port="${HOSTED_API_PORT:-8000}"
web_host="${HOSTED_WEB_HOST:-127.0.0.1}"
web_port="${HOSTED_WEB_PORT:-3000}"
api_url="${NEXT_PUBLIC_API_URL:-http://${api_host}:${api_port}}"

usage() {
  cat <<'EOF'
Usage:
  scripts/dev-hosted.sh
  scripts/dev-hosted.sh --check

Environment variable names:
  HOSTED_API_HOST       default 127.0.0.1
  HOSTED_API_PORT       default 8000
  HOSTED_WEB_HOST       default 127.0.0.1
  HOSTED_WEB_PORT       default 3000
  HOSTED_WEB_ORIGIN     optional CORS origin for the API process
  NEXT_PUBLIC_API_URL   default http://127.0.0.1:8000
  GH_TOKEN              optional GitHub read token name for API sync
  GITHUB_TOKEN          optional GitHub read token name for API sync
EOF
}

check_file() {
  local path="$1"
  if [[ ! -f "$repo_root/$path" ]]; then
    echo "missing required file: $path" >&2
    return 1
  fi
}

check_hosted_stack() {
  check_file "services/api/pyproject.toml"
  check_file "services/api/src/hosted_api/main.py"
  check_file "apps/web/package.json"
  check_file "apps/web/.env.example"

  echo "hosted local dev check passed"
  echo "api: http://${api_host}:${api_port}"
  echo "web: http://${web_host}:${web_port}"
  echo "NEXT_PUBLIC_API_URL=${api_url}"
}

start_hosted_stack() {
  check_hosted_stack

  echo "starting hosted API and web shell"
  (
    cd "$repo_root/services/api"
    python3 -m uvicorn hosted_api.main:app \
      --host "$api_host" \
      --port "$api_port"
  ) &
  api_pid=$!

  (
    cd "$repo_root/apps/web"
    NEXT_PUBLIC_API_URL="$api_url" npm run dev -- \
      --hostname "$web_host" \
      --port "$web_port"
  ) &
  web_pid=$!

  cleanup() {
    kill "$api_pid" "$web_pid" 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  wait -n "$api_pid" "$web_pid"
}

case "${1:-}" in
  --check)
    check_hosted_stack
    ;;
  -h|--help)
    usage
    ;;
  "")
    start_hosted_stack
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
