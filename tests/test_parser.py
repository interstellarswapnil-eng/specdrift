import pytest

from specdrift.parser.gdocs import extract_metadata, parse_sections


def test_extract_metadata_parses_block_and_cleans_text():
	text = """Some content
<!-- specdrift
jira: PROJ-101, PROJ-102
status: in-progress
last-reviewed: 2025-03-01
-->
More content
"""
	meta, cleaned = extract_metadata(text)
	assert meta["jira"] == "PROJ-101, PROJ-102"
	assert meta["status"] == "in-progress"
	assert "specdrift" not in cleaned
	assert "Some content" in cleaned
	assert "More content" in cleaned


def test_parse_sections_splits_on_headings_and_hashes_content():
	# Minimal mocked Google Docs API response.
	doc = {
		"body": {
			"content": [
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "HEADING_1"},
						"elements": [{"textRun": {"content": "Feature PRD\n"}}],
					}
				},
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
						"elements": [
							{"textRun": {"content": "Intro paragraph.\n"}},
							{
								"textRun": {
									"content": "<!-- specdrift\njira: PROJ-1\nstatus: in-progress\n-->\n"
								}
							},
						],
					}
				},
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "HEADING_2"},
						"elements": [{"textRun": {"content": "Functional Requirements\n"}}],
					}
				},
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "HEADING_3"},
						"elements": [{"textRun": {"content": "Authentication\n"}}],
					}
				},
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
						"elements": [{"textRun": {"content": "Users can log in.\n"}}],
					}
				},
			]
		}
	}

	sections = parse_sections(doc)
	assert [s.id for s in sections] == ["1", "1.1", "1.1.1"]
	assert sections[0].title == "Feature PRD"
	assert "Intro paragraph" in sections[0].content
	assert sections[0].metadata.get("jira") == "PROJ-1"
	assert sections[0].linked_jira_ids == ["PROJ-1"]
	assert sections[0].content_hash and len(sections[0].content_hash) == 64

	assert sections[2].title == "Authentication"
	assert "Users can log in" in sections[2].content


def test_parse_sections_ignores_leading_text_before_first_heading():
	doc = {
		"body": {
			"content": [
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
						"elements": [{"textRun": {"content": "Orphan text.\n"}}],
					}
				},
				{
					"paragraph": {
						"paragraphStyle": {"namedStyleType": "HEADING_1"},
						"elements": [{"textRun": {"content": "Start\n"}}],
					}
				},
			]
		}
	}
	sections = parse_sections(doc)
	assert len(sections) == 1
	assert sections[0].content == ""


def test_fetch_doc_oauth_uses_installed_app_flow_and_writes_token(monkeypatch):
	from unittest.mock import Mock, mock_open

	from specdrift.parser import gdocs

	# Ensure service-account path is NOT taken; OAuth path IS taken.
	monkeypatch.delenv("GOOGLE_CREDENTIALS_FILE", raising=False)
	monkeypatch.setenv("GOOGLE_OAUTH_CREDENTIALS", "/tmp/oauth-client.json")

	# Make the client secrets file "exist", token file "not exist"
	def fake_exists(path: str) -> bool:
		if path == "/tmp/oauth-client.json":
			return True
		if path.endswith("/.config/specdrift/token.json"):
			return False
		return False

	monkeypatch.setattr(gdocs.os.path, "exists", fake_exists)

	# Avoid touching the real filesystem
	makedirs = Mock()
	monkeypatch.setattr(gdocs.os, "makedirs", makedirs)

	# Fake creds returned by the OAuth flow
	fake_creds = Mock()
	fake_creds.valid = True
	fake_creds.expired = False
	fake_creds.refresh_token = None
	fake_creds.to_json.return_value = '{"token":"abc"}'

	# Mock InstalledAppFlow
	fake_flow = Mock()
	fake_flow.run_local_server.return_value = fake_creds
	InstalledAppFlow = Mock()
	InstalledAppFlow.from_client_secrets_file.return_value = fake_flow

	# Mock build() chain -> documents().get(...).execute()
	execute = Mock(return_value={"documentId": "DOC123"})
	get = Mock(return_value=Mock(execute=execute))
	documents = Mock(return_value=Mock(get=get))
	build = Mock(return_value=Mock(documents=documents))

	# Patch the google imports used inside fetch_doc by injecting into sys.modules
	import sys

	monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", Mock(InstalledAppFlow=InstalledAppFlow))
	monkeypatch.setitem(sys.modules, "googleapiclient.discovery", Mock(build=build))
	monkeypatch.setitem(sys.modules, "google.auth.transport.requests", Mock(Request=Mock()))
	monkeypatch.setitem(sys.modules, "google.oauth2.credentials", Mock(Credentials=Mock()))

	# Mock open() for writing token.json
	m = mock_open()
	monkeypatch.setattr("builtins.open", m)

	out = gdocs.fetch_doc("DOC123")

	assert out["documentId"] == "DOC123"
	InstalledAppFlow.from_client_secrets_file.assert_called_once()
	fake_flow.run_local_server.assert_called_once()
	m.assert_called()  # token.json write attempted
	build.assert_called_once()
