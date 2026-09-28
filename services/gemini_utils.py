"""Gemini prompt orchestration for PocketSmart AI.

Responsibilities:
  * Build domain-specific prompts (home / party / jewelry)
  * Format budget + preference context
  * Call Gemini (text or text+image) and parse structured JSON
  * Fall back to deterministic recommendations when the AI is
    unavailable, misconfigured or returns insufficient results
"""

import json
import os
import re
from typing import List, Optional

from models.schemas import RecommendationItem, RecommendationResponse

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

DEFAULT_PLATFORMS = {
    "home": ["IKEA", "Amazon", "Flipkart"],
    "party": ["Swiggy", "Zomato", "OYO", "Amazon", "Flipkart"],
    "jewelry": ["Amazon", "Flipkart"],
}

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


# --------------------------------------------------------------------------
# Prompt builders
# --------------------------------------------------------------------------

def _platform_line(platforms: Optional[List[str]], domain: str) -> str:
    platforms = platforms or DEFAULT_PLATFORMS[domain]
    return ", ".join(platforms)


def build_home_prompt(budget: float, rooms: List[str], items: List[dict], style: str, platforms: Optional[List[str]]) -> str:
    item_lines = ", ".join(
        f"{i.get('quantity', 1)}x {i.get('name', '').strip()}" for i in items if i.get("name")
    ) or "general decor (lights, fans, dining table, sofa, wall art)"
    return f"""You are PocketSmart AI, a budget-aware shopping assistant.
Generate home interior recommendations.

TOTAL BUDGET: INR {budget:,.0f}
ROOMS: {', '.join(rooms)}
ITEMS NEEDED: {item_lines}
STYLE PREFERENCE: {style}
PLATFORMS TO SOURCE FROM: {_platform_line(platforms, 'home')}

Rules:
- Stay within the total budget; show per-item prices that sum to <= budget.
- Prefer cost-effective options balancing functionality, style and price.
- Only suggest products available on the listed platforms.

Return ONLY valid JSON in this exact shape:
{{
  "summary": "2-3 sentence plan overview",
  "items": [
    {{"name": "...", "category": "...", "price": 0, "platform": "...", "url": "https://...", "rationale": "..."}}
  ]
}}"""


def build_party_prompt(budget: float, guest_count: int, event_type: str, venue: str, platforms: Optional[List[str]]) -> str:
    return f"""You are PocketSmart AI, a budget-aware event planning assistant.
Allocate the budget proportionally across catering, decoration and entertainment.

TOTAL BUDGET: INR {budget:,.0f}
GUEST COUNT: {guest_count}
EVENT TYPE: {event_type}
VENUE: {venue}
PLATFORMS / VENDORS: {_platform_line(platforms, 'party')}

Rules:
- Split the budget sensibly across catering, decoration, entertainment and venue.
- Per-guest catering cost must fit within the allocation.
- Only recommend vendors/services on the listed platforms.

Return ONLY valid JSON in this exact shape:
{{
  "summary": "2-3 sentence allocation overview",
  "items": [
    {{"name": "...", "category": "catering|decoration|entertainment|venue", "price": 0, "platform": "...", "url": "https://...", "rationale": "..."}}
  ]
}}"""


def build_jewelry_prompt(budget: float, occasion: str, style: str, platforms: Optional[List[str]], has_image: bool) -> str:
    image_note = (
        "An outfit image was uploaded: match jewellery colours and aesthetics to it."
        if has_image
        else "No outfit image provided; match to the occasion and style preference."
    )
    return f"""You are PocketSmart AI, a budget-aware jewellery stylist.
Recommend jewellery that matches the occasion, style and budget.

TOTAL BUDGET: INR {budget:,.0f}
OCCASION: {occasion}
STYLE PREFERENCE: {style}
IMAGE CONTEXT: {image_note}
PLATFORMS: {_platform_line(platforms, 'jewelry')}

Rules:
- Stay within budget; show per-item prices that sum to <= budget.
- Prioritise colour coordination with the outfit when an image is given.

Return ONLY valid JSON in this exact shape:
{{
  "summary": "2-3 sentence styling overview",
  "items": [
    {{"name": "...", "category": "...", "price": 0, "platform": "...", "url": "https://...", "rationale": "..."}}
  ]
}}"""


# --------------------------------------------------------------------------
# Gemini call
# --------------------------------------------------------------------------

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None
    try:
        from google import genai  # type: ignore
        return genai.Client(api_key=api_key, http_options={"timeout": 30_000})
    except Exception:
        return None


def _call_gemini(prompt: str, image_b64: Optional[str] = None) -> Optional[dict]:
    client = _get_client()
    if client is None:
        return None

    contents = [prompt]
    if image_b64:
        try:
            import base64
            from google.genai import types  # type: ignore

            raw = image_b64.split(",", 1)[-1]
            contents.append(types.Part.from_bytes(data=base64.b64decode(raw), mime_type="image/png"))
        except Exception:
            pass  # fall back to text-only

    last_err = ""
    for attempt in range(2):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
            text = getattr(response, "text", None) or ""
            match = JSON_BLOCK_RE.search(text)
            if not match:
                last_err = "no JSON block in response"
                break
            payload = json.loads(match.group(0))
            if payload.get("items"):
                return payload
            last_err = "response JSON had no items"
            break
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if status == 429 or "429" in last_err:
                # free-tier quota — no point retrying immediately
                print(f"  [gemini] rate limited: {last_err[:160]}")
                return None
            if attempt == 0:
                import time
                time.sleep(1.5)  # one retry for transient errors
                continue
            break

    print(f"  [gemini] call failed: {last_err[:200]}")
    return None


# --------------------------------------------------------------------------
# Parsing + fallback
# --------------------------------------------------------------------------

def _parse(payload: dict, domain: str, budget: float, source: str) -> RecommendationResponse:
    items: List[RecommendationItem] = []
    for raw in payload.get("items", [])[:12]:
        try:
            items.append(
                RecommendationItem(
                    name=str(raw.get("name", "Unnamed item")),
                    category=str(raw.get("category", domain)),
                    price=float(raw.get("price", 0) or 0),
                    platform=str(raw.get("platform", "Amazon")),
                    url=raw.get("url"),
                    rationale=raw.get("rationale"),
                )
            )
        except (TypeError, ValueError):
            continue
    return RecommendationResponse(
        domain=domain,
        budget=budget,
        summary=str(payload.get("summary", "")) or "Budget plan generated.",
        items=items,
        source=source,
    )


def _fallback(domain: str, budget: float) -> RecommendationResponse:
    """Deterministic mock catalogue used when Gemini is unavailable or weak."""
    if domain == "home":
        split = [
            ("LED Ceiling Lights", "lighting", 0.18, "IKEA"),
            ("Wall Art Set", "decor", 0.12, "IKEA"),
            ("Ceiling Fan", "appliance", 0.22, "Amazon"),
            ("Coffee Table", "furniture", 0.24, "IKEA"),
            ("Bookshelf", "furniture", 0.14, "Flipkart"),
            ("Area Rug", "decor", 0.10, "Amazon"),
        ]
        summary = "Balanced decor plan spreading your budget across lighting, furniture and accents."
    elif domain == "party":
        split = [
            ("Catering Package", "catering", 0.40, "Swiggy"),
            ("Venue Booking", "venue", 0.22, "OYO"),
            ("Decoration Kit", "decoration", 0.18, "Amazon"),
            ("DJ / Sound Setup", "entertainment", 0.12, "Flipkart"),
            ("Cake & Desserts", "catering", 0.08, "Zomato"),
        ]
        summary = "Event budget split across catering (40%), venue (22%), decor (18%) and entertainment (20%)."
    else:
        split = [
            ("Kundan Necklace Set", "necklace", 0.35, "Amazon"),
            ("Jhumka Earrings", "earrings", 0.18, "Flipkart"),
            ("Gold-Plated Bangles", "bangles", 0.17, "Amazon"),
            ("Statement Ring", "ring", 0.12, "Flipkart"),
            ("Anklet Pair", "anklets", 0.10, "Amazon"),
            ("Mangtika", "accessory", 0.08, "Flipkart"),
        ]
        summary = "Occasion-ready jewellery set chosen to complement your outfit within budget."

    items = [
        RecommendationItem(
            name=name,
            category=cat,
            price=round(budget * share, 2),
            platform=platform,
            url=f"https://www.{platform.lower()}.com",
            rationale=f"Allocated {int(share * 100)}% of budget for balanced coverage.",
        )
        for name, cat, share, platform in split
    ]
    return RecommendationResponse(
        domain=domain, budget=budget, summary=summary, items=items, source="fallback"
    )


def generate_recommendations(domain: str, prompt: str, budget: float, image: Optional[str] = None) -> RecommendationResponse:
    """Single entry point: try Gemini, fall back to a deterministic plan."""
    payload = _call_gemini(prompt, image)
    if payload and payload.get("items"):
        response = _parse(payload, domain, budget, source="gemini")
        if response.items:
            return response
    return _fallback(domain, budget)
