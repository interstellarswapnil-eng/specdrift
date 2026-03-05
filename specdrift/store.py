from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


class SQLiteStateStore:
	"""SQLite-backed state store for SpecDrift.

	Tables:
	- sections
	- drift_events
	- sync_log
	"""

	def __init__(self, db_path: str = "specdrift.db"):
		self.db_path = db_path
		self.conn = sqlite3.connect(db_path)
		self.conn.row_factory = sqlite3.Row
		self._init_schema()

	def close(self) -> None:
		self.conn.close()

	def _init_schema(self) -> None:
		cur = self.conn.cursor()
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS sections (
				id TEXT PRIMARY KEY,
				title TEXT NOT NULL,
				level INTEGER NOT NULL,
				content_hash TEXT NOT NULL,
				metadata_json TEXT NOT NULL,
				last_synced TEXT NOT NULL
			)
			"""
		)
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS drift_events (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				section_id TEXT NOT NULL,
				signal_type TEXT NOT NULL,
				severity TEXT NOT NULL,
				detail TEXT NOT NULL,
				detected_at TEXT NOT NULL
			)
			"""
		)
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS sync_log (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				synced_at TEXT NOT NULL,
				status TEXT NOT NULL
			)
			"""
		)
		self.conn.commit()

	def save_sections(self, sections: Iterable[Any]) -> None:
		"""Upsert a list of sections.

		Expected fields per section: id, title, level, content_hash, metadata
		"""
		now = _utc_now_iso()
		cur = self.conn.cursor()
		for s in sections:
			if is_dataclass(s):
				data = asdict(s)
			elif isinstance(s, dict):
				data = s
			else:
				raise TypeError("section must be a dataclass or dict")

			sec_id = data.get("id")
			title = data.get("title")
			level = data.get("level")
			content_hash = data.get("content_hash")
			metadata = data.get("metadata") or {}

			if not sec_id or not isinstance(sec_id, str):
				raise ValueError("section.id must be a non-empty string")
			if not title or not isinstance(title, str):
				raise ValueError(f"section.title must be a non-empty string (id={sec_id})")
			if not isinstance(level, int):
				raise ValueError(f"section.level must be an int (id={sec_id})")
			if not content_hash or not isinstance(content_hash, str):
				raise ValueError(f"section.content_hash must be a non-empty string (id={sec_id})")
			if not isinstance(metadata, dict):
				raise ValueError(f"section.metadata must be a dict (id={sec_id})")

			cur.execute(
				"""
				INSERT INTO sections (id, title, level, content_hash, metadata_json, last_synced)
				VALUES (?, ?, ?, ?, ?, ?)
				ON CONFLICT(id) DO UPDATE SET
					title=excluded.title,
					level=excluded.level,
					content_hash=excluded.content_hash,
					metadata_json=excluded.metadata_json,
					last_synced=excluded.last_synced
				""",
				(sec_id, title, level, content_hash, json.dumps(metadata), now),
			)

		self.conn.commit()

	def get_sections(self) -> list[dict[str, Any]]:
		cur = self.conn.cursor()
		rows = cur.execute(
			"SELECT id, title, level, content_hash, metadata_json, last_synced FROM sections ORDER BY id"
		).fetchall()
		out: list[dict[str, Any]] = []
		for r in rows:
			out.append(
				{
					"id": r["id"],
					"title": r["title"],
					"level": r["level"],
					"content_hash": r["content_hash"],
					"metadata": json.loads(r["metadata_json"]),
					"last_synced": r["last_synced"],
				}
			)
		return out

	def save_drift_event(
		self,
		*,
		section_id: str,
		signal_type: str,
		severity: str,
		detail: str,
		detected_at: str | None = None,
	) -> int:
		detected_at = detected_at or _utc_now_iso()
		cur = self.conn.cursor()
		cur.execute(
			"""
			INSERT INTO drift_events (section_id, signal_type, severity, detail, detected_at)
			VALUES (?, ?, ?, ?, ?)
			""",
			(section_id, signal_type, severity, detail, detected_at),
		)
		self.conn.commit()
		return int(cur.lastrowid)

	def get_drift_events(self, since: str | None = None) -> list[dict[str, Any]]:
		cur = self.conn.cursor()
		if since:
			rows = cur.execute(
				"""
				SELECT id, section_id, signal_type, severity, detail, detected_at
				FROM drift_events
				WHERE detected_at >= ?
				ORDER BY detected_at ASC
				""",
				(since,),
			).fetchall()
		else:
			rows = cur.execute(
				"""
				SELECT id, section_id, signal_type, severity, detail, detected_at
				FROM drift_events
				ORDER BY detected_at ASC
				"""
			).fetchall()

		return [dict(r) for r in rows]

	def log_sync(self, status: str, *, synced_at: str | None = None) -> int:
		synced_at = synced_at or _utc_now_iso()
		cur = self.conn.cursor()
		cur.execute(
			"INSERT INTO sync_log (synced_at, status) VALUES (?, ?)",
			(synced_at, status),
		)
		self.conn.commit()
		return int(cur.lastrowid)
