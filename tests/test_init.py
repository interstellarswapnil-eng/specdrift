from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from specdrift.cli.init import extract_gdoc_id, init


def test_extract_gdoc_id_from_docs_url():
	url = "https://docs.google.com/document/d/ABC123def_456/edit?usp=sharing"
	assert extract_gdoc_id(url) == "ABC123def_456"


def test_extract_gdoc_id_accepts_raw_id():
	assert extract_gdoc_id("ABC123def_456") == "ABC123def_456"


def test_init_writes_specdrift_yaml_and_workflows(tmp_path: Path, monkeypatch):
	runner = CliRunner()
	with runner.isolated_filesystem(temp_dir=tmp_path):
		# Provide inputs for prompts
		inputs = "\n".join(
			[
				"https://docs.google.com/document/d/DocId_123/edit",
				"https://jira.example.com",
				"PROJ",
				"org/repo",
				"./specdrift.db",
				"",  # skip slack webhook
			]
		)
		res = runner.invoke(init, input=inputs + "\n")
		assert res.exit_code == 0, res.output

		assert Path("specdrift.yaml").exists()
		assert Path(".github/workflows/specdrift-sync.yml").exists()
		assert Path(".github/workflows/specdrift-pr-check.yml").exists()

		yaml_text = Path("specdrift.yaml").read_text(encoding="utf-8")
		assert "prd_doc_id: DocId_123" in yaml_text
		assert "jira_project_key: PROJ" in yaml_text
		assert "github_repo: org/repo" in yaml_text
