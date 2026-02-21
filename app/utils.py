from pathlib import Path
from functools import wraps
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


class ProjectPaths:
    """Encapsulates common project directory paths.

    This class provides a single source of truth for project directory
    structure, eliminating duplicate path initialization across services.
    """

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.shots_dir = self.project_path / 'shots'
        self.wip_dir = self.shots_dir / 'wip'
        self.latest_images_dir = self.shots_dir / 'latest_images'
        self.latest_videos_dir = self.shots_dir / 'latest_videos'

    def ensure_directories(self):
        """Create all required directories if they don't exist."""
        self.wip_dir.mkdir(parents=True, exist_ok=True)
        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)


def sanitize_path(path_str: str) -> Path:
    """Return a Path object from a potentially quoted string."""
    if path_str is None:
        return None
    cleaned = str(path_str).strip()
    if (
        (cleaned.startswith("'") and cleaned.endswith("'"))
        or (cleaned.startswith('"') and cleaned.endswith('"'))
    ):
        cleaned = cleaned[1:-1]
    return Path(cleaned).expanduser()


def require_project(f):
    """Decorator that ensures a current project exists before running the route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app, jsonify
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400
        return f(project, *args, **kwargs)
    return decorated


def success_response(data=None):
    """Return a standardized JSON success response."""
    from flask import jsonify
    return jsonify({"success": True, "data": data})


def error_response(message, status_code=400):
    """Return a standardized JSON error response."""
    from flask import jsonify
    return jsonify({"success": False, "error": message}), status_code


def reveal_in_file_browser(file_path):
    """Open the system file browser with the specified path selected."""
    file_path = Path(file_path)
    if platform.system() == "Windows":
        subprocess.Popen(['explorer', '/select,', str(file_path)])
    elif platform.system() == "Darwin":
        subprocess.Popen(['open', '-R', str(file_path)])
    else:
        subprocess.Popen(['xdg-open', str(file_path.parent)])


def open_folder_in_browser(folder_path):
    """Open a folder in the system file browser."""
    folder_path = Path(folder_path)
    if platform.system() == "Windows":
        subprocess.Popen(["explorer", str(folder_path)])
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(folder_path)])
    else:
        subprocess.Popen(["xdg-open", str(folder_path)])


def create_image_thumbnail(image_path, thumb_path, size=None):
    """Create a JPEG thumbnail from an image file.

    Args:
        image_path: Path to the source image
        thumb_path: Path where the thumbnail should be saved
        size: Tuple of (width, height) for the thumbnail. Uses THUMBNAIL_SIZE if None.

    Returns:
        str: Path to the created thumbnail, or None on failure
    """
    from PIL import Image
    from app.config.constants import THUMBNAIL_SIZE

    if size is None:
        size = THUMBNAIL_SIZE

    try:
        image_path = Path(image_path)
        thumb_path = Path(thumb_path)
        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        if thumb_path.exists():
            thumb_path.unlink()

        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Convert images with transparency to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (64, 64, 64))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                img = background

            img.save(str(thumb_path), 'JPEG', quality=85)
            return str(thumb_path)

    except Exception as e:
        logger.warning("Error creating image thumbnail: %s", e)
        return None


def create_video_thumbnail(video_path, thumb_path, size=None):
    """Create a JPEG thumbnail from the first frame of a video file.

    Args:
        video_path: Path to the source video
        thumb_path: Path where the thumbnail should be saved
        size: Tuple of (width, height) for the thumbnail. Uses THUMBNAIL_SIZE if None.

    Returns:
        str: Path to the created thumbnail, or None on failure
    """
    import shutil as _shutil
    from PIL import Image
    from app.config.constants import THUMBNAIL_SIZE

    if size is None:
        size = THUMBNAIL_SIZE

    video_path = Path(video_path)
    thumb_path = Path(thumb_path)

    ffmpeg = _shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg not found; skipping video thumbnail for %s", video_path)
        return None

    try:
        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        # Delete existing thumbnail to ensure fresh generation
        if thumb_path.exists():
            thumb_path.unlink()

        tmp_path = thumb_path.with_suffix(".tmp.jpg")

        cmd = [ffmpeg, "-y", "-i", str(video_path), "-frames:v", "1", str(tmp_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with Image.open(tmp_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)

            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (64, 64, 64))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = background

            img.save(str(thumb_path), "JPEG", quality=85)

        tmp_path.unlink(missing_ok=True)
        return str(thumb_path)

    except Exception as e:
        logger.warning("Error creating video thumbnail: %s", e)
        return None
