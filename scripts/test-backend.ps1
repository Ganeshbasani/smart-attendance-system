$ErrorActionPreference = "Stop"
cd "$PSScriptRoot\..\backend"
python -m compileall -q app
python -m pytest -q
