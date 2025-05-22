from datetime import datetime, timezone
from typing import List, Tuple
from src.models import TrackedEvent


class PortfolioManager:
    def __init__(self, initial_value: float = 1000.0):
        self.current_value = initial_value
        self.history: List[Tuple[datetime, float]] = [
            (datetime.now(timezone.utc), initial_value)
        ]

    def update_on_event(self, event: TrackedEvent, actual_outcome: str) -> float:
        """
        Update portfolio value based on event's predicted_action and actual outcome.
        Returns the new portfolio value.
        """
        if not event.predicted_action or event.predicted_action == "Hold":
            delta = 0
        elif event.predicted_action == actual_outcome:
            delta = 100  # Reward for correct prediction
        else:
            delta = -50  # Penalty for incorrect prediction
        self.current_value += delta
        self.history.append((datetime.now(timezone.utc), self.current_value))
        return self.current_value

    def get_value(self) -> float:
        return self.current_value

    def get_history(self) -> List[Tuple[datetime, float]]:
        return self.history
