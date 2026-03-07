"""
Bus Fare Tracker — FastAPI Backend
Endpoints for price history, routes, stats
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pathlib import Path
from datetime import datetime, date
from typing import Optional
import json

app = FastAPI(title="Bus Fare Tracker API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).parent.parent / "data" / "fares.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Bus Fare Tracker", "source": "shrisairambus.com"}


@app.get("/api/routes")
def list_routes():
    """All unique routes available in DB"""
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT from_city, to_city,
               COUNT(*) as snapshot_count,
               MIN(scraped_at) as first_seen,
               MAX(scraped_at) as last_seen
        FROM price_snapshots
        GROUP BY from_city, to_city
        ORDER BY from_city, to_city
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/price-history")
def price_history(
    from_city: str = Query(..., description="Origin city e.g. Pune"),
    to_city: str = Query(..., description="Destination city e.g. Mumbai"),
    journey_date: Optional[str] = Query(None, description="Journey date dd-MM-yyyy (optional)"),
    bus_name: Optional[str] = Query(None, description="Filter by bus operator"),
    seat_type: Optional[str] = Query(None, description="Filter by seat type"),
):
    """
    Full price history for a route.
    Returns time-series data for charting.
    """
    conn = get_db()
    query = """
        SELECT from_city, to_city, bus_name, bus_type, seat_type,
               departure, arrival, price, seats_avail,
               journey_date, scraped_at
        FROM price_snapshots
        WHERE LOWER(from_city) = LOWER(?)
          AND LOWER(to_city) = LOWER(?)
    """
    params = [from_city, to_city]

    if journey_date:
        query += " AND journey_date = ?"
        params.append(journey_date)
    if bus_name:
        query += " AND LOWER(bus_name) LIKE LOWER(?)"
        params.append(f"%{bus_name}%")
    if seat_type:
        query += " AND LOWER(seat_type) LIKE LOWER(?)"
        params.append(f"%{seat_type}%")

    query += " ORDER BY scraped_at ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found for this route")

    return [dict(r) for r in rows]


@app.get("/api/price-history/daily-min")
def price_history_daily_min(
    from_city: str = Query(...),
    to_city: str = Query(...),
    bus_name: Optional[str] = Query(None),
):
    """
    Daily minimum price over time — perfect for the price history chart.
    Groups by date scraped to show price trends.
    """
    conn = get_db()
    query = """
        SELECT
            DATE(scraped_at) as date,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price,
            COUNT(*) as samples
        FROM price_snapshots
        WHERE LOWER(from_city) = LOWER(?)
          AND LOWER(to_city) = LOWER(?)
          AND price IS NOT NULL
    """
    params = [from_city, to_city]

    if bus_name:
        query += " AND LOWER(bus_name) LIKE LOWER(?)"
        params.append(f"%{bus_name}%")

    query += " GROUP BY DATE(scraped_at) ORDER BY date ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(r) for r in rows]


@app.get("/api/stats")
def stats():
    """Dashboard stats"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM price_snapshots").fetchone()["c"]
    routes = conn.execute("SELECT COUNT(DISTINCT from_city||to_city) as c FROM price_snapshots").fetchone()["c"]
    latest = conn.execute("SELECT MAX(scraped_at) as t FROM price_snapshots").fetchone()["t"]
    oldest = conn.execute("SELECT MIN(scraped_at) as t FROM price_snapshots").fetchone()["t"]

    # Price range across all routes
    price_stats = conn.execute("""
        SELECT MIN(price) as min_p, MAX(price) as max_p, AVG(price) as avg_p
        FROM price_snapshots WHERE price IS NOT NULL
    """).fetchone()
    conn.close()

    return {
        "total_snapshots": total,
        "unique_routes": routes,
        "latest_scrape": latest,
        "tracking_since": oldest,
        "price_min": price_stats["min_p"],
        "price_max": price_stats["max_p"],
        "price_avg": round(price_stats["avg_p"] or 0, 2),
    }


@app.get("/api/compare")
def compare_same_day_last_year(
    from_city: str = Query(...),
    to_city: str = Query(...),
    today: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
):
    """
    Compare today's price vs same date last year — the core feature.
    """
    target = today or date.today().isoformat()
    target_dt = datetime.strptime(target, "%Y-%m-%d")
    last_year_date = target_dt.replace(year=target_dt.year - 1).date().isoformat()

    conn = get_db()

    def fetch_prices(date_str):
        rows = conn.execute("""
            SELECT bus_name, bus_type, seat_type, MIN(price) as price,
                   departure, DATE(scraped_at) as on_date
            FROM price_snapshots
            WHERE LOWER(from_city) = LOWER(?)
              AND LOWER(to_city) = LOWER(?)
              AND DATE(scraped_at) = ?
              AND price IS NOT NULL
            GROUP BY bus_name, seat_type
            ORDER BY price ASC
        """, [from_city, to_city, date_str]).fetchall()
        return [dict(r) for r in rows]

    this_year = fetch_prices(target)
    last_year = fetch_prices(last_year_date)
    conn.close()

    return {
        "route": f"{from_city} → {to_city}",
        "this_year": {"date": target, "fares": this_year},
        "last_year": {"date": last_year_date, "fares": last_year},
    }


@app.get("/api/buses")
def list_buses(from_city: str = Query(...), to_city: str = Query(...)):
    """All bus operators for a route"""
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT bus_name, bus_type,
               MIN(price) as lowest_ever,
               MAX(price) as highest_ever,
               COUNT(*) as data_points
        FROM price_snapshots
        WHERE LOWER(from_city) = LOWER(?)
          AND LOWER(to_city) = LOWER(?)
          AND bus_name IS NOT NULL
        GROUP BY bus_name, bus_type
        ORDER BY lowest_ever ASC
    """, [from_city, to_city]).fetchall()
    conn.close()
    return [dict(r) for r in rows]
