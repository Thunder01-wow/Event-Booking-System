from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.db.supabase_client import get_supabase, get_supabase_admin

# tokenUrl makes the "Authorize" button in /docs work with email + password.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass
class CurrentUser:
    id: str
    email: str | None
    token: str


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """Validate the Bearer token with Supabase Auth and return the user."""
    try:
        res = get_supabase().auth.get_user(token)
        user = res.user if res else None
    except Exception:
        user = None

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(id=str(user.id), email=user.email, token=token)


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Gate for admin-only routes. Checked here (via the service role, so this
    read itself isn't subject to the very RLS it's enforcing) rather than
    relying solely on the admin-only RLS policies on venues/events/seats —
    this way a non-admin gets a clear 403 instead of a confusing empty
    write that RLS silently rejected.
    """
    res = (
        get_supabase_admin()
        .table("profiles")
        .select("role")
        .eq("id", user.id)
        .execute()
    )
    if not res.data or res.data[0].get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
