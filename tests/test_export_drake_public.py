from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import subprocess
import sys
import threading
from pathlib import Path

from scripts.validate_drake_export import validate_tree

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = REPO_ROOT / "scripts/export_drake_public.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts/validate_drake_export.py"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def fake_hosted_server(port: int, *, api: bool) -> Iterator[None]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if api and self.path == "/health":
                self._send_json({"status": "ok", "service": "hosted-api"})
                return
            if api and self.path == "/api/v1/portfolio":
                self._send_json({"repo_count": 1})
                return
            if not api and self.path == "/":
                self._send_text("<html><body>Software operations</body></html>")
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/html")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_export(output: Path, *, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(EXPORT_SCRIPT), "--output", str(output)]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_dry_run_lists_paths(tmp_path: Path) -> None:
    result = run_export(tmp_path / "out", dry_run=True)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "adapters/CONTRACT.md" in result.stdout
    assert "scripts/export_drake_public.py" in result.stdout
    assert not (tmp_path / "out").exists()


def test_export_writes_tree(tmp_path: Path) -> None:
    output = tmp_path / "drake-export"
    result = run_export(output)
    assert result.returncode == 0, result.stderr or result.stdout
    assert (output / "README.md").is_file()
    assert (output / "docs/getting-started.md").is_file()
    assert (output / "adapters/cursor/CURSOR-ADAPTER.md").is_file()
    assert (output / "scripts/dev-hosted.sh").is_file()
    assert (output / "scripts/hosted-ip-staging.sh").is_file()
    assert (output / ".docs/hosted-ip-staging.md").is_file()
    assert (output / ".docs/hosted_api_sketch.schema.json").is_file()
    assert (output / ".docs/mcp_environment_profile.schema.json").is_file()
    assert (output / ".docs/slice_dependency_tree.schema.json").is_file()
    assert not (output / ".docs/projects-registry.json").exists()
    assert (output / ".docs/examples/projects-registry.example.json").is_file()


def test_scrub_validator_allows_public_drake_examples(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("Drake documents the example-app fixture.\n", encoding="utf-8")

    assert validate_tree(tmp_path) == []


def test_scrub_validator_rejects_private_control_plane_markers(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    private_marker = "simon" + "-projects"
    notes.write_text(f"Do not export {private_marker} planning notes.\n", encoding="utf-8")

    assert validate_tree(tmp_path) == ["private control-plane marker in notes.md"]


def test_current_tree_passes_scrub_validator() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--tree", str(REPO_ROOT)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_hosted_ip_staging_check_requires_staging_host() -> None:
    result = subprocess.run(
        ["bash", "scripts/hosted-ip-staging.sh", "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "STAGING_HOST is required" in result.stderr


def test_hosted_ip_staging_check_prints_urls() -> None:
    result = subprocess.run(
        ["bash", "scripts/hosted-ip-staging.sh", "--check"],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "STAGING_HOST": "203.0.113.10",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "web: http://203.0.113.10:3000" in result.stdout
    assert "api: http://203.0.113.10:8000" in result.stdout
    assert "HOSTED_WEB_ORIGIN=http://203.0.113.10:3000" in result.stdout
    assert "NEXT_PUBLIC_API_URL=http://203.0.113.10:8000" in result.stdout
    assert "HOSTED_STAGING_MODE=production" in result.stdout
    assert "HTTP-only and unauthenticated" in result.stdout


def test_hosted_ip_staging_print_launch_uses_overrides() -> None:
    result = subprocess.run(
        ["bash", "scripts/hosted-ip-staging.sh", "--print-launch"],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "STAGING_HOST": "203.0.113.10",
            "HOSTED_API_PORT": "18000",
            "HOSTED_WEB_PORT": "13000",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "HOSTED_API_HOST=0.0.0.0" in result.stdout
    assert "HOSTED_WEB_HOST=0.0.0.0" in result.stdout
    assert "HOSTED_WEB_ORIGIN=http://203.0.113.10:13000" in result.stdout
    assert "NEXT_PUBLIC_API_URL=http://203.0.113.10:18000" in result.stdout
    assert "HOSTED_STAGING_MODE=production" in result.stdout
    assert "bash scripts/hosted-ip-staging.sh --run" in result.stdout


def test_hosted_ip_staging_print_smoke_outputs_review_commands() -> None:
    result = subprocess.run(
        ["bash", "scripts/hosted-ip-staging.sh", "--print-smoke"],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "STAGING_HOST": "203.0.113.10",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "curl http://203.0.113.10:8000/health" in result.stdout
    assert "curl http://203.0.113.10:8000/api/v1/portfolio" in result.stdout
    assert "open http://203.0.113.10:3000" in result.stdout
    assert "bash scripts/hosted-ip-staging.sh --smoke" in result.stdout


def test_hosted_ip_staging_smoke_checks_api_and_web() -> None:
    api_port = free_port()
    web_port = free_port()

    with fake_hosted_server(api_port, api=True), fake_hosted_server(web_port, api=False):
        result = subprocess.run(
            ["bash", "scripts/hosted-ip-staging.sh", "--smoke"],
            cwd=REPO_ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "STAGING_HOST": "127.0.0.1",
                "HOSTED_API_PORT": str(api_port),
                "HOSTED_WEB_PORT": str(web_port),
                "HOSTED_SMOKE_TIMEOUT": "2",
            },
            text=True,
            capture_output=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr or result.stdout
    assert f"smoke ok: http://127.0.0.1:{api_port}/health" in result.stdout
    assert f"smoke ok: http://127.0.0.1:{api_port}/api/v1/portfolio" in result.stdout
    assert f"smoke ok: http://127.0.0.1:{web_port}" in result.stdout


def test_hosted_ip_staging_smoke_fails_when_api_is_unreachable() -> None:
    api_port = free_port()
    web_port = free_port()

    with fake_hosted_server(web_port, api=False):
        result = subprocess.run(
            ["bash", "scripts/hosted-ip-staging.sh", "--smoke"],
            cwd=REPO_ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "STAGING_HOST": "127.0.0.1",
                "HOSTED_API_PORT": str(api_port),
                "HOSTED_WEB_PORT": str(web_port),
                "HOSTED_SMOKE_TIMEOUT": "1",
            },
            text=True,
            capture_output=True,
            check=False,
        )

    assert result.returncode == 1
    assert "/health failed" in result.stderr


def test_hosted_ip_staging_rejects_unknown_mode() -> None:
    result = subprocess.run(
        ["bash", "scripts/hosted-ip-staging.sh", "--check"],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "STAGING_HOST": "203.0.113.10",
            "HOSTED_STAGING_MODE": "debug",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "HOSTED_STAGING_MODE must be production or dev" in result.stderr
