import { useState } from "react";

function hash(str = "") {
  let h = 0;
  for (const c of str) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return h;
}

/** Shows event.image_url if set; otherwise (or if it fails to load) a gradient placeholder. */
export default function EventImage({ event, className = "card" }) {
  const [failed, setFailed] = useState(false);
  const showImg = event.image_url && !failed;
  return (
    <div className={`img-slot ${className} ${showImg ? "" : `g${hash(event.id) % 6}`}`}>
      {showImg ? (
        <img src={event.image_url} alt="" loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <span className="ph">{(event.category || "event").toUpperCase()}</span>
      )}
    </div>
  );
}
