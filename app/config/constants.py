from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[1]

UPLOAD_FOLDER = os.environ.get('SHOTBUDDY_UPLOAD_FOLDER', 'uploads')
PROJECTS_FILE = 'projects.json'
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'}
ALLOWED_LIPSYNC_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS


class AssetType:
    """Asset type constants for type-safe asset handling."""
    IMAGE = 'image'
    VIDEO = 'video'
    DRIVER = 'driver'
    TARGET = 'target'
    RESULT = 'result'

    LIPSYNC_CUSTOM = 'lipsync_custom'

    # Grouped sets for validation
    MEDIA_TYPES = {IMAGE, VIDEO}
    LIPSYNC_TYPES = {DRIVER, TARGET, RESULT}
    ALL_TYPES = MEDIA_TYPES | LIPSYNC_TYPES | {LIPSYNC_CUSTOM}

# Central thumbnail cache location. Stored inside the application's static
# directory so thumbnails persist across projects. The cache is cleared when
# switching projects or the page is refreshed.
THUMBNAIL_CACHE_DIR = BASE_DIR / "static" / "thumbnails"

# Default thumbnail resolution (width, height)
THUMBNAIL_SIZE = (240, 180)
