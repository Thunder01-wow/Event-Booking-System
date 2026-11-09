const features = [
  ["Find faster", "Search and filter by city or category to see what's on near you."],
  ["Pick better", "See live seat availability and choose exactly where you want to be."],
  ["Keep everything", "Your confirmed bookings and ticket codes stay together in one place."],
];

export default function AboutPage() {
  return (
    <section className="about">
      <p className="eyebrow">About Seatly</p>
      <h2>Good nights start here.</h2>
      <p className="lede">A simple, fast ticketing experience for live music, comedy, sport and theatre. Seats are held for you while you pay, and never sold twice.</p>
      <div className="feature-grid">
        {features.map(([t, b]) => (
          <div className="feature" key={t}><h3>{t}</h3><p>{b}</p></div>
        ))}
      </div>
    </section>
  );
}
