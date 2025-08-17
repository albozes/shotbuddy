from pathlib import Path
from PIL import Image
import logging
import re

logger = logging.getLogger(__name__)

# Shot names may optionally contain a single underscore followed by another
# three-digit number (e.g. ``SH001_050``).  Deeper nesting with multiple
# underscores is not allowed.
SHOT_NAME_RE = re.compile(r"^SH\d{3}(?:_\d{3})?$")


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
    THUMBNAIL_SIZE,
)

class ShotManager:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.shots_dir = self.project_path / 'shots'
        self.wip_dir = self.shots_dir / 'wip'
        self.latest_images_dir = self.shots_dir / 'latest_images'
        self.latest_videos_dir = self.shots_dir / 'latest_videos'
        self.legacy_dir = self.project_path / '_legacy'

        self.wip_dir.mkdir(parents=True, exist_ok=True)
        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_path(path):
        """Return a POSIX-style absolute path string or ``None``."""
        if not path:
            return None
        return str(Path(path).resolve()).replace("\\", "/")

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

        old_dir.rename(new_dir)

        for sub in ["images", "videos"]:
            d = new_dir / sub
            if d.exists():
                for f in d.glob(f"{old_name}_v*.*"):
                    f.rename(d / f.name.replace(old_name, new_name, 1))

        lipsync_dir = new_dir / "lipsync"
        if lipsync_dir.exists():
            for part in ["driver", "target", "result"]:
                for ext in ALLOWED_VIDEO_EXTENSIONS:
                    src = lipsync_dir / f"{old_name}_{part}{ext}"
                    if src.exists():
                        src.rename(lipsync_dir / f"{new_name}_{part}{ext}")
                for f in lipsync_dir.glob(f"{old_name}_{part}_v*.*"):
                    f.rename(lipsync_dir / f.name.replace(old_name, new_name, 1))

        for ext in ALLOWED_IMAGE_EXTENSIONS:
            src = self.latest_images_dir / f"{old_name}{ext}"
            if src.exists():
                src.rename(self.latest_images_dir / f"{new_name}{ext}")

        for ext in ALLOWED_VIDEO_EXTENSIONS:
            src = self.latest_videos_dir / f"{old_name}{ext}"
            if src.exists():
                src.rename(self.latest_videos_dir / f"{new_name}{ext}")

        if THUMBNAIL_CACHE_DIR.exists():
            for thumb in THUMBNAIL_CACHE_DIR.glob(f"{old_name}_*_thumb.jpg"):
                thumb.rename(THUMBNAIL_CACHE_DIR / thumb.name.replace(old_name, new_name, 1))

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

        return (max(existing_shots) + 10) if existing_shots else 10

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
                new_number = 10
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
                    new_number = after_num + 10
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

        next_num = (max(sub_numbers) + 10) if sub_numbers else 50
        if next_num > 999:
            raise ValueError('No available sub-shot numbers')

        return f"{base_shot}_{next_num:03d}"

    def get_shot_info(self, shot_name):
        """Get information about a specific shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name

        # Load notes
        notes = ''
        notes_file = shot_dir / 'notes.txt'
        if notes_file.exists():
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    notes = f.read().strip()
            except Exception:
                pass


        # Latest image
        latest_image, image_version = self._get_latest_asset(
            self.latest_images_dir, shot_dir / 'images',
            shot_name, ALLOWED_IMAGE_EXTENSIONS
        )
        latest_image = self._normalize_path(latest_image)
        image_prompt = ''
        if image_version > 0:
            image_prompt = self.load_prompt(shot_name, 'image', image_version)

        # Latest video
        latest_video, video_version = self._get_latest_asset(
            self.latest_videos_dir, shot_dir / 'videos',
            shot_name, ALLOWED_VIDEO_EXTENSIONS
        )
        latest_video = self._normalize_path(latest_video)
        video_prompt = ''
        if video_version > 0:
            video_prompt = self.load_prompt(shot_name, 'video', video_version)

        # Lipsync videos
        lipsync_dir = shot_dir / 'lipsync'
        lipsync = {}
        for part in ['driver', 'target', 'result']:
            file_path, ver = self._get_latest_asset(
                lipsync_dir, lipsync_dir,
                f'{shot_name}_{part}', ALLOWED_VIDEO_EXTENSIONS
            )
            file_path = self._normalize_path(file_path)
            prompt_text = ''
            if ver > 0:
                prompt_text = self.load_prompt(shot_name, part, ver)
            lipsync[part] = {
                'file': file_path,
                'version': ver,
                'thumbnail': None,  # will be replaced with image thumb below
                'prompt': prompt_text,
            }

        # Thumbnails
        image_thumb = self.get_thumbnail_path(Path(latest_image), shot_name) if latest_image else None
        video_thumb = self.get_video_thumbnail_path(Path(latest_video), shot_name) if latest_video else None

        for part_name, info in lipsync.items():
            info['thumbnail'] = self.get_video_thumbnail_path(Path(info['file']), f"{shot_name}_{part_name}") if info['file'] else None

        logger.debug("%s -> Image thumbnail: %s", shot_name, image_thumb)
        logger.debug("%s -> Video thumbnail: %s", shot_name, video_thumb)

        return {
            'name': shot_name,
            'notes': notes,
            'image': {
                'file': latest_image,
                'version': image_version,
                'thumbnail': image_thumb,
                'prompt': image_prompt,
            },
            'video': {
                'file': latest_video,
                'version': video_version,
                'thumbnail': video_thumb,
                'prompt': video_prompt,
            },
            'lipsync': lipsync,
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
        if asset_type == 'image':
            base_dir = shot_dir / 'images'
            filename = f'{shot_name}_v{version:03d}_image_prompt.txt'
        elif asset_type == 'video':
            base_dir = shot_dir / 'videos'
            filename = f'{shot_name}_v{version:03d}_video_prompt.txt'
        elif asset_type in {'driver', 'target', 'result'}:
            base_dir = shot_dir / 'lipsync'
            filename = f'{shot_name}_{asset_type}_v{version:03d}_prompt.txt'
        else:
            raise ValueError('Invalid asset type')
        return base_dir / filename

    def load_prompt(self, shot_name, asset_type, version):
        path = self._prompt_file_path(shot_name, asset_type, version)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                return ''
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
        if asset_type == 'image':
            base_dir = shot_dir / 'images'
            pattern = f'{shot_name}_v*_image_prompt.txt'
        elif asset_type == 'video':
            base_dir = shot_dir / 'videos'
            pattern = f'{shot_name}_v*_video_prompt.txt'
        elif asset_type in {'driver', 'target', 'result'}:
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

    def get_asset_versions(self, shot_name, asset_type):
        """Return a sorted list of available WIP versions for an asset."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        if asset_type == 'image':
            base_dir = shot_dir / 'images'
            base = shot_name
            exts = ALLOWED_IMAGE_EXTENSIONS
        elif asset_type == 'video':
            base_dir = shot_dir / 'videos'
            base = shot_name
            exts = ALLOWED_VIDEO_EXTENSIONS
        elif asset_type in {'driver', 'target', 'result'}:
            base_dir = shot_dir / 'lipsync'
            base = f'{shot_name}_{asset_type}'
            exts = ALLOWED_VIDEO_EXTENSIONS
        else:
            raise ValueError('Invalid asset type')

        versions = []
        if base_dir.exists():
            for ext in exts:
                for f in base_dir.glob(f'{base}_v*{ext}'):
                    try:
                        versions.append(int(f.stem.split('_v')[1]))
                    except (IndexError, ValueError):
                        continue
        return sorted(set(versions))

    def get_thumbnail_path(self, image_path, shot_name):
        """Return (and create if necessary) the thumbnail for an image."""
        if not image_path:
            return None

        image_path = Path(image_path)
        thumb_filename = f"{shot_name}_{image_path.stem}_thumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename

        if not thumb_path.exists():
            try:
                THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with Image.open(image_path) as img:
                    img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    if img.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", img.size, (64, 64, 64))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                        img = background
                    img.save(str(thumb_path), "JPEG", quality=85)
            except Exception as e:
                logger.warning("Error creating thumbnail: %s", e)
                return None

        return f"/static/thumbnails/{thumb_filename}"

    def get_video_thumbnail_path(self, video_path, shot_name):
        """Return (and create if necessary) the thumbnail for a video."""
        if not video_path:
            return None

        import subprocess
        import shutil as _shutil

        video_path = Path(video_path)
        thumb_filename = f"{shot_name}_{video_path.stem}_vthumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename

        if not thumb_path.exists():
            ffmpeg = _shutil.which("ffmpeg")
            if not ffmpeg:
                logger.warning("ffmpeg not found; skipping video thumbnail for %s", video_path)
                return None
            try:
                THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                tmp_path = thumb_path.with_suffix(".tmp.jpg")
                cmd = [ffmpeg, "-y", "-i", str(video_path), "-frames:v", "1", str(tmp_path)]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with Image.open(tmp_path) as img:
                    img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    if img.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", img.size, (64, 64, 64))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                        img = background
                    img.save(str(thumb_path), "JPEG", quality=85)
                tmp_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Error creating video thumbnail: %s", e)
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
