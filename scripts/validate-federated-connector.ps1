$ErrorActionPreference = 'Stop'

Get-Content (Join-Path $PSScriptRoot '..\.env') | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        $name, $value = $line -split '=', 2
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
    }
}

$resource = [Uri]$env:HSE_ENTRA_RESOURCE_URL
$metadataUri = "https://$($resource.Host)/.well-known/oauth-protected-resource$($resource.AbsolutePath)"
$metadata = Invoke-RestMethod -Uri $metadataUri
if ($metadata.resource -ne $env:HSE_ENTRA_RESOURCE_URL) {
    throw "Protected-resource metadata returned unexpected resource: $($metadata.resource)"
}
if ($metadata.scopes_supported -notcontains 'hse.read') {
    throw 'Protected-resource metadata does not advertise hse.read.'
}

$unauthenticated = Invoke-WebRequest -Uri $env:HSE_ENTRA_RESOURCE_URL -Method Post -ContentType 'application/json' -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' -SkipHttpErrorCheck
if ($unauthenticated.StatusCode -ne 401) {
    throw "Expected unauthenticated tools/list to return 401; received $($unauthenticated.StatusCode)."
}

Write-Output 'Federated connector endpoint contract is valid: OAuth metadata is available and anonymous MCP calls are denied.'