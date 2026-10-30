$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env. Please fill keys then rerun."
  Write-Host "Required: DASHSCOPE_API_KEY, TUSHARE_TOKEN"
  exit 1
}

Write-Host "Starting Flask server..."
.\.venv\Scripts\python backend\app.py

