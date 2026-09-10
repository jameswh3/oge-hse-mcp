from __future__ import annotations

import asyncio
import json
import re
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken


@dataclass(frozen=True)
class EntraTokenConfig:
    tenant_id: str
    audiences: tuple[str, ...]
    issuer: str


def normalize_site_ids(raw: Any) -> list[str]:
    if isinstance(raw, str):
        values = re.split(r"[;,\s]+", raw)
    elif isinstance(raw, list):
        values = [item for item in raw if isinstance(item, str)]
    else:
        values = []
    return sorted({value.strip().upper() for value in values if value.strip()})


def _normalize_scopes(raw: Any) -> list[str]:
    return sorted(set(raw.split())) if isinstance(raw, str) else []


@lru_cache(maxsize=8)
def _openid_configuration(tenant_id: str) -> dict[str, Any]:
    url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class EntraTokenVerifier:
    def __init__(self, config: EntraTokenConfig):
        self._config = config
        self._jwks = PyJWKClient(_openid_configuration(config.tenant_id)["jwks_uri"])

    def _validate(self, token: str) -> dict[str, Any]:
        signing_key = self._jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self._config.audiences,
            issuer=self._config.issuer,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = await asyncio.to_thread(self._validate, token)
        except (jwt.PyJWTError, ValueError):
            return None

        object_id = claims.get("oid")
        client_id = claims.get("azp") or claims.get("appid")
        if not object_id or not client_id:
            return None
        return AccessToken(
            token=token,
            client_id=str(client_id),
            scopes=_normalize_scopes(claims.get("scp")),
            expires_at=claims.get("exp"),
            resource=str(claims.get("aud", "")),
            subject=str(object_id),
            claims=claims,
        )
