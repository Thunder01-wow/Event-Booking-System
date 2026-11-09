export const money = (n) => `₹${Number(n ?? 0).toLocaleString("en-IN")}`;

export const formatDay = (iso) =>
  new Date(iso).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" });

export const formatTime = (iso) =>
  new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", hour12: true }).toUpperCase();

export const formatWhen = (iso) => `${formatDay(iso)} · ${formatTime(iso)}`;

export function formatCountdown(ms) {
  if (ms <= 0) return "0:00";
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export const tierName = (category) => {
  const c = (category || "general").toLowerCase();
  return c.charAt(0).toUpperCase() + c.slice(1);
};

/** Group seats into tiers (cheapest first) then rows (leading letters of the label). */
export function groupSeats(seats) {
  const tiers = new Map();
  for (const seat of seats) {
    const key = tierName(seat.category);
    if (!tiers.has(key)) tiers.set(key, { name: key, price: Number(seat.price), rows: new Map() });
    const tier = tiers.get(key);
    tier.price = Math.min(tier.price, Number(seat.price));
    const row = (seat.seat_label.match(/^[A-Za-z]+/) || ["#"])[0].toUpperCase();
    if (!tier.rows.has(row)) tier.rows.set(row, []);
    tier.rows.get(row).push(seat);
  }
  return [...tiers.values()]
    .sort((a, b) => a.price - b.price)
    .map((t) => ({
      name: t.name,
      price: t.price,
      rows: [...t.rows.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([row, list]) => ({
          row,
          seats: list.sort((a, b) => a.seat_label.localeCompare(b.seat_label, undefined, { numeric: true })),
        })),
    }));
}
