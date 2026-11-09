from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Basic liveness check — confirms the API process is up."""
    return {"status": "ok"}
