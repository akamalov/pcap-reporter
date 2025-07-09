"""
Health check endpoints for the MCP PCAP Reporter API.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging

from core.config import Settings, get_settings
from core.database import get_database
from core.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    """
    health_status = {
        "status": "healthy",
        "service": "MCP PCAP Reporter API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {}
    }
    
    # Check database connection
    try:
        db = await get_database()
        await db.command("ping")
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check Redis/Celery connection
    try:
        celery_inspect = celery_app.control.inspect()
        active_tasks = celery_inspect.active()
        health_status["components"]["redis"] = "healthy" if active_tasks is not None else "unhealthy"
        health_status["components"]["celery"] = health_status["components"]["redis"]
    except Exception as e:
        logger.error(f"Redis/Celery health check failed: {e}")
        health_status["components"]["redis"] = "unhealthy"
        health_status["components"]["celery"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    return health_status


@router.get("/database")
async def database_health() -> Dict[str, Any]:
    """
    Database-specific health check.
    """
    try:
        db = await get_database()
        
        # Ping database
        await db.command("ping")
        
        # Get database stats
        stats = await db.command("dbStats")
        
        return {
            "status": "healthy",
            "database": {
                "name": db.name,
                "collections": stats.get("collections", 0),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/celery")
async def celery_health() -> Dict[str, Any]:
    """
    Celery-specific health check.
    """
    try:
        celery_inspect = celery_app.control.inspect()
        
        # Get worker stats
        stats = celery_inspect.stats()
        active_tasks = celery_inspect.active()
        registered_tasks = celery_inspect.registered()
        
        return {
            "status": "healthy",
            "celery": {
                "workers": list(stats.keys()) if stats else [],
                "active_tasks": len(active_tasks) if active_tasks else 0,
                "registered_tasks": len(registered_tasks) if registered_tasks else 0,
                "broker_url": celery_app.conf.broker_url,
                "result_backend": celery_app.conf.result_backend,
            }
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 