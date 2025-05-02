import os
import time
from threading import Thread, Event
from typing import List
from loguru import logger
from dotenv import load_dotenv

from src.reddit_scraper import RedditScraper
from src.config import RedditConfig

class RedditWorker:
    def __init__(self, config: RedditConfig):
        """
        Initialize the Reddit worker.
        
        Args:
            config: Reddit configuration object containing subreddits, fetch interval,
                   and other settings
        """
        load_dotenv()
        
        self.scraper = RedditScraper(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        
        self.config = config
        self._stop_event = Event()
        self._worker_thread: Thread = None
        
        logger.info(f"Worker initialized for subreddits: {', '.join(config.subreddits)}")
    
    def _worker_loop(self):
        """Main worker loop that periodically fetches posts."""
        while not self._stop_event.is_set():
            try:
                for subreddit in self.config.subreddits:
                    try:
                        posts = self.scraper.fetch_subreddit_posts(
                            subreddit,
                            limit=self.config.max_posts_per_fetch
                        )
                        logger.info(f"Fetched {len(posts)} posts from r/{subreddit}")
                    except Exception as e:
                        logger.error(f"Error fetching from r/{subreddit}: {str(e)}")
                        continue
                
                # Wait for next fetch interval or until stopped
                self._stop_event.wait(self.config.fetch_interval)
                
            except Exception as e:
                logger.exception(f"Error in worker loop: {str(e)}")
                # Wait a bit before retrying after an error
                self._stop_event.wait(10)
    
    def start(self):
        """Start the background worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning("Worker is already running")
            return
        
        self._stop_event.clear()
        self._worker_thread = Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Worker started")
    
    def stop(self):
        """Stop the background worker thread."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join()
            logger.info("Worker stopped") 