from pathlib import Path
import shutil
from typing import List, Dict
from PIL import Image
import logging

from app.config.constants import THUMBNAIL_CACHE_DIR, THUMBNAIL_SIZE

logger = logging.getLogger(__name__)

# Ensure the thumbnail cache directory exists.
THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class ReferenceManager:
    """Manages reference images for a project."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.ref_images_dir = self.project_path / "ref-images"
        self._ensure_ref_images_dir()

    def _ensure_ref_images_dir(self):
        """Create ref-images directory if it doesn't exist."""
        self.ref_images_dir.mkdir(parents=True, exist_ok=True)

    def get_reference_images(self) -> List[Dict[str, str]]:
        """Get list of all reference images."""
        images = []
        allowed_extensions = ['.jpg', '.jpeg', '.png']

        if not self.ref_images_dir.exists():
            return images

        for img_path in sorted(self.ref_images_dir.iterdir()):
            if img_path.is_file() and img_path.suffix.lower() in allowed_extensions:
                # Create thumbnail path
                thumbnail_path = self._get_thumbnail_path(img_path.name)
                thumbnail_url = None
                if thumbnail_path and thumbnail_path.exists():
                    thumbnail_url = f"/api/reference/thumbnail/{thumbnail_path.name}"

                images.append({
                    'filename': img_path.name,
                    'path': str(img_path.relative_to(self.project_path)),
                    'thumbnail': thumbnail_url
                })

        return images

    def save_reference_image(self, file, filename: str) -> Dict[str, str]:
        """Save a reference image."""
        # Ensure valid extension
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_ext = Path(filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise ValueError(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")

        # Save the file
        destination = self.ref_images_dir / filename
        file.save(str(destination))

        # Create thumbnail
        thumbnail_path = self._create_thumbnail(str(destination), filename)
        thumbnail_url = None
        if thumbnail_path:
            thumbnail_url = f"/api/reference/thumbnail/{Path(thumbnail_path).name}"

        return {
            'filename': filename,
            'path': str(destination.relative_to(self.project_path)),
            'thumbnail': thumbnail_url
        }

    def _get_thumbnail_path(self, filename: str) -> Path:
        """Get the expected thumbnail path for a reference image."""
        project_name = self.project_path.name
        file_stem = Path(filename).stem
        thumb_filename = f"{project_name}_ref_{file_stem}_thumb.jpg"
        return THUMBNAIL_CACHE_DIR / thumb_filename

    def _create_thumbnail(self, image_path: str, filename: str, size=THUMBNAIL_SIZE):
        """Create thumbnail for reference image and save it to the central cache."""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Unique thumbnail name with project identifier to prevent collisions
                project_name = self.project_path.name
                file_stem = Path(filename).stem
                thumb_filename = f"{project_name}_ref_{file_stem}_thumb.jpg"
                thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename

                if thumb_path.exists():
                    thumb_path.unlink()

                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (64, 64, 64))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = background

                img.save(str(thumb_path), 'JPEG', quality=85)
                return str(thumb_path)

        except Exception as e:
            logger.warning("Error creating reference image thumbnail: %s", e)
            return None

    def rename_reference_image(self, old_name: str, new_name: str) -> Dict[str, str]:
        """Rename a reference image."""
        old_path = self.ref_images_dir / old_name

        if not old_path.exists():
            raise ValueError(f"Reference image '{old_name}' not found")

        # Ensure new name has the same extension as old name
        old_ext = old_path.suffix.lower()
        new_name_path = Path(new_name)

        # If new name doesn't have the correct extension, add it
        if new_name_path.suffix.lower() != old_ext:
            new_name = str(new_name_path.stem) + old_ext

        new_path = self.ref_images_dir / new_name

        if new_path.exists() and new_path != old_path:
            raise ValueError(f"A file named '{new_name}' already exists")

        # Validate extension
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        if old_ext not in allowed_extensions:
            raise ValueError(f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}")

        # Delete old thumbnail
        old_thumb_path = self._get_thumbnail_path(old_name)
        if old_thumb_path.exists():
            old_thumb_path.unlink()

        # Rename the file
        old_path.rename(new_path)

        # Create new thumbnail
        thumbnail_path = self._create_thumbnail(str(new_path), new_name)
        thumbnail_url = None
        if thumbnail_path:
            thumbnail_url = f"/api/reference/thumbnail/{Path(thumbnail_path).name}"

        return {
            'filename': new_name,
            'path': str(new_path.relative_to(self.project_path)),
            'thumbnail': thumbnail_url
        }

    def delete_reference_image(self, filename: str) -> bool:
        """Delete a reference image."""
        file_path = self.ref_images_dir / filename

        if not file_path.exists():
            raise ValueError(f"Reference image '{filename}' not found")

        # Delete thumbnail
        thumb_path = self._get_thumbnail_path(filename)
        if thumb_path.exists():
            thumb_path.unlink()

        # Delete the image
        file_path.unlink()
        return True
