"""
Health service for checking system component status.
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from celery import Celery
import logging

from core.config import get_settings

logger = logging.getLogger(__name__)

# Application start time for uptime calculation
APP_START_TIME = time.time()


class HealthService:
    """Service for checking health of system components."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def check_database_health(self) -> Dict[str, str]:
        """
        Check MongoDB database health.
        
        Returns:
            Dict with status and optional error message
        """
        try:
            # Create a temporary client for health check
            client = AsyncIOMotorClient(self.settings.DATABASE_URL)
            
            # Ping the database with timeout
            await asyncio.wait_for(
                client.admin.command('ping'),
                timeout=5.0
            )
            
            # Close the client
            client.close()
            
            return {"status": "healthy"}
            
        except asyncio.TimeoutError:
            logger.error("Database health check timed out")
            return {"status": "unhealthy", "error": "Database connection timeout"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": f"Database connection failed: {str(e)}"}
    
    async def check_redis_health(self) -> Dict[str, str]:
        """
        Check Redis health.
        
        Returns:
            Dict with status and optional error message
        """
        try:
            # Create a temporary Redis client for health check
            redis_client = Redis.from_url(self.settings.REDIS_URL)
            
            # Ping Redis with timeout
            pong = await asyncio.wait_for(
                redis_client.ping(),
                timeout=5.0
            )
            
            # Close the client
            await redis_client.close()
            
            if pong:
                return {"status": "healthy"}
            else:
                return {"status": "unhealthy", "error": "Redis ping failed"}
                
        except asyncio.TimeoutError:
            logger.error("Redis health check timed out")
            return {"status": "unhealthy", "error": "Redis connection timeout"}
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": f"Redis connection failed: {str(e)}"}
    
    async def check_celery_health(self) -> Dict[str, str]:
        """
        Check Celery worker health.
        
        Returns:
            Dict with status and optional error message
        """
        try:
            # Create a temporary Celery app for health check
            celery_app = Celery(
                'health_check',
                broker=self.settings.CELERY_BROKER_URL,
                backend=self.settings.CELERY_RESULT_BACKEND
            )
            
            # Check active workers with timeout
            inspect = celery_app.control.inspect()
            active_workers = await asyncio.wait_for(
                asyncio.to_thread(inspect.active),
                timeout=5.0
            )
            
            if active_workers:
                worker_count = len(active_workers)
                return {"status": "healthy", "workers": worker_count}
            else:
                return {"status": "unhealthy", "error": "No active Celery workers"}
                
        except asyncio.TimeoutError:
            logger.error("Celery health check timed out")
            return {"status": "unhealthy", "error": "Celery health check timeout"}
        except Exception as e:
            logger.error(f"Celery health check failed: {e}")
            return {"status": "unhealthy", "error": f"Celery workers unavailable: {str(e)}"}
    
    async def get_comprehensive_health(self) -> Dict:
        """
        Get comprehensive health status of all services.
        
        Returns:
            Complete health status report
        """
        # Run all health checks concurrently
        db_health, redis_health, celery_health = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_celery_health(),
            return_exceptions=True
        )
        
        # Handle any exceptions from health checks
        if isinstance(db_health, Exception):
            db_health = {"status": "unhealthy", "error": str(db_health)}
        if isinstance(redis_health, Exception):
            redis_health = {"status": "unhealthy", "error": str(redis_health)}
        if isinstance(celery_health, Exception):
            celery_health = {"status": "unhealthy", "error": str(celery_health)}
        
        # Determine overall status
        services = {
            "database": db_health["status"],
            "redis": redis_health["status"],
            "celery": celery_health["status"]
        }
        
        # Collect errors
        errors = []
        if db_health.get("error"):
            errors.append(db_health["error"])
        if redis_health.get("error"):
            errors.append(redis_health["error"])
        if celery_health.get("error"):
            errors.append(celery_health["error"])
        
        # Overall status is healthy only if all services are healthy
        overall_status = "healthy" if all(status == "healthy" for status in services.values()) else "unhealthy"
        
        # Calculate uptime
        uptime = time.time() - APP_START_TIME
        
        # Build response
        health_response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": self.settings.VERSION,
            "services": services,
            "uptime": round(uptime, 2)
        }
        
        # Add errors if any
        if errors:
            health_response["errors"] = errors
        
        # Add additional service info
        if celery_health.get("workers"):
            health_response["celery_workers"] = celery_health["workers"]
        
        return health_response


# Global health service instance
health_service = HealthService()


async def get_health_status() -> Dict:
    """
    Get the current health status of all services.
    
    Returns:
        Complete health status report
    """
    return await health_service.get_comprehensive_health() 