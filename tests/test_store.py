from __future__ import annotations

from specdrift.store import SQLiteStateStore


def test_sections_roundtrip_in_memory_db():
	store = SQLiteStateStore(":memory:")
	try:
		store.save_sections(
			[
				{
					"id": "1",
					"title": "Overview",
					"level": 1,
					"content_hash": "abc",
					"metadata": {"jira": "PROJ-1"},
				},
			]
		)
		sections = store.get_sections()
		assert len(sections) == 1
		assert sections[0]["id"] == "1"
		assert sections[0]["metadata"]["jira"] == "PROJ-1"
	finally:
		store.close()


def test_save_drift_event_and_filter_since():
	store = SQLiteStateStore(":memory:")
	try:
		store.save_drift_event(
			section_id="1",
			signal_type="prd_changed_tickets_stale",
			severity="high",
			detail="Something drifted",
			detected_at="2026-03-01T00:00:00+00:00",
		)
		store.save_drift_event(
			section_id="1",
			signal_type="unlinked_pr_merged",
			severity="high",
			detail="Unlinked PR",
			detected_at="2026-03-05T00:00:00+00:00",
		)

		all_events = store.get_drift_events()
		assert len(all_events) == 2

		recent = store.get_drift_events(since="2026-03-03T00:00:00+00:00")
		assert len(recent) == 1
		assert recent[0]["signal_type"] == "unlinked_pr_merged"
	finally:
		store.close()


def test_log_sync_creates_rows():
	store = SQLiteStateStore(":memory:")
	try:
		id1 = store.log_sync("success", synced_at="2026-03-05T10:00:00+00:00")
		id2 = store.log_sync("failure", synced_at="2026-03-05T11:00:00+00:00")
		assert id2 > id1
	finally:
		store.close()
