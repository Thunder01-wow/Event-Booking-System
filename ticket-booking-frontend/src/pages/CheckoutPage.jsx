import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { money, formatWhen, formatCountdown } from "../lib/format";
import { Line } from "../components/Skeleton";

const RAZORPAY_SRC = "https://checkout.razorpay.com/v1/checkout.js";
const FEE_RATE = 0.05;

function loadRazorpay() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) return resolve();
    const s = document.createElement("script");
    s.src = RAZORPAY_SRC;
    s.onload = resolve;
    s.onerror = () => reject(new Error("Couldn't load Razorpay checkout."));
    document.body.appendChild(s);
  });
}

export default function CheckoutPage() {
  const { bookingId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [booking, setBooking] = useState(null);
  const [event, setEvent] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [paying, setPaying] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [devMode, setDevMode] = useState(false);
  const [now, setNow] = useState(Date.now());
  const pollRef = useRef(null);

  useEffect(() => {
    api.getBooking(bookingId)
      .then((b) => {
        setBooking(b);
        api.getEvent(b.event_id).then(setEvent).catch(() => {});
      })
      .catch((e) => setLoadError(e.detail || "Couldn't load this booking."));
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => { clearInterval(t); clearInterval(pollRef.current); };
  }, [bookingId]);

  useEffect(() => {
    if (booking?.status === "confirmed") navigate("/tickets", { replace: true });
  }, [booking, navigate]);

  const expiry = booking?.seats?.length
    ? Math.min(...booking.seats.map((s) => new Date(s.hold_expires_at).getTime()))
    : null;
  const remaining = expiry ? expiry - now : null;
  const holdExpired = booking?.status === "pending" && remaining !== null && remaining <= 0;

  function done() {
    showToast("Payment confirmed. Your tickets are ready.", "success");
    navigate("/tickets");
  }

  async function payRazorpay() {
    setPaying(true);
    try {
      const order = await api.createPaymentOrder(bookingId);
      await loadRazorpay();
      const rzp = new window.Razorpay({
        key: order.key_id, amount: order.amount, currency: order.currency, order_id: order.order_id,
        name: "Seatly", description: event?.title || "Event tickets",
        prefill: { email: user?.email }, theme: { color: "#ff6b4a" },
        handler: poll, // not authoritative: the webhook confirms the booking
        modal: { ondismiss: () => setPaying(false) },
      });
      rzp.on("payment.failed", () => { showToast("Payment failed. You can try again.", "error"); setPaying(false); });
      rzp.open();
    } catch (err) {
      if (err.status === 503) setDevMode(true);
      else showToast(err.detail || "Couldn't start the payment.", "error");
      setPaying(false);
    }
  }

  function poll() {
    setFinalizing(true);
    const started = Date.now();
    pollRef.current = setInterval(async () => {
      try {
        const b = await api.getBooking(bookingId);
        if (b.status === "confirmed") { clearInterval(pollRef.current); done(); }
        else if (Date.now() - started > 30000) {
          clearInterval(pollRef.current); setFinalizing(false); setPaying(false);
          showToast("Payment is taking longer than expected. Check My tickets in a moment.", "error");
        }
      } catch { /* keep polling */ }
    }, 2000);
  }

  async function devConfirm() {
    setPaying(true);
    try { await api.devConfirm(bookingId); done(); }
    catch (err) { showToast(err.detail || "Couldn't confirm this booking.", "error"); setPaying(false); }
  }

  if (loadError && !booking) {
    return (
      <section className="checkout">
        <div className="notice">{loadError}</div>
        <Link to="/" className="back">← Back to discover</Link>
      </section>
    );
  }
  if (!booking) {
    return (
      <section className="checkout">
        <Line width="30%" height={44} style={{ marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 300, borderRadius: 18 }} />
      </section>
    );
  }
  if (booking.status === "cancelled" || booking.status === "expired") {
    return (
      <section className="checkout">
        <p className="eyebrow">Booking {booking.status}</p>
        <h2>Those seats were released.</h2>
        <p className="lede">Pick your seats again to start a new booking.</p>
        <Link to="/" className="primary">Browse events</Link>
      </section>
    );
  }

  const seatLabels = booking.seats.map((s) => s.seat_label).join(", ");
  const subtotal = Number(booking.total_amount);
  const fee = Math.round(subtotal * FEE_RATE);

  return (
    <section className="checkout">
      <p className="eyebrow">Almost there</p>
      <h2>Confirm your booking.</h2>
      <div className="checkout-grid">
        <div className="payment">
          <h3>{event?.title || "Your event"}</h3>
          <p>
            {event ? <>{formatWhen(event.starts_at)}<br />{event.venues?.name}{event.venues?.city ? `, ${event.venues.city}` : ""}</> : "Loading event…"}
          </p>
          <p>Seats: <b>{seatLabels}</b></p>
          {holdExpired
            ? <div className="notice">Your hold expired. <Link to={`/events/${booking.event_id}`} className="link-btn">Pick seats again</Link></div>
            : remaining !== null && <div className="countdown">Seats held for {formatCountdown(remaining)}</div>}
          <hr />
          <div className="pay-lines">
            {booking.seats.map((s) => <span key={s.id}>Seat {s.seat_label} · {s.category}<b>{money(s.price)}</b></span>)}
          </div>
          {devMode && <div className="notice good">Payments aren't configured on this server yet. Test mode confirms the booking without charging anything.</div>}
          {finalizing ? (
            <p>Finalizing your payment. This takes a few seconds…</p>
          ) : devMode ? (
            <button className="primary wide" onClick={devConfirm} disabled={paying || holdExpired}>
              {paying ? "Confirming…" : `Confirm booking (test mode) · ${money(subtotal)}`}
            </button>
          ) : (
            <button className="primary wide" onClick={payRazorpay} disabled={paying || holdExpired}>
              {paying ? "Opening payment…" : `Pay ${money(subtotal)}`}
            </button>
          )}
        </div>
        <div className="ticket-preview">
          <small>SEATLY / BOOKING SUMMARY</small>
          <h3>{event?.title || "Your event"}</h3>
          <p>{event ? formatWhen(event.starts_at) : ""}<br />{event?.venues?.name}</p>
          <hr />
          <b>{seatLabels}</b>
          <small>TOTAL {money(subtotal)}{fee ? "" : ""}</small>
        </div>
      </div>
    </section>
  );
}
