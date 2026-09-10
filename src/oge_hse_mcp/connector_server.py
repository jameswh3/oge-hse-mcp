from __future__ import annotations

import os
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from oge_hse_mcp import server
from oge_hse_mcp.auth import EntraTokenConfig, EntraTokenVerifier, normalize_site_ids
from oge_hse_mcp.config import get_settings


def _build_mcp() -> FastMCP:
    settings = get_settings()
    if not settings.require_auth:
        return FastMCP("oge-hse-connector")
    if not all((settings.tenant_id, settings.audience, settings.issuer, settings.resource_url)):
        raise ValueError(
            "HSE_ENTRA_TENANT_ID, HSE_ENTRA_AUDIENCE, HSE_ENTRA_ISSUER, and HSE_ENTRA_RESOURCE_URL "
            "must be set when HSE_REQUIRE_AUTH=true."
        )
    audiences = tuple(dict.fromkeys([settings.audience, *settings.additional_audiences]))
    config = EntraTokenConfig(settings.tenant_id, audiences, settings.issuer)
    return FastMCP(
        "oge-hse-connector",
        token_verifier=EntraTokenVerifier(config),
        auth=AuthSettings(
            issuer_url=settings.issuer,
            resource_server_url=settings.resource_url,
            required_scopes=settings.read_scopes,
        ),
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


@mcp.tool()
def search_procedures(
    query: str | None = None,
    site_ids: list[str] | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search HSE procedures using the signed-in user's authorized site scope."""
    return server.search_procedures(query, _authorized_sites(site_ids), category, limit)


@mcp.tool()
def get_procedure(procedure_id: str, site_ids: list[str] | None = None) -> dict[str, Any]:
    """Get an HSE procedure using the signed-in user's authorized site scope."""
    return server.get_procedure(procedure_id, _authorized_sites(site_ids))


@mcp.tool()
def search_incidents(
    query: str | None = None,
    site_ids: list[str] | None = None,
    severity: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search fictitious incidents using the signed-in user's authorized site scope."""
    return server.search_incidents(query, _authorized_sites(site_ids), severity, limit)


@mcp.tool()
def search_hse_knowledge(
    query: str,
    site_ids: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search HSE procedures and incident lessons using the signed-in user's site scope."""
    return server.search_hse_knowledge(query, _authorized_sites(site_ids), limit)


def main() -> None:
    transport = os.getenv("HSE_MCP_TRANSPORT", "streamable-http").strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError("HSE_MCP_TRANSPORT must be one of: stdio, sse, streamable-http")
    mcp.settings.host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
