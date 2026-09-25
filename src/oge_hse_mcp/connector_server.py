from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from oge_hse_mcp import server
from oge_hse_mcp.auth import EntraTokenConfig, EntraTokenVerifier, normalize_site_ids
from oge_hse_mcp.config import get_settings

_SERVER_INSTRUCTIONS = (
    "Use these read-only tools for HSE incident records, procedures, safety requirements, and lessons learned. "
    "Use search_incidents for requests to find, list, filter, count, or summarize incidents. "
    "Use search_hse_knowledge for broader questions that may require both procedures and incident lessons. "
    "Site access is derived from the signed-in user's delegated identity."
)
_READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _transport_security(resource_url: str | None) -> TransportSecuritySettings:
    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    if resource_url:
        hostname = urlsplit(resource_url).hostname
        if not hostname:
            raise ValueError("HSE_ENTRA_RESOURCE_URL must be an absolute URL.")
        allowed_hosts.extend([hostname, f"{hostname}:*"])
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
    )


def _build_mcp() -> FastMCP:
    settings = get_settings()
    if not settings.require_auth:
        return FastMCP(
            "oge-hse-connector",
            instructions=_SERVER_INSTRUCTIONS,
            transport_security=_transport_security(settings.resource_url),
        )
    if not all((settings.tenant_id, settings.audience, settings.issuer, settings.resource_url)):
        raise ValueError(
            "HSE_ENTRA_TENANT_ID, HSE_ENTRA_AUDIENCE, HSE_ENTRA_ISSUER, and HSE_ENTRA_RESOURCE_URL "
            "must be set when HSE_REQUIRE_AUTH=true."
        )
    audiences = tuple(dict.fromkeys([settings.audience, *settings.additional_audiences]))
    config = EntraTokenConfig(settings.tenant_id, audiences, settings.issuer)
    return FastMCP(
        "oge-hse-connector",
        instructions=_SERVER_INSTRUCTIONS,
        token_verifier=EntraTokenVerifier(config),
        auth=AuthSettings(
            issuer_url=settings.issuer,
            resource_server_url=settings.resource_url,
            required_scopes=settings.read_scopes,
        ),
        transport_security=_transport_security(settings.resource_url),
    )


mcp = _build_mcp()


def _authorized_sites(requested_site_ids: list[str] | None = None) -> list[str]:
    settings = get_settings()
    requested = normalize_site_ids(requested_site_ids)
    if not settings.require_auth:
        return requested

    access_token = get_access_token()
    if access_token is None:
        raise ValueError("Authenticated request context is required.")
    token_sites = normalize_site_ids((access_token.claims or {}).get(settings.site_claim))
    unauthorized = sorted(set(requested) - set(token_sites))
    if unauthorized:
        raise ValueError(f"Requested site scope is not authorized: {unauthorized}")
    return requested or token_sites


@mcp.tool(annotations=_READ_ONLY_TOOL, structured_output=False)
def search_procedures(
    query: str = "",
    category: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    """Find or list HSE procedures by text, category, or site; returns procedure details and revision metadata."""
    return server.search_procedures(query, _authorized_sites(), category, limit)


@mcp.tool(annotations=_READ_ONLY_TOOL, structured_output=False)
def get_procedure(procedure_id: str) -> dict[str, Any]:
    """Retrieve the full current HSE procedure for a known procedure ID when the signed-in user is authorized."""
    return server.get_procedure(procedure_id, _authorized_sites())


@mcp.tool(annotations=_READ_ONLY_TOOL, structured_output=False)
def search_incidents(
    query: str = "",
    severity: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    """Find, list, filter, count, or summarize authorized HSE incidents; returns matching total_count plus incident details."""
    return server.search_incidents(query, _authorized_sites(), severity, limit)


@mcp.tool(annotations=_READ_ONLY_TOOL, structured_output=False)
def search_hse_knowledge(
    query: str,
    limit: int = 0,
) -> dict[str, Any]:
    """Answer broad HSE questions with relevant authorized procedures and incident lessons plus grounding URLs."""
    return server.search_hse_knowledge(query, _authorized_sites(), limit)


def main() -> None:
    transport = os.getenv("HSE_MCP_TRANSPORT", "streamable-http").strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError("HSE_MCP_TRANSPORT must be one of: stdio, sse, streamable-http")
    mcp.settings.host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
