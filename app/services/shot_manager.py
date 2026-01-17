from pathlib import Path
import logging
import re

from app.utils import create_image_thumbnail, create_video_thumbnail, ProjectPaths

logger = logging.getLogger(__name__)

# Shot names may optionally contain a single underscore followed by another
# three-digit number (e.g. ``SH001_050``).  Deeper nesting with multiple
# underscores is not allowed.
SHOT_NAME_RE = re.compile(r"^SH\d{3}(?:_\d{3})?$")

# Shot numbering constants
SHOT_NUMBER_INCREMENT = 10  # Shots are numbered in increments of 10 (SH010, SH020, etc.)
INITIAL_SHOT_NUMBER = 10    # First shot starts at SH010
INITIAL_SUBSHOT_NUMBER = 50 # Sub-shots start at _050 (e.g., SH010_050)


def validate_shot_name(name):
    if not SHOT_NAME_RE.match(name):
        raise ValueError(f"Invalid shot name: {name}")
    if name == "SH000":
        raise ValueError("Invalid shot name: SH000")


def _parse_shot_parts(name):
    """Return the numeric segments for a shot name."""
    return [int(p) for p in name[2:].split("_")]


def _format_shot_parts(parts):
    """Format numeric segments back into a shot name."""
    base = f"SH{parts[0]:03d}"
    for p in parts[1:]:
        base += f"_{p:03d}"
    return base

from app.config.constants import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    THUMBNAIL_CACHE_DIR,
    AssetType,
)

class ShotManager:
    def __init__(self, project_path):
        self._paths = ProjectPaths(project_path)
        self._paths.ensure_directories()

        # Expose paths as instance attributes for compatibility
        self.project_path = self._paths.project_path
        self.shots_dir = self._paths.shots_dir
        self.wip_dir = self._paths.wip_dir
        self.latest_images_dir = self._paths.latest_images_dir
        self.latest_videos_dir = self._paths.latest_videos_dir
        self.legacy_dir = self.project_path / '_legacy'

    @staticmethod
    def _normalize_path(path):
        """Return a POSIX-style absolute path string or ``None``."""
        if not path:
            return None
        return str(Path(path).resolve()).replace("\\", "/")

    def _rename_versioned_files(self, directory, old_name, new_name, prompt_suffix=None):
        """Rename versioned asset files and their prompts in a directory.

        Args:
            directory: Path to the directory containing files
            old_name: The old shot name prefix
            new_name: The new shot name prefix
            prompt_suffix: Optional suffix for prompt files (e.g., '_image_prompt.txt')
        """
        if not directory.exists():
            return

        logger.info(f"Renaming files in {directory}")

        # Rename versioned asset files (exclude prompt files)
        for f in directory.glob(f"{old_name}_v*.*"):
            if not f.name.endswith('_prompt.txt'):
                new_name_file = f.name.replace(old_name, new_name, 1)
                logger.info(f"  Renaming {f.name} -> {new_name_file}")
                f.rename(directory / new_name_file)

        # Rename prompt files if suffix specified
        if prompt_suffix:
            for f in directory.glob(f"{old_name}_v*{prompt_suffix}"):
                new_name_file = f.name.replace(old_name, new_name, 1)
                logger.info(f"  Renaming prompt {f.name} -> {new_name_file}")
                f.rename(directory / new_name_file)

    def _rename_lipsync_files(self, lipsync_dir, old_name, new_name):
        """Rename all lipsync-related files (driver, target, result)."""
        if not lipsync_dir.exists():
            return

        logger.info(f"Renaming files in {lipsync_dir}")
        for part in ["driver", "target", "result"]:
            # Rename non-versioned lipsync files
            for ext in ALLOWED_VIDEO_EXTENSIONS:
                src = lipsync_dir / f"{old_name}_{part}{ext}"
                if src.exists():
                    new_name_file = f"{new_name}_{part}{ext}"
                    logger.info(f"  Renaming {src.name} -> {new_name_file}")
                    src.rename(lipsync_dir / new_name_file)

            # Rename versioned lipsync files
            for f in lipsync_dir.glob(f"{old_name}_{part}_v*.*"):
                if not f.name.endswith('_prompt.txt'):
                    new_name_file = f.name.replace(old_name, new_name, 1)
                    logger.info(f"  Renaming {f.name} -> {new_name_file}")
                    f.rename(lipsync_dir / new_name_file)

            # Rename lipsync prompt files
            for f in lipsync_dir.glob(f"{old_name}_{part}_v*_prompt.txt"):
                new_name_file = f.name.replace(old_name, new_name, 1)
                logger.info(f"  Renaming prompt {f.name} -> {new_name_file}")
                f.rename(lipsync_dir / new_name_file)

    def _rename_latest_files(self, old_name, new_name):
        """Rename files in the latest_images and latest_videos directories."""
        logger.info(f"Renaming files in {self.latest_images_dir}")
        for ext in ALLOWED_IMAGE_EXTENSIONS:
            src = self.latest_images_dir / f"{old_name}{ext}"
            if src.exists():
                new_name_file = f"{new_name}{ext}"
                logger.info(f"  Renaming {src.name} -> {new_name_file}")
                src.rename(self.latest_images_dir / new_name_file)

        logger.info(f"Renaming files in {self.latest_videos_dir}")
        for ext in ALLOWED_VIDEO_EXTENSIONS:
            src = self.latest_videos_dir / f"{old_name}{ext}"
            if src.exists():
                new_name_file = f"{new_name}{ext}"
                logger.info(f"  Renaming {src.name} -> {new_name_file}")
                src.rename(self.latest_videos_dir / new_name_file)

    def _rename_thumbnails(self, old_name, new_name):
        """Rename cached thumbnails for a shot."""
        if not THUMBNAIL_CACHE_DIR.exists():
            return

        logger.info(f"Renaming thumbnails in {THUMBNAIL_CACHE_DIR}")
        project_name = self.project_path.name
        for thumb in THUMBNAIL_CACHE_DIR.glob(f"{project_name}_{old_name}_*"):
            new_name_file = thumb.name.replace(
                f"{project_name}_{old_name}_",
                f"{project_name}_{new_name}_",
                1
            )
            logger.info(f"  Renaming thumbnail {thumb.name} -> {new_name_file}")
            thumb.rename(THUMBNAIL_CACHE_DIR / new_name_file)

    def rename_shot(self, old_name, new_name):
        """Rename a shot and all associated files."""
        validate_shot_name(old_name)
        validate_shot_name(new_name)
        old_dir = self.wip_dir / old_name
        new_dir = self.wip_dir / new_name

        if not old_dir.exists():
            raise ValueError(f"Shot {old_name} does not exist")
        if new_dir.exists():
            raise ValueError(f"Shot {new_name} already exists")

        logger.info(f"Renaming shot from {old_name} to {new_name}")

        # Rename the shot folder
        old_dir.rename(new_dir)

        # Rename files in each subdirectory
        self._rename_versioned_files(new_dir / "images", old_name, new_name, "_image_prompt.txt")
        self._rename_versioned_files(new_dir / "videos", old_name, new_name, "_video_prompt.txt")
        self._rename_lipsync_files(new_dir / "lipsync", old_name, new_name)

        # Rename files in latest folders and thumbnails
        self._rename_latest_files(old_name, new_name)
        self._rename_thumbnails(old_name, new_name)

        logger.info(f"Successfully renamed shot from {old_name} to {new_name}")
        return self.get_shot_info(new_name)

    def create_shot_structure(self, shot_name):
        """Create folder structure for a shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        shot_dir.mkdir(parents=True, exist_ok=True)

        # Create subfolders
        (shot_dir / 'images').mkdir(exist_ok=True)
        (shot_dir / 'videos').mkdir(exist_ok=True)
        (shot_dir / 'lipsync').mkdir(exist_ok=True)

        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)

        return shot_dir

    def get_next_shot_number(self):
        """Get next available shot number."""
        existing_shots = []
        if self.wip_dir.exists():
            for shot_dir in self.wip_dir.iterdir():
                if shot_dir.is_dir() and shot_dir.name.startswith('SH'):
                    try:
                        existing_shots.append(int(shot_dir.name[2:]))
                    except ValueError:
                        continue

        next_num = (max(existing_shots) + SHOT_NUMBER_INCREMENT) if existing_shots else INITIAL_SHOT_NUMBER
        if next_num > 999:
            raise ValueError("Cannot create more shots: shot number would exceed 999. Consider splitting your project into individual sequences.")
        return next_num

    def get_shots(self):
        """Get all shots in the project."""
        if not self.wip_dir.exists():
            return []

        shots = []
        for shot_dir in sorted(self.wip_dir.iterdir()):
            if shot_dir.is_dir() and shot_dir.name.startswith('SH'):
                shots.append(self.get_shot_info(shot_dir.name))
        return shots

    def create_shot_between(self, after_shot=None):
        """Create a new shot between existing shots.

        Parameters
        ----------
        after_shot : str or None
            Name of the shot after which the new shot should be inserted. If
            ``None`` the new shot is inserted before the first existing one.

        Returns
        -------
        dict
            Shot information for the newly created shot.
        """

        if after_shot:
            validate_shot_name(after_shot)

        existing = [s["name"] for s in self.get_shots()]

        if not after_shot:
            # Insert before the first shot using the original numeric scheme
            if not existing:
                new_number = INITIAL_SHOT_NUMBER
            else:
                first_number = min(int(s[2:]) for s in existing)
                candidate = max(first_number // 2, 1)
                existing_numbers = {int(s[2:]) for s in existing}
                while candidate in existing_numbers and candidate > 1:
                    candidate -= 1
                if candidate in existing_numbers:
                    raise ValueError("No available shot numbers before first shot")
                new_number = candidate
            shot_name = f"SH{new_number:03d}"
        else:
            base_shot = after_shot.split('_')[0]

            if '_' in after_shot:
                # After a sub-shot: simply append a new sub-shot for the same base
                shot_name = self._create_subshot_name(base_shot, existing)
            else:
                after_num = int(base_shot[2:])
                next_numbers = sorted(
                    n for n in (int(s[2:5]) for s in existing if '_' not in s) if n > after_num
                )

                if next_numbers:
                    next_num = next_numbers[0]
                    if next_num - after_num > 1:
                        new_number = after_num + ((next_num - after_num) // 2)
                        shot_name = f"SH{new_number:03d}"
                    else:
                        shot_name = self._create_subshot_name(base_shot, existing)
                else:
                    new_number = after_num + SHOT_NUMBER_INCREMENT
                    shot_name = f"SH{new_number:03d}"

        validate_shot_name(shot_name)
        if shot_name in existing:
            raise ValueError(f"Shot {shot_name} already exists")

        self.create_shot_structure(shot_name)
        return self.get_shot_info(shot_name)

    def _create_subshot_name(self, base_shot, existing):
        """Return a new sub-shot name under ``base_shot``.

        ``base_shot`` should be a top-level shot name (no underscore).  The new
        name will use a three-digit sub-shot number starting at ``050`` and
        increasing in steps of 10.  Only a single underscore level is allowed.
        """

        if '_' in base_shot:
            raise ValueError('Nested sub-shots are not supported')

        prefix = base_shot + '_'
        sub_numbers = []
        for name in existing:
            if name.startswith(prefix) and '_' not in name[len(prefix):]:
                try:
                    sub_numbers.append(int(name.split('_')[1]))
                except ValueError:
                    continue

        next_num = (max(sub_numbers) + SHOT_NUMBER_INCREMENT) if sub_numbers else INITIAL_SUBSHOT_NUMBER
        if next_num > 999:
            raise ValueError('No available sub-shot numbers')

        return f"{base_shot}_{next_num:03d}"

    def _load_shot_notes(self, shot_dir):
        """Load notes from a shot directory."""
        notes_file = shot_dir / 'notes.txt'
        if notes_file.exists():
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except (IOError, OSError) as e:
                logger.warning("Failed to read notes file %s: %s", notes_file, e)
        return ''

    def _get_asset_info(self, shot_name, shot_dir, asset_type):
        """Get info for an image or video asset.

        Args:
            shot_name: Name of the shot
            shot_dir: Path to the shot directory
            asset_type: AssetType.IMAGE or AssetType.VIDEO

        Returns:
            dict with file, version, thumbnail, and prompt keys
        """
        if asset_type == AssetType.IMAGE:
            final_dir = self.latest_images_dir
            wip_subdir = 'images'
            extensions = ALLOWED_IMAGE_EXTENSIONS
            get_thumb = self.get_thumbnail_path
        else:
            final_dir = self.latest_videos_dir
            wip_subdir = 'videos'
            extensions = ALLOWED_VIDEO_EXTENSIONS
            get_thumb = self.get_video_thumbnail_path

        file_path, version = self._get_latest_asset(
            final_dir, shot_dir / wip_subdir, shot_name, extensions
        )
        file_path = self._normalize_path(file_path)

        prompt = ''
        if version > 0:
            prompt = self.load_prompt(shot_name, asset_type, version)

        thumbnail = get_thumb(file_path, shot_name) if file_path else None

        return {
            'file': file_path,
            'version': version,
            'thumbnail': thumbnail,
            'prompt': prompt,
        }

    def _get_lipsync_info(self, shot_name, shot_dir):
        """Get info for all lipsync assets (driver, target, result)."""
        lipsync_dir = shot_dir / 'lipsync'
        lipsync = {}

        for part in [AssetType.DRIVER, AssetType.TARGET, AssetType.RESULT]:
            file_path, ver = self._get_latest_asset(
                lipsync_dir, lipsync_dir,
                f'{shot_name}_{part}', ALLOWED_VIDEO_EXTENSIONS
            )
            file_path = self._normalize_path(file_path)

            prompt_text = ''
            if ver > 0:
                prompt_text = self.load_prompt(shot_name, part, ver)

            thumbnail = None
            if file_path:
                thumbnail = self.get_video_thumbnail_path(file_path, f"{shot_name}_{part}")

            lipsync[part] = {
                'file': file_path,
                'version': ver,
                'thumbnail': thumbnail,
                'prompt': prompt_text,
            }

        return lipsync

    def get_shot_info(self, shot_name):
        """Get information about a specific shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name

        notes = self._load_shot_notes(shot_dir)
        image_info = self._get_asset_info(shot_name, shot_dir, AssetType.IMAGE)
        video_info = self._get_asset_info(shot_name, shot_dir, AssetType.VIDEO)
        lipsync_info = self._get_lipsync_info(shot_name, shot_dir)

        logger.debug("%s -> Image thumbnail: %s", shot_name, image_info['thumbnail'])
        logger.debug("%s -> Video thumbnail: %s", shot_name, video_info['thumbnail'])

        return {
            'name': shot_name,
            'notes': notes,
            'image': image_info,
            'video': video_info,
            'lipsync': lipsync_info,
            'archived': False  # TODO: Implement archiving
        }


    def _get_latest_asset(self, final_dir, wip_dir, shot_name, extensions):
        """Helper for finding the latest final or highest versioned WIP asset."""
        latest_final = None
        if final_dir.exists():
            for ext in extensions:
                candidate = final_dir / f'{shot_name}{ext}'
                if candidate.exists():
                    latest_final = str(candidate)
                    break

        version = 0
        if wip_dir.exists():
            wip_files = []
            for ext in extensions:
                wip_files.extend(wip_dir.glob(f'{shot_name}_v*{ext}'))

            versions = []
            for f in wip_files:
                try:
                    version_str = f.stem.split('_v')[1]
                    versions.append(int(version_str))
                except (IndexError, ValueError):
                    continue

            if versions:
                version = max(versions)

        return latest_final, version

    def save_shot_notes(self, shot_name, notes):
        """Save notes for a shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        if not shot_dir.exists():
            raise ValueError(f"Shot {shot_name} does not exist")

        notes_file = shot_dir / 'notes.txt'
        try:
            with open(notes_file, 'w', encoding='utf-8') as f:
                f.write(notes)
        except Exception as e:
            raise ValueError(f"Failed to save notes: {str(e)}")

    def _prompt_file_path(self, shot_name, asset_type, version):
        """Return the path to the prompt file for a specific asset version."""
        shot_dir = self.wip_dir / shot_name
        if asset_type == AssetType.IMAGE:
            base_dir = shot_dir / 'images'
            filename = f'{shot_name}_v{version:03d}_image_prompt.txt'
        elif asset_type == AssetType.VIDEO:
            base_dir = shot_dir / 'videos'
            filename = f'{shot_name}_v{version:03d}_video_prompt.txt'
        elif asset_type in AssetType.LIPSYNC_TYPES:
            base_dir = shot_dir / 'lipsync'
            filename = f'{shot_name}_{asset_type}_v{version:03d}_prompt.txt'
        else:
            raise ValueError('Invalid asset type')
        return base_dir / filename

    def load_prompt(self, shot_name, asset_type, version):
        """Load a prompt for a specific asset version."""
        path = self._prompt_file_path(shot_name, asset_type, version)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except (IOError, OSError) as e:
                logger.warning("Failed to read prompt file %s: %s", path, e)
        return ''

    def save_prompt(self, shot_name, asset_type, version, prompt):
        """Save prompt for a specific asset version."""
        validate_shot_name(shot_name)
        path = self._prompt_file_path(shot_name, asset_type, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(prompt)
        except Exception as e:
            raise ValueError(f"Failed to save prompt: {str(e)}")

    def get_prompt_versions(self, shot_name, asset_type):
        """Return a sorted list of prompt versions for the given asset."""
        shot_dir = self.wip_dir / shot_name
        if asset_type == AssetType.IMAGE:
            base_dir = shot_dir / 'images'
            pattern = f'{shot_name}_v*_image_prompt.txt'
        elif asset_type == AssetType.VIDEO:
            base_dir = shot_dir / 'videos'
            pattern = f'{shot_name}_v*_video_prompt.txt'
        elif asset_type in AssetType.LIPSYNC_TYPES:
            base_dir = shot_dir / 'lipsync'
            pattern = f'{shot_name}_{asset_type}_v*_prompt.txt'
        else:
            raise ValueError('Invalid asset type')

        versions = []
        if base_dir.exists():
            for f in base_dir.glob(pattern):
                stem = f.stem
                if '_v' not in stem:
                    continue
                try:
                    part = stem.split('_v')[1]
                    ver_str = part.split('_')[0]
                    versions.append(int(ver_str))
                except (IndexError, ValueError):
                    continue
        return sorted(set(versions))

    def get_thumbnail_path(self, image_path, shot_name, generate=True):
        """Return (and optionally create) the thumbnail for an image.

        Args:
            image_path: Path to the source image
            shot_name: Name of the shot
            generate: If True, generate thumbnail if missing. If False, return None for missing.
        """
        if not image_path:
            return None

        image_path = Path(image_path)
        project_name = self.project_path.name
        thumb_filename = f"{project_name}_{shot_name}_{image_path.stem}_thumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename

        if thumb_path.exists():
            return f"/static/thumbnails/{thumb_filename}"

        if not generate:
            return None

        result = create_image_thumbnail(image_path, thumb_path)
        if not result:
            return None

        return f"/static/thumbnails/{thumb_filename}"

    def get_video_thumbnail_path(self, video_path, shot_name, generate=True):
        """Return (and optionally create) the thumbnail for a video.

        Args:
            video_path: Path to the source video
            shot_name: Name of the shot
            generate: If True, generate thumbnail if missing. If False, return None for missing.
        """
        if not video_path:
            return None

        video_path = Path(video_path)
        project_name = self.project_path.name
        thumb_filename = f"{project_name}_{shot_name}_{video_path.stem}_vthumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename

        if thumb_path.exists():
            return f"/static/thumbnails/{thumb_filename}"

        if not generate:
            return None

        result = create_video_thumbnail(video_path, thumb_path)
        if not result:
            return None

        return f"/static/thumbnails/{thumb_filename}"

def get_shot_manager(project_path, cache=None):
    """Retrieve a cached ``ShotManager`` for the given path."""
    from flask import current_app

    if cache is None:
        cache = current_app.config.setdefault('SHOT_MANAGER_CACHE', {})

    path_key = str(Path(project_path).resolve())
    if path_key not in cache:
        cache[path_key] = ShotManager(path_key)
    return cache[path_key]


def clear_shot_manager_cache(cache=None):
    """Clear cached ``ShotManager`` instances."""
    from flask import current_app

    if cache is None:
        cache = current_app.config.get('SHOT_MANAGER_CACHE')

    if cache is not None:
        cache.clear()
