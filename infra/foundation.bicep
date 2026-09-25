targetScope = 'resourceGroup'

@description('Azure region for the demonstration resources.')
param location string = resourceGroup().location

@description('Short environment label used in resource names.')
param environmentName string

@description('Optional resource tags supplied by the deployment environment.')
param resourceTags object = {}

var suffix = substring(uniqueString(resourceGroup().id, environmentName), 0, 8)
var logAnalyticsName = 'log-hse-${environmentName}-${suffix}'
var managedEnvironmentName = 'cae-hse-${environmentName}-${suffix}'
var registryName = toLower('acrhse${environmentName}${suffix}')

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: resourceTags
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: managedEnvironmentName
  location: location
  tags: resourceTags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: resourceTags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output managedEnvironmentName string = managedEnvironment.name
output managedEnvironmentDomain string = managedEnvironment.properties.defaultDomain
output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
