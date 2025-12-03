# settings_routes.py

from flask import Blueprint, jsonify, request, current_app
import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@settings_bp.route('/', methods=['GET'])
def get_settings():
    """Get user settings."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        settings = project_manager.get_settings()
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        logger.error("Failed to get settings: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route('/', methods=['POST'])
def update_settings():
    """Update user settings."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        settings = project_manager.update_settings(data)
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        logger.error("Failed to update settings: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


def restart_server():
    """Restart the server by starting a new process and exiting the current one."""
    try:
        logger.info("Restarting server...")
        import subprocess
        import socket
        from pathlib import Path
        from configparser import ConfigParser

        # Get the current port (same logic as run.py)
        cfg_path = Path(__file__).parents[2] / "shotbuddy.cfg"
        cfg_port = None
        if cfg_path.exists():
            parser = ConfigParser()
            parser.read(cfg_path)
            if parser.has_section("server"):
                cfg_port = parser.getint("server", "port", fallback=None)

        port = int(os.environ.get("SHOTBUDDY_PORT", cfg_port or 5001))

        # Create a wrapper script that waits for the port to be free
        python = sys.executable
        restart_script = f"""
import time
import socket
import subprocess
import sys

port = {port}
max_wait = 10  # Maximum seconds to wait

# Wait for port to become available
for i in range(max_wait * 10):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()

        if result != 0:
            # Port is free
            break
    except:
        break

    time.sleep(0.1)

# Start the actual server
subprocess.Popen(['{python}'] + {sys.argv})
"""

        # Write the restart script to a temporary file
        import tempfile
        fd, script_path = tempfile.mkstemp(suffix='.py', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(restart_script)

            # Start the wrapper script
            subprocess.Popen([python, script_path])
        except Exception as e:
            logger.error("Failed to create restart wrapper: %s", e)
            if os.path.exists(script_path):
                os.unlink(script_path)
            raise

        # Give the response time to be sent, then exit this process
        import time
        time.sleep(1)

        # Force exit to release the port immediately
        os._exit(0)
    except Exception as e:
        logger.error("Failed to restart server: %s", e)


@settings_bp.route('/restart', methods=['POST'])
def restart():
    """Restart the Shotbuddy server."""
    try:
        logger.info("Server restart requested")

        # Delay the restart slightly to allow the response to be sent
        def delayed_restart():
            import time
            time.sleep(0.5)
            restart_server()

        thread = threading.Thread(target=delayed_restart)
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "Server is restarting..."})
    except Exception as e:
        logger.error("Failed to initiate restart: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
