import os
import signal
import sys
import time
from datetime import timezone  # Removed timedelta, datetime
from loguru import logger
from dotenv import load_dotenv
from pathlib import Path

import threading

from src.config import load_config
from src.logger import setup_logging
from src.app_repository import AppRepository
from src.portfolio_manager import PortfolioManager
from src.models import TrackedEvent
from src.news_analyzer import NewsAnalyzer
from src.event_predictor import Predictor
from src.reddit_scraper import RedditScraper
from src.find_target_events import FindTargetEvents

# Load configuration
load_dotenv()
config = load_config(Path("config/config.yaml"))
setup_logging(config.logging)
logger.info("Starting TwitchBot...")
logger.info("Test log: server started and logging is working.")

# Initialize NewsAnalyzer after dotenv is loaded
news_analyzer = NewsAnalyzer()

# Load state from disk if available
state_file = "state.json"
state_exists = os.path.exists(state_file)
app_repo = AppRepository(max_events=getattr(config, "max_events", 10))
portfolio_manager = PortfolioManager()
# Store global LLM log entries
app_repo.llm_log = []


def main(with_signals=True):
    """Main entry point for the application."""
    try:
        # Load configuration
        load_dotenv()
        config = load_config(Path("config/config.yaml"))
        setup_logging(config.logging)
        logger.info("Starting TwitchBot...")
        logger.info("Test log: server started and logging is working.")

        # Initialize NewsAnalyzer after dotenv is loaded
        news_analyzer = NewsAnalyzer()

        # Load state from disk if available
        state_file = "state.json"
        state_exists = os.path.exists(state_file)
        app_repo.load()
        if not state_exists:
            # Seed events from config.yaml only if state.json does not exist
            for event_cfg in config.events:
                event = TrackedEvent(
                    id=event_cfg.id,
                    name=event_cfg.name,
                    event_time=event_cfg.event_time,
                    keywords=event_cfg.keywords,
                )
                logger.info(f"main.py: Adding event from config of type {type(event)}")
                assert isinstance(
                    event, TrackedEvent
                ), f"Attempted to add non-TrackedEvent: {event}"
                event_time = event.event_time
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                event.event_time = event_time
                app_repo.events.add(event)
                logger.info(f"Added event from config: {event.id}")
            # Force immediate save to debug state
            app_repo.save()

        # --- Event update logic: ensure at least 3 up-to-date events ---
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        # Remove outdated events
        current_events = app_repo.events.get_all()
        outdated_ids = [e.id for e in current_events if e.event_time < now]
        for eid in outdated_ids:
            app_repo.events.remove(eid)
        # Refresh current events after removals
        current_events = app_repo.events.get_all()
        needed = 3 - len(current_events)
        logger.info(f"Event update: needed={needed}, outdated_ids={outdated_ids}")
        if needed > 0:
            logger.info("Attempting to fetch new events from LLM...")
            # Call the synchronous method to get LLM events
            llm_events = FindTargetEvents().get_llm_events(needed)
            logger.info(
                f"Fetched {len(llm_events)} events from LLM: "
                f"{[e.id for e in llm_events]}"
            )
            # Only add events that are not already present (by ID)
            existing_ids = {e.id for e in app_repo.events.get_all()}
            added = False
            for event in llm_events:
                if event.id not in existing_ids:
                    logger.info(
                        f"Adding event to repository: {event.id} - {event.name}"
                    )
                    app_repo.events.add(event)
                    added = True
            logger.info(
                f"Events after update: {[e.id for e in app_repo.events.get_all()]}"
            )
            if added or outdated_ids:
                app_repo.save()
                logger.info("Saved state after event update.")

        last_save = time.time()

        # Initialize RedditScraper directly
        scraper = RedditScraper(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )

        shutdown_event = threading.Event()

        def signal_handler(signum, frame):
            logger.info("Shutting down...")
            app_repo.save()
            shutdown_event.set()
            sys.exit(0)

        if with_signals:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

        # Track processed news IDs to avoid duplicate analysis
        # Use persistent processed_news_ids from app_repo
        shown_news_ids = set()

        # Main integration loop
        fetch_interval = getattr(config.reddit, "fetch_interval", 300)
        logger.info(
            f"Reddit fetch interval set to {fetch_interval} seconds from config."
        )
        save_interval = getattr(config, "ui_update_interval", 5)
        while not shutdown_event.is_set():
            try:
                # 1. Fetch news from all subreddits and update state
                all_news = []
                for subreddit in config.reddit.subreddits:
                    try:
                        posts = scraper.fetch_subreddit_posts(
                            subreddit, limit=config.reddit.max_posts_per_fetch
                        )
                        all_news.extend(posts)
                    except Exception as e:
                        logger.error(f"Error fetching from r/{subreddit}: {str(e)}")
                        continue
                # Only process new news for analysis
                new_news = [
                    n for n in all_news if n.id not in app_repo.processed_news_ids
                ]
                for news in new_news:
                    # Only add to state if not already shown, and only if truly new
                    if news.id not in shown_news_ids:
                        added = app_repo.news.add(news)
                        if added:
                            app_repo.save()  # Save state immediately after adding news
                        shown_news_ids.add(news.id)

                # 2. Analyze all new news items (synchronously)
                for news in new_news:
                    results = news_analyzer.analyze(news, app_repo.events.get_all())
                    if hasattr(results, "__await__"):
                        import asyncio

                        results = asyncio.run(results)
                    for event_id, insight in results:
                        if event_id == "__global__":
                            current_time_iso = datetime.now(timezone.utc).isoformat()
                            log_entry = (
                                {
                                    "text": insight.text,
                                    "score": insight.score,
                                    "trend": insight.trend,
                                    "timestamp": insight.timestamp.isoformat(),
                                    "news_id": news.id,
                                    "news_title": news.title,
                                    "added_at": current_time_iso,
                                },
                            )
                            app_repo.llm_log.insert(0, log_entry)
                        else:
                            event = next(
                                (
                                    e
                                    for e in app_repo.events.get_all()
                                    if e.id == event_id
                                ),
                                None,
                            )
                            if event:
                                event.insights.append(insight)
                                app_repo.events.update(event_id, event)
                                # Also add event-specific insights to llm_log for UI display
                                app_repo.llm_log.insert(
                                    0,
                                    {
                                        "text": insight.text,
                                        "score": insight.score,
                                        "trend": insight.trend,
                                        "timestamp": insight.timestamp.isoformat(),
                                        "news_id": news.id,
                                        "news_title": news.title,
                                        "event_id": event_id,
                                        "added_at": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                    },
                                )
                    app_repo.processed_news_ids.add(news.id)
                    app_repo.save()  # Save state after each LLM analysis

                # 3. After all news are analyzed, run prediction for each event
                for event in app_repo.events.get_all():
                    assert not isinstance(event, dict), f"Dict found in events: {event}"
                    updated_event = Predictor.predict(event)
                    app_repo.events.update(event.id, updated_event)

                # 4. Simulate event completion and portfolio update
                now = datetime.now(timezone.utc)
                for event in app_repo.events.get_all():
                    et = event.event_time
                    if et.tzinfo is None:
                        et = et.replace(tzinfo=timezone.utc)
                    et_ts = et.timestamp()
                    now_ts = now.timestamp()
                    if not event.is_locked and (et_ts - now_ts) < 0:
                        actual_outcome = "Call"
                        portfolio_manager.update_on_event(event, actual_outcome)
                        from src.models import VirtualPortfolio

                        app_repo.portfolio.set(
                            VirtualPortfolio(
                                current_value=portfolio_manager.get_value()
                            )
                        )
                        # For lock, update the event object directly and store
                        locked_event = app_repo.events.get(event.id)
                        locked_event.is_locked = True
                        locked_event.lock_time = now
                        app_repo.events.update(event.id, locked_event)

                # 5. Update portfolio in state
                from src.models import VirtualPortfolio

                app_repo.portfolio.set(
                    VirtualPortfolio(current_value=portfolio_manager.get_value())
                )

                # 6. Save state every 5 seconds
                now = time.time()
                if now - last_save >= save_interval:
                    app_repo.save()
                    last_save = now

            except Exception as e:
                logger.exception(f"Main loop error: {e}")
            sleep_step = 1
            slept = 0
            while not shutdown_event.is_set() and slept < fetch_interval:
                time.sleep(sleep_step)
                slept += sleep_step

    except Exception as e:
        logger.exception(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main(with_signals=True)
