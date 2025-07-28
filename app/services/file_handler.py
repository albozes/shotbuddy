from pathlib import Path
import shutil
from PIL import Image

from app.services.prompt_importer import extract_prompt_from_png
import logging

logger = logging.getLogger(__name__)
from app.services.shot_manager import get_shot_manager
from app.config.constants import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    THUMBNAIL_CACHE_DIR,
    THUMBNAIL_SIZE,
)

# Ensure the thumbnail cache directory exists.
THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class FileHandler:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.shots_dir = self.project_path / 'shots'
        self.wip_dir = self.shots_dir / 'wip'
        self.latest_images_dir = self.shots_dir / 'latest_images'
        self.latest_videos_dir = self.shots_dir / 'latest_videos'

        self.wip_dir.mkdir(parents=True, exist_ok=True)
        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)

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

    def save_file(self, file, shot_name, file_type):
        """Save uploaded file with proper versioning"""
        shot_dir = self.wip_dir / shot_name
        file_ext = Path(file.filename).suffix.lower()

        if file_type == 'image' and file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")
        elif file_type == 'video' and file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError(f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")
        elif file_type in {'driver', 'target', 'result'} and file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError(f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")

        if not shot_dir.exists():
            get_shot_manager(self.project_path).create_shot_structure(shot_name)

        if file_type in {'image', 'video'}:
            wip_dir = shot_dir / ('images' if file_type == 'image' else 'videos')
            version = self.get_next_version(wip_dir, shot_name, file_ext)

            wip_filename = f'{shot_name}_v{version:03d}{file_ext}'
            wip_path = wip_dir / wip_filename
            file.save(str(wip_path))

            final_dir = self.latest_images_dir if file_type == 'image' else self.latest_videos_dir
            final_filename = f'{shot_name}{file_ext}'
            final_path = final_dir / final_filename

            for existing_file in final_dir.glob(f'{shot_name}.*'):
                existing_file.unlink()

            shutil.copy2(str(wip_path), str(final_path))

            # Attempt to extract embedded prompt metadata from PNG files
            if file_ext == '.png':
                prompt_data = extract_prompt_from_png(final_path)
                if prompt_data and prompt_data.get('prompt'):
                    prompt_text = prompt_data['prompt'].strip()
                    neg = prompt_data.get('negative_prompt', '').strip()
                    if neg:
                        prompt_text += f"\nNegative: {neg}"
                    try:
                        manager = get_shot_manager(self.project_path)
                        manager.save_prompt(shot_name, 'image', version, prompt_text)
                    except Exception as e:
                        logger.warning('Failed to save imported prompt: %s', e)
        else:
            # lipsync driver/target/result
            dest_dir = shot_dir / 'lipsync'
            dest_dir.mkdir(exist_ok=True)
            base = f'{shot_name}_{file_type}'
            version = self.get_next_version(dest_dir, base, file_ext)
            wip_filename = f'{base}_v{version:03d}{file_ext}'
            wip_path = dest_dir / wip_filename
            file.save(str(wip_path))

            final_path = dest_dir / f'{base}{file_ext}'
            for existing_file in dest_dir.glob(f'{base}.*'):
                if existing_file != wip_path:
                    existing_file.unlink()

            shutil.copy2(str(wip_path), str(final_path))

        thumbnail_path = None
        if file_type == 'image':
            thumbnail_path = self.create_thumbnail(str(final_path), shot_name)

        return {
            'wip_path': str(wip_path).replace('\\', '/'),
            'final_path': str(final_path).replace('\\', '/'),
            'version': version,
            'thumbnail': f"static/thumbnails/{Path(thumbnail_path).name}" if thumbnail_path else None
        }

    def get_next_version(self, wip_dir, shot_name, file_ext):
        if not wip_dir.exists():
            return 1

        file_type = 'image' if 'image' in str(wip_dir) else 'video'
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS if file_type == 'image' else ALLOWED_VIDEO_EXTENSIONS

        existing_files = []
        for ext in allowed_extensions:
            existing_files.extend(wip_dir.glob(f'{shot_name}_v*{ext}'))

        if not existing_files:
            return 1

        versions = []
        for f in existing_files:
            try:
                version_str = f.stem.split('_v')[1]
                versions.append(int(version_str))
            except (IndexError, ValueError):
                continue

        return max(versions) + 1 if versions else 1

    def create_thumbnail(self, image_path, shot_name, size=THUMBNAIL_SIZE):
        """Create thumbnail for image and save it to the central cache"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Unique thumbnail name
                image_path = Path(image_path)
                thumb_filename = f"{shot_name}_{image_path.stem}_thumb.jpg"
                thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename

                if thumb_path.exists():
                    thumb_path.unlink()

                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (64, 64, 64))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = background

                img.save(str(thumb_path), 'JPEG', quality=85)
                return str(thumb_path)

        except Exception as e:
            logger.warning("Error creating thumbnail: %s", e)
            return None
