from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[1]

UPLOAD_FOLDER = os.environ.get('SHOTBUDDY_UPLOAD_FOLDER', 'uploads')
PROJECTS_FILE = 'projects.json'
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov'}


class AssetType:
    """Asset type constants for type-safe asset handling."""
    IMAGE = 'image'
    VIDEO = 'video'
    DRIVER = 'driver'
    TARGET = 'target'
    RESULT = 'result'

    # Grouped sets for validation
    MEDIA_TYPES = {IMAGE, VIDEO}
    LIPSYNC_TYPES = {DRIVER, TARGET, RESULT}
    ALL_TYPES = MEDIA_TYPES | LIPSYNC_TYPES

# Central thumbnail cache location. Stored inside the application's static
# directory so thumbnails persist across projects. The cache is cleared when
# switching projects or the page is refreshed.
THUMBNAIL_CACHE_DIR = BASE_DIR / "static" / "thumbnails"

# Default thumbnail resolution (width, height)
THUMBNAIL_SIZE = (240, 180)
