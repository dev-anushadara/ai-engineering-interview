"""
AI Agent Social Network — main application entry point.
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.feed import router as feed_router
from app.api.posts import router as posts_router
from app.database import init_db

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Agent Social Network",
    description="Twitter for AI Agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in dev; restrict in production
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(agents_router)
app.include_router(posts_router)
app.include_router(feed_router)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


@app.on_event("startup")
def on_startup():
    """Create all database tables on first run."""
    init_db()


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------


@app.get("/", tags=["root"])
def root():
    return {
        "message": "AI Agent Social Network",
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
