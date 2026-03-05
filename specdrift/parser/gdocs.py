from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Any


_METADATA_RE = re.compile(r"<!--\s*specdrift(?P<body>.*?)-->", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class Section:
	"""A PRD section parsed from a Google Doc.

	Sections are delimited by H1/H2/H3 headings (per the v0.1 spec).
	"""

	id: str
	title: str
	level: int  # 1, 2, or 3
	content: str
	content_hash: str
	metadata: dict[str, str] = field(default_factory=dict)
	linked_jira_ids: list[str] = field(default_factory=list)
	status: str | None = None


class GoogleDocsError(RuntimeError):
	pass


def _get_text_from_paragraph(paragraph: dict[str, Any]) -> str:
	"""Extract plain text from a Google Docs paragraph structure."""
	out: list[str] = []
	for el in paragraph.get("elements", []):
		text_run = el.get("textRun")
		if not text_run:
			continue
		out.append(text_run.get("content", ""))
	return "".join(out)


def _named_style_to_level(named_style_type: str | None) -> int | None:
	if named_style_type == "HEADING_1":
		return 1
	if named_style_type == "HEADING_2":
		return 2
	if named_style_type == "HEADING_3":
		return 3
	return None


def extract_metadata(text: str) -> tuple[dict[str, str], str]:
	"""Extract the first <!-- specdrift ... --> metadata block from text.

	Returns: (metadata, cleaned_text)
	"""
	m = _METADATA_RE.search(text)
	if not m:
		return {}, text

	body = m.group("body")
	metadata: dict[str, str] = {}
	for raw_line in body.splitlines():
		line = raw_line.strip()
		if not line:
			continue
		if ":" not in line:
			continue
		k, v = line.split(":", 1)
		metadata[k.strip().lower()] = v.strip()

	cleaned = (text[: m.start()] + text[m.end() :]).strip()
	return metadata, cleaned


def _compute_hash(title: str, content: str) -> str:
	normalized = (title.strip() + "\n" + content.strip()).encode("utf-8")
	return hashlib.sha256(normalized).hexdigest()


def parse_sections(doc: dict[str, Any]) -> list[Section]:
	"""Parse a Google Docs API document response into sections.

	We treat each H1/H2/H3 as the start of a new section and collect text until
	the next heading.
	"""

	content = (doc.get("body") or {}).get("content") or []
	sections: list[Section] = []

	n1 = n2 = n3 = 0
	current: dict[str, Any] | None = None

	def flush() -> None:
		nonlocal current
		if not current:
			return

		meta, cleaned = extract_metadata(current["content"].strip())
		jira_raw = meta.get("jira", "")
		jira_ids = [j.strip() for j in re.split(r"[,\s]+", jira_raw) if j.strip()] if jira_raw else []
		status = meta.get("status")

		sections.append(
			Section(
				id=current["id"],
				title=current["title"],
				level=current["level"],
				content=cleaned,
				content_hash=_compute_hash(current["title"], cleaned),
				metadata=meta,
				linked_jira_ids=jira_ids,
				status=status,
			)
		)
		current = None

	for block in content:
		paragraph = block.get("paragraph")
		if not paragraph:
			continue

		style = (paragraph.get("paragraphStyle") or {}).get("namedStyleType")
		level = _named_style_to_level(style)
		text = _get_text_from_paragraph(paragraph).replace("\u000b", "").strip()
		if not text:
			continue

		if level in (1, 2, 3):
			flush()

			if level == 1:
				n1 += 1
				n2 = 0
				n3 = 0
				sec_id = f"{n1}"
			elif level == 2:
				n2 += 1
				n3 = 0
				sec_id = f"{n1}.{n2}"
			else:
				n3 += 1
				sec_id = f"{n1}.{n2}.{n3}"

			current = {"id": sec_id, "title": text, "level": level, "content": ""}
			continue

		# Normal paragraph: belongs to the current section.
		if current is None:
			# Ignore leading content before first heading.
			continue
		current["content"] += (text + "\n")

	flush()
	return sections


def fetch_doc(doc_id: str) -> dict[str, Any]:
	"""Fetch a Google Doc using a service account credentials JSON.

	Credentials file path must be provided via GOOGLE_CREDENTIALS_FILE.
	"""
	creds_path = os.environ.get("GOOGLE_CREDENTIALS_FILE")
	if not creds_path:
		raise GoogleDocsError("GOOGLE_CREDENTIALS_FILE env var is required")
	if not os.path.exists(creds_path):
		raise GoogleDocsError(f"GOOGLE_CREDENTIALS_FILE not found: {creds_path}")

	try:
		from google.oauth2.service_account import Credentials
		from googleapiclient.discovery import build
	except Exception as e:  # pragma: no cover
		raise GoogleDocsError(
			"Google API dependencies not installed. Install optional deps: pip install 'specdrift[engine]'"
		) from e

	scopes = ["https://www.googleapis.com/auth/documents.readonly"]
	creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
	service = build("docs", "v1", credentials=creds)
	return service.documents().get(documentId=doc_id).execute()
