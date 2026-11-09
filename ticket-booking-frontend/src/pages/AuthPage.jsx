import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function AuthPage({ initialMode = "login" }) {
  const { login, signup } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setNotice("");
    if (mode === "signup" && password.length < 6) {
      setNotice("Use a password of at least 6 characters.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "signup") {
        await signup(email, password, name);
        showToast("Account created. Logging you in…", "success");
      }
      await login(email, password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      setNotice(err.detail || "Couldn't sign you in. Check your email and password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth">
      <p className="eyebrow">Seatly account</p>
      <h2>Save your nights.</h2>
      <p className="lede">Log in to hold seats, finish your booking and keep every ticket in one place.</p>
      <div className="auth-card">
        <div className="tabs">
          <button type="button" className={mode === "login" ? "selected-tab" : ""} onClick={() => setMode("login")}>Log in</button>
          <button type="button" className={mode === "signup" ? "selected-tab" : ""} onClick={() => setMode("signup")}>Create account</button>
        </div>
        <form onSubmit={submit}>
          {mode === "signup" && (
            <label>Full name<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          )}
          <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label>{mode === "login" ? "Password" : "Create password"}
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {notice && <div className="notice">{notice}</div>}
          <button className="primary wide" disabled={busy}>
            {busy ? "One moment…" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
      </div>
    </section>
  );
}
