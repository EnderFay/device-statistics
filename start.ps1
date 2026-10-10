$ErrorActionPreference = 'Stop'

Push-Location -LiteralPath $PSScriptRoot
try {
    docker compose up --build -d --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) {
        throw 'Service startup failed. Check docker compose logs.'
    }
    Write-Host 'http://localhost:8000/docs'
} finally {
    Pop-Location
}
