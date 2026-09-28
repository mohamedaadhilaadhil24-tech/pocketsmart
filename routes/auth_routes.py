"""Authentication routes: /register, /login, /logout, /token."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from models.schemas import Token, UserInDB, UserLogin, UserPublic, UserRegister
from routes.deps import get_current_user
from services import auth as auth_service
from services import db

router = APIRouter(tags=["auth"])

COOKIE = "access_token"


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, response: Response):
    if db.get_user_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    user = db.create_user(
        username=payload.username,
        email=payload.email,
        hashed_password=auth_service.hash_password(payload.password),
    )
    if not user:
        raise HTTPException(status_code=409, detail="Username already taken")
    _set_cookie(response, auth_service.create_access_token(user))
    return UserPublic(id=user.id, username=user.username, email=user.email)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, response: Response):
    user = db.get_user_by_username(payload.username)
    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = auth_service.create_access_token(user)
    _set_cookie(response, token)
    return Token(access_token=token)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"detail": "Logged out"}


@router.post("/token", response_model=Token)
def issue_token(payload: UserLogin):
    """JSON-only token endpoint (used by API clients / tests)."""
    user = db.get_user_by_username(payload.username)
    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return Token(access_token=auth_service.create_access_token(user))


@router.get("/me", response_model=UserPublic)
def me(user: UserInDB = Depends(get_current_user)):
    return UserPublic(id=user.id, username=user.username, email=user.email)
