$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:IMPLEMENTATION_PROFILE="m0"
$env:PROVIDER="ollama"
if (-not $env:LOCAL_LLM_MODEL) { $env:LOCAL_LLM_MODEL="qwen3:4b" }
& .\.venv\Scripts\python.exe scripts\check_local_llm.py
& .\.venv\Scripts\python.exe scripts\bootstrap_demo.py
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
