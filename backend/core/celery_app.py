"""
Celery application configuration for PCAP Reporter.
ROBUST version with simplified worker initialization.
"""

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
import logging
import atexit

from core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "pcap_reporter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.analysis_tasks"],
)

# Worker process initialization - simplified
@worker_process_init.connect
def init_worker_process(**kwargs):
    """
    Initialize worker process.
    Simplified version that doesn't pre-initialize async components.
    """
    logger.info("🔧 Worker process initialized")
    logger.info("✅ Worker ready for task processing")

# Worker process shutdown
@worker_process_shutdown.connect
def shutdown_worker_process(**kwargs):
    """
    Clean shutdown of worker process.
    """
    logger.info("🔧 Worker process shutting down")
    
    # Cleanup global bridge if it exists
    try:
        from core.sync_async_bridge import shutdown_global_bridge
        shutdown_global_bridge()
        logger.info("✅ Global bridge cleaned up")
    except Exception as e:
        logger.warning(f"Error cleaning up global bridge: {e}")
    
    logger.info("✅ Worker process shutdown complete")

# Register cleanup on exit
atexit.register(shutdown_worker_process)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=True,
    
    # Task routing
    task_routes={
        "tasks.analysis_tasks.*": {"queue": "analysis"},
    },
    
    # Task annotations
    task_annotations={
        "tasks.analysis_tasks.analyze_pcap_file": {
            "rate_limit": "10/m",
            "time_limit": settings.ANALYSIS_TIMEOUT,
            "soft_time_limit": settings.ANALYSIS_TIMEOUT - 30,
        },
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        "cleanup-old-reports": {
            "task": "tasks.analysis_tasks.cleanup_old_reports",
            "schedule": 3600.0,  # Every hour
            "args": [30],  # Clean reports older than 30 days
        },
    },
)

@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """
    Health check task for monitoring.
    """
    task_id = self.request.id
    logger.info(f"Health check task {task_id}")
    
    try:
        # Test basic functionality
        import time
        start_time = time.time()
        
        # Simple operations
        time.sleep(0.1)
        
        end_time = time.time()
        
        return {
            "status": "healthy",
            "task_id": task_id,
            "execution_time": end_time - start_time,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "task_id": task_id,
            "error": str(e),
            "timestamp": time.time()
        }

# Configure logging for Celery
if not celery_app.conf.worker_hijack_root_logger:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )