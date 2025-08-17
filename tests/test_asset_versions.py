import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.shot_manager import ShotManager


def test_get_asset_versions_with_extra_tokens(tmp_path):
    project_path = tmp_path
    image_dir = project_path / 'shots' / 'wip' / 'SH001' / 'images'
    image_dir.mkdir(parents=True)
    (image_dir / 'SH001_v001_extra.png').write_text('x')
    (image_dir / 'SH001_v002.PNG').write_text('x')
    sm = ShotManager(project_path)
    assert sm.get_asset_versions('SH001', 'image') == [1, 2]
