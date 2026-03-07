# 🚌 FareTrackMH — Shri Sairam Bus Fare Price History Tracker

> Like PriceHistory.app — but for Maharashtra bus fares.
> Tracks daily price changes on shrisairambus.com.

---

## Project Structure

```
busfaretracker/
├── scraper/
│   └── scraper.py        ← Python scraper (HTTP GET, no bot detection issues)
├── backend/
│   └── main.py           ← FastAPI REST API
├── frontend/
│   └── src/App.jsx       ← React dashboard with price history chart
├── data/
│   ├── fares.db          ← SQLite database (auto-created on first run)
│   └── scraper.log       ← Scraper logs
└── requirements.txt
```

---

## How the Scraper Works

shrisairambus.com uses **ASP.NET WebForms** with plain HTML pages.
The route search is a simple GET request — no JavaScript rendering, no auth:

```
GET https://shrisairambus.com/FindRoute.aspx?From=Pune&To=Mumbai&Date=08-03-2025
```

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
uvicorn backend.main:app --reload --port 8000

# API docs
open http://localhost:8000/docs
```

---

## First Run: Selector Debug

The scraper saves raw HTML to `/data/raw_Pune_Mumbai_08-03-2025.html` on first run
if it can't parse data. Open that file in browser, use DevTools to find:

- Bus listing container class → update `bus_rows` selector
- Bus name element → update `.bus-name` selector
- Price element → update `.fare` selector
- etc.

This is a one-time step. Once selectors are correct, it works forever.

---

## Cron Setup (Run 4× daily)

```cron
0 6,10,14,22 * * * cd /path/to/busfaretracker && python scraper/scraper.py >> /tmp/scraper.log 2>&1
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/routes` | All available routes in DB |
| `GET /api/price-history?from_city=Pune&to_city=Mumbai` | Full price history |
| `GET /api/price-history/daily-min?from_city=Pune&to_city=Mumbai` | Daily min/max/avg for chart |
| `GET /api/compare?from_city=Pune&to_city=Mumbai&today=2025-03-07` | This year vs last year |
| `GET /api/buses?from_city=Pune&to_city=Mumbai` | All operators on route |
| `GET /api/stats` | Total snapshots, routes, price range |

---

## Routes Tracked (Maharashtra)

- Pune ↔ Mumbai
- Pune ↔ Jalgaon
- Pune ↔ Malkapur
- Pune ↔ Aurangabad
- Pune ↔ Nashik
- Pune ↔ Solapur
- Pune ↔ Dhulia
- Jalgaon ↔ Mumbai
- + 40 more on the site

---

## Tech Stack

- **Scraper**: Python + requests + BeautifulSoup4
- **Database**: SQLite (upgrade to PostgreSQL for production)
- **Backend**: FastAPI + uvicorn
- **Frontend**: React + Recharts
- **Hosting**: Free tier on Railway / Render / GitHub Pages (frontend)
