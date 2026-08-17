"""HTTP client for the saimon 6-core-MCP platform.

The saimon platform exposes a set of JSON-over-HTTP MCP services (search,
verify, generate, export, evaluate) guarded by the ``X-Saimon-API-Key`` header.
This client is the single choke point through which the Drake lifecycle talks
to saimon, so auth, request shape, and error semantics live here once.
"""

from __future__ import annotations

from typing import Any

import httpx

# Saimon MCP tool routes (relative to the configured service base URL).
HEALTH_PATH = "/health"
SEARCH_TOOL_PATH = "/tools/search_knowledge_graph"
VERIFY_TOOL_PATH = "/tools/verify_claim"
GENERATE_TOOL_PATH = "/tools/generate_content"
EXPORT_TOOL_PATH = "/tools/export_content"
EVALUATE_TOOL_PATH = "/tools/evaluate_content"

# Default auth header used by the saimon MCP platform.
DEFAULT_HEADER_NAME = "X-Saimon-API-Key"


class SaimonError(Exception):
    """Base error for saimon client failures."""


class SaimonUnreachableError(SaimonError):
    """Raised when the saimon platform cannot be reached."""


class SaimonClient:
    """Minimal authenticated client for saimon search/verify/generate."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        header_name: str = DEFAULT_HEADER_NAME,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.header_name = header_name
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SaimonClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {self.header_name: self.api_key}

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        try:
            response = self._client.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            raise SaimonUnreachableError(
                f"saimon unreachable at {self.base_url}: {exc}"
            ) from exc
        if response.status_code >= 400:
            detail = response.text[:200]
            raise SaimonError(
                f"saimon {path} failed ({response.status_code}): {detail}"
            )
        return response.json()

    def health(self) -> dict[str, Any]:
        """Return the saimon service health payload."""
        try:
            response = self._client.get(f"{self.base_url}{HEALTH_PATH}")
        except httpx.HTTPError as exc:
            raise SaimonUnreachableError(
                f"saimon unreachable at {self.base_url}: {exc}"
            ) from exc
        if response.status_code >= 400:
            raise SaimonError(
                f"saimon health check failed ({response.status_code})"
            )
        return response.json()

    def search(self, query: str, **kwargs: Any) -> Any:
        """Search the saimon knowledge graph / shadow sources."""
        payload: dict[str, Any] = {"query": query, **kwargs}
        return self._post(SEARCH_TOOL_PATH, payload)

    def verify(self, claim: str, **kwargs: Any) -> Any:
        """Verify a claim against the saimon knowledge graph."""
        payload = {"claim": claim, **kwargs}
        return self._post(VERIFY_TOOL_PATH, payload)

    def generate(
        self,
        content: str,
        content_type: str = "decision_record",
        **kwargs: Any,
    ) -> Any:
        """Generate content (e.g. a decision record) via saimon."""
        payload = {"content": content, "content_type": content_type, **kwargs}
        return self._post(GENERATE_TOOL_PATH, payload)

    def evaluate(
        self,
        content: str,
        criteria: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Evaluate content against quality criteria (e.g. consistency)."""
        payload: dict[str, Any] = {"content": content}
        if criteria is not None:
            payload["criteria"] = criteria
        payload.update(kwargs)
        return self._post(EVALUATE_TOOL_PATH, payload)

    def export(
        self,
        content: str,
        format: str = "markdown",
        **kwargs: Any,
    ) -> Any:
        """Export content in a requested format (e.g. task_context as markdown)."""
        payload = {"content": content, "format": format, **kwargs}
        return self._post(EXPORT_TOOL_PATH, payload)
