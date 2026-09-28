"""Session metadata routes: /session-info and /session-data."""

from fastapi import APIRouter, Depends

from models.schemas import UserInDB
from routes.deps import get_current_user, get_optional_user
from services import db

router = APIRouter(tags=["session"])


@router.get("/session-info")
def session_info(user: UserInDB = Depends(get_current_user)):
    """Lightweight metadata about the current session."""
    return {
        "user_id": user.id,
        "username": user.username,
        "logged_in": True,
        "history_count": len(db.get_history(user.id)),
    }


@router.get("/session-data")
def session_data(user: UserInDB = Depends(get_current_user)):
    """Detailed session data used for personalisation / recommendation tracking."""
    history = db.get_history(user.id)
    return {
        "user": {"id": user.id, "username": user.username, "email": user.email},
        "logged_in": True,
        "recent_activity": [h.model_dump() for h in history[:10]],
        "domains_used": sorted({h.domain for h in history}),
        "total_queries": len(history),
    }


@router.get("/whoami")
def whoami(user: UserInDB | None = Depends(get_optional_user)):
    if not user:
        return {"logged_in": False}
    return {"logged_in": True, "username": user.username, "user_id": user.id}
