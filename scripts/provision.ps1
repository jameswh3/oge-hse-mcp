$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

function Import-DotEnv([string]$Path) {
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            $name, $value = $line -split '=', 2
            [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
        }
    }
}

Import-DotEnv (Join-Path $PSScriptRoot '..\.env')

$required = @('AZURE_SUBSCRIPTION_ID', 'AZURE_TENANT_ID', 'AZURE_LOCATION', 'AZURE_RESOURCE_GROUP', 'AZURE_ENVIRONMENT_NAME', 'HSE_ENTRA_APP_DISPLAY_NAME', 'HSE_CONTAINER_IMAGE_TAG', 'HSE_ENTRA_ADDITIONAL_AUDIENCES', 'HSE_SOURCE_ITEM_BASE_URL')
foreach ($name in $required) {
    if (-not [Environment]::GetEnvironmentVariable($name, 'Process')) {
        throw "Missing required .env variable: $name"
    }
}

az account set --subscription $env:AZURE_SUBSCRIPTION_ID
az group create --name $env:AZURE_RESOURCE_GROUP --location $env:AZURE_LOCATION --output none

$appId = az ad app list --display-name $env:HSE_ENTRA_APP_DISPLAY_NAME --query '[0].appId' --output tsv
if (-not $appId) {
    $appId = az ad app create --display-name $env:HSE_ENTRA_APP_DISPLAY_NAME --sign-in-audience AzureADMyOrg --query appId --output tsv
    az ad app update --id $appId --identifier-uris "api://$appId"
}

$application = az ad app show --id $appId --query '{id:id,scopes:api.oauth2PermissionScopes,appRoles:appRoles}' --output json | ConvertFrom-Json
if (-not $application.scopes) {
    $scope = @{
        api = @{
            oauth2PermissionScopes = @(@{
        adminConsentDescription = 'Read HSE safety procedures and fictitious incidents as the signed-in user.'
        adminConsentDisplayName = 'Read HSE knowledge'
                id = [guid]::NewGuid().ToString()
        isEnabled = $true
        type = 'User'
        userConsentDescription = 'Read HSE safety procedures and fictitious incidents on your behalf.'
        userConsentDisplayName = 'Read HSE knowledge'
        value = 'hse.read'
            })
        }
    } | ConvertTo-Json -Depth 5 -Compress
    $scopePath = 'C:\temp\oge-hse-mcp-scope.json'
    New-Item -ItemType Directory -Path (Split-Path $scopePath) -Force | Out-Null
    [System.IO.File]::WriteAllText($scopePath, $scope)
    try {
        az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$($application.id)" --headers 'Content-Type=application/json' --body "@$scopePath" --output none
    }
    finally {
        Remove-Item $scopePath -Force -ErrorAction SilentlyContinue
    }
}

$requiredSiteRoles = @(
    @{ value = 'DEMO-GULF'; displayName = 'DEMO-GULF site reader'; description = 'Read HSE content for the DEMO-GULF site.' },
    @{ value = 'DEMO-PERMIAN'; displayName = 'DEMO-PERMIAN site reader'; description = 'Read HSE content for the DEMO-PERMIAN site.' }
)
$appRoles = @($application.appRoles)
$rolesChanged = $false
foreach ($requiredRole in $requiredSiteRoles) {
    if ($requiredRole.value -notin $appRoles.value) {
        $appRoles += @{
            allowedMemberTypes = @('User')
            description = $requiredRole.description
            displayName = $requiredRole.displayName
            id = [guid]::NewGuid().ToString()
            isEnabled = $true
            value = $requiredRole.value
        }
        $rolesChanged = $true
    }
}
if ($rolesChanged) {
    $rolesPayload = @{ appRoles = $appRoles } | ConvertTo-Json -Depth 5 -Compress
    $rolesPath = 'C:\temp\oge-hse-mcp-app-roles.json'
    [System.IO.File]::WriteAllText($rolesPath, $rolesPayload)
    try {
        az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$($application.id)" --headers 'Content-Type=application/json' --body "@$rolesPath" --output none
    }
    finally {
        Remove-Item $rolesPath -Force -ErrorAction SilentlyContinue
    }
}

$resourceTagsJson = if ($env:HSE_RESOURCE_TAGS_JSON) {
    $env:HSE_RESOURCE_TAGS_JSON | ConvertFrom-Json -AsHashtable | ConvertTo-Json -Compress
}
else {
    '{}'
}

$foundation = az deployment group create --resource-group $env:AZURE_RESOURCE_GROUP --template-file (Join-Path $PSScriptRoot '..\infra\foundation.bicep') --parameters environmentName=$env:AZURE_ENVIRONMENT_NAME location=$env:AZURE_LOCATION resourceTags=$resourceTagsJson --query properties.outputs --output json | ConvertFrom-Json
$registryName = $foundation.registryName.value
$loginServer = $foundation.registryLoginServer.value
$imageTag = "$($env:HSE_CONTAINER_IMAGE_TAG)-$(Get-Date -Format 'yyyyMMddHHmmss')"
$image = "$loginServer/oge-hse-mcp:$imageTag"

az acr build --registry $registryName --image "oge-hse-mcp:$imageTag" --no-logs --no-wait (Join-Path $PSScriptRoot '..') | Out-Null
for ($attempt = 1; $attempt -le 120; $attempt++) {
    Start-Sleep -Seconds 5
    $builtTag = az acr repository show-tags --name $registryName --repository oge-hse-mcp --query "[?@=='$imageTag'] | [0]" --output tsv
    if ($builtTag -eq $imageTag) {
        break
    }
}
if ($builtTag -ne $imageTag) {
    throw "ACR image tag '$imageTag' was not available after 10 minutes."
}

$deployment = az deployment group create --resource-group $env:AZURE_RESOURCE_GROUP --template-file (Join-Path $PSScriptRoot '..\infra\main.bicep') --parameters environmentName=$env:AZURE_ENVIRONMENT_NAME location=$env:AZURE_LOCATION resourceTags=$resourceTagsJson managedEnvironmentName=$($foundation.managedEnvironmentName.value) registryName=$registryName containerImage=$image entraTenantId=$env:AZURE_TENANT_ID entraAudience=$appId entraAdditionalAudiences=$env:HSE_ENTRA_ADDITIONAL_AUDIENCES entraSiteClaim=$env:HSE_ENTRA_SITE_CLAIM entraReadScopes=$env:HSE_ENTRA_READ_SCOPES sourceItemBaseUrl=$env:HSE_SOURCE_ITEM_BASE_URL --query properties.outputs --output json | ConvertFrom-Json

Write-Host "HSE_ENTRA_AUDIENCE=$appId"
Write-Host "HSE MCP URL=$($deployment.mcpUrl.value)"
Write-Host "Resource API scope=$($deployment.resourceScope.value)"
