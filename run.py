"""
run.py — Unified runner for AI Job Hunter
Starts both FastAPI Backend and Next.js Frontend concurrently with a single command.
Usage:
    python run.py
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Fix Windows console charmap encoding errors with emojis
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Locate python in virtualenv if available
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
PYTHON_BIN = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

# NPM command
NPM_BIN = "npm.cmd" if sys.platform == "win32" else "npm"

print("\n" + "=" * 60)
print("  🚀 Starting AI Job Hunter — Fullstack Application")
print("=" * 60)
print(f"  📁 Root Directory : {ROOT_DIR}")
print(f"  🐍 Python Binary  : {PYTHON_BIN}")
print("  🌐 Frontend URL   : http://localhost:3000")
print("  ⚡ Backend API    : http://localhost:8000")
print("  📖 Swagger Docs   : http://localhost:8000/docs")
print("=" * 60 + "\n")

processes = []

def cleanup(*args):
    print("\n🛑 Shutting down AI Job Hunter services...")
    for p in processes:
        if p.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
            except Exception:
                pass
    print("👋 All services stopped cleanly.\n")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, cleanup)

def start_backend():
    print("⏳ Launching FastAPI backend...")
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        [PYTHON_BIN, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        shell=False,
        creationflags=creationflags,
    )

def start_frontend():
    print("⏳ Launching Next.js frontend...")
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    return subprocess.Popen(
        [NPM_BIN, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        shell=True,
        creationflags=creationflags,
    )

try:
    backend_proc = start_backend()
    processes.append(backend_proc)

    time.sleep(1.5)

    frontend_proc = start_frontend()
    processes.append(frontend_proc)

    print("\n✅ Both services are now running! Press Ctrl+C to stop all.\n")

    # Monitor and auto-restart if either service exits
    while True:
        time.sleep(2)
        if backend_proc.poll() is not None:
            print(f"\n⚠️ Backend process exited (code {backend_proc.returncode}). Auto-restarting in 2s...")
            time.sleep(2)
            backend_proc = start_backend()
            processes[0] = backend_proc

        if frontend_proc.poll() is not None:
            print(f"\n⚠️ Frontend process exited (code {frontend_proc.returncode}). Auto-restarting in 2s...")
            time.sleep(2)
            frontend_proc = start_frontend()
            processes[1] = frontend_proc

except KeyboardInterrupt:
    cleanup()
except Exception as e:
    print(f"Error launching services: {e}")
    cleanup()
