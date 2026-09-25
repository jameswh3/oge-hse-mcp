targetScope = 'resourceGroup'

@description('Azure region for the demonstration resources.')
param location string = resourceGroup().location

@description('Short environment label used in resource names.')
param environmentName string

@description('Optional resource tags supplied by the deployment environment.')
param resourceTags object = {}

@description('Existing Container Apps managed environment name.')
param managedEnvironmentName string

@description('Existing Azure Container Registry name.')
param registryName string

@description('Fully qualified container image and tag.')
param containerImage string

@description('Microsoft Entra tenant ID accepted by the HSE resource API.')
param entraTenantId string

@description('Application client ID used as the HSE API token audience.')
param entraAudience string

@description('Additional space-delimited token audiences accepted by the HSE API.')
param entraAdditionalAudiences string = ''

@description('Claim containing authorized HSE site identifiers.')
param entraSiteClaim string = 'roles'

@description('Delegated scopes required by the HSE API.')
param entraReadScopes string = 'hse.read'

@description('Base URL used for procedure and incident citation links.')
param sourceItemBaseUrl string

var suffix = substring(uniqueString(resourceGroup().id, environmentName), 0, 8)
var appName = 'ca-hse-${environmentName}-${suffix}'
var connectorUrl = 'https://${appName}.${managedEnvironment.properties.defaultDomain}/mcp'

resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: managedEnvironmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-hse-${environmentName}-${suffix}'
  location: location
  tags: resourceTags
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, pullIdentity.id, 'AcrPull')
  scope: registry
  properties: {
    principalId: pullIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  tags: resourceTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: pullIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'hse-mcp'
          image: containerImage
          env: [
            { name: 'HSE_DATABASE_URL', value: 'sqlite:////data/hse_demo.db' }
            { name: 'HSE_DEFAULT_SEARCH_LIMIT', value: '10' }
            { name: 'HSE_MAX_SEARCH_LIMIT', value: '50' }
            { name: 'HSE_REQUIRE_AUTH', value: 'true' }
            { name: 'HSE_MCP_TRANSPORT', value: 'streamable-http' }
            { name: 'FASTMCP_HOST', value: '0.0.0.0' }
            { name: 'HSE_ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'HSE_ENTRA_AUDIENCE', value: entraAudience }
            { name: 'HSE_ENTRA_ADDITIONAL_AUDIENCES', value: entraAdditionalAudiences }
            { name: 'HSE_ENTRA_ISSUER', value: '${environment().authentication.loginEndpoint}${entraTenantId}/v2.0' }
            { name: 'HSE_ENTRA_RESOURCE_URL', value: connectorUrl }
            { name: 'HSE_ENTRA_SITE_CLAIM', value: entraSiteClaim }
            { name: 'HSE_ENTRA_READ_SCOPES', value: entraReadScopes }
            { name: 'HSE_SOURCE_ITEM_BASE_URL', value: sourceItemBaseUrl }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
  dependsOn: [acrPull]
}

output mcpUrl string = connectorUrl
output containerAppName string = app.name
output resourceScope string = 'api://${entraAudience}/.default'
