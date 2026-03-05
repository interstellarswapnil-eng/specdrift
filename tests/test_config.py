from pathlib import Path

import pytest

from specdrift.config import load_config


def test_load_config_missing(tmp_path: Path):
	with pytest.raises(FileNotFoundError):
		load_config(tmp_path / "specdrift.yaml")
