"""Start backend and frontend together.

Run with:  python main_start.py

Launches uvicorn (backend) and the Vite dev server (frontend) as subprocesses,
streams both logs to this console, and shuts both down on Ctrl+C. Calling
npm via its .cmd directly (not through a PowerShell wrapper) means this works
even when PowerShell's script execution policy blocks npm.ps1 -- the classic
"running scripts is disabled on this system" error.
"""

from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173


def _venv_python() -> Path:
    candidate = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    if not candidate.exists():
        sys.exit(
            f"Backend venv not found at {candidate}.\n"
            f"Set it up first:\n"
            f"  cd backend\n"
            f"  python -m venv .venv\n"
            f'  .\\.venv\\Scripts\\python.exe -m pip install -e ".[dev]"'
        )
    return candidate


def _npm_command() -> str:
    # On Windows, resolve to npm.cmd explicitly. Invoking it via subprocess
    # never goes through a PowerShell script host, so the execution-policy
    # restriction on npm.ps1 does not apply here.
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        sys.exit("npm not found on PATH. Install Node.js first.")
    return npm


def _free_port(port: int) -> None:
    """Best-effort: kill whatever is already listening on `port` (Windows).

    A process left over from a previous run (e.g. a background shell that
    didn't get closed) holds the port and makes the new server fail with
    WinError 10013 / 10048. Freeing it here means this script always starts
    cleanly instead of requiring a manual netstat/taskkill first.
    """
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return
    for line in result.stdout.splitlines():
        parts = line.split()
        # Columns: Proto, Local Address, Foreign Address, State, PID. The
        # State column's text is locale-dependent (LISTENING / ABHOEREN /
        # ...), so match on the local address port instead of the state name.
        if len(parts) >= 5 and parts[0] == "TCP" and parts[1].endswith(f":{port}"):
            pid = parts[-1]
            subprocess.run(
                ["taskkill", "/PID", pid, "/F"],
                capture_output=True, check=False,
            )


def main() -> None:
    python = _venv_python()
    npm = _npm_command()

    for port in (BACKEND_PORT, FRONTEND_PORT):
        _free_port(port)

    print(f"Starting backend on http://localhost:{BACKEND_PORT} ...")
    backend = subprocess.Popen(
        [str(python), "-m", "uvicorn", "app.main:app", "--reload", "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
    )

    time.sleep(2)  # give the backend a head start before the frontend proxies to it

    print(f"Starting frontend on http://localhost:{FRONTEND_PORT} ...")
    frontend = subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND_DIR)

    print("\nBoth servers are starting. Open http://localhost:5173 in your browser.")
    print("Press Ctrl+C to stop both.\n")

    def shutdown(*_args) -> None:
        print("\nStopping...")
        for proc in (frontend, backend):
            if proc.poll() is None:
                proc.terminate()
        for proc in (frontend, backend):
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    # Exit if either process dies on its own (e.g. a startup error).
    while True:
        if backend.poll() is not None:
            print(f"Backend exited with code {backend.returncode}.")
            shutdown()
        if frontend.poll() is not None:
            print(f"Frontend exited with code {frontend.returncode}.")
            shutdown()
        time.sleep(1)


if __name__ == "__main__":
    main()
