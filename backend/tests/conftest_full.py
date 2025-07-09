"""
Pytest configuration and shared fixtures for backend testing.
"""
import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

# Import our app and dependencies
from main import app
from core.config import get_settings
from core.database import get_database


class TestSettings:
    """Test-specific configuration settings."""
    
    def __init__(self):
        self.mongodb_url = os.getenv("TEST_MONGODB_URL", "mongodb://localhost:27017")
        self.mongodb_db_name = "pcap_reporter_test"
        self.redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")
        self.secret_key = "test-secret-key-not-for-production"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Provide test configuration settings."""
    return TestSettings()


@pytest.fixture(scope="session")
async def test_mongodb_client(test_settings: TestSettings) -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create a test MongoDB client."""
    client = AsyncIOMotorClient(test_settings.mongodb_url)
    yield client
    # Cleanup: Drop test database
    await client.drop_database(test_settings.mongodb_db_name)
    client.close()


@pytest.fixture(scope="session")
async def test_database(test_mongodb_client: AsyncIOMotorClient, test_settings: TestSettings):
    """Provide test database instance."""
    return test_mongodb_client[test_settings.mongodb_db_name]


@pytest.fixture(scope="session")
async def test_redis_client(test_settings: TestSettings) -> AsyncGenerator[Redis, None]:
    """Create a test Redis client."""
    redis_client = Redis.from_url(test_settings.redis_url)
    yield redis_client
    # Cleanup: Flush test Redis database
    await redis_client.flushdb()
    await redis_client.close()


@pytest.fixture(scope="function")
async def clean_database(test_database):
    """Clean database before each test function."""
    # Drop all collections before each test
    collections = await test_database.list_collection_names()
    for collection_name in collections:
        await test_database.drop_collection(collection_name)
    yield test_database


@pytest.fixture(scope="function")
async def clean_redis(test_redis_client: Redis):
    """Clean Redis before each test function."""
    await test_redis_client.flushdb()
    yield test_redis_client


@pytest.fixture(scope="function")
def override_get_settings(test_settings: TestSettings):
    """Override application settings for testing."""
    def _override_get_settings():
        return test_settings
    
    app.dependency_overrides[get_settings] = _override_get_settings
    yield test_settings
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def override_get_database(clean_database):
    """Override database dependency for testing."""
    def _override_get_database():
        return clean_database
    
    app.dependency_overrides[get_database] = _override_get_database
    yield clean_database
    # Cleanup
    if get_database in app.dependency_overrides:
        del app.dependency_overrides[get_database]


@pytest.fixture(scope="function")
def test_client(override_get_settings, override_get_database) -> Generator[TestClient, None, None]:
    """Create a test client for synchronous testing."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
async def async_test_client(override_get_settings, override_get_database) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for asynchronous testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def sample_pcap_file_path():
    """Provide path to a sample PCAP file for testing."""
    # This would be a small test PCAP file
    return "tests/fixtures/sample.pcap"


@pytest.fixture(scope="function")
def sample_analysis_job_data():
    """Provide sample analysis job data for testing."""
    return {
        "filename": "test.pcap",
        "file_size": 1024,
        "upload_timestamp": "2024-01-01T00:00:00Z",
        "analysis_type": "full",
        "priority": "normal"
    }


@pytest.fixture(scope="function")
def sample_report_data():
    """Provide sample report data for testing."""
    return {
        "job_id": "test-job-123",
        "filename": "test.pcap",
        "analysis_summary": {
            "total_packets": 100,
            "protocols": ["TCP", "UDP", "HTTP"],
            "duration": 60.0
        },
        "security_findings": [],
        "performance_metrics": {
            "processing_time": 5.2,
            "memory_usage": 128
        }
    }


# Pytest markers for different test types
pytestmark = [
    pytest.mark.asyncio,
]


class TestBase:
    """Base class for test cases with common utilities."""
    
    @staticmethod
    def assert_response_success(response, expected_status: int = 200):
        """Assert that response is successful with expected status."""
        assert response.status_code == expected_status
        assert response.headers["content-type"] == "application/json"
    
    @staticmethod
    def assert_response_error(response, expected_status: int = 400):
        """Assert that response contains an error with expected status."""
        assert response.status_code == expected_status
        data = response.json()
        assert "detail" in data or "error" in data 