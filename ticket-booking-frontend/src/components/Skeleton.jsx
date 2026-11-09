export function Line({ width = "100%", height = 14, style }) {
  return <div className="skeleton" style={{ width, height, ...style }} />;
}

export function EventGridSkeleton({ count = 6 }) {
  return (
    <div className="event-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="skeleton" style={{ height: 210, borderRadius: 0 }} />
          <div className="body"><Line width="30%" height={16} /><Line width="75%" height={20} /><Line width="55%" /></div>
        </div>
      ))}
    </div>
  );
}

export function SeatsSkeleton({ count = 16 }) {
  return (
    <div data-skeleton>
      {Array.from({ length: count }).map((_, i) => <div className="skeleton skeleton-seat" key={i} />)}
    </div>
  );
}

export function TicketsSkeleton() {
  return (
    <div className="tickets">
      {[0, 1].map((i) => <div className="skeleton" key={i} style={{ height: 290, borderRadius: 20 }} />)}
    </div>
  );
}
