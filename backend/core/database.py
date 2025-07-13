"""
Database module for MongoDB connection and Beanie ODM setup with resilience features.
"""

import motor.motor_asyncio
from beanie import init_beanie
from typing import Optional
import logging
import asyncio
from contextlib import asynccontextmanager
from functools import wraps
import time

from core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Global database client
_database_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_database: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
_connection_status = {"connected": False, "last_check": 0, "retry_count": 0}

# Connection retry settings
MAX_RETRIES = 5
RETRY_DELAY = 2.0  # seconds
HEALTH_CHECK_INTERVAL = 30  # seconds


async def get_database_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Get the MongoDB client instance with connection resilience.
    """
    global _database_client, _connection_status
    
    if _database_client is None or not _connection_status["connected"]:
        await _connect_with_retry()
    
    return _database_client


async def _connect_with_retry():
    """
    Connect to MongoDB with retry logic.
    """
    global _database_client, _connection_status
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{MAX_RETRIES})")
            
            # Create new client with optimized settings
            _database_client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.DATABASE_URL,
                maxPoolSize=20,
                minPoolSize=5,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxIdleTimeMS=60000,
                waitQueueTimeoutMS=10000,
                retryWrites=True,
                retryReads=True
            )
            
            # Test the connection
            await _database_client.admin.command('ping')
            
            _connection_status.update({
                "connected": True,
                "last_check": time.time(),
                "retry_count": 0
            })
            
            logger.info("Successfully connected to MongoDB")
            return
            
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            _connection_status["retry_count"] = attempt + 1
            
            if _database_client:
                _database_client.close()
                _database_client = None
            
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                _connection_status["connected"] = False
                logger.error(f"Failed to connect to MongoDB after {MAX_RETRIES} attempts")
                raise ConnectionError(f"Could not connect to MongoDB: {e}")


async def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """
    Get the MongoDB database instance with health checking.
    """
    global _database
    
    if _database is None or not _connection_status["connected"]:
        client = await get_database_client()
        # Extract database name from URL - handle auth parameters
        url_parts = settings.DATABASE_URL.split('/')
        db_name = url_parts[-1].split('?')[0]  # Remove query parameters
        _database = client[db_name]
        logger.info(f"Connected to database: {db_name}")
    
    # Periodic health check
    current_time = time.time()
    if current_time - _connection_status["last_check"] > HEALTH_CHECK_INTERVAL:
        await _health_check()
    
    return _database


async def _health_check():
    """
    Perform a health check on the database connection.
    """
    global _connection_status
    
    try:
        if _database_client:
            await _database_client.admin.command('ping')
            _connection_status.update({
                "connected": True,
                "last_check": time.time()
            })
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        _connection_status["connected"] = False
        # Will trigger reconnection on next request


def with_db_retry(max_retries: int = 3):
    """
    Decorator to retry database operations on connection failures.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
                        if attempt < max_retries - 1:
                            # Force reconnection
                            global _connection_status
                            _connection_status["connected"] = False
                            await asyncio.sleep(1)
                            continue
                    raise
            return None
        return wrapper
    return decorator


@asynccontextmanager
async def database_transaction():
    """
    Context manager for database transactions with automatic retry.
    """
    client = await get_database_client()
    session = await client.start_session()
    
    try:
        async with session.start_transaction():
            yield session
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        raise
    finally:
        await session.end_session()


@with_db_retry(max_retries=3)
async def init_db():
    """
    Initialize the database and Beanie ODM with retry logic.
    """
    try:
        # Get database instance
        database = await get_database()
        
        # Import all models here
        from models.report import Report
        from models.analysis_job import AnalysisJob
        from models.user import User
        
        # Initialize Beanie with the models
        await init_beanie(
            database=database,
            document_models=[
                Report,
                AnalysisJob,
                User,
            ]
        )
        
        # Create indexes if they don't exist
        await _ensure_indexes()
        
        logger.info("Database and Beanie ODM initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def _ensure_indexes():
    """
    Ensure all required indexes exist for optimal performance.
    """
    try:
        database = await get_database()
        
        # Reports collection indexes
        reports_collection = database.get_collection("reports")
        
        # Check if indexes exist before creating
        existing_indexes = await reports_collection.list_indexes().to_list(None)
        index_names = [idx["name"] for idx in existing_indexes]
        
        # Create missing indexes
        if "status_created_at_idx" not in index_names:
            await reports_collection.create_index(
                [("status", 1), ("created_at", -1)],
                name="status_created_at_idx"
            )
        
        if "file_hash_idx" not in index_names:
            await reports_collection.create_index(
                "file_hash",
                name="file_hash_idx",
                sparse=True
            )
        
        logger.info("Database indexes verified/created")
        
    except Exception as e:
        logger.warning(f"Failed to ensure indexes: {e}")
        # Don't fail initialization if index creation fails


async def close_db():
    """
    Close the database connection.
    """
    global _database_client, _database, _connection_status
    
    if _database_client:
        _database_client.close()
        _database_client = None
        _database = None
        _connection_status.update({
            "connected": False,
            "last_check": 0,
            "retry_count": 0
        })
        logger.info("Database connection closed")


async def get_connection_status() -> dict:
    """
    Get the current database connection status.
    """
    return {
        "connected": _connection_status["connected"],
        "last_check": _connection_status["last_check"],
        "retry_count": _connection_status["retry_count"],
        "client_available": _database_client is not None
    }


async def wait_for_database(timeout: int = 60):
    """
    Wait for database to become available.

    Args:
        timeout: Maximum time to wait in seconds
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            await get_database_client()
            logger.info("Database is ready")
            return
        except Exception as e:
            logger.info(f"Waiting for database... ({e})")
            await asyncio.sleep(2)
    
    raise TimeoutError(f"Database not available after {timeout} seconds")