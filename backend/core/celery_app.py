"""
Celery application configuration for MCP PCAP Reporter.
"""

from celery import Celery
import logging

from core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "pcap_reporter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["services.analysis_tasks"],
)

# Optional configuration
celery_app.conf.update(
    task_track_started=True,
)

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
        # "tasks.report_tasks.*": {"queue": "reports"},  # TODO: Uncomment when module exists
    },
    
    # Task annotations
    task_annotations={
        "tasks.analysis_tasks.analyze_pcap_file": {
            "rate_limit": "10/m",
            "time_limit": settings.ANALYSIS_TIMEOUT,
            "soft_time_limit": settings.ANALYSIS_TIMEOUT - 30,
        },
        # "tasks.report_tasks.generate_pdf_report": {  # TODO: Uncomment when module exists
        #     "rate_limit": "20/m",
        #     "time_limit": 120,
        # },
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        # "cleanup-old-reports": {  # TODO: Uncomment when maintenance_tasks module exists
        #     "task": "tasks.maintenance_tasks.cleanup_old_reports",
        #     "schedule": 3600.0,  # Every hour
        # },
        # "health-check": {  # TODO: Uncomment when maintenance_tasks module exists
        #     "task": "tasks.maintenance_tasks.health_check",
        #     "schedule": 300.0,  # Every 5 minutes
        # },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """
    Debug task for testing Celery functionality.
    """
    logger.info(f"Request: {self.request!r}")
    return {"status": "success", "message": "Debug task completed"}


# Configure logging for Celery
if not celery_app.conf.worker_hijack_root_logger:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ) 