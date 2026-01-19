"""
Automated CE Outcomes Dashboard - FastAPI Backend

Main application entry point for V3.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

from .routers import questions, reports, entities, tagging, review
from .services.database import get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Automated CE Outcomes Dashboard API",
    description="API for CME question tagging with 3-model LLM voting system",
    version="3.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(entities.router, prefix="/api")
app.include_router(tagging.router, prefix="/api")
app.include_router(review.router, prefix="/api")


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
    logger.info("Starting Automated CE Outcomes Dashboard API v3.0...")
    db = get_database()
    stats = db.get_stats()
    logger.info(f"Database stats: {stats}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Automated CE Outcomes Dashboard API",
        "docs": "/docs",
        "version": "3.0.0",
        "features": [
            "3-model LLM voting (GPT-5.2, Claude Opus 4.5, Gemini 2.5 Pro)",
            "Web search via Perplexity Sonar",
            "Human review workflow",
            "Iterative prompt refinement"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db = get_database()
    stats = db.get_stats()
    return {
        "status": "healthy",
        "version": "3.0.0",
        "database": stats
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
