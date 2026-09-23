$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not $env:ATTENDX_SECRET_KEY) {
    $env:ATTENDX_SECRET_KEY = "dev-only-change-this"
}

$existingDb = Join-Path $PSScriptRoot "data\attendx.db"
if (-not (Test-Path $existingDb)) {
    & .\.venv\Scripts\python.exe seed.py
}

& .\.venv\Scripts\python.exe -m streamlit run app.py
