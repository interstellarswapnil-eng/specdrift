from __future__ import annotations

from dataclasses import dataclass

import pytest

from specdrift.gh_linker.pr_bot import build_pr_comment, check_pr_and_maybe_comment
from specdrift.gh_linker.gh_linker import detect_unlinked_prs


@dataclass
class FakeFile:
	filename: str


class FakePR:
	def __init__(self, *, number: int, body: str, files: list[str], merged: bool = True):
		self.number = number
		self.body = body
		self._files = [FakeFile(f) for f in files]
		self.merged = merged

	def get_files(self):
		return self._files

	def create_issue_comment(self, body: str):
		self._comment_body = body


class FakeRepo:
	def __init__(self, pr: FakePR):
		self._pr = pr

	def get_pull(self, number: int):
		assert number == self._pr.number
		return self._pr


class FakeGithub:
	def __init__(self, token: str):
		self.token = token
		self._repo = None

	def get_repo(self, full_name: str):
		assert self._repo is not None
		return self._repo


def test_build_pr_comment_includes_copy_paste_template():
	body = build_pr_comment(
		jira_project_key="PROJ",
		matched_prd_sections=["3.1"],
		files=["src/auth/login.ts"],
		dashboard_url="https://org.github.io/repo/",
	)
	assert "PRD-Section:" in body
	assert "Jira:" in body
	assert "src/auth/login.ts" in body
	assert "Dashboard:" in body


def test_check_pr_and_maybe_comment_posts_comment_when_unlinked(monkeypatch):
	# PR with no references touching scoped files
	pr = FakePR(number=45, body="no refs", files=["src/auth/login.ts"], merged=True)
	fake_repo = FakeRepo(pr)

	# Monkeypatch PyGithub import path used inside pr_bot
	import specdrift.gh_linker.pr_bot as pr_bot

	class _GithubFactory:
		def __call__(self, token: str):
			gh = FakeGithub(token)
			gh._repo = fake_repo
			return gh

	monkeypatch.setenv("GITHUB_TOKEN", "tkn")
	monkeypatch.setattr(pr_bot, "Github", _GithubFactory(), raising=False)

	# Instead of relying on real PyGithub import, patch module-level import resolution:
	def fake_import_github():
		return None

	# Patch the already-imported name lookup by injecting into sys.modules
	import types, sys

	mod = types.SimpleNamespace(Github=_GithubFactory())
	sys.modules["github"] = mod

	scope_config = {
		"scope": {"modules": [{"name": "Auth", "prd_section": "3.1", "file_patterns": ["src/auth/**"]}]}
	}

	res = check_pr_and_maybe_comment(
		repo="org/repo",
		pr_number=45,
		scope_config=scope_config,
		jira_project_key="PROJ",
		github_token="tkn",
	)

	assert res.should_comment is True
	assert "PRD-Section:" in (res.comment_body or "")
	assert hasattr(pr, "_comment_body")
	assert "Scoped files touched" in pr._comment_body


def test_check_pr_and_maybe_comment_noop_when_not_merged(monkeypatch):
	pr = FakePR(number=1, body="no refs", files=["src/auth/login.ts"], merged=False)
	fake_repo = FakeRepo(pr)

	import types, sys

	class _GithubFactory:
		def __call__(self, token: str):
			gh = FakeGithub(token)
			gh._repo = fake_repo
			return gh

	sys.modules["github"] = types.SimpleNamespace(Github=_GithubFactory())

	res = check_pr_and_maybe_comment(
		repo="org/repo",
		pr_number=1,
		scope_config={"scope": {"modules": [{"prd_section": "3.1", "file_patterns": ["src/auth/**"]}]}},
		jira_project_key="PROJ",
		github_token="tkn",
	)
	assert res.should_comment is False
