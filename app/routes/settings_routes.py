# settings_routes.py

from flask import Blueprint, jsonify, request, current_app
import logging

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
