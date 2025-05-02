# Database Schema

This schema is designed to persist the application's state as managed by `AppRepository`, supporting future migration to a relational database (e.g., PostgreSQL, SQLite).

---

## Table: `events`
| Column         | Type        | Description                                 |
|--------------- |------------|---------------------------------------------|
| id             | TEXT (PK)   | Unique event identifier                     |
| name           | TEXT        | Event name                                  |
| event_time     | TIMESTAMP   | When the event occurs (UTC)                 |
| keywords       | TEXT[]      | List of keywords associated with the event  |
| is_locked      | BOOLEAN     | Whether the event is locked                 |
| lock_time      | TIMESTAMP   | When the event was locked (nullable)        |
| insights       | JSONB       | List of insights (see below)                |
| ...            | ...         | Other event-specific fields                 |

- **Notes:**
  - `insights` is a JSON array of objects (see `insights` structure below).
  - `keywords` can be a separate join table for normalization if needed.

---

## Table: `news_items`
| Column     | Type        | Description                                 |
|------------|------------|---------------------------------------------|
| id         | TEXT (PK)   | Unique news item identifier (Reddit post ID) |
| source     | TEXT        | Source subreddit or news provider           |
| title      | TEXT        | News headline/title                         |
| snippet    | TEXT        | Short content or summary                    |
| timestamp  | TIMESTAMP   | When the news was published (UTC)           |

---

## Table: `portfolio`
| Column         | Type        | Description                                 |
|----------------|------------|---------------------------------------------|
| id             | SERIAL (PK) | Portfolio record identifier                 |
| current_value  | FLOAT       | Current portfolio value                     |
| updated_at     | TIMESTAMP   | Last update timestamp (UTC)                 |

---

## Table: `insights` (if normalized)
| Column         | Type        | Description                                 |
|----------------|------------|---------------------------------------------|
| id             | SERIAL (PK) | Insight record identifier                   |
| event_id       | TEXT (FK)   | Related event ID                            |
| text           | TEXT        | Explanation of relevance                    |
| score          | FLOAT       | Sentiment score (-1 to 1)                   |
| trend          | TEXT        | Trend (improving/worsening/stable)          |
| timestamp      | TIMESTAMP   | When the insight was generated (UTC)        |

---

## Relationships
- `insights.event_id` → `events.id` (many-to-one)
- `events.keywords` can be normalized to a join table if needed

---

## Example ER Diagram (Textual)
- **events** (1) ← (many) **insights**
- **portfolio** (singleton, latest row is current)
- **news_items** (standalone, referenced by ID)

---

## Notes
- All timestamps are stored in UTC.
- For performance, `insights` can be embedded as JSON in `events` or normalized as a separate table.
- This schema is designed for extensibility and can be adapted for other backends (NoSQL, etc.). 