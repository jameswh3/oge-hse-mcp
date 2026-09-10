$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

Get-Content (Join-Path $PSScriptRoot '..\.env') | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $name, $value = $line -split '=', 2
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
    }
}

if (-not $env:AZURE_RESOURCE_GROUP -or -not $env:HSE_ENTRA_AUDIENCE) {
    throw 'AZURE_RESOURCE_GROUP and HSE_ENTRA_AUDIENCE must be set in .env.'
}

az group delete --name $env:AZURE_RESOURCE_GROUP --yes
az ad app delete --id $env:HSE_ENTRA_AUDIENCE
