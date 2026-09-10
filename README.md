# OGE HSE MCP demonstration

This repository provisions an Entra-protected, read-only remote MCP server containing fictitious HSE procedures and incidents. It is a demonstration only; none of the records are operational safety guidance.

## Local validation

1. Copy `.env.example` to `.env` and set the variables.
2. Install with `py -m pip install -e ".[dev]"`.
3. Run `oge-hse-seed`.
4. Run tests with `py -m pytest -q`.

## Azure provisioning

The script reads deployment-specific values only from `.env`:

```powershell
.\scripts\provision.ps1
```

It creates the resource API registration when needed, provisions Azure Container Apps and Azure Container Registry, builds the image in ACR, and prints the MCP URL and resource API scope. It does not grant tenant-wide consent or create Microsoft 365 integrations; those are explicit administrator review steps described in [docs/microsoft-365-integration.md](docs/microsoft-365-integration.md).

Remove all demonstration Azure resources and the Entra app registration with `.\scripts\remove.ps1`.

## MCP tools

- `search_hse_knowledge`: Search procedures and incident lessons with grounding metadata.
- `search_procedures`: Search global and site-authorized HSE procedures.
- `get_procedure`: Retrieve one authorized procedure.
- `search_incidents`: Search fictitious incidents for authorized sites.

Authorization is fail-closed. The HTTP bearer token is validated for signature, issuer, audience, expiry, and required delegated scope. Site access comes from the configured claim named by `HSE_ENTRA_SITE_CLAIM`; a tool argument can't expand that scope.

## Microsoft 365 integration paths

- [Copilot Studio custom connector with OBO OAuth](docs/copilot-studio-custom-connector-obo.md): bind the MCP server to a specific HSE agent while preserving delegated user identity.
- [Microsoft 365 federated connector](docs/m365-federated-connector.md): expose live, read-only HSE retrieval through a tenant-local connector in supported Microsoft 365 Copilot experiences.
- [Architecture and rollout comparison](docs/microsoft-365-integration.md): compare the agent-specific and tenant-local federated paths.
