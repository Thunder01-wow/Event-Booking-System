import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import admin, auth, bookings, events, health, payments

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Event Ticket Booking System",
    description="Backend API for browsing events and booking tickets.",
    version="0.4.0",
)

# Lets the frontend (a different origin — Vite dev server on :5173 by
# default) call this API from the browser. Without this, every request
# from the frontend fails silently with a CORS error in the console.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Any exception not already turned into an HTTPException lands here instead
    of becoming a bare, unhelpful 500. Always logged to the terminal; the
    actual message is only put in the response body in development, since it
    can reveal internal details (e.g. a bad Supabase key) you don't want a
    real user to see once this goes to production.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = str(exc) if settings.app_env == "development" else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/")
def root():
    return {"message": "Event Ticket Booking System API. See /docs for endpoints."}
