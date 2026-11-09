import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { money, formatWhen, formatCountdown } from "../lib/format";
import EventImage from "../components/EventImage";
import SeatMap from "../components/SeatMap";
import { Line, SeatsSkeleton } from "../components/Skeleton";

const FEE_RATE = 0.05;

export default function EventDetailPage() {
  const { eventId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [event, setEvent] = useState(null);
  const [seats, setSeats] = useState(null);
  const [bookingId, setBookingId] = useState(null);
  const [selected, setSelected] = useState({});
  const [expiresAt, setExpiresAt] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);

  const refreshSeats = useCallback(
    () => api.listSeats(eventId).then(setSeats).catch((e) => setLoadError(e.detail || "Couldn't load seats.")),
    [eventId]
  );

  useEffect(() => {
    api.getEvent(eventId).then(setEvent).catch((e) => setLoadError(e.detail || "Event not found."));
    refreshSeats();
  }, [eventId, refreshSeats]);

  // Restore an in-progress (pending) booking for this event, e.g. after a page refresh.
  useEffect(() => {
    if (authLoading || !user) return;
    let cancelled = false;
    (async () => {
      try {
        const list = await api.myBookings();
        const pending = list.find((b) => b.event_id === eventId && b.status === "pending");
        if (!pending) return;
        const full = await api.getBooking(pending.id);
        const live = (full.seats || []).filter(
          (s) => s.status === "held" && new Date(s.hold_expires_at).getTime() > Date.now()
        );
        if (cancelled || !live.length) return;
        setBookingId(pending.id);
        setSelected(Object.fromEntries(live.map((s) => [s.id, s])));
        setExpiresAt(Math.min(...live.map((s) => new Date(s.hold_expires_at).getTime())));
      } catch {
        /* nothing to restore */
      }
    })();
    return () => { cancelled = true; };
  }, [authLoading, user, eventId]);

  useEffect(() => {
    if (!expiresAt) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [expiresAt]);

  const remaining = expiresAt ? expiresAt - now : null;
  const expired = remaining !== null && remaining <= 0;

  useEffect(() => {
    if (expired) {
      setSelected({}); setBookingId(null); setExpiresAt(null);
      refreshSeats();
      showToast("Your seat hold expired. Pick your seats again.", "error");
    }
  }, [expired, refreshSeats, showToast]);

  async function toggle(seat) {
    if (!user) {
      navigate("/login", { state: { from: { pathname: `/events/${eventId}` } } });
      return;
    }
    setBusy(true);
    try {
      if (selected[seat.id]) {
        await api.releaseSeat(bookingId, seat.id);
        const next = { ...selected };
        delete next[seat.id];
        setSelected(next);
        if (!Object.keys(next).length) { setExpiresAt(null); }
        showToast(`Seat ${seat.seat_label} released`, "info");
      } else {
        let id = bookingId;
        if (!id) {
          id = (await api.createBooking(eventId)).id;
          setBookingId(id);
        }
        const res = await api.holdSeat(id, seat.id);
        setSelected((prev) => ({ ...prev, [seat.id]: seat }));
        const exp = new Date(res.hold_expires_at).getTime();
        setExpiresAt((prev) => (prev ? Math.min(prev, exp) : exp));
        showToast(`Seat ${seat.seat_label} held for you`, "success");
      }
    } catch (err) {
      showToast(err.detail || "Couldn't update that seat.", "error");
    } finally {
      await refreshSeats();
      setBusy(false);
    }
  }

  async function clearSelection() {
    if (!bookingId) return;
    setBusy(true);
    try { await api.cancelBooking(bookingId); } catch { /* already gone */ }
    setBookingId(null); setSelected({}); setExpiresAt(null);
    await refreshSeats();
    setBusy(false);
    showToast("Selection cleared", "info");
  }

  if (loadError && !event) {
    return (
      <section className="detail">
        <Link to="/" className="back">← Back to discover</Link>
        <div className="notice">{loadError}</div>
      </section>
    );
  }

  const picked = Object.values(selected);
  const subtotal = picked.reduce((sum, s) => sum + Number(s.price), 0);
  const fee = Math.round(subtotal * FEE_RATE);

  return (
    <section className="detail">
      <Link to="/" className="back">← Back to discover</Link>

      {!event ? (
        <>
          <div className="skeleton" style={{ height: 310, borderRadius: 20, marginBottom: 34 }} />
          <Line width="40%" height={44} style={{ marginBottom: 14 }} />
          <Line width="30%" />
        </>
      ) : (
        <>
          <EventImage event={event} className="hero-img" />
          <p className="eyebrow">{event.category || "Event"}</p>
          <h2>{event.title}</h2>
          {event.description && <p className="lede">{event.description}</p>}
          <p className="event-line">
            <b>{formatWhen(event.starts_at)}</b><br />
            ⌖ {event.venues?.name}{event.venues?.city ? `, ${event.venues.city}` : ""}
          </p>
        </>
      )}

      <div className="detail-grid">
        <div>
          <h3>Choose your seats</h3>
          {seats === null ? <SeatsSkeleton /> : <SeatMap seats={seats} selected={selected} onToggle={toggle} disabled={busy} />}
        </div>

        <aside className="order">
          <h3>Your order</h3>
          <div className="order-stat">
            <small>Selected seats</small>
            <strong>{picked.length}</strong>
            <span>{picked.map((s) => s.seat_label).join(", ") || "Choose a seat to continue"}</span>
          </div>
          {picked.length > 0 && remaining > 0 && (
            <div className="countdown">Held for {formatCountdown(remaining)}</div>
          )}
          <div className="total-lines">
            <span>Tickets <b>{money(subtotal)}</b></span>
            <span>Booking fee <b>{money(fee)}</b></span>
            <hr />
            <span>Total <strong>{money(subtotal + fee)}</strong></span>
          </div>
          <button className="primary wide" disabled={!picked.length || busy} onClick={() => navigate(`/checkout/${bookingId}`)}>
            Continue to payment
          </button>
          {picked.length > 0 && (
            <button className="secondary wide" disabled={busy} onClick={clearSelection}>Clear selection</button>
          )}
        </aside>
      </div>
    </section>
  );
}
