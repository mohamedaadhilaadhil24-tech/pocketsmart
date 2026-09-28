from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ---------- Auth ----------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    email: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserInDB(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str


class UserPublic(BaseModel):
    id: str
    username: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Planner inputs ----------

class HomeRequest(BaseModel):
    budget: float = Field(gt=0)
    rooms: List[str] = Field(default_factory=lambda: ["Living Room"])
    items: List[dict] = Field(default_factory=list)  # [{"name": "lights", "quantity": 4}]
    style: Optional[str] = "modern"
    platforms: Optional[List[str]] = None


class PartyRequest(BaseModel):
    budget: float = Field(gt=0)
    guest_count: int = Field(gt=0)
    event_type: str = "birthday"  # birthday | corporate | wedding
    venue: Optional[str] = "home"
    platforms: Optional[List[str]] = None


class JewelryRequest(BaseModel):
    budget: float = Field(gt=0)
    occasion: str = "wedding"
    style: Optional[str] = "traditional"
    outfit_image: Optional[str] = None  # base64 data URI (optional)
    platforms: Optional[List[str]] = None


# ---------- Output ----------

class RecommendationItem(BaseModel):
    name: str
    category: str
    price: float
    platform: str
    url: Optional[str] = None
    rationale: Optional[str] = None


class RecommendationResponse(BaseModel):
    domain: str
    budget: float
    allocated_budget: Optional[float] = None
    summary: str
    items: List[RecommendationItem] = Field(default_factory=list)
    source: str = "gemini"  # gemini | fallback


class HistoryEntry(BaseModel):
    id: str
    domain: str
    budget: float
    summary: str
    item_count: int
    created_at: str
