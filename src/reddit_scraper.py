import time
from datetime import datetime, timedelta, timezone
from typing import List
import praw
from loguru import logger

from src.models import NewsItem

class RedditScraper:
    def __init__(self, client_id: str, client_secret: str, user_agent: str,
                 rate_limit_calls: int = 30, rate_limit_period: int = 60):
        """
        Initialize the Reddit scraper with rate limiting.
        
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit API user agent
            rate_limit_calls: Maximum number of API calls per period (default: 30)
            rate_limit_period: Period in seconds for rate limiting (default: 60)
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        # Rate limiting setup
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period
        self.call_timestamps: List[float] = []
        self.seen_news_ids = set()
        
        logger.info("Reddit scraper initialized")
    
    def _check_rate_limit(self) -> None:
        """
        Implement rate limiting by tracking API calls.
        Sleeps if necessary to respect the rate limit.
        """
        current_time = time.time()
        
        # Remove timestamps older than the rate limit period
        self.call_timestamps = [ts for ts in self.call_timestamps
                              if current_time - ts <= self.rate_limit_period]
        
        # If we've hit the rate limit, sleep until we can make another call
        if len(self.call_timestamps) >= self.rate_limit_calls:
            sleep_time = self.call_timestamps[0] + self.rate_limit_period - current_time
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        # Add current timestamp
        self.call_timestamps.append(current_time)
    
    def fetch_subreddit_posts(self, subreddit_name: str, limit: int = 10,
                            max_retries: int = 3, retry_delay: int = 5) -> List[NewsItem]:
        """
        Fetch recent posts from a subreddit with retry logic.
        
        Args:
            subreddit_name: Name of the subreddit to fetch from
            limit: Maximum number of posts to fetch
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        
        Returns:
            List of NewsItem objects
        """
        for attempt in range(max_retries):
            try:
                self._check_rate_limit()
                
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = list(subreddit.new(limit=limit))
                
                news_items = []
                for post in posts:
                    # Only include posts from the last 24 hours
                    post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                    if datetime.now(timezone.utc) - post_time > timedelta(hours=24):
                        continue
                    if post.id in self.seen_news_ids:
                        continue
                        
                    news_item = NewsItem(
                        id=post.id,
                        source=subreddit_name,
                        title=post.title,
                        snippet=post.selftext[:500] if post.selftext else "[No content]",
                        timestamp=post_time,
                        added_at=datetime.now(timezone.utc)
                    )
                    news_items.append(news_item)
                    self.seen_news_ids.add(post.id)
                
                logger.info(f"RedditScraper: {len(posts)} posts fetched, {len(news_items)} news items after filtering. IDs: {[n.id for n in news_items]}")
                return sorted(news_items, key=lambda x: x.timestamp, reverse=True)
                
            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise 