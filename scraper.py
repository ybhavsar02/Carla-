"""
Shri Sairam Bus Fare Tracker - Scraper
Focused route: Pune -> Jalgaon
Scrapes fare for every bus and every seat via site JSON web methods.
"""

import json
import logging
import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "fares.db"
BASE_URL = "https://shrisairambus.com"
IST_TZ = ZoneInfo("Asia/Kolkata")

ROUTES = [
    ("Pune", "Aurangabad"),
    ("Pune", "Dhule"),
    ("Dhule", "Pune"),
    ("Pune", "Malkapur"),
    ("Buldana", "Pune"),
    ("Pune", "Jalgaon"),
    ("Pune", "Bhusawal"),
    ("Dhule", "Mumbai"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Connection": "keep-alive",
    "Referer": "https://shrisairambus.com/",
}

DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(DATA_DIR / "scraper.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS seat_snapshots (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            from_city          TEXT NOT NULL,
            to_city            TEXT NOT NULL,
            journey_date       TEXT NOT NULL,
            bus_name           TEXT,
            bus_type           TEXT,
            reference_number   TEXT,
            route_id           INTEGER,
            route_time_id      INTEGER,
            start_time         TEXT,
            end_time           TEXT,
            departure          TEXT,
            arrival            TEXT,
            seat_no            TEXT,
            seat_type          INTEGER,
            up_low_berth       TEXT,
            available          INTEGER,
            seat_rate          REAL,
            base_fare          REAL,
            service_tax        REAL,
            surcharges         REAL,
            original_seat_rate REAL,
            scraped_date       TEXT,
            scraped_time       TEXT,
            scraped_at         TEXT NOT NULL,
            scrape_duration_sec REAL
        )
        """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_seat_route_date
        ON seat_snapshots(from_city, to_city, journey_date, bus_name, seat_no, scraped_at)
        """
    )
    # Backfill schema for existing DBs created before scrape_duration_sec was added.
    cols = {
        row[1] for row in c.execute("PRAGMA table_info(seat_snapshots)").fetchall()
    }
    if "scrape_duration_sec" not in cols:
        c.execute(
            "ALTER TABLE seat_snapshots ADD COLUMN scrape_duration_sec REAL"
        )
    if "start_time" not in cols:
        c.execute("ALTER TABLE seat_snapshots ADD COLUMN start_time TEXT")
    if "end_time" not in cols:
        c.execute("ALTER TABLE seat_snapshots ADD COLUMN end_time TEXT")
    if "scraped_date" not in cols:
        c.execute("ALTER TABLE seat_snapshots ADD COLUMN scraped_date TEXT")
    if "scraped_time" not in cols:
        c.execute("ALTER TABLE seat_snapshots ADD COLUMN scraped_time TEXT")
    conn.commit()
    conn.close()
    log.info(f"DB ready at {DB_PATH}")


def save_seat_snapshots(records: list[dict]):
    if not records:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany(
        """
        INSERT INTO seat_snapshots (
            from_city, to_city, journey_date, bus_name, bus_type,
            reference_number, route_id, route_time_id, start_time, end_time, departure, arrival,
            seat_no, seat_type, up_low_berth, available,
            seat_rate, base_fare, service_tax, surcharges, original_seat_rate,
            scraped_date, scraped_time, scraped_at, scrape_duration_sec
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                r["from_city"],
                r["to_city"],
                r["journey_date"],
                r.get("bus_name"),
                r.get("bus_type"),
                r.get("reference_number"),
                r.get("route_id"),
                r.get("route_time_id"),
                r.get("start_time"),
                r.get("end_time"),
                r.get("departure"),
                r.get("arrival"),
                r.get("seat_no"),
                r.get("seat_type"),
                r.get("up_low_berth"),
                r.get("available"),
                r.get("seat_rate"),
                r.get("base_fare"),
                r.get("service_tax"),
                r.get("surcharges"),
                r.get("original_seat_rate"),
                r.get("scraped_date"),
                r.get("scraped_time"),
                r["scraped_at"],
                r.get("scrape_duration_sec"),
            )
            for r in records
        ],
    )
    conn.commit()
    conn.close()
    log.info(f"Saved {len(records)} seat records")


def _normalize_city(city: str) -> str:
    aliases = {"dhulia": "dhule"}
    return aliases.get(city.strip().lower(), city.strip().lower())


def _post_json(session: requests.Session, path: str, payload: dict):
    try:
        resp = session.post(
            f"{BASE_URL}{path}",
            json=payload,
            headers={**HEADERS, "Content-Type": "application/json; charset=UTF-8"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        log.error(f"Request failed for {path}: {exc}")
        return None


def _pick_route_time(route: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = route.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if value:
            return value
    return None


def _build_city_pair_map(session: requests.Session) -> dict[tuple[str, str], dict]:
    data = _post_json(session, "/Web_Methods/MainPage.aspx/GetMainPage_Details", {})
    if not data or "d" not in data or not data["d"].get("data"):
        return {}

    city_list = json.loads(data["d"]["data"]).get("cityList", [])
    mapping = {}
    for p in city_list:
        f = _normalize_city(p.get("FromCity", ""))
        t = _normalize_city(p.get("ToCity", ""))
        if f and t:
            mapping[(f, t)] = p
    return mapping


def bind_available_routes(session: requests.Session, pair: dict, journey_date: str) -> list[dict]:
    bind_payload = {
        "SRI": {
            "fromCityID": int(pair["FromCityID"]),
            "toCityID": int(pair["ToCityID"]),
            "fromCityName": pair["FromCity"],
            "toCityName": pair["ToCity"],
            "jdate": journey_date,
            "jdateR": "",
            "isBindReturnRoute": 0,
            "redirectUrl": "",
            "msg": "",
            "fromCityID1": 0,
            "toCityID1": 0,
            "fromCityName1": "",
            "toCityName1": "",
            "journeyDate1": "",
            "tripType": 0,
            "fromCityID2": 0,
            "toCityID2": 0,
            "fromCityName2": "",
            "toCityName2": "",
            "journeyDate2": "",
        }
    }

    bind_resp = _post_json(session, "/Web_Methods/MainPage.aspx/Bind_AvailableRoutes", bind_payload)
    if not bind_resp or "AvailebleRoutes" not in str(bind_resp.get("d", {}).get("data", "")):
        return []

    fares_resp = _post_json(session, "/Web_Methods/AvailbleRoutes.aspx/BindAvailableRoutes_RJ", {})
    if not fares_resp or not fares_resp.get("d", {}).get("data"):
        return []

    payload = json.loads(fares_resp["d"]["data"])
    return payload.get("data", [])


def fetch_seat_rows(session: requests.Session, route: dict, from_city: str, to_city: str, journey_date: str) -> list[dict]:
    ref_no = route.get("ReferenceNumber")
    if not ref_no:
        return []

    started_at = time.perf_counter()
    seat_resp = _post_json(
        session,
        "/Web_Methods/AvailbleRoutes.aspx/GetSeatArrangementDetails",
        {"RNumber": ref_no},
    )
    scrape_duration_sec = round(time.perf_counter() - started_at, 3)
    if not seat_resp or not seat_resp.get("d", {}).get("data"):
        return []

    seat_data = json.loads(seat_resp["d"]["data"]).get("data", [])
    now = datetime.now(IST_TZ)
    scraped_at = now.strftime("%Y-%m-%d %I:%M %p")
    scraped_date = now.strftime("%Y-%m-%d")
    scraped_time = now.strftime("%I:%M:%S %p")
    start_time = _pick_route_time(route, ("CityTime", "RouteTime", "StartTime", "DepartureTime", "BoardingTime"))
    end_time = _pick_route_time(route, ("ArrivalTime", "EndTime", "DropTime", "DropingTime"))

    rows = []
    for seat in seat_data:
        rows.append(
            {
                "from_city": from_city,
                "to_city": to_city,
                "journey_date": journey_date,
                "bus_name": route.get("RouteName") or route.get("CompanyName"),
                "bus_type": route.get("BusTypeName") or route.get("BusTypeSeatType"),
                "reference_number": ref_no,
                "route_id": route.get("RouteID"),
                "route_time_id": route.get("RouteTimeID"),
                "start_time": start_time,
                "end_time": end_time,
                "departure": start_time,
                "arrival": end_time,
                "seat_no": seat.get("SeatNo"),
                "seat_type": seat.get("SeatType"),
                "up_low_berth": seat.get("UpLowBerth"),
                "available": 1 if seat.get("Available") == "Y" else 0,
                "seat_rate": seat.get("SeatRate"),
                "base_fare": seat.get("BaseFare"),
                "service_tax": seat.get("ServiceTax"),
                "surcharges": seat.get("Surcharges"),
                "original_seat_rate": seat.get("OriginalSeatRate"),
                "scraped_date": scraped_date,
                "scraped_time": scraped_time,
                "scraped_at": scraped_at,
                "scrape_duration_sec": scrape_duration_sec,
            }
        )
    return rows


def run_scrape(days_ahead=1):
    init_db()

    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(f"{BASE_URL}/index.aspx", timeout=20)
    except requests.RequestException as exc:
        log.error(f"Failed to initialize session: {exc}")
        return []

    city_pair_map = _build_city_pair_map(session)
    if not city_pair_map:
        log.error("Could not load city pair data from site. Aborting run.")
        return []

    all_records = []
    dates = [
        (datetime.now(IST_TZ) + timedelta(days=i)).strftime("%d-%m-%Y")
        for i in range(0, days_ahead + 1)
    ]

    for from_city, to_city in ROUTES:
        key = (_normalize_city(from_city), _normalize_city(to_city))
        pair = city_pair_map.get(key)
        if not pair:
            log.warning(f"Route not currently available: {from_city} -> {to_city}")
            continue

        for jdate in dates:
            log.info(f"Scraping {from_city} -> {to_city} | {jdate}")
            routes = bind_available_routes(session, pair, jdate)
            log.info(f"Found {len(routes)} buses for {from_city}->{to_city} on {jdate}")

            for route in routes:
                seat_rows = fetch_seat_rows(session, route, from_city, to_city, jdate)
                all_records.extend(seat_rows)
                log.info(
                    f"Bus: {route.get('RouteName', 'Unknown')} | Seats captured: {len(seat_rows)}"
                )
                time.sleep(random.uniform(0.7, 1.5))

            time.sleep(random.uniform(4, 8))

    save_seat_snapshots(all_records)
    log.info(f"Total seat rows saved: {len(all_records)}")
    return all_records


if __name__ == "__main__":
    run_scrape(days_ahead=1)
