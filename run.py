#!/usr/bin/env python3
"""
run.py - Start all Virtual Staging services
"""

import subprocess
import sys
import time
import os
import json
import threading
import webbrowser
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.resolve()
PID_FILE = PROJECT_ROOT / "services.pid"
LOG_DIR = PROJECT_ROOT / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

COMFYUI_DIR = PROJECT_ROOT / "ComfyUI"
COMFYUI_PORT = 8188
FASTAPI_PORT = 8000
STREAMLIT_PORT = 8501

# ----------------------------- Environment Setup -----------------------------

def get_python_exec():
    """Find the Python executable in the local .venv if it exists."""
    # Windows
    venv_win = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_win.exists():
        return str(venv_win)
    # Linux / Mac
    venv_unix = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_unix.exists():
        return str(venv_unix)
    return sys.executable

PYTHON_EXEC = get_python_exec()
print(f"🐍 Using Python: {PYTHON_EXEC}")

# Ensure logs are flushed immediately
ENV_VARS = os.environ.copy()
ENV_VARS["PYTHONUNBUFFERED"] = "1"
# Critical: Add project root to PYTHONPATH so 'app.config' imports work
ENV_VARS["PYTHONPATH"] = str(PROJECT_ROOT)

# ----------------------------- Helpers -----------------------------

def check_port_in_use(port: int) -> bool:
    """Check if a port is already in use on localhost."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1) # Don't hang
        return s.connect_ex(("127.0.0.1", port)) == 0

def save_pid(service_name: str, pid: int):
    """Append or update a service PID in the PID file."""
    pids = {}
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pids = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not read PID file, starting fresh: {exc}")
    pids[service_name] = pid
    with open(PID_FILE, "w") as f:
        json.dump(pids, f)

def stream_logs(pipe, prefix: str, log_file):
    """Stream process output to log file."""
    if pipe is None:
        return
    for line in iter(pipe.readline, b""):
        if line:
            text = line.decode("utf-8", errors="replace").rstrip()
            # Uncomment it for streaming log in terminal
            # print(f"[{prefix}] {text}")
            log_file.write(text + "\n")
            log_file.flush()

# ----------------------------- Service Starters -----------------------------

def start_comfyui():
    """Start ComfyUI server."""
    if check_port_in_use(COMFYUI_PORT):
        print(f"   ⚠️  Port {COMFYUI_PORT} in use. Assuming ComfyUI is running.")
        return None

    print("📸 Starting ComfyUI...")
    log_path = LOG_DIR / "comfyui.log"
    log_file = open(log_path, "w", encoding="utf-8")

    process = subprocess.Popen(
        [PYTHON_EXEC, "main.py", "--port", str(COMFYUI_PORT)],
        cwd=COMFYUI_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=ENV_VARS,
        bufsize=1,
    )

    save_pid("comfyui", process.pid)
    threading.Thread(target=stream_logs, args=(process.stdout, "COMFYUI", log_file), daemon=True).start()
    time.sleep(1)
    return process

def start_fastapi():
    """Start FastAPI backend."""
    if check_port_in_use(FASTAPI_PORT):
        print(f"   ⚠️  Port {FASTAPI_PORT} in use. Assuming FastAPI is running.")
        return None

    print("🔌 Starting FastAPI backend...")
    log_path = LOG_DIR / "fastapi.log"
    log_file = open(log_path, "w", encoding="utf-8")

    process = subprocess.Popen(
        [PYTHON_EXEC, "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", str(FASTAPI_PORT)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=ENV_VARS,
        bufsize=1,
    )

    save_pid("fastapi", process.pid)
    threading.Thread(target=stream_logs, args=(process.stdout, "FASTAPI", log_file), daemon=True).start()
    time.sleep(1)
    return process

def start_streamlit():
    """Start Streamlit frontend."""
    if check_port_in_use(STREAMLIT_PORT):
        print(f"   ⚠️  Port {STREAMLIT_PORT} in use. Assuming Streamlit is running.")
        return None

    print("🎨 Starting Streamlit app...")
    log_path = LOG_DIR / "streamlit.log"
    log_file = open(log_path, "w", encoding="utf-8")

    streamlit_script = PROJECT_ROOT / "app" / "frontend.py"
    process = subprocess.Popen(
        [PYTHON_EXEC, "-m", "streamlit", "run", str(streamlit_script),
         "--server.port", str(STREAMLIT_PORT), 
         "--server.address", "127.0.0.1", 
         "--server.headless", "true"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=ENV_VARS,
        bufsize=1,
    )

    save_pid("streamlit", process.pid)
    threading.Thread(target=stream_logs, args=(process.stdout, "STREAMLIT", log_file), daemon=True).start()
    time.sleep(1)
    return process

def check_ollama():
    """Check if Ollama is running using HTTP request (Does not freeze)."""
    print("🤖 Checking Ollama...")
    
    # Method 1: HTTP Request (Safest/Fastest)
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=1)
        print("   ✓ Ollama is running")
        return True
    except urllib.error.URLError:
        pass

    # Method 2: Attempt Start
    print("   ⏳ Starting Ollama...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        # Wait a bit for it to spin up
        for _ in range(5):
            time.sleep(1)
            try:
                urllib.request.urlopen("http://127.0.0.1:11434", timeout=1)
                print("   ✓ Ollama started successfully")
                return True
            except urllib.error.URLError:
                pass
    except Exception as e:
        print(f"   ❌ Could not start Ollama: {e}")
        return False
    
    print("   ⚠️  Ollama started but not yet responding (it might take a moment).")
    return True

# ----------------------------- Main -----------------------------

def main():
    print("========================================")
    print("🚀 Starting Virtual Staging Services")
    print("========================================\n")

    start_comfyui()
    start_fastapi()
    start_streamlit()
    check_ollama()

    print("\n✅ Services Initialized!")
    print(f"  • ComfyUI      : http://127.0.0.1:{COMFYUI_PORT}")
    print(f"  • FastAPI Docs : http://127.0.0.1:{FASTAPI_PORT}/docs")
    print(f"  • Streamlit UI : http://127.0.0.1:{STREAMLIT_PORT}")
    print("  • Ollama       : http://127.0.0.1:11434")
    
    print("\nLogs are being written to the 'log/' folder.")
    print("To stop services, run 'python stop.py'")
    
    try:
        time.sleep(2)
        webbrowser.open(f"http://127.0.0.1:{STREAMLIT_PORT}")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Received Ctrl+C. Exiting launcher.")
        print("Run 'python stop.py' to stop services.")

if __name__ == "__main__":
    main()