"""In-memory data store for users, sessions and recommendation history.

Swap this module with a real database (SQLAlchemy / MongoDB) without
touching the routes: everything here is accessed through helper functions.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from models.schemas import HistoryEntry, RecommendationResponse, UserInDB

_lock = threading.Lock()
_users: Dict[str, UserInDB] = {}
_users_by_name: Dict[str, str] = {}
_history: Dict[str, List[dict]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- users ----------

def create_user(username: str, email: str, hashed_password: str) -> Optional[UserInDB]:
    with _lock:
        if username.lower() in _users_by_name:
            return None
        user = UserInDB(
            id=uuid.uuid4().hex,
            username=username,
            email=email,
            hashed_password=hashed_password,
        )
        _users[user.id] = user
        _users_by_name[username.lower()] = user.id
        _history.setdefault(user.id, [])
        return user


def get_user_by_username(username: str) -> Optional[UserInDB]:
    user_id = _users_by_name.get(username.lower())
    return _users.get(user_id) if user_id else None


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    return _users.get(user_id)


# ---------- history ----------

def add_history(user_id: str, domain: str, response: RecommendationResponse) -> HistoryEntry:
    entry = HistoryEntry(
        id=uuid.uuid4().hex[:12],
        domain=domain,
        budget=response.budget,
        summary=response.summary,
        item_count=len(response.items),
        created_at=_now(),
    )
    with _lock:
        _history.setdefault(user_id, []).insert(0, entry.model_dump())
    return entry


def get_history(user_id: str, limit: int = 50) -> List[HistoryEntry]:
    raw = _history.get(user_id, [])[:limit]
    return [HistoryEntry(**e) for e in raw]


def clear_history(user_id: str) -> None:
    with _lock:
        _history[user_id] = []
