# Microsoft 365 Copilot integration position

Validated against Microsoft Learn pages updated through August 27, 2026. Reconfirm preview status and connector availability before production rollout.

## Architecture conclusion

There are two distinct Microsoft integration paths for this server.

1. **Copilot Studio custom connector with OBO:** Bind the MCP server to a specific agent through an OAuth custom connector. Publish the agent to Teams and Microsoft 365 Copilot. See [Copilot Studio custom connector with OBO OAuth](copilot-studio-custom-connector-obo.md).
2. **Microsoft 365 federated connector:** Register the server as a tenant-local, read-only connector for live grounding in supported Microsoft 365 experiences. Microsoft documents Copilot Chat, Excel, Researcher, and Cowork. An admin creates and stages the connector from the Copilot Connectors Gallery. See [Microsoft 365 Copilot federated connector](m365-federated-connector.md).

## Discovery and invocation

In the Copilot Studio path, tools are dynamically available only inside the configured agent. Users install or select that agent and can invoke it with `@` in Microsoft 365 Copilot. In the federated path, a user connects the admin-enabled HSE source under Copilot **Settings > Sources** and Microsoft 365 can dynamically invoke its retrieval tools in supported experiences.

## Delegated identity flow

All paths use the HSE resource app's delegated authorization contract, but client registration and token acquisition differ.

1. Expose delegated scope `hse.read` on the Entra resource app whose client ID is `HSE_ENTRA_AUDIENCE`.
2. Configure the custom or federated connector to request `api://<HSE_ENTRA_AUDIENCE>/hse.read`.
3. The user signs in or consents. The client obtains an access token for the HSE API and sends it as `Authorization: Bearer` to the `/mcp` endpoint.
4. The server validates issuer from `HSE_ENTRA_ISSUER`, audience from `HSE_ENTRA_AUDIENCE`, required scope from `HSE_ENTRA_READ_SCOPES`, and authorization attributes from `HSE_ENTRA_SITE_CLAIM`.

Do not pass an access token as an MCP tool parameter. Do not use an app-only identity when HMS requires per-user authorization. The demo expects the site claim to be emitted in the access token; in production, use Entra app roles/groups or query the HMS entitlement store by the validated `oid` when token group overage or frequently changing permissions make custom claims unsuitable.

## Tenant controls and roles

- Approval plus tenant-wide consent requires **AI Administrator** or **Global Administrator**. Prefer AI Administrator.
- Copilot Studio uses Power Platform connectors, environments, solutions, connection references, and data policies. Apply DLP policy to govern the MCP connector.
- Federated connectors are enabled and staged from **Microsoft 365 admin center > Copilot connectors**. Users then connect the source through Copilot settings. Microsoft Purview provides connector activity auditing.
- Agent publishing requires maker access to Copilot Studio and permission to publish to the Teams and Microsoft 365 Copilot channel. Admins approve organizational distribution and can target users/groups through app policies.
- Agent availability can be limited to one shared user first, then selected groups, then the organization.
- Licensing is workload- and tenant-specific. Confirm Microsoft 365 Copilot user entitlement and Copilot Studio capacity/licensing with the tenant licensing administrator; current setup articles require intended users to be able to use Microsoft 365 Copilot but don't establish a universal SKU matrix for this combined scenario.

## Recommended Dev POC

1. Deploy this server in a nonproduction Azure subscription with fictitious data and `HSE_REQUIRE_AUTH=true`.
2. Add one pilot user's `site_ids` claim and grant/admin-consent only `hse.read`.
3. Implement the Copilot Studio path from its runbook and validate the pilot user's OBO token and site boundaries.
4. In parallel, validate the federated endpoint contract. Create the tenant-local connector and enable it only for the pilot group.
5. Compare explicit HSE agent use with direct HSE source grounding. Test allowed and denied sites, token expiry, missing claims, citations, audit logs, and prompt-injection handling.
6. Promote through staged Entra groups after HSE, security, privacy, records, Power Platform, and Microsoft 365 administrators approve.

## Current product status

| Capability | Status / current name |
| --- | --- |
| MCP tools and resources in Copilot Studio | Supported; Streamable HTTP only; generative orchestration required |
| Copilot Studio agent published to Microsoft 365 Copilot | Supported |
| Explicit agent install, selection, and `@` invocation | Supported and documented |
| Tenant-local federated connector in Copilot Chat, Excel, Researcher, and Cowork | Supported; connector-specific and subject to tenant availability |
| Live read-only MCP retrieval without Graph indexing | Supported by federated connectors |

## Microsoft sources

- [Manage tools for agents in Microsoft 365 admin center](https://learn.microsoft.com/microsoft-365/admin/manage/manage-tools-for-agent) (updated August 21, 2026)
- [Federated connectors overview](https://learn.microsoft.com/microsoft-365/copilot/connectors/federated-connectors-overview) (updated August 27, 2026)
- [Manage Microsoft 365 Copilot connectors](https://learn.microsoft.com/microsoft-365/admin/manage/manage-copilot-connectors) (updated August 21, 2026)
- [Configure OBO authentication for custom connectors](https://learn.microsoft.com/microsoft-copilot-studio/advanced-custom-connector-on-behalf-of)
- [Connect your agent to an existing MCP server](https://learn.microsoft.com/microsoft-copilot-studio/mcp-add-existing-server-to-agent) (updated August 19, 2026)
- [Extend your agent with Model Context Protocol](https://learn.microsoft.com/microsoft-copilot-studio/agent-extend-action-mcp) (updated August 26, 2026)
- [Connect an agent to Teams and Microsoft 365 Copilot](https://learn.microsoft.com/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams) (updated August 17, 2026)
- [Configure user authentication](https://learn.microsoft.com/microsoft-copilot-studio/configuration-end-user-authentication) (updated July 21, 2026)
- [Publish and deploy your agent](https://learn.microsoft.com/microsoft-copilot-studio/publication-fundamentals-publish-channels) (updated August 19, 2026)
