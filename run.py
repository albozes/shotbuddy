import os
import socket
import threading
import time
import webbrowser
import sys
import signal
from configparser import ConfigParser
from pathlib import Path

from app import create_app


def load_server_config():
    """Load server host and port from shotbuddy.cfg if it exists."""
    cfg_path = Path(__file__).with_name("shotbuddy.cfg")
    host = None
    port = None
    if cfg_path.exists():
        parser = ConfigParser()
        parser.read(cfg_path)
        if parser.has_section("server"):
            host = parser.get("server", "host", fallback=None)
            port = parser.getint("server", "port", fallback=None)
    return host, port


def check_port_in_use(host, port):
    """Check if a port is already in use by trying to bind to it."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return False  # Port is available
    except OSError as e:
        if sock:
            sock.close()
        # Port is in use if we get "Address already in use" error
        return e.errno == 48 or e.errno == 98 or "Address already in use" in str(e)
    except Exception:
        if sock:
            sock.close()
        return False


def is_shotbuddy_process(pid):
    """Check if a PID belongs to a Shotbuddy process."""
    import platform
    import subprocess

    system = platform.system()

    try:
        if system == "Darwin" or system == "Linux":
            # Get process command line
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                cmd = result.stdout.strip()
                # Check if it's a Python process running run.py or Shotbuddy
                return "python" in cmd.lower() and ("run.py" in cmd or "shotbuddy" in cmd.lower())
        elif system == "Windows":
            # Get process command line
            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                cmd = result.stdout.strip()
                return "python" in cmd.lower() and ("run.py" in cmd or "shotbuddy" in cmd.lower())
    except Exception as e:
        print(f"Could not check process {pid}: {e}")
        return False

    return False


def kill_shotbuddy_on_port(port):
    """Try to kill Shotbuddy processes using the specified port."""
    import platform
    import subprocess

    system = platform.system()

    try:
        if system == "Darwin" or system == "Linux":
            # Find the process using the port
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                killed_any = False
                for pid in pids:
                    if is_shotbuddy_process(pid):
                        print(f"Found ghost Shotbuddy process {pid} on port {port}")
                        print(f"Killing process {pid}...")
                        subprocess.run(["kill", "-9", pid])
                        killed_any = True
                    else:
                        print(f"Port {port} is in use by another application (PID {pid}), not Shotbuddy.")
                        return False
                if killed_any:
                    time.sleep(0.5)
                    return True
        elif system == "Windows":
            # Find the process using the port
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if is_shotbuddy_process(pid):
                        print(f"Found ghost Shotbuddy process {pid} on port {port}")
                        print(f"Killing process {pid}...")
                        subprocess.run(["taskkill", "/F", "/PID", pid])
                        time.sleep(0.5)
                        return True
                    else:
                        print(f"Port {port} is in use by another application (PID {pid}), not Shotbuddy.")
                        return False
    except Exception as e:
        print(f"Could not kill process on port {port}: {e}")
        return False

    return False


app = create_app()

if __name__ == "__main__":
    cfg_host, cfg_port = load_server_config()
    host = os.environ.get("SHOTBUDDY_HOST", cfg_host or "127.0.0.1")
    port = int(os.environ.get("SHOTBUDDY_PORT", cfg_port or 5001))
    debug = os.environ.get("SHOTBUDDY_DEBUG", "0").lower() in {"1", "true", "yes"}

    # Check if port is already in use
    if check_port_in_use(host, port):
        print(f"Port {port} is already in use.")
        print("Checking if it's a ghost Shotbuddy process...")

        if kill_shotbuddy_on_port(port):
            # Wait a bit more to ensure port is released
            time.sleep(1)
            if check_port_in_use(host, port):
                print(f"Failed to free port {port}. Please manually stop the process or use a different port.")
                sys.exit(1)
            else:
                print(f"Ghost process cleaned up. Port {port} is now free.")
        else:
            print(f"\nPort {port} is in use by another application.")
            print(f"Please either:")
            print(f"  1. Stop the other application using port {port}")
            print(f"  2. Configure Shotbuddy to use a different port in shotbuddy.cfg")
            sys.exit(1)

    def _open_browser_when_ready(url):
        while True:
            try:
                with socket.create_connection((host, port), timeout=1):
                    break
            except OSError:
                time.sleep(0.1)
        webbrowser.open_new(url)

    threading.Thread(
        target=_open_browser_when_ready,
        args=(f"http://{host}:{port}/",),
        daemon=True,
    ).start()

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down Shotbuddy...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        app.run(debug=debug, host=host, port=port)
    except OSError as e:
        if "Address already in use" in str(e) or e.errno in (48, 98):
            print(f"\nError: Port {port} is in use by another application.")
            print(f"Please either:")
            print(f"  1. Stop the other application using port {port}")
            print(f"  2. Configure Shotbuddy to use a different port in shotbuddy.cfg")
            print(f"  3. Set the SHOTBUDDY_PORT environment variable to use a different port")
            sys.exit(1)
        else:
            raise
