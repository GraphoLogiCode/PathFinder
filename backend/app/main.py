"""
PathFinder API — FastAPI Application Entrypoint

Registers all route modules, configures CORS for the Next.js frontend,
and exposes a /health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import detect, georef, route, missions

app = FastAPI(
    title="PathFinder API",
    description="Satellite-based disaster navigation — safe routing around danger zones",
    version="0.1.0",
    redirect_slashes=True,
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js frontend at localhost:3000
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
app.include_router(detect.router, tags=["Detection"])
app.include_router(georef.router, tags=["Geo-Referencing"])
app.include_router(route.router, tags=["Routing"])
app.include_router(missions.router, tags=["Missions"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}
