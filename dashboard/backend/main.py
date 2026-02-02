"""
CME Question Explorer - FastAPI Backend

Main application entry point.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

from .routers import questions, reports, novel_entities, user_values, dedup, proposals, eval, qboost
from .services.database import get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CME Question Explorer API",
    description="API for searching and exploring CME outcomes questions with tags and performance metrics",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(novel_entities.router, prefix="/api")
app.include_router(user_values.router, prefix="/api")
app.include_router(dedup.router, prefix="/api")
app.include_router(proposals.router, prefix="/api")
app.include_router(eval.router, prefix="/api")
app.include_router(qboost.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to log all errors."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting CME Question Explorer API...")
    db = get_database()
    stats = db.get_stats()
    logger.info(f"Database stats: {stats}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CME Question Explorer API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db = get_database()
    stats = db.get_stats()
    return {
        "status": "healthy",
        "database": stats
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

