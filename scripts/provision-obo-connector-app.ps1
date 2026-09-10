$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

Get-Content (Join-Path $PSScriptRoot '..\.env') | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $name, $value = $line -split '=', 2
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
    }
}

$required = @('HSE_ENTRA_AUDIENCE', 'HSE_OBO_CONNECTOR_APP_DISPLAY_NAME')
foreach ($name in $required) {
    if (-not [Environment]::GetEnvironmentVariable($name, 'Process')) {
        throw "Missing required .env variable: $name"
    }
}

function Ensure-ServicePrincipal([string]$AppId) {
    $servicePrincipalId = az ad sp list --filter "appId eq '$AppId'" --query '[0].id' -o tsv
    if (-not $servicePrincipalId) {
        $servicePrincipalId = az ad sp create --id $AppId --query id -o tsv
    }
    return $servicePrincipalId
}

$resourceApp = az ad app show --id $env:HSE_ENTRA_AUDIENCE --query '{appId:appId,scopeId:api.oauth2PermissionScopes[?value==`hse.read`].id | [0]}' -o json | ConvertFrom-Json
if (-not $resourceApp.scopeId) {
    throw 'The HSE resource app does not expose hse.read.'
}

$connector = az ad app list --display-name $env:HSE_OBO_CONNECTOR_APP_DISPLAY_NAME --query '[0].{id:id,appId:appId}' -o json | ConvertFrom-Json
if (-not $connector) {
    $connector = az ad app create --display-name $env:HSE_OBO_CONNECTOR_APP_DISPLAY_NAME --sign-in-audience AzureADMyOrg --query '{id:id,appId:appId}' -o json | ConvertFrom-Json
}

$connectorScopeId = [guid]::NewGuid().ToString()
$existingScopeId = az ad app show --id $connector.appId --query 'api.oauth2PermissionScopes[?value==`access_as_user`].id | [0]' -o tsv
if ($existingScopeId) {
    $connectorScopeId = $existingScopeId
}

$permissionScope = @{
    id = $connectorScopeId
    value = 'access_as_user'
    type = 'User'
    isEnabled = $true
    adminConsentDisplayName = 'Allow Azure API Connections to obtain tokens on behalf of users'
    adminConsentDescription = 'Allows the HSE connector to obtain delegated tokens on behalf of signed-in users.'
    userConsentDisplayName = 'Use the HSE connector on your behalf'
    userConsentDescription = 'Allows the HSE connector to read authorized HSE knowledge on your behalf.'
}
$baseBody = @{
    identifierUris = @("api://$($connector.appId)")
    api = @{
        oauth2PermissionScopes = @($permissionScope)
    }
    requiredResourceAccess = @(@{
        resourceAppId = $resourceApp.appId
        resourceAccess = @(@{ id = $resourceApp.scopeId; type = 'Scope' })
    })
} | ConvertTo-Json -Depth 8
$completeBody = @{
    api = @{
        oauth2PermissionScopes = @($permissionScope)
        preAuthorizedApplications = @(@{
            appId = 'fe053c5f-3692-4f14-aef2-ee34fc081cae'
            delegatedPermissionIds = @($connectorScopeId)
        })
    }
} | ConvertTo-Json -Depth 8

$baseBodyPath = 'C:\temp\oge-hse-obo-connector-app-base.json'
$completeBodyPath = 'C:\temp\oge-hse-obo-connector-app-complete.json'
New-Item -ItemType Directory -Path (Split-Path $baseBodyPath) -Force | Out-Null
[System.IO.File]::WriteAllText($baseBodyPath, $baseBody)
[System.IO.File]::WriteAllText($completeBodyPath, $completeBody)
try {
    az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$($connector.id)" --headers 'Content-Type=application/json' --body "@$baseBodyPath" --output none
    az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$($connector.id)" --headers 'Content-Type=application/json' --body "@$completeBodyPath" --output none
}
finally {
    Remove-Item $baseBodyPath, $completeBodyPath -Force -ErrorAction SilentlyContinue
}

$resourceServicePrincipalId = Ensure-ServicePrincipal $resourceApp.appId
$connectorServicePrincipalId = Ensure-ServicePrincipal $connector.appId
az ad app permission admin-consent --id $connector.appId

$grantScope = az rest --method GET --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?`$filter=clientId eq '$connectorServicePrincipalId' and resourceId eq '$resourceServicePrincipalId'" --query 'value[0].scope' -o tsv
if (($grantScope -split ' ') -notcontains 'hse.read') {
    throw 'Tenant admin consent did not create the expected hse.read OAuth grant.'
}

if ($env:HSE_OBO_REDIRECT_URI) {
    az ad app update --id $connector.appId --web-redirect-uris $env:HSE_OBO_REDIRECT_URI
}

if ($env:HSE_OBO_MANAGED_IDENTITY_ISSUER -and $env:HSE_OBO_MANAGED_IDENTITY_SUBJECT) {
    $credential = @{
        name = 'power-platform-custom-connector'
        issuer = $env:HSE_OBO_MANAGED_IDENTITY_ISSUER
        subject = $env:HSE_OBO_MANAGED_IDENTITY_SUBJECT
        audiences = @('api://AzureADTokenExchange')
    } | ConvertTo-Json -Compress
    $credentialPath = 'C:\temp\oge-hse-obo-federated-credential.json'
    [System.IO.File]::WriteAllText($credentialPath, $credential)
    try {
        $existingCredential = az rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$($connector.id)/federatedIdentityCredentials" --query "value[?name=='power-platform-custom-connector'].id | [0]" -o tsv
        if (-not $existingCredential) {
            az rest --method POST --uri "https://graph.microsoft.com/v1.0/applications/$($connector.id)/federatedIdentityCredentials" --headers 'Content-Type=application/json' --body "@$credentialPath" --output none
        }
    }
    finally {
        Remove-Item $credentialPath -Force -ErrorAction SilentlyContinue
    }
}

Write-Output "HSE_OBO_CONNECTOR_CLIENT_ID=$($connector.appId)"
Write-Output 'Tenant admin consent is verified. Import the generated Swagger, then add the connector redirect URI and optional managed-identity federation values to .env and rerun.'