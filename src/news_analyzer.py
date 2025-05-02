from datetime import datetime, timezone
from typing import List
import os

from loguru import logger
from anthropic import Anthropic
from ratelimit import limits, sleep_and_retry

from src.models import NewsItem, TrackedEvent, Insight
from src.app_repository import EventRepository
import openai

# NewsAnalyzer: Only handles news analysis for events.
# For LLM-powered event discovery, see LLMEventService in event_llm_service.py

class NewsAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = Anthropic(api_key=api_key)

    @sleep_and_retry
    @limits(calls=15, period=60)
    async def analyze(self, news: NewsItem, events: List[TrackedEvent]) -> List[Insight]:
        logger.info(f"NewsAnalyzer: Starting analysis for news ID={news.id}, title='{news.title}'")
        """
        Analyze a single news item for relevance and sentiment to each event.
        Returns a list of Insight objects, each linked to a relevant event.
        """
        # Prepare prompt for LLM
        events_text = "\n".join([
            f"Event: {e.name} (ID: {e.id})\nKeywords: {', '.join(e.keywords)}\nCurrent sentiment: {e.current_sentiment_score:.2f}"
            for e in events
        ])
        prompt = f'''Given the following news item, analyze its relevance and sentiment for each of the upcoming events.\n\nNews:\nTitle: {news.title}\nSnippet: {news.snippet}\nTimestamp: {news.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\nUpcoming Events:\n{events_text}\n\nFor each event that is truly relevant to this news, provide:\n1. A brief explanation of the relevance\n2. A relevance score from 0 (not relevant) to 1 (highly relevant)\n3. A sentiment score from -1 (very negative) to 1 (very positive)\n4. The trend (improving/worsening/stable) compared to current sentiment\n\nIf the news is not relevant to an event, do not include that event in your response at all.\nIf the news is not relevant to any event, reply with a single short sentence explaining why, prefixed with 'NOT RELEVANT:'.\n\nIMPORTANT: For each relevant event, always use the event's ID (not name) in your output.\n\nFormat:\nEVENT_ID: <event_id>\nRELEVANCE: <explanation>\nRELEVANCE_SCORE: <number between 0 and 1>\nSCORE: <number between -1 and 1>\nTREND: <improving/worsening/stable>\n'''
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=500,
            temperature=0.0,
            system="You are a financial analyst providing detailed event-relevant news analysis.",
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse response
        insights = []
        current_event = None
        relevance = None
        relevance_score = None
        score = None
        trend = None
        for line in response.content[0].text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("EVENT_ID:"):
                if current_event and relevance is not None and relevance_score is not None and score is not None and trend is not None:
                    insights.append((current_event, relevance, relevance_score, score, trend))
                current_event = line.split(":", 1)[1].strip()
                relevance = None
                relevance_score = None
                score = None
                trend = None
            elif line.startswith("RELEVANCE:"):
                relevance = line.split(":", 1)[1].strip()
            elif line.startswith("RELEVANCE_SCORE:"):
                relevance_score = float(line.split(":", 1)[1].strip())
            elif line.startswith("SCORE:"):
                score = float(line.split(":", 1)[1].strip())
            elif line.startswith("TREND:"):
                trend = line.split(":", 1)[1].strip().lower()
        if current_event and relevance is not None and relevance_score is not None and score is not None and trend is not None:
            insights.append((current_event, relevance, relevance_score, score, trend))
        # Create Insight objects, filter by relevance_score
        RELEVANCE_THRESHOLD = 0.5
        result = []
        for event_id, relevance, relevance_score, score, trend in insights:
            if relevance_score >= RELEVANCE_THRESHOLD:
                result.append((event_id, Insight(
                    text=relevance,
                    score=score,
                    trend=trend,
                    timestamp=datetime.now(timezone.utc)
                )))
        # If no relevant events, add a global insight for LLM reasoning
        if not result:
            # Use the LLM's response as-is (should be a short sentence)
            llm_reasoning = response.content[0].text.strip()
            result.append(("__global__", Insight(
                text=f"LLM: {llm_reasoning}",
                score=0.0,
                trend="n/a",
                timestamp=datetime.now(timezone.utc)
            )))
        logger.info(f"NewsAnalyzer: Finished analysis for news ID={news.id}, title='{news.title}', found {len(result)} insights.")
        for event_id, insight in result:
            logger.info(
                f"Insight for Event: {event_id}\n"
                f"  RELEVANCE: {insight.text}\n"
                f"  SCORE: {insight.score}\n"
                f"  TREND: {insight.trend}\n"
                f"  (Linked to event ID: {event_id})"
            )
        import asyncio
        # Delay only after finishing all analysis and logging
        await asyncio.sleep(3)
        return result 