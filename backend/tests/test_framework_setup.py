"""
Test to verify the testing framework setup is working correctly.
"""
import pytest
from fastapi.testclient import TestClient


def test_pytest_is_working():
    """Basic test to ensure pytest is configured correctly."""
    assert True


def test_async_support():
    """Test that async support is working."""
    import asyncio
    
    async def sample_async_function():
        await asyncio.sleep(0.01)
        return "async_working"
    
    # This should work with pytest-asyncio
    result = asyncio.run(sample_async_function())
    assert result == "async_working"


@pytest.mark.asyncio
async def test_async_marker():
    """Test that async markers work correctly."""
    import asyncio
    await asyncio.sleep(0.01)
    assert True


def test_imports_work():
    """Test that our main application imports work."""
    try:
        from main import app
        from core.config import get_settings
        from core.database import get_database
        assert app is not None
        assert get_settings is not None
        assert get_database is not None
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.unit
def test_unit_marker():
    """Test that unit test markers work."""
    assert True


@pytest.mark.integration
def test_integration_marker():
    """Test that integration test markers work."""
    assert True 