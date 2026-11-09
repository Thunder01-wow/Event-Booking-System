import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { user, logout } = useAuth();
  const cls = ({ isActive }) => (isActive ? "active" : "");
  return (
    <header className="header">
      <Link to="/" className="logo">seatly<span>✦</span></Link>
      <nav>
        <NavLink to="/" end className={cls}>Discover</NavLink>
        <NavLink to="/tickets" className={cls}>My tickets</NavLink>
        <NavLink to="/about" className={cls}>About</NavLink>
      </nav>
      {user ? (
        <button className="account-link" onClick={logout}>Log out ↗</button>
      ) : (
        <Link className="account-link" to="/login">Log in</Link>
      )}
    </header>
  );
}
