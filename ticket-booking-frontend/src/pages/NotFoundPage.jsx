import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="about">
      <p className="eyebrow">Error 404</p>
      <h2>Nothing here.</h2>
      <p className="lede">That page doesn't exist or has moved.</p>
      <Link to="/" className="primary">Back to discover</Link>
    </section>
  );
}
