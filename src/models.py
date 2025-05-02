from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class NewsItem(BaseModel):
    """Represents a news item fetched from Reddit."""
    id: str = Field(..., description="Unique identifier for the news item")
    source: str = Field(..., description="Source of the news item (e.g., subreddit name)")
    title: str = Field(..., description="Title of the news item")
    snippet: str = Field(..., description="Brief excerpt or content of the news item")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the news item was created/fetched")
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the news item was added to the repository")

class Insight(BaseModel):
    text: str = Field(..., description="LLM-generated insight or thought")
    score: float = Field(..., description="Sentiment score for this insight")
    trend: str = Field(..., description="Trend: improving/worsening/stable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the insight was generated")

class TrackedEvent(BaseModel):
    """Represents a financial event being tracked by the system."""
    id: str = Field(..., description="Unique identifier for the event")
    name: str = Field(..., description="Name of the event")
    event_time: datetime = Field(..., description="When the event is scheduled to occur")
    keywords: List[str] = Field(..., description="Keywords to match against news items")
    current_sentiment_score: float = Field(default=0.0, description="Current sentiment score based on news analysis")
    predicted_action: Optional[str] = Field(None, description="Predicted action (Put/Call/Hold)")
    thinking_text: Optional[str] = Field(None, description="Generated text explaining the current analysis")
    is_locked: bool = Field(default=False, description="Whether the event's bias is locked")
    lock_time: Optional[datetime] = Field(None, description="When the event's bias was locked")
    insights: List[Insight] = Field(default_factory=list, description="LLM-generated insights for this event")

    @field_validator('event_time', mode='before')
    def ensure_utc(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return v  # Let Pydantic parse ISO strings
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "fed_meeting_2024_03",
                "name": "Federal Reserve Meeting March 2024",
                "event_time": "2024-03-20T18:00:00Z",
                "keywords": ["Federal Reserve", "Fed", "interest rates", "Powell"],
                "current_sentiment_score": 0.75,
                "predicted_action": "Call",
                "thinking_text": "Strong positive sentiment in recent Fed-related news...",
                "is_locked": False,
                "lock_time": None
            }
        }

class VirtualPortfolio(BaseModel):
    """Represents the virtual trading portfolio."""
    current_value: float = Field(default=1000.0, description="Current value of the portfolio")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_value": 1250.75
            }
        } 