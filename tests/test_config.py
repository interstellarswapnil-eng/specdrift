from pathlib import Path

import pytest

from specdrift.config import ConfigError, load_config


def test_load_config_missing(tmp_path: Path):
	with pytest.raises(FileNotFoundError):
		load_config(tmp_path / "specdrift.yaml")


def test_load_config_requires_mapping(tmp_path: Path):
	p = tmp_path / "specdrift.yaml"
	p.write_text("- not-a-mapping\n", encoding="utf-8")
	with pytest.raises(ConfigError, match="must be a YAML mapping"):
		load_config(p)


def test_load_config_requires_project_section(tmp_path: Path):
	p = tmp_path / "specdrift.yaml"
	p.write_text("{}\n", encoding="utf-8")
	with pytest.raises(ConfigError, match="Missing required section: project"):
		load_config(p)


def test_load_config_validates_required_fields(tmp_path: Path):
	p = tmp_path / "specdrift.yaml"
	p.write_text(
		"""
project:
  name: SpecDrift
  prd_doc_id: ""
  jira_project_key: PROJ
""".lstrip(),
		encoding="utf-8",
	)
	with pytest.raises(ConfigError, match=r"project\.prd_doc_id"):
		load_config(p)


def test_load_config_success(tmp_path: Path):
	p = tmp_path / "specdrift.yaml"
	p.write_text(
		"""
project:
  name: SpecDrift
  prd_doc_id: abc123
  jira_project_key: PROJ
  github_repo: interstellarswapnil-eng/specdrift
""".lstrip(),
		encoding="utf-8",
	)
	cfg = load_config(p)
	assert cfg.project.prd_doc_id == "abc123"
	assert cfg.project.jira_project_key == "PROJ"
	assert cfg.project.github_repo == "interstellarswapnil-eng/specdrift"
