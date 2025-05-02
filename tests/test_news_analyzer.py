from dotenv import load_dotenv
load_dotenv()
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.models import NewsItem, TrackedEvent
from src.news_analyzer import NewsAnalyzer

@pytest.fixture
def sample_news_item():
    return NewsItem(
        id="news1",
        source="test_source",
        title="Positive market outlook for tech sector",
        snippet="Analysts predict strong growth and increased profits.",
        timestamp=datetime.utcnow()
    )

@pytest.fixture
def sample_event():
    return TrackedEvent(
        id="event1",
        name="Tech Sector Report",
        event_time=datetime.utcnow(),
        keywords=["tech", "market", "growth"],
        current_sentiment_score=0.0
    )

@pytest.fixture
def mock_llm_response():
    return """EVENT_ID: event1
RELEVANCE: Market growth predictions remain strong despite challenges\nAnalyst confidence suggests potential for exceeding expectations
SCORE: 0.6
TREND: improving"""

@pytest.fixture
def analyzer():
    return NewsAnalyzer()

@pytest.mark.asyncio
async def test_analyze_simple(analyzer, sample_event, sample_news_item, mock_llm_response):
    with patch.object(analyzer.client.messages, 'create') as mock_create:
        mock_create.return_value.content = [Mock(text=mock_llm_response)]
        results = await analyzer.analyze(sample_news_item, [sample_event])
        for event_id, insight in results:
            if event_id == sample_event.id:
                sample_event.insights.append(insight)
        assert len(sample_event.insights) == 1
        insight = sample_event.insights[0]
        assert "Market growth predictions remain strong despite challenges" in insight.text
        assert insight.score == 0.6
        assert insight.trend == "improving" 