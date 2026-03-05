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
