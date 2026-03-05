from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SpecDriftConfig:
	raw: dict[str, Any]

	@property
	def prd_doc_id(self) -> str | None:
		return self.raw.get("project", {}).get("prd_doc_id")

	@property
	def jira_project_key(self) -> str | None:
		return self.raw.get("project", {}).get("jira_project_key")

	@property
	def github_repo(self) -> str | None:
		return self.raw.get("project", {}).get("github_repo")


def load_config(path: Path) -> SpecDriftConfig:
	if not path.exists():
		raise FileNotFoundError(
			f"Config file not found: {path}. Copy specdrift.yaml.example → specdrift.yaml"
		)
	data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
	if not isinstance(data, dict):
		raise ValueError("specdrift.yaml must be a YAML mapping/object")
	return SpecDriftConfig(raw=data)
