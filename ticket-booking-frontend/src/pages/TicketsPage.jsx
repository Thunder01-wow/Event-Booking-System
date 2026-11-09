import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { money, formatWhen } from "../lib/format";
import { TicketsSkeleton } from "../components/Skeleton";

export default function TicketsPage() {
  const [bookings, setBookings] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.myBookings().then(setBookings).catch((e) => setError(e.detail || "Couldn't load your tickets."));
  }, []);

  const confirmed = (bookings || []).filter((b) => b.status === "confirmed");
  const others = (bookings || []).filter((b) => b.status !== "confirmed");

  return (
    <section className="tickets-page">
      <p className="eyebrow">Your collection</p>
      <h2>My tickets.</h2>
      {error && <div className="notice">{error}</div>}
      {!bookings && !error && <TicketsSkeleton />}

      {bookings && !confirmed.length && (
        <div className="empty">
          Your confirmed tickets will appear here.<br />
          <Link to="/" className="primary" style={{ marginTop: 12 }}>Browse events</Link>
        </div>
      )}

      {confirmed.length > 0 && (
        <div className="tickets">
          {confirmed.map((b) =>
            (b.tickets?.length ? b.tickets : [null]).map((t, i) => (
              <div className="ticket" key={t?.id || `${b.id}-${i}`}>
                <small>CONFIRMED · {t?.ticket_code || b.id.slice(0, 8).toUpperCase()}</small>
                <h3>{b.events?.title || "Event"}</h3>
                <p>
                  {b.events?.starts_at ? formatWhen(b.events.starts_at) : ""}<br />
                  {b.events?.venues?.name}{b.events?.venues?.city ? `, ${b.events.venues.city}` : ""}
                </p>
                <hr />
                <b>Seat {t?.seats?.seat_label || "—"} · {t?.seats?.category || ""}</b>
                <small>PAID {money(t?.seats?.price ?? b.total_amount)}</small>
              </div>
            ))
          )}
        </div>
      )}

      {others.length > 0 && (
        <div className="other-list">
          <h3>Other bookings</h3>
          {others.map((b) => (
            <div className="other-row" key={b.id}>
              <span>{b.events?.title || "Event"}<br /><small>{b.status}</small></span>
              {b.status === "pending"
                ? <Link to={`/checkout/${b.id}`} className="link-btn">Continue</Link>
                : <small>{money(b.total_amount)}</small>}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
