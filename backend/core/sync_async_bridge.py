"""
Sync/Async Bridge for Celery Tasks
This module provides a robust bridge between synchronous Celery tasks and asynchronous database operations.
"""

import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AsyncBridge:
    """
    A robust bridge for running async functions in sync Celery tasks.
    Uses isolated thread pools and proper event loop management.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._thread_local = threading.local()
        
    def run(self, coro: Callable[..., T], *args, **kwargs) -> T:
        """
        Run an async coroutine in a synchronous context.
        
        Args:
            coro: The async function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the async function
        """
        def run_in_thread():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the coroutine
                if asyncio.iscoroutinefunction(coro):
                    return loop.run_until_complete(coro(*args, **kwargs))
                else:
                    return loop.run_until_complete(coro)
            finally:
                # Clean up the event loop
                try:
                    loop.close()
                except:
                    pass
        
        # Run in a separate thread to avoid event loop conflicts
        future = self.executor.submit(run_in_thread)
        return future.result()
    
    def shutdown(self):
        """Shutdown the thread pool executor."""
        self.executor.shutdown(wait=True)


class DatabaseContext:
    """
    Manages database context for Celery tasks with proper lifecycle management.
    """
    
    def __init__(self):
        self.bridge = AsyncBridge()
        self._initialized = False
        
    async def _init_database(self):
        """Initialize database connection and models."""
        import sys
        import os
        # Add the app directory to the Python path
        sys.path.insert(0, '/app')
        
        from motor.motor_asyncio import AsyncIOMotorClient
        from beanie import init_beanie
        from core.config import get_settings
        from models.report import Report, ReportStatus
        from models.analysis_job import AnalysisJob, JobStatus
        
        settings = get_settings()
        
        # Create database connection
        self.client = AsyncIOMotorClient(settings.DATABASE_URL)
        database_name = settings.DATABASE_URL.split('/')[-1].split('?')[0]
        self.database = self.client[database_name]
        
        # Initialize Beanie
        await init_beanie(
            database=self.database,
            document_models=[Report, AnalysisJob]
        )
        
        logger.info("Database context initialized successfully")
        
    def initialize(self):
        """Initialize database context synchronously."""
        if not self._initialized:
            self.bridge.run(self._init_database)
            self._initialized = True
            
    async def _cleanup_database(self):
        """Clean up database connections."""
        if hasattr(self, 'client'):
            self.client.close()
            
    def cleanup(self):
        """Clean up database context synchronously."""
        if self._initialized:
            self.bridge.run(self._cleanup_database)
            self.bridge.shutdown()
            self._initialized = False
            
    @contextmanager
    def get_context(self):
        """Context manager for database operations."""
        self.initialize()
        try:
            yield self
        finally:
            self.cleanup()


class TaskStateManager:
    """
    Manages Celery task state updates with proper error handling.
    """
    
    def __init__(self, task_instance, bridge: AsyncBridge):
        self.task_instance = task_instance
        self.bridge = bridge
        self.task_id = task_instance.request.id
        
    def update_progress(self, progress: int, message: str, **meta):
        """Update task progress safely."""
        try:
            self.task_instance.update_state(
                state="PROGRESS",
                meta={
                    "progress": progress,
                    "message": message,
                    "task_id": self.task_id,
                    **meta
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update task progress: {e}")
            
    def update_success(self, result: Dict[str, Any]):
        """Update task success state."""
        try:
            self.task_instance.update_state(
                state="SUCCESS",
                meta=result
            )
        except Exception as e:
            logger.warning(f"Failed to update task success: {e}")
            
    def update_failure(self, error: str, **meta):
        """Update task failure state."""
        try:
            self.task_instance.update_state(
                state="FAILURE",
                meta={
                    "error": error,
                    "task_id": self.task_id,
                    **meta
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update task failure: {e}")


def celery_async_task(func: Callable) -> Callable:
    """
    Decorator to convert async functions to sync Celery tasks.
    Provides proper event loop management and error handling.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        task_id = self.request.id
        logger.info(f"Starting async task {func.__name__} [{task_id}]")
        
        # Create database context and task state manager
        with DatabaseContext().get_context() as db_context:
            state_manager = TaskStateManager(self, db_context.bridge)
            
            try:
                # Run the async function with proper context
                result = db_context.bridge.run(
                    func, 
                    self, 
                    db_context, 
                    state_manager, 
                    *args, 
                    **kwargs
                )
                
                # Update success state
                state_manager.update_success(result)
                logger.info(f"Task {func.__name__} [{task_id}] completed successfully")
                return result
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Task {func.__name__} [{task_id}] failed: {error_msg}")
                
                # Update failure state
                state_manager.update_failure(error_msg)
                raise
                
    return wrapper


# Global bridge instance for simple usage
_global_bridge = None

def get_global_bridge() -> AsyncBridge:
    """Get or create the global async bridge."""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = AsyncBridge()
    return _global_bridge

def run_async(coro: Callable[..., T], *args, **kwargs) -> T:
    """
    Simple function to run async code in sync context.
    
    Args:
        coro: The async function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        The result of the async function
    """
    bridge = get_global_bridge()
    return bridge.run(coro, *args, **kwargs)

def shutdown_global_bridge():
    """Shutdown the global bridge."""
    global _global_bridge
    if _global_bridge:
        _global_bridge.shutdown()
        _global_bridge = None