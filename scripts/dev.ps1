param(
  [switch]$BackendOnly,
  [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $FrontendOnly) {
  Start-Process -WindowStyle Hidden -WorkingDirectory (Join-Path $Root "backend") -FilePath "uv" -ArgumentList @("run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload")
}

if (-not $BackendOnly) {
  Start-Process -WindowStyle Hidden -WorkingDirectory (Join-Path $Root "frontend") -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--port", "5173")
}

Write-Host "ReviewForge dev servers requested."
Write-Host "Backend:  http://127.0.0.1:8000/api"
Write-Host "Frontend: http://127.0.0.1:5173"
