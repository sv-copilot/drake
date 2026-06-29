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

usage() {
  cat <<'EOF'
Usage:
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --check
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --print-launch
  STAGING_HOST=<ip-or-hostname> scripts/hosted-ip-staging.sh --run

Environment variable names:
  STAGING_HOST          required public IP or temporary hostname without scheme
  HOSTED_API_HOST       default 0.0.0.0
  HOSTED_API_PORT       default 8000
  HOSTED_WEB_HOST       default 0.0.0.0
  HOSTED_WEB_PORT       default 3000
  HOSTED_WEB_ORIGIN     default http://${STAGING_HOST}:${HOSTED_WEB_PORT}
  NEXT_PUBLIC_API_URL   default http://${STAGING_HOST}:${HOSTED_API_PORT}
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
bash scripts/dev-hosted.sh
EOF
}

check_staging_stack() {
  require_staging_host
  check_file "scripts/dev-hosted.sh"
  check_file "services/api/src/hosted_api/main.py"
  check_file "apps/web/package.json"
  print_summary
}

run_staging_stack() {
  check_staging_stack
  echo "starting hosted stack for temporary IP staging"
  export HOSTED_API_HOST="$api_host"
  export HOSTED_API_PORT="$api_port"
  export HOSTED_WEB_HOST="$web_host"
  export HOSTED_WEB_PORT="$web_port"
  export HOSTED_WEB_ORIGIN="$web_origin"
  export NEXT_PUBLIC_API_URL="$api_url"
  exec "$repo_root/scripts/dev-hosted.sh"
}

case "${1:-}" in
  --check)
    check_staging_stack
    ;;
  --print-launch)
    check_staging_stack
    print_launch
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
