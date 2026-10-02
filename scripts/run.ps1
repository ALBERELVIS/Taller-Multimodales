param(
    [switch]$SkipModels,
    [switch]$SkipInstall
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not $SkipInstall) {
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r requirements.txt
}
$env:PYTHONPATH = Join-Path $Root "src"
& $Python -m helios.doctor
& $Python scripts\build_demo_case.py
if (-not $SkipModels) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
    } catch {
        if (Get-Command ollama -ErrorAction SilentlyContinue) {
            Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 2
        }
    }
    & $Python scripts\pull_models.py
}
& $Python -m streamlit run (Join-Path $Root "app\streamlit_app.py")
