import pytest
from datetime import datetime, timezone
from src.app_repository import AppRepository


def make_entry(text, added_at):
    return {
        "text": text,
        "score": 0.0,
        "trend": "n/a",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "news_id": "n1",
        "news_title": "title",
        "added_at": added_at,
    }

def test_llm_log_entries_are_dicts_and_sorted():
    repo = AppRepository()
    e1 = make_entry("first", "2024-01-01T00:00:00Z")
    e2 = make_entry("second", "2024-01-02T00:00:00Z")
    repo.llm_log.append(e1)
    repo.llm_log.append(e2)
    data = repo.get_app_data()
    assert isinstance(data["llm_log"][0], dict)
    assert data["llm_log"][0]["text"] == "second"
    assert data["llm_log"][1]["text"] == "first"
