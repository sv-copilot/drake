#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
staging_host="${STAGING_HOST:-}"
api_host="${HOSTED_API_HOST:-0.0.0.0}"
api_port="${HOSTED_API_PORT:-8000}"
web_host="${HOSTED_WEB_HOST:-0.0.0.0}"
web_port="${HOSTED_WEB_PORT:-3000}"
web_origin="${HOSTED_WEB_ORIGIN:-http://${staging_host}:${web_port}}"
api_url="${NEXT_PUBLIC_API_URL:-http://${staging_host}:${api_port}}"
staging_mode="${HOSTED_STAGING_MODE:-production}"

usage() {
  cat <<'EOF'
Usage:
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --check
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --print-launch
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --print-smoke
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --run

Environment variable names:
  STAGING_HOST          required public IP or temporary hostname without scheme
  HOSTED_API_HOST       default 0.0.0.0
  HOSTED_API_PORT       default 8000
  HOSTED_WEB_HOST       default 0.0.0.0
  HOSTED_WEB_PORT       default 3000
  HOSTED_WEB_ORIGIN     default http://${STAGING_HOST}:${HOSTED_WEB_PORT}
  NEXT_PUBLIC_API_URL   default http://${STAGING_HOST}:${HOSTED_API_PORT}
  HOSTED_STAGING_MODE   default production; allowed production or dev
  GH_TOKEN              optional GitHub read token name for API sync
  GITHUB_TOKEN          optional GitHub read token name for API sync
EOF
}

require_staging_host() {
  if [[ -z "$staging_host" ]]; then
    echo "STAGING_HOST is required, for example: STAGING_HOST=203.0.113.10" >&2
    return 1
  fi
  if [[ "$staging_host" == http://* || "$staging_host" == https://* ]]; then
    echo "STAGING_HOST must be a bare host or IP without http:// or https://" >&2
    return 1
  fi
}

require_staging_mode() {
  if [[ "$staging_mode" != "production" && "$staging_mode" != "dev" ]]; then
    echo "HOSTED_STAGING_MODE must be production or dev" >&2
    return 1
  fi
}

check_file() {
  local path="$1"
  if [[ ! -f "$repo_root/$path" ]]; then
    echo "missing required file: $path" >&2
    return 1
  fi
}

print_summary() {
  echo "hosted IP staging check passed"
  echo "web: http://${staging_host}:${web_port}"
  echo "api: http://${staging_host}:${api_port}"
  echo "HOSTED_WEB_ORIGIN=${web_origin}"
  echo "NEXT_PUBLIC_API_URL=${api_url}"
  echo "HOSTED_STAGING_MODE=${staging_mode}"
  echo "warning: temporary IP staging is HTTP-only and unauthenticated; restrict firewall access"
}

print_launch() {
  cat <<EOF
STAGING_HOST=${staging_host} \\
HOSTED_API_HOST=${api_host} \\
HOSTED_API_PORT=${api_port} \\
HOSTED_WEB_HOST=${web_host} \\
HOSTED_WEB_PORT=${web_port} \\
HOSTED_WEB_ORIGIN=${web_origin} \\
NEXT_PUBLIC_API_URL=${api_url} \\
HOSTED_STAGING_MODE=${staging_mode} \\
bash scripts/hosted-ip-staging.sh --run
EOF
}

print_smoke() {
  cat <<EOF
curl http://${staging_host}:${api_port}/health
curl http://${staging_host}:${api_port}/api/v1/portfolio
open http://${staging_host}:${web_port}
EOF
}

check_staging_stack() {
  require_staging_host
  require_staging_mode
  check_file "scripts/dev-hosted.sh"
  check_file "services/api/src/hosted_api/main.py"
  check_file "apps/web/package.json"
  print_summary
}

run_staging_stack() {
  check_staging_stack
  echo "starting hosted stack for temporary IP staging (${staging_mode})"
  (
    cd "$repo_root/services/api"
    PYTHONPATH="$repo_root/services/api/src:${PYTHONPATH:-}" \
      HOSTED_WEB_ORIGIN="$web_origin" \
      python3 -m uvicorn hosted_api.main:app \
        --host "$api_host" \
        --port "$api_port"
  ) &
  api_pid=$!

  (
    cd "$repo_root/apps/web"
    if [[ "$staging_mode" == "production" ]]; then
      NEXT_PUBLIC_API_URL="$api_url" npm run build
      NEXT_PUBLIC_API_URL="$api_url" npm run start -- \
        --hostname "$web_host" \
        --port "$web_port"
    else
      NEXT_PUBLIC_API_URL="$api_url" npm run dev -- \
        --hostname "$web_host" \
        --port "$web_port"
    fi
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
    check_staging_stack
    ;;
  --print-launch)
    check_staging_stack
    print_launch
    ;;
  --print-smoke)
    check_staging_stack
    print_smoke
    ;;
  --run)
    run_staging_stack
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
