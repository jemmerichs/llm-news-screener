import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.models import TrackedEvent, Insight
from src.event_manager import EventManager

@pytest.fixture
def sample_event():
    return TrackedEvent(
        id="test_event",
        name="Test Event",
        event_time=datetime.utcnow() + timedelta(hours=2),
        keywords=["test", "event"]
    )

@pytest.fixture
def temp_persistence_file(tmp_path):
    return tmp_path / "events.json"

def test_add_event(sample_event):
    manager = EventManager()
    added_event = manager.add_event(sample_event)
    assert added_event == sample_event
    assert len(manager.get_events()) == 1

def test_add_duplicate_event(sample_event):
    manager = EventManager()
    manager.add_event(sample_event)
    with pytest.raises(ValueError):
        manager.add_event(sample_event)

def test_get_event(sample_event):
    manager = EventManager()
    manager.add_event(sample_event)
    retrieved = manager.get_event(sample_event.id)
    assert retrieved == sample_event

def test_update_event(sample_event):
    manager = EventManager()
    manager.add_event(sample_event)
    
    # Update name
    updated = manager.update_event(sample_event.id, {"name": "Updated Event"})
    assert updated.name == "Updated Event"
    assert updated.id == sample_event.id

def test_update_locked_event(sample_event):
    manager = EventManager()
    manager.add_event(sample_event)
    
    # Lock the event
    manager.update_event(sample_event.id, {"is_locked": True})
    
    # Try to update name (should be prevented)
    updated = manager.update_event(sample_event.id, {"name": "Updated Event"})
    assert updated.name == sample_event.name  # Name should not change

def test_remove_event(sample_event):
    manager = EventManager()
    manager.add_event(sample_event)
    assert manager.remove_event(sample_event.id)
    assert len(manager.get_events()) == 0

def test_process_events():
    manager = EventManager()
    
    # Add event happening in 30 minutes
    soon_event = TrackedEvent(
        id="soon_event",
        name="Soon Event",
        event_time=datetime.utcnow() + timedelta(minutes=30),
        keywords=["test"]
    )
    manager.add_event(soon_event)
    
    # Add event happening in 2 hours
    later_event = TrackedEvent(
        id="later_event",
        name="Later Event",
        event_time=datetime.utcnow() + timedelta(hours=2),
        keywords=["test"]
    )
    manager.add_event(later_event)
    
    # Process events
    changed = manager.process_events()
    
    # Only soon_event should be locked
    assert len(changed) == 1
    assert changed[0].id == "soon_event"
    assert changed[0].is_locked
    assert changed[0].lock_time is not None

def test_persistence(sample_event, temp_persistence_file):
    # Create manager and add event
    manager = EventManager(persistence_file=temp_persistence_file)
    manager.add_event(sample_event)
    
    # Create new manager with same file
    new_manager = EventManager(persistence_file=temp_persistence_file)
    loaded_event = new_manager.get_event(sample_event.id)
    
    assert loaded_event == sample_event 

def test_reevaluate_event_positive():
    event = TrackedEvent(
        id="e1",
        name="Event 1",
        event_time=datetime.utcnow(),
        keywords=["test"],
        insights=[
            Insight(text="Positive outlook", score=0.8, trend="improving"),
            Insight(text="Strong growth", score=0.7, trend="improving"),
        ]
    )
    manager = EventManager()
    updated = manager.reevaluate_event(event)
    assert updated.predicted_action == "Call"
    assert "Positive outlook" in updated.thinking_text
    assert "Strong growth" in updated.thinking_text

def test_reevaluate_event_negative():
    event = TrackedEvent(
        id="e2",
        name="Event 2",
        event_time=datetime.utcnow(),
        keywords=["test"],
        insights=[
            Insight(text="Negative news", score=-0.9, trend="worsening"),
            Insight(text="Declining sentiment", score=-0.7, trend="worsening"),
        ]
    )
    manager = EventManager()
    updated = manager.reevaluate_event(event)
    assert updated.predicted_action == "Put"
    assert "Negative news" in updated.thinking_text
    assert "Declining sentiment" in updated.thinking_text

def test_reevaluate_event_neutral():
    event = TrackedEvent(
        id="e3",
        name="Event 3",
        event_time=datetime.utcnow(),
        keywords=["test"],
        insights=[
            Insight(text="Mixed signals", score=0.1, trend="stable"),
            Insight(text="Unclear direction", score=-0.1, trend="stable"),
        ]
    )
    manager = EventManager()
    updated = manager.reevaluate_event(event)
    assert updated.predicted_action == "Hold"
    assert "Mixed signals" in updated.thinking_text
    assert "Unclear direction" in updated.thinking_text

def test_reevaluate_event_no_insights():
    event = TrackedEvent(
        id="e4",
        name="Event 4",
        event_time=datetime.utcnow(),
        keywords=["test"],
        insights=[]
    )
    manager = EventManager()
    updated = manager.reevaluate_event(event)
    assert updated.predicted_action is None
    assert updated.thinking_text is None 