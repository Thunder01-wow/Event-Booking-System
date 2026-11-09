import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { money, formatWhen } from "../lib/format";
import EventImage from "../components/EventImage";
import { EventGridSkeleton } from "../components/Skeleton";

function Availability({ ev }) {
  if (ev.total_seats == null) return null;
  if (ev.available_seats === 0) return <span className="pill sold">Sold out</span>;
  if (ev.available_seats <= Math.max(3, ev.total_seats * 0.2))
    return <span className="pill low">Only {ev.available_seats} left</span>;
  return <span className="pill ok">{ev.available_seats} seats</span>;
}

export default function EventsPage() {
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    api.listEvents().then(setEvents).catch((e) => setError(e.detail || "Couldn't load events."));
  }, []);

  const cities = useMemo(() => [...new Set((events || []).map((e) => e.venues?.city).filter(Boolean))].sort(), [events]);
  const categories = useMemo(() => [...new Set((events || []).map((e) => e.category).filter(Boolean))].sort(), [events]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (events || []).filter((e) => {
      const hay = `${e.title} ${e.venues?.name || ""} ${e.category || ""}`.toLowerCase();
      return (!q || hay.includes(q)) && (!city || e.venues?.city === city) && (!category || e.category === category);
    });
  }, [events, search, city, category]);

  return (
    <section>
      <div className="hero">
        <p className="eyebrow">Your night, sorted</p>
        <h1>Make plans.<br /><i>Feel everything.</i></h1>
        <p className="lede">Discover the best live experiences around you, then make them yours.</p>
      </div>

      <div className="filters">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="⌕  Search events, artists or venues" aria-label="Search events" />
        <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="Filter by city">
          <option value="">All cities</option>
          {cities.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category">
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="section-heading">
        <h2>Happening soon <span>{events ? `${filtered.length} events` : ""}</span></h2>
      </div>

      {error && <div className="notice">{error}</div>}
      {!events && !error && <EventGridSkeleton />}

      {events && (
        <div className="event-grid">
          {filtered.map((ev) => (
            <Link to={`/events/${ev.id}`} className="event-card" key={ev.id}>
              <EventImage event={ev} />
              <div className="event-card-body">
                <div className="badges">
                  <span className="pill">{ev.category || "Event"}</span>
                  <Availability ev={ev} />
                </div>
                <h3>{ev.title}</h3>
                <p>◷ {formatWhen(ev.starts_at)}<br />⌖ {ev.venues?.name}{ev.venues?.city ? `, ${ev.venues.city}` : ""}</p>
                <div className="card-footer">
                  <strong>{ev.min_price != null ? `From ${money(ev.min_price)}` : "View seats"}</strong>
                  <span className="go">View event ↗</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
      {events && !filtered.length && (
        <div className="empty">
          {events.length ? "No events match those filters. Try a different search." : "No events are published yet. Check back soon."}
        </div>
      )}
    </section>
  );
}
