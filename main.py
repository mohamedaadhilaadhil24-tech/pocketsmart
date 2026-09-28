"""PocketSmart AI — FastAPI entry point.

Run with:  python main.py   (or: uvicorn main:app --reload)
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

from routes import auth_routes, page_routes, planner_routes, session_routes  # noqa: E402

APP_TITLE = "PocketSmart AI"
APP_DESCRIPTION = "Your Smart Budget & Recommendation Assistant"
APP_VERSION = "1.0.0"
PORT = int(os.getenv("PORT", "8010"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    key = os.getenv("GEMINI_API_KEY", "")
    status = "configured" if key and not key.startswith("your_") else "missing (fallback mode)"
    print(f"  Gemini API key: {status}")
    print(f"  Model: {os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')}")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # CORS — allow the frontend / dev servers to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static assets (CSS / JS / images)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # API routers
    app.include_router(auth_routes.router)
    app.include_router(planner_routes.router)
    app.include_router(session_routes.router)

    # HTML page router (registered last so it never shadows API paths)
    app.include_router(page_routes.router)

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
