# New Project

---

## Project Structure


The scraper:
1. Sends this GET request with real browser headers
2. Parses the HTML response for fare data
3. Stores each price snapshot to SQLite with timestamp
4. Waits 8–15 seconds between requests (polite, won't get blocked)

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run scraper (first run)
python scraper/scraper.py

# Check /data/ folder for raw HTML files if no data is parsed
# Open raw HTML, find the correct CSS selectors, update parse_fare_page() in scraper.py

# Start API
uvicorn backend.main:app --reload --port 8080

# API docs
open http://localhost:8000/docs
```
## First Run: Selector Debug

## Cron Setup (Run 4× daily)

```cron
0 6,10,14,22 * * * cd /path/to/busfaretracker && python scraper/scraper.py >> /tmp/scraper.log 2>&1
```
---
