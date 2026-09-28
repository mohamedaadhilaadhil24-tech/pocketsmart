"""Planner routes: /generate-home, /generate-party, /generate-jewelry,
/recommendations-details and /history."""

from typing import Literal

from fastapi import APIRouter, Depends

from models.schemas import (
    HomeRequest,
    HistoryEntry,
    JewelryRequest,
    PartyRequest,
    RecommendationResponse,
    UserInDB,
)
from routes.deps import get_current_user
from services import db
from services import gemini_utils as gutil

router = APIRouter(tags=["planners"])

Domain = Literal["home", "party", "jewelry"]


@router.post("/generate-home", response_model=RecommendationResponse)
def generate_home(payload: HomeRequest, user: UserInDB = Depends(get_current_user)):
    """Home interior recommendations (furniture, decor, lighting)."""
    prompt = gutil.build_home_prompt(
        budget=payload.budget,
        rooms=payload.rooms,
        items=payload.items,
        style=payload.style or "modern",
        platforms=payload.platforms,
    )
    result = gutil.generate_recommendations("home", prompt, payload.budget)
    db.add_history(user.id, "home", result)
    return result


@router.post("/generate-party", response_model=RecommendationResponse)
def generate_party(payload: PartyRequest, user: UserInDB = Depends(get_current_user)):
    """Party budget allocation: catering, decoration, entertainment, venue."""
    prompt = gutil.build_party_prompt(
        budget=payload.budget,
        guest_count=payload.guest_count,
        event_type=payload.event_type,
        venue=payload.venue or "home",
        platforms=payload.platforms,
    )
    result = gutil.generate_recommendations("party", prompt, payload.budget)
    db.add_history(user.id, "party", result)
    return result


@router.post("/generate-jewelry", response_model=RecommendationResponse)
def generate_jewelry(payload: JewelryRequest, user: UserInDB = Depends(get_current_user)):
    """Jewellery planner with optional outfit image (multimodal)."""
    prompt = gutil.build_jewelry_prompt(
        budget=payload.budget,
        occasion=payload.occasion,
        style=payload.style or "traditional",
        platforms=payload.platforms,
        has_image=bool(payload.outfit_image),
    )
    result = gutil.generate_recommendations(
        "jewelry", prompt, payload.budget, image=payload.outfit_image
    )
    db.add_history(user.id, "jewelry", result)
    return result


@router.post("/recommendations-details", response_model=RecommendationResponse)
def recommendations_details(
    payload: HomeRequest | PartyRequest | JewelryRequest,
    domain: Domain = "home",
    user: UserInDB = Depends(get_current_user),
):
    """Generic dispatch: returns detailed AI recommendations for any category."""
    if domain == "party" and isinstance(payload, PartyRequest):
        return generate_party(payload, user)
    if domain == "jewelry" and isinstance(payload, JewelryRequest):
        return generate_jewelry(payload, user)
    if isinstance(payload, HomeRequest):
        return generate_home(payload, user)
    return gutil._fallback(domain, payload.budget)


@router.get("/api/history", response_model=list[HistoryEntry])
def history(limit: int = 50, user: UserInDB = Depends(get_current_user)):
    """Past recommendation queries and results for review / re-use.

    Note: the HTML view lives at GET /history (page_routes); this JSON
    endpoint is namespaced under /api to avoid a route collision.
    """
    return db.get_history(user.id, limit=limit)
