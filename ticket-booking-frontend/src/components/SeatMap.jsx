import { groupSeats, money } from "../lib/format";

/** `selected` is a map of seatId -> seat for this user's holds. */
export default function SeatMap({ seats, selected, onToggle, disabled }) {
  if (!seats.length) return <div className="empty">No seats have been added to this event yet.</div>;
  return (
    <div>
      <div className="screen">STAGE / SCREEN</div>
      {groupSeats(seats).map((tier) => (
        <div className="seat-tier" key={tier.name}>
          <p><b>{tier.name}</b> · {money(tier.price)}</p>
          {tier.rows.map((r) => (
            <div className="seat-row" key={r.row}>
              {r.seats.map((seat) => {
                const mine = !!selected[seat.id];
                const status = mine ? "selected" : seat.status;
                const clickable = !disabled && (seat.status === "available" || mine);
                return (
                  <button
                    key={seat.id}
                    type="button"
                    className="seat"
                    data-status={status}
                    disabled={!clickable}
                    aria-pressed={mine}
                    title={`${seat.seat_label} · ${tier.name} · ${money(seat.price)}`}
                    onClick={() => onToggle(seat)}
                  >
                    {mine ? "✓ " : ""}{seat.seat_label}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      ))}
      <div className="legend">
        <span><i style={{ background: "#fff" }} />Available</span>
        <span><i style={{ background: "var(--coral)", borderColor: "var(--coral)" }} />Yours</span>
        <span><i style={{ background: "#fff7e6" }} />Held by someone</span>
        <span><i style={{ background: "#f0f0f2" }} />Booked</span>
      </div>
    </div>
  );
}
