"""HTML page routes (Jinja2 templates)."""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.schemas import UserInDB
from routes.deps import get_optional_user
from services import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _inr(n) -> str:
    """Indian digit grouping: 1234567 -> 12,34,567"""
    try:
        s = str(int(float(n)))
    except (TypeError, ValueError):
        return str(n)
    neg = s.startswith("-")
    s = s.lstrip("-")
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        rest = ",".join(rest[i:i + 2] for i in range(0, len(rest), 2))
        s = rest + "," + last3
    return ("-" if neg else "") + s


templates.env.filters["inr"] = _inr


def _ctx(
    request: Request,
    user: Optional[UserInDB],
    page_title: str,
    active_nav: str,
    **extra,
) -> dict:
    return {
        "request": request,
        "user": user,
        "page_title": page_title,
        "active_nav": active_nav,
        **extra,
    }


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    return templates.TemplateResponse(
        "index.html",
        _ctx(request, user, "Overview", "home", history=db.get_history(user.id) if user else []),
    )


@router.get("/testimonials", response_class=HTMLResponse)
def testimonials(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    return templates.TemplateResponse(
        "testimonials.html",
        _ctx(request, user, "Testimonials", "testimonials"),
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        "login.html", _ctx(request, None, "Sign in", "")
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        "register.html", _ctx(request, None, "Create account", "")
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    history = db.get_history(user.id)
    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(request, user, "Dashboard", "dashboard", history=history),
    )


@router.get("/planner/home", response_class=HTMLResponse)
def home_planner(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    return templates.TemplateResponse(
        "home_planner.html",
        _ctx(request, user, "Home interior", "planner-home"),
    )


@router.get("/planner/party", response_class=HTMLResponse)
def party_planner(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    return templates.TemplateResponse(
        "party_planner.html",
        _ctx(request, user, "Party budget", "planner-party"),
    )


@router.get("/planner/jewelry", response_class=HTMLResponse)
def jewelry_planner(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    return templates.TemplateResponse(
        "jewelry_planner.html",
        _ctx(request, user, "Jewelry matcher", "planner-jewelry"),
    )


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, user: Optional[UserInDB] = Depends(get_optional_user)):
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        "history.html",
        _ctx(request, user, "History", "history", history=db.get_history(user.id)),
    )
