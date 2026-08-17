"""Saimon ↔ Drake integration bindings.

This package exposes a shared :class:`saimon.client.SaimonClient` plus
per-phase bindings (REFINE, DISPATCH, VERIFY, SYNC) that compose the saimon
6-core-MCP platform into the Drake slice lifecycle.

Saimon informs; the operator decides.
"""

from saimon.client import SaimonClient, SaimonError, SaimonUnreachableError

__all__ = ["SaimonClient", "SaimonError", "SaimonUnreachableError"]
