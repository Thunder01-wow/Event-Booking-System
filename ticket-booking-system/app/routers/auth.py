from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import CurrentUser, get_current_user
from app.db.supabase_client import get_fresh_anon_client
from app.schemas.schemas import SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(body: SignupRequest):
    payload: dict = {"email": body.email, "password": body.password}
    if body.full_name:
        payload["options"] = {"data": {"full_name": body.full_name}}
    try:
        res = get_fresh_anon_client().auth.sign_up(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if res.user is None:
        raise HTTPException(status_code=400, detail="Signup failed")
    return {
        "id": str(res.user.id),
        "email": res.user.email,
        # True means the user must click a confirmation email before logging in.
        "email_confirmation_required": res.session is None,
    }


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Send your email in the 'username' field."""
    try:
        res = get_fresh_anon_client().auth.sign_in_with_password(
            {"email": form.username, "password": form.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if res.session is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": res.session.access_token, "token_type": "bearer"}


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}
