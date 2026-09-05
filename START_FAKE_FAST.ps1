$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PROVIDER="fake"
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
