"""
LLMEventService: Handles LLM-powered event discovery and updating for financial events.
Uses OpenAI to fetch and update the top three upcoming financial events.
"""
from datetime import datetime, timezone, timedelta, time as dtime
import json
import asyncio
import openai
import os
from loguru import logger
from src.app_repository import EventRepository
from src.models import TrackedEvent
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List

# Pydantic models for structured output
class EventResponseItem(BaseModel):
    id: str | int # Allow int or str from LLM
    name: str
    event_time: str # LLM provides ISO string
    keywords: List[str]
    stock: str
class EventListResponse(BaseModel):
    events: List[EventResponseItem]

class FindTargetEvents:
    """
    Service for seeding the event repository with upcoming financial events using OpenAI LLM.
    Should be called at app startup if there are no events defined.
    """
    def __init__(self):
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=openai_api_key)

    def get_llm_events(self, n=3) -> List[TrackedEvent]:
        """Fetch N events using OpenAI Structured Outputs and return TrackedEvent list."""
        prompt = (
            f"What are the next top {n} upcoming financial events? Focus on events within the next week or two."
            # No need to specify JSON format in prompt when using parse
        )
        try:
            response = self.client.responses.parse(
                model="gpt-4o", # Use a model supporting structured outputs
                input=[
                    {"role": "system", "content": "Extract the event information."},
                    {"role": "user", "content": prompt},
                ],
                text_format=EventListResponse,
                tools=[{"type": "web_search_preview"}] # Still use web search
            )
            parsed_output: EventListResponse = response.output_parsed
            if not parsed_output or not parsed_output.events:
                 logger.warning("LLM parsing returned no events.")
                 return []

        except Exception as e:
            logger.error(f"Failed to fetch or parse LLM events: {e}\nResponse: {locals().get('response', None)}")
            return []

        # Convert parsed items to TrackedEvent objects
        tracked_events = []
        for event_item in parsed_output.events:
            event_time = None
            try:
                # Try parsing ISO string (LLM should provide UTC via Z)
                event_time = datetime.fromisoformat(event_item.event_time.replace("Z", "+00:00"))
                if event_time.tzinfo is None: # Ensure timezone
                     event_time = event_time.replace(tzinfo=timezone.utc)
            except Exception as e_parse:
                logger.warning(f"Could not parse event_time '{event_item.event_time}' for event {event_item.id}: {e_parse}. Skipping.")
                continue

            try:
                tracked_event = TrackedEvent(
                    id=str(event_item.id), # Ensure ID is string
                    name=event_item.name,
                    event_time=event_time,
                    keywords=event_item.keywords,
                    stock=event_item.stock,  # Pass the stock field
                )
                tracked_events.append(tracked_event)
                logger.info(f"FindTargetEvents: Parsed event {tracked_event.id} at {tracked_event.event_time}")
            except Exception as e_create:
                logger.warning(f"Failed to create TrackedEvent from {event_item}: {e_create}")

        return tracked_events[:n] # Return up to N valid events 