import pytest
from datetime import datetime, timedelta
from src.models import TrackedEvent
from src.portfolio_manager import PortfolioManager

def make_event(predicted_action):
    return TrackedEvent(
        id="e1",
        name="Event 1",
        event_time=datetime.utcnow(),
        keywords=["test"],
        predicted_action=predicted_action
    )

def test_correct_prediction():
    pm = PortfolioManager(1000)
    event = make_event("Call")
    new_value = pm.update_on_event(event, actual_outcome="Call")
    assert new_value == 1100
    assert pm.get_value() == 1100
    assert len(pm.get_history()) == 2

def test_incorrect_prediction():
    pm = PortfolioManager(1000)
    event = make_event("Put")
    new_value = pm.update_on_event(event, actual_outcome="Call")
    assert new_value == 950
    assert pm.get_value() == 950
    assert len(pm.get_history()) == 2

def test_hold_prediction():
    pm = PortfolioManager(1000)
    event = make_event("Hold")
    new_value = pm.update_on_event(event, actual_outcome="Call")
    assert new_value == 1000
    assert pm.get_value() == 1000
    assert len(pm.get_history()) == 2

def test_no_prediction():
    pm = PortfolioManager(1000)
    event = make_event(None)
    new_value = pm.update_on_event(event, actual_outcome="Call")
    assert new_value == 1000
    assert pm.get_value() == 1000
    assert len(pm.get_history()) == 2

def test_history_tracking():
    pm = PortfolioManager(1000)
    event1 = make_event("Call")
    event2 = make_event("Put")
    pm.update_on_event(event1, actual_outcome="Call")
    pm.update_on_event(event2, actual_outcome="Call")
    history = pm.get_history()
    assert len(history) == 3
    assert history[0][1] == 1000
    assert history[1][1] == 1100
    assert history[2][1] == 1050 