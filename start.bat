@echo off
title AI Job Hunter — Fullstack Launcher
cd /d "%~dp0"

if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" run.py
) else (
    python run.py
)

pause
