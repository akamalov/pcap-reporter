"""
Database module for MongoDB connection and Beanie ODM setup.
"""

import motor.motor_asyncio
from beanie import init_beanie
from typing import Optional
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# Global database client
_database_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_database: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None


async def get_database_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Get the MongoDB client instance.
    """
    global _database_client
    
    if _database_client is None:
        logger.info(f"Connecting to MongoDB at {settings.DATABASE_URL}")
        _database_client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.DATABASE_URL,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )
        
        # Test the connection
        try:
            await _database_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    return _database_client


async def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """
    Get the MongoDB database instance.
    """
    global _database
    
    if _database is None:
        client = await get_database_client()
        # Extract database name from URL
        db_name = settings.DATABASE_URL.split('/')[-1]
        _database = client[db_name]
        logger.info(f"Connected to database: {db_name}")
    
    return _database


async def init_db():
    """
    Initialize the database and Beanie ODM.
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
        
        logger.info("Database and Beanie ODM initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """
    Close the database connection.
    """
    global _database_client, _database
    
    if _database_client:
        _database_client.close()
        _database_client = None
        _database = None
        logger.info("Database connection closed") 