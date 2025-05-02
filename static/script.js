let lastNewsIds = new Set();
let lastEventIds = new Set();
let lastGoodState = null;
let lastPortfolioHTML = '';
let lastEventsHTML = '';
let lastNewsHTML = '';
let newsCountFilter = 10;

// Add a delay between LLM log panel updates to limit the rate of new insights
let llmUpdateTimeout = null;

const newsCountSelect = document.getElementById('news-count-select');
if (newsCountSelect) {
    newsCountSelect.addEventListener('change', function() {
        const val = newsCountSelect.value;
        newsCountFilter = val === 'all' ? 'all' : parseInt(val, 10);
        if (lastGoodState) updatePanels(lastGoodState);
    });
}

async function fetchState() {
    try {
        const res = await fetch(`/api/state?news_limit=${newsCountFilter}`);
        if (!res.ok) throw new Error('Failed to fetch state');
        const data = await res.json();

        // Only update if data is not empty (has events or news)
        if (data && ((data.events && data.events.length > 0) || (data.news_items && data.news_items.length > 0))) {
            lastGoodState = data;
            delayedUpdatePanels(data);
        } else if (lastGoodState) {
            // If new data is empty, keep showing the last good state
            delayedUpdatePanels(lastGoodState);
        }
    } catch (e) {
        console.error(e);
        // On error, keep showing the last good state
        if (lastGoodState) delayedUpdatePanels(lastGoodState);
    }
}

function updatePanels(data) {
    // Gather all insights from all events, flatten, and sort by timestamp desc
    let allInsights = [];
    data.events.forEach(ev => {
        ev.insights.forEach(insight => {
            allInsights.push({
                event: ev.name,
                ...insight
            });
        });
    });
    allInsights.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    let llmLogHtml = '<h2>LLM Reasoning</h2>';
    // Build a map from news_id to added_at for sorting
    const newsAddedAtMap = {};
    if (data.news_items) {
        data.news_items.forEach(n => {
            newsAddedAtMap[n.id] = n.added_at ? new Date(n.added_at) : new Date(n.timestamp);
        });
    }
    if (data.llm_log && data.llm_log.length > 0) {
        llmLogHtml += data.llm_log.map(entry => `
            <div style="margin-bottom:0;padding:4px 6px 3px 6px;border-radius:5px;background:#23282c;border:1px solid #2a2e32;">
                ${entry.event_id ? `<span style='font-weight:600;color:#ffd700;'>Event: ${entry.event_id}</span><br>` : ''}
                <span style="color:#b0ffb0;"><b>News:</b> ${entry.news_title ?? ''}</span><br>
                <span style="color:#fff;"><span style="color:#7fd7ff;font-weight:500;">Thought:</span> ${entry.text}</span><br>
                <span style="color:#aaa;"><b>Score:</b> <span style="color:${scoreColor(entry.score)}">${entry.score}</span> <b>Trend:</b> ${entry.trend} <span style='color:#888;font-size:0.88em;'> &middot; ${entry.added_at ? new Date(entry.added_at).toLocaleString() : new Date(entry.timestamp).toLocaleString()}</span></span>
            </div>
        `).join('');
    } else {
        llmLogHtml += '<div style="color:#888;">No insights yet.</div>';
    }
    // Render LLM log in the left panel
    const llmPanel = document.getElementById('llm-log-panel');
    if (llmPanel && llmPanel.innerHTML !== llmLogHtml) {
        llmPanel.innerHTML = llmLogHtml;
    }

    // Portfolio
    const portfolioPanel = document.getElementById('portfolio-panel');
    const portfolioHTML =
        `<h2>Portfolio</h2><div>Value: $${data.portfolio.current_value.toFixed(2)}</div>`;
    if (portfolioHTML !== lastPortfolioHTML) {
        portfolioPanel.innerHTML = portfolioHTML;
        lastPortfolioHTML = portfolioHTML;
    }

    // Events
    const eventsPanel = document.getElementById('events-panel');
    const eventsHTML = '<h2>Events</h2>' +
        data.events.map(ev => `
            <div class="event" data-event-id="${ev.id}">
                <strong>${ev.name}</strong><br>
                Time: ${new Date(ev.event_time).toLocaleString()}<br>
                Bias: <span style="color:${biasColor(ev.predicted_action)}">${ev.predicted_action ?? 'N/A'}</span><br>
                Thinking: <span class="thinking-text">${ev.thinking_text ?? ''}</span><br>
                <details style="margin-top:8px;"><summary>Insights (${ev.insights.length})</summary>
                  <ul style="margin:0 0 0 16px;padding:0;list-style:disc;">
                    ${ev.insights.map(insight => `
                      <li style="margin-bottom:6px;">
                        <div><b>Score:</b> <span style="color:${scoreColor(insight.score)}">${insight.score}</span> <b>Trend:</b> ${insight.trend}</div>
                        <div style="font-size:0.95em;">${insight.text}</div>
                        <div style="font-size:0.85em;color:#aaa;">${new Date(insight.timestamp).toLocaleString()}</div>
                      </li>
                    `).join('')}
                  </ul>
                </details>
            </div>
        `).join('<hr>');
    if (eventsHTML !== lastEventsHTML) {
        eventsPanel.innerHTML = eventsHTML;
        lastEventsHTML = eventsHTML;
    }

    // News
    const newsPanel = document.getElementById('news-panel');
    let sortedNews = data.news_items.slice().sort((a, b) => {
        const aTime = a.added_at ? new Date(a.added_at) : new Date(a.timestamp);
        const bTime = b.added_at ? new Date(b.added_at) : new Date(b.timestamp);
        return bTime - aTime;
    });
    const newsHTML = '<h2>News</h2>' +
        sortedNews.map(n => `
            <div class="news-item" data-news-id="${n.id}">
                <strong>${n.title}</strong><br>
                <span>${n.snippet}</span><br>
                <small>${n.added_at ? new Date(n.added_at).toLocaleString() : new Date(n.timestamp).toLocaleString()}</small>
            </div>
        `).join('<hr>');
    if (newsHTML !== lastNewsHTML) {
        newsPanel.innerHTML = newsHTML;
        lastNewsHTML = newsHTML;
    }

    // Animate new news items
    const newNewsIds = new Set(data.news_items.map(n => n.id));
    data.news_items.forEach(n => {
        if (!lastNewsIds.has(n.id)) {
            const el = document.querySelector(`.news-item[data-news-id='${n.id}']`);
            if (el) {
                el.style.background = '#333a1a';
                setTimeout(() => { el.style.background = ''; }, 700);
            }
        }
    });
    lastNewsIds = newNewsIds;

    // Animate new events (if needed in future)
    lastEventIds = new Set(data.events.map(e => e.id));
}

function delayedUpdatePanels(data) {
    if (llmUpdateTimeout) return; // Skip if a delay is in progress
    updatePanels(data);
    llmUpdateTimeout = setTimeout(() => {
        llmUpdateTimeout = null;
    }, 2000); // 2 seconds delay between updates
}

function biasColor(bias) {
    if (bias === 'Call') return '#4caf50';
    if (bias === 'Put') return '#e53935';
    if (bias === 'Hold') return '#ffb300';
    return '#aaa';
}

function scoreColor(score) {
    if (score > 0.3) return '#4caf50';
    if (score < -0.3) return '#e53935';
    return '#ffb300';
}

async function fetchLogs() {
    try {
        const res = await fetch('/api/logs');
        const text = await res.text();
        const panel = document.getElementById('server-logs-panel');
        if (panel) panel.textContent = text;
    } catch (e) {
        const panel = document.getElementById('server-logs-panel');
        if (panel) panel.textContent = 'Error loading logs';
    }
}

setInterval(fetchState, 5000);
setInterval(fetchLogs, 3000);
fetchState();
fetchLogs(); 