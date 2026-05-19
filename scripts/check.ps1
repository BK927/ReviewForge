$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
  Write-Host "Checking documentation guard..."
  Push-Location (Join-Path $Root "backend")
  try {
    uv run python ..\scripts\check_docs.py
    uv run python scripts\smoke_test.py
  }
  finally {
    Pop-Location
  }

  Write-Host "Checking frontend..."
  Push-Location (Join-Path $Root "frontend")
  try {
    npm run check
    npm run build
  }
  finally {
    Pop-Location
  }
}
finally {
  Pop-Location
}

Write-Host "ReviewForge checks passed."
