from pathlib import Path
import logging

from flask import Blueprint, request, jsonify, send_file, current_app

from ..services.shot_manager import get_shot_manager
from ..services.file_handler import FileHandler, resolve_naming_pattern
from ..utils import (
    require_project,
    error_response,
    reveal_in_file_browser,
    open_folder_in_browser,
    create_image_thumbnail,
    create_video_thumbnail,
)
from ..config.constants import (
    AssetType,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    THUMBNAIL_CACHE_DIR,
)

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


@shot_bp.route("/", strict_slashes=False, methods=["GET"])
@require_project
def get_shots(project):
    try:
        shot_manager = get_shot_manager(project["path"])
        shots = shot_manager.get_shots(generate=False)
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

        custom_label = request.form.get('custom_label')

        project_manager = current_app.config['PROJECT_MANAGER']
        settings = project_manager.get_settings()
        naming_pattern = settings.get('file_naming_pattern', '{shot}')
        file_handler = FileHandler(project['path'], naming_pattern=naming_pattern)
        result = file_handler.save_file(file, shot_name, file_type, custom_label=custom_label)

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

        # Update shot_artists mapping for the renamed shot
        project_manager = current_app.config['PROJECT_MANAGER']
        shared_data = project_manager.load_shared_project_data()
        shot_artists = shared_data.get('shot_artists', {})
        if old_name in shot_artists:
            shot_artists[new_name] = shot_artists.pop(old_name)
            shared_data['shot_artists'] = shot_artists
            project_manager.save_shared_project_data(shared_data)

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response(str(e), 500)

@shot_bp.route("/delete", methods=["POST"])
@require_project
def delete_shot(project):
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        if not shot_name:
            return error_response("Shot name required")

        shot_manager = get_shot_manager(project["path"])
        shot_manager.delete_empty_shot(shot_name)

        # Remove shot_artists mapping for the deleted shot
        project_manager = current_app.config['PROJECT_MANAGER']
        shared_data = project_manager.load_shared_project_data()
        shot_artists = shared_data.get('shot_artists', {})
        if shot_name in shot_artists:
            del shot_artists[shot_name]
            shared_data['shot_artists'] = shot_artists
            project_manager.save_shared_project_data(shared_data)

        return jsonify({"success": True})
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

        if shot_name and asset_type:
            naming_pattern = settings.get('file_naming_pattern', '{shot}')
            base_name = resolve_naming_pattern(naming_pattern, project_path.name, shot_name)
            ext = Path(rel_path).suffix

            if thumbnail_behavior == 'latest_folder':
                subfolder = 'latest_images' if asset_type == AssetType.IMAGE else 'latest_videos'
                file_to_select = project_path / 'shots' / subfolder / f'{base_name}{ext}'

            elif thumbnail_behavior == 'version_folder':
                shot_manager = get_shot_manager(project["path"])
                shot_info = shot_manager.get_shot_info(shot_name)
                version = shot_info.get(asset_type, {}).get('version', 0)
                if version > 0:
                    media_dir = 'images' if asset_type == AssetType.IMAGE else 'videos'
                    file_to_select = project_path / 'shots' / 'wip' / shot_name / media_dir / f'{base_name}_v{version:03d}{ext}'

        if file_to_select and file_to_select.exists():
            reveal_in_file_browser(file_to_select)
            return jsonify({"success": True})

        # Fallback: open the shot's media folder directly
        if shot_name and asset_type:
            media_dir = 'images' if asset_type == AssetType.IMAGE else 'videos'
            folder = project_path / 'shots' / 'wip' / shot_name / media_dir
            if folder.exists():
                open_folder_in_browser(folder)
                return jsonify({"success": True})

        return error_response("File not found", 404)
    except Exception as e:
        return error_response(str(e), 500)


@shot_bp.route("/open-folder", methods=["POST"])
@require_project
def open_shots_folder(project):
    """Open the current project's shots folder in the file browser."""
    try:
        data = request.get_json() or {}
        shot_name = data.get("shot_name")
        subfolder = data.get("subfolder")

        if shot_name and subfolder:
            folder_path = Path(project["path"]) / "shots" / "wip" / shot_name / subfolder
        else:
            folder_path = Path(project["path"]) / "shots"

        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)

        open_folder_in_browser(folder_path)
        return jsonify({"success": True})
    except Exception as e:
        return error_response(str(e), 500)


@shot_bp.route("/serve-video")
@require_project
def serve_video(project):
    """Serve a video file for preview playback."""
    try:
        video_path = request.args.get("path")
        if not video_path:
            return error_response("Video path required")

        video_path = Path(video_path).resolve()
        project_path = Path(project["path"]).resolve()

        # Security check: ensure video is within project directory
        try:
            video_path.relative_to(project_path)
        except ValueError:
            return error_response("Invalid video path", 403)

        if not video_path.exists():
            return error_response("Video not found", 404)

        return send_file(
            str(video_path),
            mimetype='video/mp4',
            conditional=True
        )
    except Exception as e:
        logger.error("Error serving video: %s", e)
        return error_response(str(e), 500)


@shot_bp.route("/refresh-thumbnails", methods=["POST"])
@require_project
def refresh_thumbnails(project):
    """Clear and regenerate all thumbnails for the current project."""
    try:
        project_name = Path(project["path"]).name

        # Delete all thumbnails for this project
        deleted_count = 0
        if THUMBNAIL_CACHE_DIR.exists():
            for thumb_file in THUMBNAIL_CACHE_DIR.iterdir():
                if thumb_file.name.startswith(f"{project_name}_"):
                    thumb_file.unlink()
                    deleted_count += 1

        logger.info("Deleted %d thumbnails for project %s", deleted_count, project_name)

        # Sync latest folders first so deleted/missing files are rebuilt from WIP
        shot_manager = get_shot_manager(project["path"])
        shot_manager.sync_latest_folders()

        # Regenerate by loading all shots (which triggers thumbnail creation)
        shots = shot_manager.get_shots()

        return jsonify({
            "success": True,
            "message": f"Regenerated thumbnails for {len(shots)} shots"
        })
    except Exception as e:
        logger.error("Error refreshing thumbnails: %s", e)
        return error_response(str(e), 500)


@shot_bp.route("/sync-latest", methods=["POST"])
@require_project
def sync_latest(project):
    """Sync latest_images/ and latest_videos/ with the highest WIP versions."""
    try:
        shot_manager = get_shot_manager(project["path"])
        stats = shot_manager.sync_latest_folders()
        return jsonify({
            "success": True,
            "data": stats,
            "message": f"Synced {stats['synced']}, removed {stats['removed']} orphans, {stats['errors']} errors"
        })
    except Exception as e:
        logger.error("Error syncing latest folders: %s", e)
        return error_response(str(e), 500)


@shot_bp.route("/generate-thumbnail", methods=["POST"])
@require_project
def generate_thumbnail(project):
    """Generate thumbnail on-demand for a specific shot asset.

    Used for lazy-loading thumbnails after initial page load.
    """
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")  # 'image', 'video', 'driver', 'target', 'result'

        if not shot_name or not asset_type:
            return error_response("shot_name and asset_type required")

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.get_shot_info(shot_name)

        # Get the file path for the requested asset
        if asset_type == AssetType.IMAGE:
            file_path = shot_info['image'].get('file')
            if file_path:
                thumbnail = shot_manager.get_thumbnail_path(file_path, shot_name, generate=True)
                return jsonify({"success": True, "thumbnail": thumbnail})
        elif asset_type == AssetType.VIDEO:
            file_path = shot_info['video'].get('file')
            if file_path:
                thumbnail = shot_manager.get_video_thumbnail_path(file_path, shot_name, generate=True)
                return jsonify({"success": True, "thumbnail": thumbnail})
        elif asset_type in AssetType.LIPSYNC_TYPES:
            lipsync_info = shot_info['lipsync'].get(asset_type, {})
            file_path = lipsync_info.get('file')
            if file_path:
                thumbnail = shot_manager.get_video_thumbnail_path(file_path, f"{shot_name}_{asset_type}", generate=True)
                return jsonify({"success": True, "thumbnail": thumbnail})

        return jsonify({"success": True, "thumbnail": None})
    except Exception as e:
        logger.error("Error generating thumbnail: %s", e)
        return error_response(str(e), 500)


@shot_bp.route("/restore-version", methods=["POST"])
@require_project
def restore_version(project):
    """Restore a previous version to the latest folder."""
    try:
        import shutil

        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        version = data.get("version")

        if not shot_name or not asset_type or version is None:
            return error_response("Missing required parameters")

        project_path = Path(project["path"])

        project_manager = current_app.config['PROJECT_MANAGER']
        settings = project_manager.get_settings()
        naming_pattern = settings.get('file_naming_pattern', '{shot}')
        base_name = resolve_naming_pattern(naming_pattern, project_path.name, shot_name)

        # Determine paths based on asset type
        if asset_type == AssetType.IMAGE:
            wip_dir = project_path / "shots" / "wip" / shot_name / "images"
            latest_dir = project_path / "shots" / "latest_images"
            extensions = ALLOWED_IMAGE_EXTENSIONS
        elif asset_type == AssetType.VIDEO:
            wip_dir = project_path / "shots" / "wip" / shot_name / "videos"
            latest_dir = project_path / "shots" / "latest_videos"
            extensions = ALLOWED_VIDEO_EXTENSIONS
        else:
            return error_response(f"Invalid asset type: {asset_type}")

        # Find the versioned file
        version_file = _find_file_with_extensions(
            wip_dir,
            f"{base_name}_v{version:03d}",
            extensions
        )

        if not version_file:
            return error_response(f"Version {version} not found")

        # Remove existing files in latest folder for this shot
        for ext in extensions:
            existing = latest_dir / f"{base_name}{ext}"
            if existing.exists():
                existing.unlink()

        # Copy the versioned file to latest folder
        dest_path = latest_dir / f"{base_name}{version_file.suffix}"
        shutil.copy2(str(version_file), str(dest_path))

        # Regenerate thumbnail for the restored version
        project_name = project_path.name
        if asset_type == AssetType.IMAGE:
            thumb_filename = f"{project_name}_{shot_name}_{dest_path.stem}_thumb.jpg"
            thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename
            create_image_thumbnail(dest_path, thumb_path)
        else:
            thumb_filename = f"{project_name}_{shot_name}_{dest_path.stem}_vthumb.jpg"
            thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename
            create_video_thumbnail(dest_path, thumb_path)

        thumbnail_url = f"/static/thumbnails/{thumb_filename}"

        # For videos, also return the file path for hover preview
        file_path = str(dest_path) if asset_type == AssetType.VIDEO else None

        logger.info("Restored %s %s version %d", shot_name, asset_type, version)
        return jsonify({
            "success": True,
            "thumbnail": thumbnail_url,
            "file_path": file_path
        })
    except Exception as e:
        logger.error("Error restoring version: %s", e)
        return error_response(str(e), 500)


@shot_bp.route("/generate-thumbnails-batch", methods=["POST"])
@require_project
def generate_thumbnails_batch(project):
    """Generate multiple thumbnails in a single request.

    Expects: { "items": [{"shot_name": "SH010", "asset_type": "image"}, ...] }
    Returns: { "success": true, "thumbnails": {"SH010-image": "/static/thumbnails/...", ...} }
    """
    try:
        data = request.get_json()
        items = data.get("items", [])

        if not items:
            return jsonify({"success": True, "thumbnails": {}})

        shot_manager = get_shot_manager(project["path"])
        thumbnails = {}

        # Cache shot info to avoid repeated lookups
        shot_info_cache = {}

        for item in items:
            shot_name = item.get("shot_name")
            asset_type = item.get("asset_type")

            if not shot_name or not asset_type:
                continue

            key = f"{shot_name}-{asset_type}"

            # Get shot info (cached)
            if shot_name not in shot_info_cache:
                try:
                    shot_info_cache[shot_name] = shot_manager.get_shot_info(shot_name)
                except Exception:
                    continue

            shot_info = shot_info_cache[shot_name]

            try:
                if asset_type == AssetType.IMAGE:
                    file_path = shot_info['image'].get('file')
                    if file_path:
                        thumbnails[key] = shot_manager.get_thumbnail_path(file_path, shot_name, generate=True)
                elif asset_type == AssetType.VIDEO:
                    file_path = shot_info['video'].get('file')
                    if file_path:
                        thumbnails[key] = shot_manager.get_video_thumbnail_path(file_path, shot_name, generate=True)
                elif asset_type in AssetType.LIPSYNC_TYPES:
                    lipsync_info = shot_info['lipsync'].get(asset_type, {})
                    file_path = lipsync_info.get('file')
                    if file_path:
                        thumbnails[key] = shot_manager.get_video_thumbnail_path(file_path, f"{shot_name}_{asset_type}", generate=True)
            except Exception as e:
                logger.warning("Failed to generate thumbnail for %s: %s", key, e)

        return jsonify({"success": True, "thumbnails": thumbnails})
    except Exception as e:
        logger.error("Error generating thumbnails batch: %s", e)
        return error_response(str(e), 500)
