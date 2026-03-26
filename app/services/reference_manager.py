import filecmp
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import logging

from ..utils import create_image_thumbnail
from ..config.constants import THUMBNAIL_CACHE_DIR, ALLOWED_IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

VERSION_RE = re.compile(r'_v(\d{3})')


class ReferenceManager:
    """Manages reference images for a project."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.ref_images_dir = self.project_path / "ref-images"
        self.ref_latest_dir = self.ref_images_dir / "latest"
        self.ref_wip_dir = self.ref_images_dir / "wip"
        self._ensure_ref_images_dir()
        self._migrate_flat_to_versioned()

    def _ensure_ref_images_dir(self):
        """Create ref-images directory structure if it doesn't exist."""
        self.ref_images_dir.mkdir(parents=True, exist_ok=True)
        self.ref_latest_dir.mkdir(exist_ok=True)
        self.ref_wip_dir.mkdir(exist_ok=True)

    def _migrate_flat_to_versioned(self):
        """One-time migration of flat ref-images into latest/ + wip/ structure.

        Only scans for loose image files directly in ref-images/. Once migrated,
        no loose files remain so subsequent calls are a cheap no-op.
        """
        self.migrated_count = 0
        for img_path in list(self.ref_images_dir.iterdir()):
            if img_path.is_file() and img_path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                latest_dest = self.ref_latest_dir / img_path.name
                wip_dest = self.ref_wip_dir / f"{img_path.stem}_v001{img_path.suffix}"
                shutil.move(str(img_path), str(latest_dest))
                shutil.copy2(str(latest_dest), str(wip_dest))
                self.migrated_count += 1
        if self.migrated_count:
            logger.info("Migrated %d reference image(s) to versioned structure",
                        self.migrated_count)

    def _strip_version_suffix(self, stem: str) -> str:
        """Strip any _v### suffix from a filename stem."""
        return VERSION_RE.sub('', stem)

    def _collect_versions(self, base_stem: str) -> List[int]:
        """Collect all version numbers for a base stem from the WIP directory."""
        versions = []
        for f in self.ref_wip_dir.iterdir():
            if not f.is_file():
                continue
            if self._strip_version_suffix(f.stem) == base_stem:
                m = VERSION_RE.search(f.stem)
                if m:
                    versions.append(int(m.group(1)))
        return versions

    def _build_version_index(self) -> Dict[str, List[int]]:
        """Scan WIP directory once and return {base_stem: [version_numbers]}."""
        index = {}
        for f in self.ref_wip_dir.iterdir():
            if not f.is_file():
                continue
            m = VERSION_RE.search(f.stem)
            if m:
                base = self._strip_version_suffix(f.stem)
                index.setdefault(base, []).append(int(m.group(1)))
        return index

    def _get_active_version(self, latest_file: Path, base_stem: str,
                            versions: List[int]) -> int:
        """Determine which WIP version matches the latest file."""
        for v in sorted(versions, reverse=True):
            wip_file = self.find_wip_version_file(base_stem, v)
            if wip_file and filecmp.cmp(str(latest_file), str(wip_file), shallow=True):
                return v
        return max(versions) if versions else 0

    def find_wip_version_file(self, base_stem: str, version: int) -> Optional[Path]:
        """Find the WIP file for a specific version of a reference image."""
        expected_stem = f"{base_stem}_v{version:03d}"
        for f in self.ref_wip_dir.iterdir():
            if f.is_file() and f.stem == expected_stem:
                return f
        return None

    def _remove_latest_by_stem(self, base_stem: str):
        """Remove any file in latest/ that matches the given base stem."""
        for f in self.ref_latest_dir.iterdir():
            if f.is_file() and f.stem == base_stem:
                f.unlink()

    def _thumbnail_url(self, filename: str) -> Optional[str]:
        """Return the thumbnail URL for a reference image, or None."""
        thumb_path = self._get_thumbnail_path(filename)
        if thumb_path and thumb_path.exists():
            return f"/api/reference/thumbnail/{thumb_path.name}"
        return None

    def get_reference_images(self) -> List[Dict]:
        """Get list of all reference images with version info."""
        images = []
        if not self.ref_latest_dir.exists():
            return images

        version_index = self._build_version_index()

        for img_path in sorted(self.ref_latest_dir.iterdir()):
            if img_path.is_file() and img_path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                base_stem = img_path.stem
                versions = version_index.get(base_stem, [])
                max_version = max(versions) if versions else 0
                active_version = self._get_active_version(
                    img_path, base_stem, versions)

                images.append({
                    'filename': img_path.name,
                    'path': str(img_path.relative_to(self.project_path)),
                    'thumbnail': self._thumbnail_url(img_path.name),
                    'version': max_version,
                    'active_version': active_version,
                })

        return images

    def save_reference_image(self, file, filename: str) -> Dict:
        """Save a reference image as a new version."""
        file_ext = Path(filename).suffix.lower()

        if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

        base_stem = self._strip_version_suffix(Path(filename).stem)
        versions = self._collect_versions(base_stem)
        version = (max(versions) + 1) if versions else 1

        wip_filename = f"{base_stem}_v{version:03d}{file_ext}"
        wip_path = self.ref_wip_dir / wip_filename
        file.save(str(wip_path))

        self._remove_latest_by_stem(base_stem)
        latest_filename = f"{base_stem}{file_ext}"
        latest_path = self.ref_latest_dir / latest_filename
        shutil.copy2(str(wip_path), str(latest_path))

        self._create_thumbnail(str(latest_path), latest_filename)

        return {
            'filename': latest_filename,
            'path': str(latest_path.relative_to(self.project_path)),
            'thumbnail': self._thumbnail_url(latest_filename),
            'version': version,
        }

    def restore_reference_version(self, filename: str, version: int) -> Dict:
        """Restore a specific version of a reference image to latest."""
        base_stem = Path(filename).stem

        wip_file = self.find_wip_version_file(base_stem, version)
        if not wip_file:
            raise ValueError(f"Version {version} not found for '{filename}'")

        self._remove_latest_by_stem(base_stem)
        latest_filename = f"{base_stem}{wip_file.suffix}"
        latest_path = self.ref_latest_dir / latest_filename
        shutil.copy2(str(wip_file), str(latest_path))

        # Regenerate thumbnail (old one may have different extension)
        old_thumb = self._get_thumbnail_path(filename)
        if old_thumb.exists():
            old_thumb.unlink()
        self._create_thumbnail(str(latest_path), latest_filename)

        return {
            'filename': latest_filename,
            'thumbnail': self._thumbnail_url(latest_filename),
        }

    def _get_thumbnail_path(self, filename: str) -> Path:
        """Get the expected thumbnail path for a reference image."""
        project_name = self.project_path.name
        file_stem = Path(filename).stem
        thumb_filename = f"{project_name}_ref_{file_stem}_thumb.jpg"
        return THUMBNAIL_CACHE_DIR / thumb_filename

    def _create_thumbnail(self, image_path: str, filename: str):
        """Create thumbnail for reference image and save it to the central cache."""
        project_name = self.project_path.name
        file_stem = Path(filename).stem
        thumb_filename = f"{project_name}_ref_{file_stem}_thumb.jpg"
        thumb_path = THUMBNAIL_CACHE_DIR / thumb_filename
        return create_image_thumbnail(image_path, thumb_path)

    def rename_reference_image(self, old_name: str, new_name: str) -> Dict:
        """Rename a reference image and all its versions."""
        old_path = self.ref_latest_dir / old_name

        if not old_path.exists():
            raise ValueError(f"Reference image '{old_name}' not found")

        old_ext = old_path.suffix.lower()
        old_stem = old_path.stem
        new_name_path = Path(new_name)

        if new_name_path.suffix.lower() != old_ext:
            new_name = str(new_name_path.stem) + old_ext
        new_stem = Path(new_name).stem

        new_path = self.ref_latest_dir / new_name

        if new_path.exists() and new_path != old_path:
            raise ValueError(f"A file named '{new_name}' already exists")

        if old_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Invalid file extension. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")

        old_thumb_path = self._get_thumbnail_path(old_name)
        if old_thumb_path.exists():
            old_thumb_path.unlink()

        old_path.rename(new_path)

        for f in list(self.ref_wip_dir.iterdir()):
            if not f.is_file():
                continue
            if self._strip_version_suffix(f.stem) == old_stem:
                m = VERSION_RE.search(f.stem)
                if m:
                    new_wip_name = f"{new_stem}{m.group(0)}{f.suffix}"
                    try:
                        f.rename(self.ref_wip_dir / new_wip_name)
                    except OSError as e:
                        logger.error("Failed to rename WIP file %s: %s", f.name, e)

        self._create_thumbnail(str(new_path), new_name)

        return {
            'filename': new_name,
            'path': str(new_path.relative_to(self.project_path)),
            'thumbnail': self._thumbnail_url(new_name),
        }

    def delete_reference_image(self, filename: str) -> bool:
        """Delete a reference image and all its versions."""
        file_path = (self.ref_latest_dir / filename).resolve()

        try:
            file_path.relative_to(self.ref_latest_dir.resolve())
        except ValueError:
            raise ValueError("Invalid filename")

        if not file_path.exists():
            raise ValueError(f"Reference image '{filename}' not found")

        base_stem = file_path.stem

        thumb_path = self._get_thumbnail_path(filename)
        if thumb_path.exists():
            thumb_path.unlink()

        file_path.unlink()

        for f in list(self.ref_wip_dir.iterdir()):
            if not f.is_file():
                continue
            if self._strip_version_suffix(f.stem) == base_stem:
                try:
                    f.unlink()
                except OSError as e:
                    logger.error("Failed to delete WIP file %s: %s", f.name, e)

        return True
