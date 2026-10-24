from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers import goals, sessions, drift, evolutions, simulations, orchestrator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed initial demo data
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Northstar: A Persistent Long-Horizon Goal Tracking Layer for Autonomous Multi-Session AI Agents.",
    lifespan=lifespan
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(goals.router)
app.include_router(sessions.router)
app.include_router(drift.router)
app.include_router(evolutions.router)
app.include_router(simulations.router)
app.include_router(orchestrator.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
