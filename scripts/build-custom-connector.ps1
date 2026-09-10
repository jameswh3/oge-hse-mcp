$ErrorActionPreference = 'Stop'

Get-Content (Join-Path $PSScriptRoot '..\.env') | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $name, $value = $line -split '=', 2
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
    }
}

$required = @(
    'HSE_ENTRA_TENANT_ID',
    'HSE_ENTRA_AUDIENCE',
    'HSE_ENTRA_RESOURCE_URL',
    'HSE_OBO_CONNECTOR_CLIENT_ID',
    'HSE_FEDERATED_CONNECTOR_PUBLISHER'
)
foreach ($name in $required) {
    if (-not [Environment]::GetEnvironmentVariable($name, 'Process')) {
        throw "Missing required .env variable: $name"
    }
}

$mcpUri = [Uri]$env:HSE_ENTRA_RESOURCE_URL
$scope = "api://$($env:HSE_ENTRA_AUDIENCE)/hse.read"
$authority = "https://login.microsoftonline.com/$($env:HSE_ENTRA_TENANT_ID)/oauth2/v2.0"
$templatePath = Join-Path $PSScriptRoot '..\integrations\custom-connector\hse-mcp.swagger.template.yaml'
$outputPath = Join-Path $PSScriptRoot '..\integrations\custom-connector\hse-mcp.generated.yaml'
$content = Get-Content $templatePath -Raw
$content = $content.Replace('__HSE_MCP_HOST__', $mcpUri.Host)
$content = $content.Replace('__HSE_AUTHORIZATION_URL__', "$authority/authorize")
$content = $content.Replace('__HSE_TOKEN_URL__', "$authority/token")
$content = $content.Replace('__HSE_FULL_SCOPE__', $scope)
[System.IO.File]::WriteAllText($outputPath, $content)
Write-Output $outputPath

$jsonTemplatePath = Join-Path $PSScriptRoot '..\integrations\custom-connector\hse-mcp.swagger.template.json'
$jsonOutputPath = Join-Path $PSScriptRoot '..\integrations\custom-connector\hse-mcp.generated.json'
$jsonContent = Get-Content $jsonTemplatePath -Raw
$jsonContent = $jsonContent.Replace('__HSE_MCP_HOST__', $mcpUri.Host)
$jsonContent = $jsonContent.Replace('__HSE_AUTHORIZATION_URL__', "$authority/authorize")
$jsonContent = $jsonContent.Replace('__HSE_TOKEN_URL__', "$authority/token")
$jsonContent = $jsonContent.Replace('__HSE_FULL_SCOPE__', $scope)
[System.IO.File]::WriteAllText($jsonOutputPath, $jsonContent)
Write-Output $jsonOutputPath

$propertiesTemplatePath = Join-Path $PSScriptRoot '..\integrations\custom-connector\apiProperties.template.json'
$propertiesOutputPath = Join-Path $PSScriptRoot '..\integrations\custom-connector\apiProperties.generated.json'
$properties = Get-Content $propertiesTemplatePath -Raw
$properties = $properties.Replace('__HSE_OBO_CONNECTOR_CLIENT_ID__', $env:HSE_OBO_CONNECTOR_CLIENT_ID)
$properties = $properties.Replace('__HSE_FULL_SCOPE__', $scope)
$properties = $properties.Replace('__HSE_RESOURCE_ID__', "api://$($env:HSE_ENTRA_AUDIENCE)")
$properties = $properties.Replace('__HSE_TENANT_ID__', $env:HSE_ENTRA_TENANT_ID)
$properties = $properties.Replace('__HSE_CONNECTOR_PUBLISHER__', $env:HSE_FEDERATED_CONNECTOR_PUBLISHER)
[System.IO.File]::WriteAllText($propertiesOutputPath, $properties)
Write-Output $propertiesOutputPath