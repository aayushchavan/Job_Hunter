# PowerShell launcher for AI Job Hunter
Set-Location $PSScriptRoot

if (Test-Path "backend\.venv\Scripts\python.exe") {
    & "backend\.venv\Scripts\python.exe" run.py
} else {
    python run.py
}
