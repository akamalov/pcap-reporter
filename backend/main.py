"""
MCP PCAP Reporter - FastAPI Backend
Main application module with FastAPI setup and Celery integration.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging
from typing import Dict, Any

# Import our modules
from core.config import get_settings
from core.database import init_db, wait_for_database, close_db
from core.celery_app import celery_app
from api.v1.api import api_router

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events - startup and shutdown.
    """
    # Startup
    logger.info("Starting MCP PCAP Reporter API...")
    
    try:
        # Wait for database to be available
        logger.info("Waiting for database connection...")
        await wait_for_database(timeout=60)
        
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP PCAP Reporter API...")
    try:
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MCP Server for PCAP Analysis and Reporting",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"🔥 REQUEST: {request.method} {request.url}")
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"🔥 RESPONSE: {response.status_code}")
    logger.info(f"Response: {response.status_code}")
    return response


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify service status.
    """
    try:
        # Check database connection
        from core.database import get_database
        db = await get_database()
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    try:
        # Check Redis/Celery connection
        celery_inspect = celery_app.control.inspect()
        active_tasks = celery_inspect.active()
        redis_status = "healthy" if active_tasks is not None else "unhealthy"
    except Exception as e:
        logger.error(f"Redis/Celery health check failed: {e}")
        redis_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "MCP PCAP Reporter API",
        "version": settings.VERSION,
        "components": {
            "database": db_status,
            "redis": redis_status,
            "celery": redis_status  # Celery uses Redis as broker
        }
    }


@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": "MCP PCAP Reporter API",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": "/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled exceptions.
    """
    logger.error(f"Global exception handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9090,
        reload=True,
        log_level="info"
    ) 