"""
Simplified pytest configuration for basic testing.
"""
import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def sample_data():
    """Provide sample test data."""
    return {
        "test_string": "hello world",
        "test_number": 42,
        "test_list": [1, 2, 3, 4, 5],
        "test_dict": {"key1": "value1", "key2": "value2"}
    }


class TestBase:
    """Base class for test cases with common utilities."""
    
    @staticmethod
    def assert_success(result, expected=True):
        """Assert that result is successful."""
        assert result == expected 