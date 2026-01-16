from flask import Blueprint, request, jsonify, send_file, current_app
from pathlib import Path
import logging

from app.services.shot_manager import get_shot_manager
from app.services.file_handler import FileHandler
from app.utils import (
    require_project,
    error_response,
    reveal_in_file_browser,
    open_folder_in_browser,
)
from app.config.constants import AssetType

logger = logging.getLogger(__name__)

shot_bp = Blueprint('shot', __name__)


def _find_file_with_extensions(folder_path, base_name, extensions):
    """Find a file in folder_path matching base_name with any of the given extensions."""
    if not folder_path or not folder_path.exists():
        return None

    for ext in extensions:
        candidate = folder_path / f'{base_name}{ext}'
        if candidate.exists():
            return candidate
    return None


def _get_file_for_latest_folder(project_path, shot_name, asset_type):
    """Get the file to reveal when using 'latest_folder' behavior."""
    from app.config.constants import ALLOWED_IMAGE_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS

    if asset_type == AssetType.IMAGE:
        folder_path = project_path / 'shots' / 'latest_images'
        extensions = ALLOWED_IMAGE_EXTENSIONS
    elif asset_type == AssetType.VIDEO:
        folder_path = project_path / 'shots' / 'latest_videos'
        extensions = ALLOWED_VIDEO_EXTENSIONS
    else:
        return None

    return _find_file_with_extensions(folder_path, shot_name, extensions)


def _get_file_for_version_folder(project_path, shot_name, asset_type, version):
    """Get the versioned file to reveal when using 'version_folder' behavior."""
    from app.config.constants import ALLOWED_IMAGE_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS

    if version <= 0:
        return None

    if asset_type == AssetType.IMAGE:
        folder_path = project_path / 'shots' / 'wip' / shot_name / 'images'
        extensions = ALLOWED_IMAGE_EXTENSIONS
    elif asset_type == AssetType.VIDEO:
        folder_path = project_path / 'shots' / 'wip' / shot_name / 'videos'
        extensions = ALLOWED_VIDEO_EXTENSIONS
    else:
        return None

    return _find_file_with_extensions(folder_path, f'{shot_name}_v{version:03d}', extensions)

@shot_bp.route("/", strict_slashes=False, methods=["GET"])
@require_project
def get_shots(project):
    try:
        shot_manager = get_shot_manager(project["path"])
        shots = shot_manager.get_shots()
        return jsonify({"success": True, "data": shots})
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/", methods=["POST"])
@require_project
def create_shot(project):
    try:
        shot_manager = get_shot_manager(project["path"])
        next_number = shot_manager.get_next_shot_number()
        shot_name = f"SH{next_number:03d}"

        shot_manager.create_shot_structure(shot_name)
        shot_info = shot_manager.get_shot_info(shot_name)

        return jsonify({"success": True, "data": shot_info})
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/upload", methods=["POST"])
@require_project
def upload_file(project):
    try:
        file = request.files.get('file')
        shot_name = request.form.get('shot_name')
        file_type = request.form.get('file_type')

        if not file or not shot_name or not file_type:
            return error_response("Missing required parameters")
        if file.filename == '':
            return error_response("No file selected")

        file_handler = FileHandler(project['path'])
        result = file_handler.save_file(file, shot_name, file_type)

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/notes", methods=["POST"])
@require_project
def save_shot_notes(project):
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        notes = data.get("notes", "")

        if not shot_name:
            return error_response("Shot name required")

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_shot_notes(shot_name, notes)

        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/prompt", methods=["POST"])
@require_project
def save_shot_prompt(project):
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        version = data.get("version")
        prompt = data.get("prompt", "")

        if not shot_name or not asset_type or version is None:
            return error_response("Missing parameters")

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_prompt(shot_name, asset_type, int(version), prompt)

        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/prompt", methods=["GET"])
@require_project
def get_shot_prompt(project):
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        version = request.args.get("version", type=int)

        if not shot_name or not asset_type or version is None:
            return error_response("Missing parameters")

        shot_manager = get_shot_manager(project["path"])
        prompt = shot_manager.load_prompt(shot_name, asset_type, version)

        return jsonify({"success": True, "data": prompt})
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/prompt-versions")
@require_project
def get_prompt_versions(project):
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        if not shot_name or not asset_type:
            return error_response("Missing parameters")

        shot_manager = get_shot_manager(project["path"])
        versions = shot_manager.get_prompt_versions(shot_name, asset_type)
        return jsonify({"success": True, "data": versions})
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/rename", methods=["POST"])
@require_project
def rename_shot(project):
    try:
        data = request.get_json()
        old_name = data.get("old_name")
        new_name = data.get("new_name")
        if not old_name or not new_name:
            return error_response("Old and new names required")

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.rename_shot(old_name, new_name)

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/create-between", methods=["POST"])
@require_project
def create_shot_between(project):
    try:
        data = request.get_json()
        after_shot = data.get("after_shot")

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.create_shot_between(after_shot)

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/thumbnail/<path:filepath>")
def serve_thumbnail(filepath):
    """Serve a thumbnail from the cache directory."""
    try:
        from app.config.constants import THUMBNAIL_CACHE_DIR

        thumb_path = THUMBNAIL_CACHE_DIR / Path(filepath).name
        thumb_dir = THUMBNAIL_CACHE_DIR.resolve()
        thumb_path = thumb_path.resolve()

        if not str(thumb_path).startswith(str(thumb_dir)):
            return error_response("Invalid path")

        if thumb_path.is_file():
            return send_file(str(thumb_path))
        return error_response("File not found", 404)
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/reveal", methods=["POST"])
@require_project
def reveal_file(project):
    """Reveal a file in the system file browser based on settings."""
    try:
        data = request.get_json()
        rel_path = data.get("path")
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")

        project_manager = current_app.config['PROJECT_MANAGER']
        settings = project_manager.get_settings()
        thumbnail_behavior = settings.get('thumbnail_click_behavior', 'latest_folder')

        project_path = Path(project["path"]).resolve()
        file_to_select = None

        # Determine which file to select based on settings
        if shot_name and asset_type:
            if thumbnail_behavior == 'latest_folder':
                file_to_select = _get_file_for_latest_folder(project_path, shot_name, asset_type)

            elif thumbnail_behavior == 'version_folder':
                shot_manager = get_shot_manager(project["path"])
                shot_info = shot_manager.get_shot_info(shot_name)
                version = shot_info.get(asset_type, {}).get('version', 0)
                file_to_select = _get_file_for_version_folder(project_path, shot_name, asset_type, version)

        if file_to_select:
            reveal_in_file_browser(file_to_select)
            return jsonify({"success": True})

        # Fallback: reveal the specific file from rel_path
        file_path = Path(rel_path)
        if not file_path.is_absolute():
            file_path = (project_path / file_path).resolve()
        else:
            file_path = file_path.resolve()

        # Security check: ensure the resolved path is within the project directory
        if not str(file_path).startswith(str(project_path)):
            return error_response("Invalid path")

        if not file_path.exists():
            return error_response(f"File does not exist: {file_path}", 404)

        reveal_in_file_browser(file_path)
        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)


@shot_bp.route("/open-folder", methods=["POST"])
@require_project
def open_shots_folder(project):
    """Open the current project's shots folder in the file browser."""
    try:
        shots_path = Path(project["path"]) / "shots"
        if not shots_path.exists():
            return error_response("Shots folder missing", 404)

        open_folder_in_browser(shots_path)
        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)
