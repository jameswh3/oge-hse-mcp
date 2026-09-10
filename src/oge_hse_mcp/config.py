from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    source_item_base_url: str
    default_search_limit: int
    max_search_limit: int
    require_auth: bool
    tenant_id: str | None
    audience: str | None
    additional_audiences: list[str]
    issuer: str | None
    resource_url: str | None
    site_claim: str
    read_scopes: list[str]


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean; received '{value}'.")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer; received '{value}'.") from exc
    if parsed < 1:
        raise ValueError(f"{name} must be >= 1; received '{parsed}'.")
    return parsed


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("HSE_DATABASE_URL", "sqlite:///./hse_demo.db"),
        source_item_base_url=os.getenv("HSE_SOURCE_ITEM_BASE_URL", "https://hse.example.invalid/records"),
        default_search_limit=_get_int("HSE_DEFAULT_SEARCH_LIMIT", 10),
        max_search_limit=_get_int("HSE_MAX_SEARCH_LIMIT", 50),
        require_auth=_get_bool("HSE_REQUIRE_AUTH", False),
        tenant_id=os.getenv("HSE_ENTRA_TENANT_ID"),
        audience=os.getenv("HSE_ENTRA_AUDIENCE"),
        additional_audiences=sorted(set(os.getenv("HSE_ENTRA_ADDITIONAL_AUDIENCES", "").split())),
        issuer=os.getenv("HSE_ENTRA_ISSUER"),
        resource_url=os.getenv("HSE_ENTRA_RESOURCE_URL"),
        site_claim=os.getenv("HSE_ENTRA_SITE_CLAIM", "site_ids"),
        read_scopes=sorted(set(os.getenv("HSE_ENTRA_READ_SCOPES", "hse.read").split())),
    )
