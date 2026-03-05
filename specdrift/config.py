from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
	"""Raised when specdrift.yaml is missing required fields or has an invalid shape."""


@dataclass(frozen=True)
class ProjectConfig:
	name: str
	prd_doc_id: str
	jira_project_key: str
	github_repo: str


@dataclass(frozen=True)
class SpecDriftConfig:
	raw: dict[str, Any]
	project: ProjectConfig


def _require_str(obj: dict[str, Any], key: str, *, path: str) -> str:
	val = obj.get(key)
	if val is None:
		raise ConfigError(f"Missing required field: {path}{key}")
	if not isinstance(val, str) or not val.strip():
		raise ConfigError(f"Field must be a non-empty string: {path}{key}")
	return val.strip()


def load_config(path: Path) -> SpecDriftConfig:
	"""Load and validate SpecDrift config.

	Required fields (per spec):
	- project.prd_doc_id
	- project.jira_project_key
	- project.github_repo
	"""

	if not path.exists():
		raise FileNotFoundError(
			f"Config file not found: {path}. Copy specdrift.yaml.example → specdrift.yaml"
		)

	data = yaml.safe_load(path.read_text(encoding="utf-8"))
	if data is None:
		data = {}
	if not isinstance(data, dict):
		raise ConfigError("specdrift.yaml must be a YAML mapping/object")

	project = data.get("project")
	if project is None:
		raise ConfigError("Missing required section: project")
	if not isinstance(project, dict):
		raise ConfigError("'project' must be a mapping/object")

	# name is useful but not strictly required by the user request. Provide a default.
	name = project.get("name")
	if name is None:
		name = "SpecDrift"
	if not isinstance(name, str) or not name.strip():
		raise ConfigError("Field must be a non-empty string: project.name")

	prd_doc_id = _require_str(project, "prd_doc_id", path="project.")
	jira_project_key = _require_str(project, "jira_project_key", path="project.")
	github_repo = _require_str(project, "github_repo", path="project.")

	return SpecDriftConfig(
		raw=data,
		project=ProjectConfig(
			name=name.strip(),
			prd_doc_id=prd_doc_id,
			jira_project_key=jira_project_key,
			github_repo=github_repo,
		),
	)
