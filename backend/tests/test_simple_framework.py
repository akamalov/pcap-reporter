"""
Simple test to verify pytest framework is working without complex imports.
"""
import pytest


def test_pytest_basic():
    """Basic test to ensure pytest is working."""
    assert True


def test_basic_math():
    """Test basic math operations."""
    assert 2 + 2 == 4
    assert 5 * 3 == 15


@pytest.mark.asyncio
async def test_async_basic():
    """Test async functionality."""
    import asyncio
    await asyncio.sleep(0.001)
    assert True


@pytest.mark.unit
def test_unit_marker():
    """Test unit marker."""
    assert True


@pytest.mark.integration  
def test_integration_marker():
    """Test integration marker."""
    assert True


class TestBasicClass:
    """Test class structure."""
    
    def test_class_method(self):
        """Test method in class."""
        assert True
    
    @pytest.mark.asyncio
    async def test_async_class_method(self):
        """Test async method in class."""
        assert True 