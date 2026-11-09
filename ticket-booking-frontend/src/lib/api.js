const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "seatly_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/**
 * Error shape the backend returns is always {detail: string}, whether it's
 * our own raise_from_api_error() mapping or FastAPI's own validation errors
 * (where detail can be an array — we flatten that to one readable string).
 */
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status;
    this.detail = detail;
  }
}

function flattenDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return "Something went wrong";
}

async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let payload;
  if (form) {
    payload = new URLSearchParams(form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Can't reach the server — is the backend running?");
  }

  if (res.status === 204) return null;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    throw new ApiError(res.status, flattenDetail(data?.detail));
  }
  return data;
}

export const api = {
  signup: (email, password, fullName) =>
    request("/auth/signup", { method: "POST", body: { email, password, full_name: fullName }, auth: false }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", form: { username: email, password }, auth: false }),
  me: () => request("/auth/me"),

  listEvents: () => request("/events"),
  getEvent: (eventId) => request(`/events/${eventId}`),
  listSeats: (eventId) => request(`/events/${eventId}/seats`),

  myBookings: () => request("/bookings"),
  getBooking: (bookingId) => request(`/bookings/${bookingId}`),
  createBooking: (eventId) => request("/bookings", { method: "POST", body: { event_id: eventId } }),
  holdSeat: (bookingId, seatId) =>
    request(`/bookings/${bookingId}/hold-seat`, { method: "POST", body: { seat_id: seatId } }),
  releaseSeat: (bookingId, seatId) =>
    request(`/bookings/${bookingId}/release-seat`, { method: "POST", body: { seat_id: seatId } }),
  cancelBooking: (bookingId) => request(`/bookings/${bookingId}/cancel`, { method: "POST" }),
  devConfirm: (bookingId) => request(`/bookings/${bookingId}/dev-confirm`, { method: "POST" }),

  createPaymentOrder: (bookingId) =>
    request(`/bookings/${bookingId}/create-payment-order`, { method: "POST" }),
};
