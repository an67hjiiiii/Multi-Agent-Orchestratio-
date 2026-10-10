$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:IMPLEMENTATION_PROFILE="m0"
$env:PROVIDER="ollama"
& .\.venv\Scripts\python.exe scripts\check_local_llm.py
& .\.venv\Scripts\python.exe scripts\run_m0_calibration.py --provider ollama
& .\.venv\Scripts\python.exe scripts\create_m0_manifest.py
