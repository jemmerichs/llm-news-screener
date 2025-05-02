from src.models import TrackedEvent

class Predictor:
    @staticmethod
    def predict(event: TrackedEvent) -> TrackedEvent:
        """
        Aggregates all insights for the event, determines predicted_action, generates thinking_text, and updates the event.
        """
        if not event.insights:
            return event
        # Use the most recent N insights (e.g., last 5)
        recent_insights = event.insights[-5:]
        avg_score = sum(i.score for i in recent_insights) / len(recent_insights)
        # Determine bias
        if avg_score > 0.3:
            action = "Call"
        elif avg_score < -0.3:
            action = "Put"
        else:
            action = "Hold"
        # Combine thoughts for thinking_text
        thinking_text = "\n".join(i.text for i in recent_insights)
        # Update event
        updated_event = event.copy(update={
            "predicted_action": action,
            "thinking_text": thinking_text
        })
        return updated_event 