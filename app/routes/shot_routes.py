from flask import Blueprint, request, jsonify, send_file, current_app
from pathlib import Path

from app.services.shot_manager import get_shot_manager
from app.services.file_handler import FileHandler

import subprocess
import platform

shot_bp = Blueprint('shot', __name__)

@shot_bp.route("/", strict_slashes=False, methods=["GET"])
def get_shots():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shots = shot_manager.get_shots()
        return jsonify({"success": True, "data": shots})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/", methods=["POST"])
def create_shot():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        next_number = shot_manager.get_next_shot_number()
        shot_name = f"SH{next_number:03d}"

        shot_manager.create_shot_structure(shot_name)
        shot_info = shot_manager.get_shot_info(shot_name)

        return jsonify({"success": True, "data": shot_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files.get('file')
        shot_name = request.form.get('shot_name')
        file_type = request.form.get('file_type')

        if not file or not shot_name or not file_type:
            return jsonify({"success": False, "error": "Missing required parameters"}), 400
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        file_handler = FileHandler(project['path'])
        result = file_handler.save_file(file, shot_name, file_type)

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/notes", methods=["POST"])
def save_shot_notes():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        notes = data.get("notes", "")

        if not shot_name:
            return jsonify({"success": False, "error": "Shot name required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_shot_notes(shot_name, notes)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/prompt", methods=["POST"])
def save_shot_prompt():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        version = data.get("version")
        prompt = data.get("prompt", "")

        if not shot_name or not asset_type or version is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_prompt(shot_name, asset_type, int(version), prompt)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/prompt", methods=["GET"])
def get_shot_prompt():
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        version = request.args.get("version", type=int)

        if not shot_name or not asset_type or version is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        prompt = shot_manager.load_prompt(shot_name, asset_type, version)

        return jsonify({"success": True, "data": prompt})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/prompt_versions")
@shot_bp.route("/prompt-versions")
def get_prompt_versions():
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        if not shot_name or not asset_type:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        versions = shot_manager.get_prompt_versions(shot_name, asset_type)
        return jsonify({"success": True, "data": versions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/versions")
def get_asset_versions():
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        if not shot_name or not asset_type:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        versions = shot_manager.get_asset_versions(shot_name, asset_type)
        return jsonify({"success": True, "data": versions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/use-version", methods=["POST"])
def use_version():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        version = data.get("version")

        if not shot_name or not asset_type or version is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        file_handler = FileHandler(project['path'])
        result = file_handler.use_version(shot_name, asset_type, int(version))

        shot_manager = get_shot_manager(project["path"])
        prompt = shot_manager.load_prompt(shot_name, asset_type, int(version))
        result['prompt'] = prompt
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/rename", methods=["POST"])
def rename_shot():
    try:
        data = request.get_json()
        old_name = data.get("old_name")
        new_name = data.get("new_name")
        if not old_name or not new_name:
            return jsonify({"success": False, "error": "Old and new names required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.rename_shot(old_name, new_name)

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/create-between", methods=["POST"])
def create_shot_between():
    try:
        data = request.get_json()
        after_shot = data.get("after_shot")

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.create_shot_between(after_shot)

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/thumbnail/<path:filepath>")
def serve_thumbnail(filepath):
    """Serve a thumbnail from the cache directory."""
    try:
        from app.config.constants import THUMBNAIL_CACHE_DIR

        thumb_path = THUMBNAIL_CACHE_DIR / Path(filepath).name
        thumb_dir = THUMBNAIL_CACHE_DIR.resolve()
        thumb_path = thumb_path.resolve()

        if not str(thumb_path).startswith(str(thumb_dir)):
            return "Invalid path", 400

        if thumb_path.is_file():
            return send_file(str(thumb_path))
        return "File not found", 404
    except Exception as e:
        return str(e), 500

@shot_bp.route("/reveal", methods=["POST"])
def reveal_file():
    try:
        data = request.get_json()
        rel_path = data.get("path")
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        file_path = Path(rel_path)
        if not file_path.is_absolute():
            file_path = (Path(project["path"]) / file_path).resolve()
        else:
            file_path = file_path.resolve()

        if not file_path.exists():
            return jsonify({"success": False, "error": f"File does not exist: {file_path}"}), 404

        if platform.system() == "Windows":
            subprocess.Popen(['explorer', '/select,', str(file_path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(['open', '-R', str(file_path)])
        else:
            subprocess.Popen(['xdg-open', str(file_path.parent)])

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shot_bp.route("/open-folder", methods=["POST"])
def open_shots_folder():
    """Open the current project's shots folder in the file browser."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shots_path = Path(project["path"]) / "shots"
        if not shots_path.exists():
            return jsonify({"success": False, "error": "Shots folder missing"}), 404

        if platform.system() == "Windows":
            subprocess.Popen(["explorer", str(shots_path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(shots_path)])
        else:
            subprocess.Popen(["xdg-open", str(shots_path)])

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
