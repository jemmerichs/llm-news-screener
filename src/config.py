from typing import List
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from datetime import datetime

class RedditConfig(BaseModel):
    """Reddit-specific configuration."""
    subreddits: List[str] = Field(..., description="List of subreddits to monitor")
    fetch_interval: int = Field(300, description="Interval between fetches in seconds")
    max_posts_per_fetch: int = Field(4, description="Maximum number of posts to fetch per interval")

class EventConfig(BaseModel):
    """Configuration for a tracked event."""
    id: str
    name: str
    event_time: datetime
    keywords: List[str]

class PortfolioConfig(BaseModel):
    """Virtual portfolio configuration."""
    initial_value: float = Field(1000.0, description="Initial portfolio value")
    points_per_correct: float = Field(100.0, description="Points awarded for correct predictions")
    points_per_incorrect: float = Field(-50.0, description="Points deducted for incorrect predictions")

class SentimentConfig(BaseModel):
    """Sentiment analysis configuration."""
    lock_hours_before: int = Field(1, description="Hours before event to lock bias")
    min_confidence: float = Field(0.6, description="Minimum confidence score for predictions")

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field("INFO", description="Logging level")
    file: str = Field("logs/app.log", description="Log file path")
    max_size: str = Field("10MB", description="Maximum size of log file")
    backup_count: int = Field(5, description="Number of backup log files to keep")

class AppConfig(BaseModel):
    """Main application configuration."""
    reddit: RedditConfig
    portfolio: PortfolioConfig
    sentiment: SentimentConfig
    logging: LoggingConfig
    ui_update_interval: int = Field(5, description="Interval (in seconds) between UI/state updates")
    max_events: int = Field(10, description="Maximum number of events allowed")

def load_config(config_path: str | Path) -> AppConfig:
    """
    Load and validate configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        AppConfig: Validated configuration object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ValidationError: If config doesn't match expected schema
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    return AppConfig(**config_dict) 