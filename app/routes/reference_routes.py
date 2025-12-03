from flask import Blueprint, request, jsonify, send_file, current_app
from pathlib import Path
from werkzeug.utils import secure_filename
import subprocess
import platform

from app.services.reference_manager import ReferenceManager

reference_bp = Blueprint('reference', __name__)

@reference_bp.route("/", methods=["GET"])
def get_reference_images():
    """Get all reference images for the current project."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        ref_manager = ReferenceManager(project["path"])
        images = ref_manager.get_reference_images()
        return jsonify({"success": True, "data": images})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@reference_bp.route("/upload", methods=["POST"])
def upload_reference_image():
    """Upload a new reference image."""
    try:
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({"success": False, "error": "No file provided"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        # Secure the filename
        filename = secure_filename(file.filename)

        ref_manager = ReferenceManager(project["path"])
        result = ref_manager.save_reference_image(file, filename)

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@reference_bp.route("/rename", methods=["POST"])
def rename_reference_image():
    """Rename a reference image."""
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

        # Secure the new filename
        new_name = secure_filename(new_name)

        ref_manager = ReferenceManager(project["path"])
        result = ref_manager.rename_reference_image(old_name, new_name)

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@reference_bp.route("/delete", methods=["POST"])
def delete_reference_image():
    """Delete a reference image."""
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            return jsonify({"success": False, "error": "Filename required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        ref_manager = ReferenceManager(project["path"])
        ref_manager.delete_reference_image(filename)

        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@reference_bp.route("/image/<path:filename>")
def serve_reference_image(filename):
    """Serve a reference image."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        project_path = Path(project["path"])
        image_path = project_path / "ref-images" / filename

        # Security check: ensure the resolved path is within ref-images
        ref_images_dir = (project_path / "ref-images").resolve()
        image_path = image_path.resolve()

        if not str(image_path).startswith(str(ref_images_dir)):
            return "Invalid path", 400

        if image_path.is_file():
            return send_file(str(image_path))
        return "File not found", 404
    except Exception as e:
        return str(e), 500

@reference_bp.route("/thumbnail/<path:filename>")
def serve_reference_thumbnail(filename):
    """Serve a reference image thumbnail from the cache directory."""
    try:
        from app.config.constants import THUMBNAIL_CACHE_DIR

        thumb_path = THUMBNAIL_CACHE_DIR / Path(filename).name
        thumb_dir = THUMBNAIL_CACHE_DIR.resolve()
        thumb_path = thumb_path.resolve()

        # Security check: ensure the resolved path is within thumbnail cache
        if not str(thumb_path).startswith(str(thumb_dir)):
            return "Invalid path", 400

        if thumb_path.is_file():
            return send_file(str(thumb_path))
        return "File not found", 404
    except Exception as e:
        return str(e), 500

@reference_bp.route("/reveal", methods=["POST"])
def reveal_reference_image():
    """Reveal a reference image in the file explorer."""
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            return jsonify({"success": False, "error": "Filename required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        project_path = Path(project["path"])
        file_path = project_path / "ref-images" / filename

        # Security check: ensure the resolved path is within ref-images
        ref_images_dir = (project_path / "ref-images").resolve()
        file_path = file_path.resolve()

        if not str(file_path).startswith(str(ref_images_dir)):
            return jsonify({"success": False, "error": "Invalid path"}), 400

        if not file_path.exists():
            return jsonify({"success": False, "error": f"File does not exist: {filename}"}), 404

        # Reveal the file in the appropriate file explorer
        if platform.system() == "Windows":
            subprocess.Popen(['explorer', '/select,', str(file_path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(['open', '-R', str(file_path)])
        else:
            subprocess.Popen(['xdg-open', str(file_path.parent)])

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
