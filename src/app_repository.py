from typing import List
from src.models import TrackedEvent, NewsItem, VirtualPortfolio
import json
import os
from pydantic import TypeAdapter
from loguru import logger
from datetime import datetime, timezone

class EventRepository:
    def __init__(self, max_events: int = 10):
        self._events: dict[str, TrackedEvent] = {}
        self.max_events = max_events
    def add(self, event: TrackedEvent):
        from src.models import TrackedEvent as TrackedEventModel
        logger.info(f"EventRepository.add: Adding event of type {type(event)}")
        assert isinstance(event, TrackedEventModel), f"Attempted to add non-TrackedEvent: {event}"
        if isinstance(event, dict):
            event = TrackedEventModel(**event)
        if event.id in self._events:
            raise ValueError(f"Event with ID {event.id} already exists")
        if len(self._events) >= self.max_events:
            logger.warning(f"EventRepository: Max events limit ({self.max_events}) reached. Not adding event {event.id}.")
            return False
        self._events[event.id] = event
        return True
    def update(self, event_id: str, new_event: TrackedEvent):
        from src.models import TrackedEvent as TrackedEventModel
        if isinstance(new_event, dict):
            new_event = TrackedEventModel(**new_event)
        self._events[event_id] = new_event
        return new_event
    def get_all(self) -> List[TrackedEvent]:
        from src.models import TrackedEvent as TrackedEventModel
        fixed = False
        for k, v in list(self._events.items()):
            pass  # No-op, previously logged event types
        for k, v in list(self._events.items()):
            if isinstance(v, dict):
                logger.warning(f"EventRepository: Found dict for event {k}, converting to TrackedEvent.")
                self._events[k] = TrackedEventModel(**v)
                fixed = True
            elif not isinstance(v, TrackedEventModel):
                logger.error(f"EventRepository: Found non-TrackedEvent for event {k}: {type(v)}")
                assert False, f"Non-TrackedEvent in repository: {v}"
        if fixed:
            logger.warning("EventRepository: One or more dicts were converted to TrackedEvent at runtime.")
        return list(self._events.values())
    def get(self, event_id: str):
        return self._events.get(event_id)
    def remove(self, event_id: str) -> bool:
        return self._events.pop(event_id, None) is not None

class NewsRepository:
    def __init__(self, max_news: int = 50):
        self.news_items: List[NewsItem] = []
        self.news_ids = set()
        self.max_news = max_news
    def add(self, news: NewsItem):
        if news.id in self.news_ids:
            return False  # No change
        self.news_items.append(news)
        self.news_ids.add(news.id)
        # Keep only the most recent N news, sorted by timestamp
        self.news_items = sorted(self.news_items, key=lambda n: n.timestamp, reverse=True)[:self.max_news]
        self.news_ids = set(n.id for n in self.news_items)
        logger.info(f"NewsRepository: Added news ID={news.id}, title='{news.title}'")
        return True  # News was added
    def get_all(self) -> List[NewsItem]:
        return self.news_items

class PortfolioRepository:
    def __init__(self):
        self.portfolio: VirtualPortfolio = VirtualPortfolio()
    def set(self, portfolio: VirtualPortfolio):
        self.portfolio = portfolio
    def get(self) -> VirtualPortfolio:
        return self.portfolio

class AppRepository:
    def __init__(self, max_events: int = 10):
        self.events = EventRepository(max_events=max_events)
        self.news = NewsRepository()
        self.portfolio = PortfolioRepository()
        self.llm_log = []
        self.processed_news_ids = set()
    def get_app_data(self) -> dict:
        sorted_llm_log = sorted(self.llm_log, key=lambda x: x.get("added_at") or x["timestamp"], reverse=True)
        sorted_news = sorted(self.news.get_all(), key=lambda n: n.added_at, reverse=True)
        return {
            "events": [e.model_dump(mode="json") for e in self.events.get_all()],
            "portfolio": self.portfolio.get().model_dump(mode="json"),
            "news_items": [n.model_dump(mode="json") for n in sorted_news],
            "llm_log": sorted_llm_log[:10],
            "processed_news_ids": list(self.processed_news_ids),
        }
    def save(self, filename="state.json"):
        tmp_filename = filename + ".tmp"
        news_count = len(self.news.get_all())
        logger.info(f"AppRepository: Saving state with {news_count} news items and {len(self.llm_log)} llm_log entries.")
        with open(tmp_filename, "w") as f:
            json.dump(self.get_app_data(), f, indent=2)
        os.replace(tmp_filename, filename)
    def load(self, filename="state.json"):
        try:
            with open(filename, "r") as f:
                state = json.load(f)
            # Restore events
            self.events._events = {}
            events_to_load = state.get("events", [])[:self.events.max_events]
            for e in events_to_load:
                from src.models import TrackedEvent
                self.events.add(TrackedEvent(**e))
            # Restore news
            self.news.news_items = []
            self.news.news_ids = set()
            for n in state.get("news_items", []):
                from src.models import NewsItem
                if "added_at" not in n:
                    n["added_at"] = n["timestamp"]
                self.news.add(NewsItem(**n))
            # Restore portfolio
            from src.models import VirtualPortfolio
            portfolio_data = state.get("portfolio")
            if portfolio_data:
                self.portfolio.set(VirtualPortfolio(**portfolio_data))
            # Restore llm_log
            self.llm_log = state.get("llm_log", [])
            # Restore processed_news_ids
            self.processed_news_ids = set(state.get("processed_news_ids", []))
            logger.info(f"AppRepository: Loaded state with {len(self.news.news_items)} news, {len(self.events._events)} events, {len(self.llm_log)} llm_log entries, {len(self.processed_news_ids)} processed news IDs.")
        except FileNotFoundError:
            logger.warning(f"AppRepository: State file {filename} not found. Starting fresh.")
        except Exception as e:
            logger.error(f"AppRepository: Failed to load state: {e}") 