"""Shared FastAPI dependencies: current-user resolution from JWT cookie/header."""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from models.schemas import UserInDB
from services import auth as auth_service
from services import db

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.cookies.get("access_token")


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserInDB:
    token = _extract_token(request, credentials)
    user_id = auth_service.decode_token(token) if token else None
    user = db.get_user_by_id(user_id) if user_id else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[UserInDB]:
    token = _extract_token(request, credentials)
    user_id = auth_service.decode_token(token) if token else None
    return db.get_user_by_id(user_id) if user_id else None
