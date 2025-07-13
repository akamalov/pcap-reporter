"""
Simplified pytest configuration for basic testing.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """
    Mocks the get_settings function to return a test-specific Settings instance.
    This autouse fixture ensures that all application code gets the test settings.
    """
    test_settings = Settings(
        ALLOWED_HOSTS=["localhost", "127.0.0.1", "testserver"],
        BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"],
    )
    with patch('core.config.get_settings', return_value=test_settings) as _mock_get_settings:
        yield _mock_get_settings


@pytest.fixture(scope="function")
def sample_data():
    """Provide sample test data."""
    return {
        "test_string": "hello world",
        "test_number": 42,
        "test_list": [1, 2, 3, 4, 5],
        "test_dict": {"key1": "value1", "key2": "value2"}
    }


@pytest.fixture(scope="function")
async def mock_database():
    """Mock database for testing without requiring actual MongoDB."""
    with patch('core.database.init_db') as mock_init_db, \
         patch('core.database.get_database') as mock_get_db:
        
        # Mock the database initialization
        mock_init_db.return_value = None
        mock_get_db.return_value = MagicMock()
        
        # Mock Beanie document operations
        with patch('models.report.Report') as mock_report, \
             patch('models.analysis_job.AnalysisJob') as mock_job:
            
            # Setup mock report
            mock_report.insert = AsyncMock()
            mock_report.get = AsyncMock()
            mock_report.find_one = AsyncMock()
            mock_report.find = MagicMock()
            mock_report.find_by_status = AsyncMock(return_value=[])
            mock_report.find_recent = AsyncMock(return_value=[])
            mock_report.aggregate = MagicMock()
            
            # Setup mock job
            mock_job.insert = AsyncMock()
            mock_job.find_one = AsyncMock()
            mock_job.find = MagicMock()
            mock_job.update_many = AsyncMock()
            
            yield {
                'mock_init_db': mock_init_db,
                'mock_get_db': mock_get_db,
                'mock_report': mock_report,
                'mock_job': mock_job
            }


class TestBase:
    """Base class for test cases with common utilities."""
    
    @staticmethod
    def assert_success(result, expected=True):
        """Assert that result is successful."""
        assert result == expected 