#!/usr/bin/env python3
"""
stop.py - Stop all Virtual Staging services
"""

import subprocess
import sys
import json
import os
import signal
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.resolve()
PID_FILE = PROJECT_ROOT / "services.pid"

SERVICES = [
    ("ComfyUI",   8188),
    ("FastAPI",   8000),
    ("Streamlit", 8501),
]

def kill_process_by_pid(pid: int) -> bool:
    """Attempt to kill a process by its PID."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], 
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.kill(pid, signal.SIGKILL)
        return True
    except (ProcessLookupError, OSError):
        return False

def kill_process_by_port(port: int) -> bool:
    """Kill whatever process is listening on the given port."""
    try:
        if sys.platform == "win32":
            # Find PID by port
            cmd = f"netstat -ano | findstr :{port}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        return True
        else:
            # Unix way (lsof)
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, capture_output=True)
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False

def main():
    print("========================================")
    print("🛑 Stopping Virtual Staging Services")
    print("========================================\n")

    # 1. Try stopping via PIDs
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pids = json.load(f)
            
            for name, pid in pids.items():
                print(f"  • Killing {name} (PID: {pid})...", end=" ")
                if kill_process_by_pid(pid):
                    print("✓")
                else:
                    print("Skipped (Not running)")
        except Exception:
            print("  ⚠️  Could not read PID file.")
        
        # Remove file
        try:
            PID_FILE.unlink()
        except OSError as exc:
            print(f"Warning: could not remove PID file: {exc}")
    
    # 2. Cleanup via Ports (Fallback)
    print("\n  • Ensuring ports are clear...")
    for name, port in SERVICES:
        kill_process_by_port(port)
        
    print("\n✅ All app services stopped.")
    print("---------------------------------------------------------")
    print("NOTE: Ollama is NOT stopped by this script.")
    print("If you wish to stop Ollama, you must do it manually")
    print("(e.g., via Task Manager or right-clicking the tray icon).")
    print("---------------------------------------------------------")

if __name__ == "__main__":
    main()