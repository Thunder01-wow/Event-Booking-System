import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./context/ToastContext";
import ProtectedRoute from "./components/ProtectedRoute";
import NavBar from "./components/NavBar";
import EventsPage from "./pages/EventsPage";
import EventDetailPage from "./pages/EventDetailPage";
import AuthPage from "./pages/AuthPage";
import CheckoutPage from "./pages/CheckoutPage";
import TicketsPage from "./pages/TicketsPage";
import AboutPage from "./pages/AboutPage";
import NotFoundPage from "./pages/NotFoundPage";

function OldTicketRedirect() {
  useParams();
  return <Navigate to="/tickets" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <div className="app">
            <NavBar />
            <main>
              <Routes>
                <Route path="/" element={<EventsPage />} />
                <Route path="/events/:eventId" element={<EventDetailPage />} />
                <Route path="/login" element={<AuthPage key="login" initialMode="login" />} />
                <Route path="/signup" element={<AuthPage key="signup" initialMode="signup" />} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="/checkout/:bookingId" element={<ProtectedRoute><CheckoutPage /></ProtectedRoute>} />
                <Route path="/tickets" element={<ProtectedRoute><TicketsPage /></ProtectedRoute>} />
                <Route path="/tickets/:bookingId" element={<OldTicketRedirect />} />
                <Route path="/bookings" element={<Navigate to="/tickets" replace />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </main>
          </div>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
