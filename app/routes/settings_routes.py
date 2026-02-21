# settings_routes.py

from flask import Blueprint, jsonify, request, current_app
from app.services.file_handler import FileHandler
import logging

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)

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


@settings_bp.route('/rename-files-preview', methods=['POST'])
def rename_files_preview():
    """Return a count of files that would be renamed by a naming pattern."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No project open"}), 400

        data = request.get_json() or {}
        pattern = data.get('pattern', '{shot}')
        handler = FileHandler(project['path'], naming_pattern=pattern)
        file_count, shot_count = handler.count_renameable_files()

        return jsonify({
            "success": True,
            "file_count": file_count,
            "shot_count": shot_count
        })
    except Exception as e:
        logger.error("Failed to preview rename: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route('/apply-naming', methods=['POST'])
def apply_naming():
    """Save the naming pattern and rename all existing files to match it."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No project open"}), 400

        data = request.get_json() or {}
        pattern = data.get('pattern', '{shot}')

        # Save the pattern first so it persists even if rename is partial
        project_manager.update_settings({'file_naming_pattern': pattern})

        handler = FileHandler(project['path'], naming_pattern=pattern)
        stats = handler.apply_naming_pattern()

        return jsonify({
            "success": True,
            "renamed": stats['renamed'],
            "errors": stats['errors']
        })
    except Exception as e:
        logger.error("Failed to apply naming pattern: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
