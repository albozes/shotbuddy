from datetime import datetime
from pathlib import Path
import logging
import re
import shutil

from .prompt_importer import extract_prompt_from_png
from .shot_manager import get_shot_manager
from ..utils import create_image_thumbnail, create_video_thumbnail, ProjectPaths
from ..config.constants import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_LIPSYNC_EXTENSIONS,
    THUMBNAIL_CACHE_DIR,
    AssetType,
)

VERSION_RE = re.compile(r'_v(\d{3})')

logger = logging.getLogger(__name__)

# Ensure the thumbnail cache directory exists.
THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def resolve_naming_pattern(pattern, project_name, shot_name):
    """Resolve a naming pattern template into a filename base.

    Supported variables: {project}, {shot}, {date}.
    Falls back to shot_name if pattern is empty or missing {shot}.
    """
    if not pattern or '{shot}' not in pattern:
        return shot_name
    try:
        return pattern.format(
            project=project_name,
            shot=shot_name,
            date=datetime.now().strftime('%Y%m%d'),
        )
    except (KeyError, ValueError):
        return shot_name


class FileHandler:
    def __init__(self, project_path, naming_pattern='{shot}'):
        self._paths = ProjectPaths(project_path)
        self._paths.ensure_directories()

        # Expose paths as instance attributes for compatibility
        self.project_path = self._paths.project_path
        self.shots_dir = self._paths.shots_dir
        self.wip_dir = self._paths.wip_dir
        self.latest_images_dir = self._paths.latest_images_dir
        self.latest_videos_dir = self._paths.latest_videos_dir
        self.naming_pattern = naming_pattern

    def clear_thumbnail_cache(self):
        """Remove all files from the thumbnail cache."""
        if not THUMBNAIL_CACHE_DIR.exists():
            THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            return

        for thumb in THUMBNAIL_CACHE_DIR.iterdir():
            if thumb.is_file():
                try:
                    thumb.unlink()
                except Exception as e:
                    logger.warning("Could not delete thumbnail %s: %s", thumb, e)

    def save_file(self, file, shot_name, file_type, custom_label=None):
        """Save uploaded file with proper versioning"""
        shot_dir = self.wip_dir / shot_name
        file_ext = Path(file.filename).suffix.lower()

        if file_type == AssetType.IMAGE and file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")
        elif file_type == AssetType.VIDEO and file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError(f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")
        elif file_type in (AssetType.DRIVER, AssetType.RESULT) and file_ext in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"{file_type.capitalize()} does not accept image files")
        elif file_type in (AssetType.LIPSYNC_TYPES | {AssetType.LIPSYNC_CUSTOM}) and file_ext not in ALLOWED_LIPSYNC_EXTENSIONS:
            raise ValueError(f"Invalid lipsync format. Allowed: {', '.join(ALLOWED_LIPSYNC_EXTENSIONS)}")

        if not shot_dir.exists():
            get_shot_manager(self.project_path).create_shot_structure(shot_name)

        if file_type in AssetType.MEDIA_TYPES:
            wip_dir = shot_dir / ('images' if file_type == AssetType.IMAGE else 'videos')
            base_name = resolve_naming_pattern(
                self.naming_pattern, self.project_path.name, shot_name
            )
            version = self.get_next_version(wip_dir, base_name)
            wip_filename = f'{base_name}_v{version:03d}{file_ext}'
            wip_path = wip_dir / wip_filename
            file.save(str(wip_path))

            final_dir = self.latest_images_dir if file_type == AssetType.IMAGE else self.latest_videos_dir
            final_filename = f'{base_name}{file_ext}'
            final_path = final_dir / final_filename

            # Remove old latest files for this shot (any naming pattern)
            for existing_file in final_dir.glob(f'*{shot_name}*'):
                if existing_file.is_file():
                    existing_file.unlink()

            shutil.copy2(str(wip_path), str(final_path))
            thumb_key = shot_name

            # Attempt to extract embedded prompt metadata from PNG files
            if file_ext == '.png':
                prompt_data = extract_prompt_from_png(final_path)
                if prompt_data and prompt_data.get('prompt'):
                    prompt_text = prompt_data['prompt'].strip()
                    neg = prompt_data.get('negative_prompt', '').strip()
                    if neg:
                        prompt_text += f"\n\nNegative: {neg}"
                    try:
                        manager = get_shot_manager(self.project_path)
                        manager.save_prompt(shot_name, AssetType.IMAGE, version, prompt_text)
                        logger.info("Imported prompt from metadata for %s", final_path)
                    except Exception as e:
                        logger.warning('Failed to save imported prompt: %s', e)
                else:
                    logger.info("No embedded prompt found in %s", final_path)
        else:
            # Lipsync files: driver/target/result or custom-labeled
            if file_type == AssetType.LIPSYNC_CUSTOM:
                if not custom_label:
                    raise ValueError("Custom label is required for custom lipsync files")
                suffix = custom_label
            else:
                suffix = file_type

            dest_dir = shot_dir / 'lipsync'
            dest_dir.mkdir(exist_ok=True)
            base_name = resolve_naming_pattern(
                self.naming_pattern, self.project_path.name, shot_name
            )
            base = f'{base_name}_{suffix}'
            version = self.get_next_version(dest_dir, base)
            wip_filename = f'{base}_v{version:03d}{file_ext}'
            wip_path = dest_dir / wip_filename
            file.save(str(wip_path))

            final_path = wip_path
            thumb_key = f'{shot_name}_{suffix}'

        thumbnail_path = None
        if file_type == AssetType.IMAGE:
            thumbnail_path = self.create_thumbnail(str(final_path), shot_name)
        elif file_ext in ALLOWED_IMAGE_EXTENSIONS:
            thumbnail_path = self.create_thumbnail(str(final_path), thumb_key)
        elif file_ext in ALLOWED_VIDEO_EXTENSIONS:
            thumbnail_path = self.create_video_thumbnail(str(final_path), thumb_key)
        # Audio files get no thumbnail

        return {
            'wip_path': str(wip_path).replace('\\', '/'),
            'final_path': str(final_path).replace('\\', '/'),
            'version': version,
            'thumbnail': f"static/thumbnails/{Path(thumbnail_path).name}" if thumbnail_path else None
        }

    def get_next_version(self, wip_dir, base_name):
        """Get the next available version number for a shot asset.

        Searches for files matching ``{base_name}_v###.*`` in the directory.
        """
        if not wip_dir.exists():
            return 1

        existing_files = list(wip_dir.glob(f'{base_name}_v*'))
        if not existing_files:
            return 1

        versions = []
        for f in existing_files:
            m = VERSION_RE.search(f.stem)
            if m:
                versions.append(int(m.group(1)))

        return max(versions) + 1 if versions else 1

    def count_renameable_files(self):
        """Count files that would be renamed by apply_naming_pattern."""
        file_count = 0
        shot_count = 0
        project_name = self.project_path.name

        if not self.wip_dir.exists():
            return 0, 0

        all_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

        for shot_dir in sorted(self.wip_dir.iterdir()):
            if not shot_dir.is_dir() or not shot_dir.name.startswith('SH'):
                continue

            shot_name = shot_dir.name
            base_name = resolve_naming_pattern(
                self.naming_pattern, project_name, shot_name
            )
            shot_has_renames = False

            for subdir_name in ('images', 'videos'):
                subdir = shot_dir / subdir_name
                if not subdir.exists():
                    continue
                for f in subdir.iterdir():
                    if not f.is_file() or f.suffix.lower() not in all_extensions:
                        continue
                    m = VERSION_RE.search(f.stem)
                    if not m:
                        continue
                    new_name = f'{base_name}_v{m.group(1)}{f.suffix}'
                    if f.name != new_name:
                        file_count += 1
                        shot_has_renames = True

            # Check latest files
            for latest_dir in (self.latest_images_dir, self.latest_videos_dir):
                if not latest_dir.exists():
                    continue
                for f in latest_dir.glob(f'*{shot_name}*'):
                    if not f.is_file() or f.suffix.lower() not in all_extensions:
                        continue
                    new_name = f'{base_name}{f.suffix}'
                    if f.name != new_name:
                        file_count += 1
                        shot_has_renames = True

            if shot_has_renames:
                shot_count += 1

        return file_count, shot_count

    def apply_naming_pattern(self):
        """Rename all existing WIP and latest files to match the current naming pattern.

        Returns:
            dict with 'renamed' and 'errors' counts.
        """
        stats = {'renamed': 0, 'errors': 0}
        project_name = self.project_path.name

        if not self.wip_dir.exists():
            return stats

        all_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

        for shot_dir in sorted(self.wip_dir.iterdir()):
            if not shot_dir.is_dir() or not shot_dir.name.startswith('SH'):
                continue

            shot_name = shot_dir.name
            base_name = resolve_naming_pattern(
                self.naming_pattern, project_name, shot_name
            )

            # Rename WIP versioned files (images and videos)
            for subdir_name in ('images', 'videos'):
                subdir = shot_dir / subdir_name
                if not subdir.exists():
                    continue
                for f in sorted(subdir.iterdir()):
                    if not f.is_file() or f.suffix.lower() not in all_extensions:
                        continue
                    m = VERSION_RE.search(f.stem)
                    if not m:
                        continue
                    new_name = f'{base_name}_v{m.group(1)}{f.suffix}'
                    if f.name == new_name:
                        continue
                    try:
                        f.rename(subdir / new_name)
                        stats['renamed'] += 1
                    except OSError as e:
                        logger.error("Failed to rename %s: %s", f, e)
                        stats['errors'] += 1

            # Rename latest files for this shot
            for latest_dir in (self.latest_images_dir, self.latest_videos_dir):
                if not latest_dir.exists():
                    continue
                for f in list(latest_dir.glob(f'*{shot_name}*')):
                    if not f.is_file() or f.suffix.lower() not in all_extensions:
                        continue
                    new_name = f'{base_name}{f.suffix}'
                    if f.name == new_name:
                        continue
                    try:
                        f.rename(latest_dir / new_name)
                        stats['renamed'] += 1
                    except OSError as e:
                        logger.error("Failed to rename %s: %s", f, e)
                        stats['errors'] += 1

        return stats

    def create_thumbnail(self, image_path, shot_name):
        """Create thumbnail for image and save it to the central cache."""
        image_path = Path(image_path)
        project_name = self.project_path.name
        thumb_filename = f"{project_name}_{shot_name}_{image_path.stem}_thumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename
        return create_image_thumbnail(image_path, thumb_path)

    def create_video_thumbnail(self, video_path, shot_name):
        """Extract the first frame of ``video_path`` and save it as a thumbnail."""
        video_path = Path(video_path)
        project_name = self.project_path.name
        thumb_filename = f"{project_name}_{shot_name}_{video_path.stem}_vthumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename
        return create_video_thumbnail(video_path, thumb_path)
