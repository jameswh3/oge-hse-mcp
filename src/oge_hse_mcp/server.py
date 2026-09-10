from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_, select

from oge_hse_mcp.config import get_settings
from oge_hse_mcp.db import session_scope
from oge_hse_mcp.models import Incident, Procedure

mcp = FastMCP("oge-hse")


def _normalize_sites(site_ids: list[str] | None) -> list[str]:
    return sorted({site.strip().upper() for site in site_ids or [] if site and site.strip()})


def _procedure_dict(procedure: Procedure) -> dict[str, Any]:
    return {
        "id": procedure.id,
        "title": procedure.title,
        "summary": procedure.summary,
        "content": procedure.content,
        "category": procedure.category,
        "site_id": procedure.site_id,
        "revision": procedure.revision,
        "effective_date": procedure.effective_date,
        "owner": procedure.owner,
    }


def _incident_dict(incident: Incident) -> dict[str, Any]:
    return {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "lesson_learned": incident.lesson_learned,
        "severity": incident.severity,
        "status": incident.status,
        "site_id": incident.site_id,
        "occurred_at": incident.occurred_at,
    }


@mcp.tool()
def search_procedures(
    query: str | None = None,
    site_ids: list[str] | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search current HSE procedures in the caller's authorized site scope."""
    settings = get_settings()
    effective_limit = limit or settings.default_search_limit
    if effective_limit > settings.max_search_limit:
        raise ValueError(f"limit cannot exceed HSE_MAX_SEARCH_LIMIT ({settings.max_search_limit}).")

    allowed_sites = _normalize_sites(site_ids)
    with session_scope() as session:
        statement = select(Procedure).order_by(Procedure.title).limit(effective_limit)
        if allowed_sites:
            statement = statement.where(or_(Procedure.site_id.is_(None), Procedure.site_id.in_(allowed_sites)))
        else:
            statement = statement.where(Procedure.site_id.is_(None))
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(Procedure.title.ilike(pattern), Procedure.summary.ilike(pattern), Procedure.content.ilike(pattern))
            )
        if category:
            statement = statement.where(Procedure.category == category.strip().lower())
        return {"procedures": [_procedure_dict(item) for item in session.scalars(statement).all()]}


@mcp.tool()
def get_procedure(procedure_id: str, site_ids: list[str] | None = None) -> dict[str, Any]:
    """Get one HSE procedure when it is global or in the caller's authorized site scope."""
    allowed_sites = _normalize_sites(site_ids)
    with session_scope() as session:
        procedure = session.get(Procedure, procedure_id)
        if procedure is None:
            raise ValueError(f"Procedure not found: '{procedure_id}'.")
        if procedure.site_id is not None and procedure.site_id not in allowed_sites:
            raise ValueError(f"Procedure '{procedure_id}' is outside the authorized site scope.")
        return {"procedure": _procedure_dict(procedure)}


@mcp.tool()
def search_incidents(
    query: str | None = None,
    site_ids: list[str] | None = None,
    severity: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search fictitious HSE incidents in the caller's authorized site scope."""
    settings = get_settings()
    effective_limit = limit or settings.default_search_limit
    if effective_limit > settings.max_search_limit:
        raise ValueError(f"limit cannot exceed HSE_MAX_SEARCH_LIMIT ({settings.max_search_limit}).")

    allowed_sites = _normalize_sites(site_ids)
    if not allowed_sites:
        return {"incidents": []}
    with session_scope() as session:
        statement = select(Incident).where(Incident.site_id.in_(allowed_sites)).order_by(Incident.occurred_at.desc())
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(or_(Incident.title.ilike(pattern), Incident.description.ilike(pattern)))
        if severity:
            statement = statement.where(Incident.severity == severity.strip().lower())
        statement = statement.limit(effective_limit)
        return {"incidents": [_incident_dict(item) for item in session.scalars(statement).all()]}


@mcp.tool()
def search_hse_knowledge(
    query: str,
    site_ids: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search current HSE procedures and incident lessons for grounded answers."""
    if not query.strip():
        raise ValueError("query is required.")

    settings = get_settings()
    effective_limit = limit or settings.default_search_limit
    procedures = search_procedures(query=query, site_ids=site_ids, limit=effective_limit)["procedures"]
    incidents = search_incidents(query=query, site_ids=site_ids, limit=effective_limit)["incidents"]
    results = [
        {
            "record_type": "procedure",
            "id": item["id"],
            "title": item["title"],
            "content": item["content"],
            "site_id": item["site_id"],
            "revision": item["revision"],
            "source_url": f"{settings.source_item_base_url.rstrip('/')}/procedures/{item['id']}",
        }
        for item in procedures
    ]
    results.extend(
        {
            "record_type": "incident",
            "id": item["id"],
            "title": item["title"],
            "content": f"{item['description']} Lesson learned: {item['lesson_learned']}",
            "site_id": item["site_id"],
            "revision": None,
            "source_url": f"{settings.source_item_base_url.rstrip('/')}/incidents/{item['id']}",
        }
        for item in incidents
    )
    return {"query": query.strip(), "results": results[:effective_limit]}


def main() -> None:
    transport = os.getenv("HSE_MCP_TRANSPORT", "stdio").strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError("HSE_MCP_TRANSPORT must be one of: stdio, sse, streamable-http")
    mcp.settings.host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
