from flask import Blueprint, request, jsonify, send_file, current_app
from pathlib import Path
from werkzeug.utils import secure_filename
import logging

from app.services.reference_manager import ReferenceManager
from app.utils import require_project, error_response, reveal_in_file_browser

logger = logging.getLogger(__name__)

reference_bp = Blueprint('reference', __name__)

@reference_bp.route("/", methods=["GET"])
@require_project
def get_reference_images(project):
    """Get all reference images for the current project."""
    try:
        ref_manager = ReferenceManager(project["path"])
        images = ref_manager.get_reference_images()
        return jsonify({"success": True, "data": images})
    except Exception as e:
        return error_response(str(e), 500)

@reference_bp.route("/upload", methods=["POST"])
@require_project
def upload_reference_image(project):
    """Upload a new reference image."""
    try:
        file = request.files.get('file')
        if not file or file.filename == '':
            return error_response("No file provided")

        # Secure the filename
        filename = secure_filename(file.filename)

        ref_manager = ReferenceManager(project["path"])
        result = ref_manager.save_reference_image(file, filename)

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@reference_bp.route("/rename", methods=["POST"])
@require_project
def rename_reference_image(project):
    """Rename a reference image."""
    try:
        data = request.get_json()
        old_name = data.get("old_name")
        new_name = data.get("new_name")

        if not old_name or not new_name:
            return error_response("Old and new names required")

        # Secure the new filename
        new_name = secure_filename(new_name)

        ref_manager = ReferenceManager(project["path"])
        result = ref_manager.rename_reference_image(old_name, new_name)

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@reference_bp.route("/delete", methods=["POST"])
@require_project
def delete_reference_image(project):
    """Delete a reference image."""
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            return error_response("Filename required")

        ref_manager = ReferenceManager(project["path"])
        ref_manager.delete_reference_image(filename)

        return jsonify({"success": True})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@reference_bp.route("/image/<path:filename>")
@require_project
def serve_reference_image(project, filename):
    """Serve a reference image."""
    try:
        project_path = Path(project["path"])
        image_path = project_path / "ref-images" / filename

        # Security check: ensure the resolved path is within ref-images
        ref_images_dir = (project_path / "ref-images").resolve()
        image_path = image_path.resolve()

        if not str(image_path).startswith(str(ref_images_dir)):
            return error_response("Invalid path")

        if image_path.is_file():
            return send_file(str(image_path))
        return error_response("File not found", 404)
    except Exception as e:
        return error_response(str(e), 500)

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
            return error_response("Invalid path")

        if thumb_path.is_file():
            return send_file(str(thumb_path))
        return error_response("File not found", 404)
    except Exception as e:
        return error_response(str(e), 500)

@reference_bp.route("/reveal", methods=["POST"])
@require_project
def reveal_reference_image(project):
    """Reveal a reference image in the file explorer."""
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            return error_response("Filename required")

        project_path = Path(project["path"])
        file_path = project_path / "ref-images" / filename

        # Security check: ensure the resolved path is within ref-images
        ref_images_dir = (project_path / "ref-images").resolve()
        file_path = file_path.resolve()

        if not str(file_path).startswith(str(ref_images_dir)):
            return error_response("Invalid path")

        if not file_path.exists():
            return error_response(f"File does not exist: {filename}", 404)

        reveal_in_file_browser(file_path)
        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)
