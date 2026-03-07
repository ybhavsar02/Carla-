import { useState, useEffect, useCallback } from "react";
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from "recharts";

// ─── Mock data for demo (replace with real API calls when backend is running) ─
const DEMO_ROUTES = [
  { from_city: "Pune", to_city: "Mumbai", snapshot_count: 342 },
  { from_city: "Mumbai", to_city: "Pune", snapshot_count: 287 },
  { from_city: "Pune", to_city: "Jalgaon", snapshot_count: 198 },
  { from_city: "Pune", to_city: "Aurangabad", snapshot_count: 156 },
  { from_city: "Pune", to_city: "Solapur", snapshot_count: 132 },
];

function generateDemoHistory(from, to) {
  const base = { "Pune-Mumbai": 420, "Mumbai-Pune": 420, "Pune-Jalgaon": 380, "Pune-Aurangabad": 350, "Pune-Solapur": 310 };
  const basePrice = base[`${from}-${to}`] || 400;
  const data = [];
  const start = new Date("2024-03-07");
  for (let i = 0; i < 365; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().split("T")[0];
    const isWeekend = d.getDay() === 0 || d.getDay() === 6;
    const isFestival = (d.getMonth() === 9 && d.getDate() >= 10 && d.getDate() <= 25);
    const seasonalMultiplier = isFestival ? 1.4 : isWeekend ? 1.15 : 1.0;
    const noise = (Math.random() - 0.5) * 60;
    const price = Math.round((basePrice * seasonalMultiplier + noise) / 10) * 10;
    data.push({ date: dateStr, min_price: price - 30, max_price: price + 50, avg_price: price });
  }
  return data;
}

const DEMO_STATS = { total_snapshots: 12483, unique_routes: 15, tracking_since: "2024-03-07", price_min: 180, price_max: 980, price_avg: 412 };

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmt = (n) => n != null ? `₹${Math.round(n)}` : "—";
const fmtDate = (d) => {
  if (!d) return "";
  const dt = new Date(d);
  return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
};

// ─── Custom Tooltip ───────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: "#0f172a", border: "1px solid #334155",
      padding: "12px 16px", borderRadius: 8,
      fontFamily: "'DM Mono', monospace", fontSize: 12
    }}>
      <div style={{ color: "#64748b", marginBottom: 6 }}>{fmtDate(label)}</div>
      <div style={{ color: "#f59e0b", fontWeight: 700, fontSize: 15 }}>min {fmt(d?.min_price)}</div>
      <div style={{ color: "#94a3b8" }}>avg {fmt(d?.avg_price)}</div>
      <div style={{ color: "#475569" }}>max {fmt(d?.max_price)}</div>
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [routes, setRoutes] = useState(DEMO_ROUTES);
  const [stats, setStats] = useState(DEMO_STATS);
  const [selected, setSelected] = useState({ from: "Pune", to: "Mumbai" });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState("1Y"); // 1M, 3M, 6M, 1Y

  const API = "http://localhost:8000"; // Change to your deployed backend URL

  // Load history when route changes
  useEffect(() => {
    setLoading(true);
    // Try real API first, fallback to demo data
    fetch(`${API}/api/price-history/daily-min?from_city=${selected.from}&to_city=${selected.to}`)
      .then(r => r.json())
      .then(data => { setHistory(data); setLoading(false); })
      .catch(() => {
        setHistory(generateDemoHistory(selected.from, selected.to));
        setLoading(false);
      });
  }, [selected]);

  // Filter by view range
  const filteredHistory = (() => {
    if (!history.length) return [];
    const now = new Date();
    const cutoff = new Date(now);
    if (view === "1M") cutoff.setMonth(now.getMonth() - 1);
    else if (view === "3M") cutoff.setMonth(now.getMonth() - 3);
    else if (view === "6M") cutoff.setMonth(now.getMonth() - 6);
    else cutoff.setFullYear(now.getFullYear() - 1);
    return history.filter(d => new Date(d.date) >= cutoff);
  })();

  const currentPrice = filteredHistory[filteredHistory.length - 1]?.avg_price;
  const oldestPrice = filteredHistory[0]?.avg_price;
  const priceChange = currentPrice && oldestPrice ? ((currentPrice - oldestPrice) / oldestPrice * 100).toFixed(1) : null;
  const minAll = Math.min(...filteredHistory.map(d => d.min_price));
  const maxAll = Math.max(...filteredHistory.map(d => d.max_price));

  return (
    <div style={{
      minHeight: "100vh", background: "#020817",
      fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0"
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet" />

      {/* ── Header ── */}
      <header style={{
        borderBottom: "1px solid #1e293b", padding: "16px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: "linear-gradient(135deg, #f59e0b, #ef4444)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18
          }}>🚌</div>
          <div>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 18, letterSpacing: "-0.5px" }}>
              FareTrack<span style={{ color: "#f59e0b" }}>MH</span>
            </div>
            <div style={{ fontSize: 11, color: "#475569", fontFamily: "'DM Mono', monospace" }}>
              shrisairambus.com · Maharashtra
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 20, fontFamily: "'DM Mono', monospace", fontSize: 12, color: "#475569" }}>
          <span>📊 {stats.total_snapshots?.toLocaleString()} snapshots</span>
          <span>🛣️ {stats.unique_routes} routes</span>
          <span style={{ color: "#22c55e" }}>● LIVE</span>
        </div>
      </header>

      <div style={{ padding: "24px 32px", maxWidth: 1200, margin: "0 auto" }}>

        {/* ── Route Selector ── */}
        <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 13, color: "#475569", marginRight: 4, fontFamily: "'DM Mono', monospace" }}>ROUTE:</div>
          {routes.map(r => (
            <button
              key={`${r.from_city}-${r.to_city}`}
              onClick={() => setSelected({ from: r.from_city, to: r.to_city })}
              style={{
                padding: "8px 16px", borderRadius: 6, border: "1px solid",
                borderColor: selected.from === r.from_city && selected.to === r.to_city ? "#f59e0b" : "#1e293b",
                background: selected.from === r.from_city && selected.to === r.to_city ? "rgba(245,158,11,0.1)" : "#0f172a",
                color: selected.from === r.from_city && selected.to === r.to_city ? "#f59e0b" : "#64748b",
                cursor: "pointer", fontSize: 13, fontFamily: "'DM Mono', monospace",
                transition: "all 0.15s"
              }}
            >
              {r.from_city} → {r.to_city}
            </button>
          ))}
        </div>

        {/* ── Stats Row ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
          {[
            { label: "CURRENT PRICE", value: fmt(currentPrice), sub: "avg fare today" },
            { label: `${view} CHANGE`, value: priceChange != null ? `${priceChange > 0 ? "+" : ""}${priceChange}%` : "—", sub: "vs period start", color: priceChange > 0 ? "#ef4444" : "#22c55e" },
            { label: "LOWEST IN PERIOD", value: fmt(minAll === Infinity ? null : minAll), sub: "best price found" },
            { label: "HIGHEST IN PERIOD", value: fmt(maxAll === -Infinity ? null : maxAll), sub: "peak price" },
          ].map(s => (
            <div key={s.label} style={{
              background: "#0f172a", border: "1px solid #1e293b",
              borderRadius: 10, padding: "16px 20px"
            }}>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: "#475569", letterSpacing: "0.1em", marginBottom: 8 }}>
                {s.label}
              </div>
              <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 26, color: s.color || "#f1f5f9" }}>
                {s.value}
              </div>
              <div style={{ fontSize: 11, color: "#334155", marginTop: 4 }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {/* ── Main Chart ── */}
        <div style={{
          background: "#0f172a", border: "1px solid #1e293b",
          borderRadius: 12, padding: "24px 24px 16px"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div>
              <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 16 }}>
                {selected.from} → {selected.to} · Fare History
              </div>
              <div style={{ fontSize: 12, color: "#475569", fontFamily: "'DM Mono', monospace", marginTop: 3 }}>
                {filteredHistory.length} data points · Shri Sairam Travels
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              {["1M", "3M", "6M", "1Y"].map(v => (
                <button key={v} onClick={() => setView(v)} style={{
                  padding: "5px 12px", borderRadius: 5, border: "1px solid",
                  borderColor: view === v ? "#f59e0b" : "#1e293b",
                  background: view === v ? "rgba(245,158,11,0.12)" : "transparent",
                  color: view === v ? "#f59e0b" : "#475569",
                  cursor: "pointer", fontSize: 12, fontFamily: "'DM Mono', monospace"
                }}>{v}</button>
              ))}
            </div>
          </div>

          {loading ? (
            <div style={{ height: 280, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155" }}>
              Loading...
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={filteredHistory} margin={{ top: 5, right: 10, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="minGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis
                  dataKey="date" tick={{ fill: "#475569", fontSize: 11, fontFamily: "'DM Mono', monospace" }}
                  tickFormatter={d => fmtDate(d)}
                  interval={Math.floor(filteredHistory.length / 6)}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#475569", fontSize: 11, fontFamily: "'DM Mono', monospace" }}
                  tickFormatter={v => `₹${v}`}
                  axisLine={false} tickLine={false} width={52}
                  domain={["auto", "auto"]}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone" dataKey="min_price"
                  stroke="#f59e0b" strokeWidth={2}
                  fill="url(#minGrad)" dot={false} name="Min Fare"
                />
                <Line
                  type="monotone" dataKey="avg_price"
                  stroke="#64748b" strokeWidth={1.5}
                  strokeDasharray="4 4" dot={false} name="Avg Fare"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* ── How This Works ── */}
        <div style={{
          marginTop: 28, background: "#0f172a", border: "1px solid #1e293b",
          borderRadius: 12, padding: "20px 24px"
        }}>
          <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 14, marginBottom: 16, color: "#64748b" }}>
            HOW IT WORKS
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {[
              { icon: "🔍", title: "XHR Interception", desc: "Scraper mimics a real browser and calls shrisairambus.com search endpoint — plain HTTP GET, no login needed." },
              { icon: "🗄️", title: "SQLite Storage", desc: "Every price snapshot is stored with timestamp. Run the scraper 4× daily via cron to build a rich time-series." },
              { icon: "📈", title: "Price History", desc: "Query any date range. Compare this year vs last year on the same date — exactly like PriceHistory.app." },
            ].map(c => (
              <div key={c.title} style={{ padding: "14px", background: "#020817", borderRadius: 8, border: "1px solid #1e293b" }}>
                <div style={{ fontSize: 20, marginBottom: 8 }}>{c.icon}</div>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6, color: "#cbd5e1" }}>{c.title}</div>
                <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.6 }}>{c.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Setup Guide ── */}
        <div style={{
          marginTop: 16, background: "#020817", border: "1px dashed #1e293b",
          borderRadius: 12, padding: "20px 24px"
        }}>
          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12, color: "#334155", lineHeight: 2 }}>
            <span style={{ color: "#22c55e" }}># Quick start</span><br />
            <span style={{ color: "#f59e0b" }}>pip install</span> -r requirements.txt<br />
            <span style={{ color: "#f59e0b" }}>python</span> scraper/scraper.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style={{ color: "#334155" }}># first run, saves raw HTML to /data/ for selector debugging</span><br />
            <span style={{ color: "#f59e0b" }}>uvicorn</span> backend.main:app --reload &nbsp;<span style={{ color: "#334155" }}># start API at localhost:8000</span><br /><br />
            <span style={{ color: "#22c55e" }}># Cron (4× daily scrape)</span><br />
            <span style={{ color: "#94a3b8" }}>0 6,10,14,22 * * * cd /path/to/project && python scraper/scraper.py</span>
          </div>
        </div>

      </div>
    </div>
  );
}
