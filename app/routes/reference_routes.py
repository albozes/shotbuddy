from pathlib import Path
import logging

from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from ..config.constants import THUMBNAIL_CACHE_DIR
from ..services.reference_manager import ReferenceManager
from ..utils import require_project, error_response, reveal_in_file_browser

logger = logging.getLogger(__name__)

reference_bp = Blueprint('reference', __name__)

@reference_bp.route("/", methods=["GET"])
@require_project
def get_reference_images(project):
    """Get all reference images for the current project."""
    try:
        ref_manager = ReferenceManager(project["path"])
        images = ref_manager.get_reference_images()
        result = {"success": True, "data": images}
        if ref_manager.migrated_count:
            result["migrated"] = ref_manager.migrated_count
        return jsonify(result)
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

        # Allow caller to specify a target base name (for versioning onto existing image)
        target_name = request.form.get('target_name')
        if target_name:
            target_name = secure_filename(target_name)
            # Use the target's stem with the uploaded file's extension
            ext = Path(filename).suffix
            filename = Path(target_name).stem + ext

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
    """Serve a reference image from latest/ or a specific WIP version."""
    try:
        ref_manager = ReferenceManager(project["path"])

        version = request.args.get('version', type=int)
        if version:
            base_stem = Path(filename).stem
            wip_file = ref_manager.find_wip_version_file(base_stem, version)
            if wip_file and wip_file.is_file():
                return send_file(str(wip_file))
            return error_response("Version not found", 404)

        image_path = (ref_manager.ref_latest_dir / filename).resolve()
        try:
            image_path.relative_to(ref_manager.ref_latest_dir.resolve())
        except ValueError:
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

        ref_manager = ReferenceManager(project["path"])
        file_path = (ref_manager.ref_latest_dir / filename).resolve()

        try:
            file_path.relative_to(ref_manager.ref_latest_dir.resolve())
        except ValueError:
            return error_response("Invalid path")

        if not file_path.exists():
            return error_response(f"File does not exist: {filename}", 404)

        reveal_in_file_browser(file_path)
        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)

@reference_bp.route("/restore-version", methods=["POST"])
@require_project
def restore_reference_version(project):
    """Restore a specific version of a reference image."""
    try:
        data = request.get_json()
        filename = data.get("filename")
        version = data.get("version")

        if not filename or version is None:
            return error_response("Filename and version required")

        ref_manager = ReferenceManager(project["path"])
        result = ref_manager.restore_reference_version(filename, int(version))

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)
