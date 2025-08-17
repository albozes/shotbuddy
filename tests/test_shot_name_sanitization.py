import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.shot_manager import ShotManager, validate_shot_name


def test_validate_shot_name_uppercases_lowercase():
    assert validate_shot_name("sh001") == "SH001"


def test_validate_shot_name_trims_whitespace():
    assert validate_shot_name("  sh003  ") == "SH003"


def test_create_shot_structure_trims_whitespace(tmp_path):
    sm = ShotManager(tmp_path)
    sm.create_shot_structure("  sh002  ")
    assert (tmp_path / "shots" / "wip" / "SH002").exists()
