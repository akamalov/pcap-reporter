"""
Unit tests for health check endpoint.
Test-Driven Development approach - tests written first.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from datetime import datetime
import time

from main import app
from services.health_service import health_service


class TestHealthEndpoint:
    """Test cases for health check endpoint using TDD."""
    
    @pytest.mark.asyncio
    async def test_health_check_success_all_healthy(self):
        """Test successful health check when all services are healthy."""
        # Mock all health checks to return healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check required fields
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data
            assert "services" in data
            assert "uptime" in data
            
            # Check services
            assert data["services"]["database"] == "healthy"
            assert data["services"]["redis"] == "healthy"
            assert data["services"]["celery"] == "healthy"
            
            # Should not have errors when all healthy
            assert "errors" not in data
    
    @pytest.mark.asyncio
    async def test_health_check_database_unhealthy(self):
        """Test health check when database is unhealthy."""
        # Mock database as unhealthy, others healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "unhealthy", "error": "Database connection failed"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["redis"] == "healthy"
            assert data["services"]["celery"] == "healthy"
            
            # Should have errors
            assert "errors" in data
            assert "Database connection failed" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_health_check_redis_unhealthy(self):
        """Test health check when Redis is unhealthy."""
        # Mock Redis as unhealthy, others healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "unhealthy", "error": "Redis connection failed"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["redis"] == "unhealthy"
            assert data["services"]["celery"] == "healthy"
            
            # Should have errors
            assert "errors" in data
            assert "Redis connection failed" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_health_check_celery_unhealthy(self):
        """Test health check when Celery is unhealthy."""
        # Mock Celery as unhealthy, others healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "unhealthy", "error": "No active Celery workers"}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "healthy"
            assert data["services"]["redis"] == "healthy"
            assert data["services"]["celery"] == "unhealthy"
            
            # Should have errors
            assert "errors" in data
            assert "No active Celery workers" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_health_check_multiple_services_unhealthy(self):
        """Test health check when multiple services are unhealthy."""
        # Mock multiple services as unhealthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "unhealthy", "error": "Database connection failed"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "unhealthy", "error": "Redis connection failed"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Overall status should be unhealthy
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["redis"] == "unhealthy"
            assert data["services"]["celery"] == "healthy"
            
            # Should have multiple errors
            assert "errors" in data
            assert len(data["errors"]) == 2
            assert "Database connection failed" in data["errors"]
            assert "Redis connection failed" in data["errors"]
    
    @pytest.mark.asyncio
    async def test_health_check_response_structure(self):
        """Test that health check response has correct structure."""
        # Mock all services as healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check required fields
            required_fields = ["status", "timestamp", "version", "services", "uptime"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Check services structure
            assert "services" in data
            services = data["services"]
            required_services = ["database", "redis", "celery"]
            for service in required_services:
                assert service in services, f"Missing service: {service}"
            
            # Check status values
            assert data["status"] in ["healthy", "unhealthy"]
            for service_status in services.values():
                assert service_status in ["healthy", "unhealthy"]
            
            # Check data types
            assert isinstance(data["uptime"], (int, float))
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["version"], str)
    
    @pytest.mark.asyncio
    async def test_health_check_uptime_calculation(self):
        """Test uptime calculation in health check."""
        # Mock all services as healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Uptime should be a positive number
            assert "uptime" in data
            assert isinstance(data["uptime"], (int, float))
            assert data["uptime"] >= 0
    
    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self):
        """Test that timestamp is in correct ISO format."""
        # Mock all services as healthy
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check timestamp format
            assert "timestamp" in data
            timestamp_str = data["timestamp"]
            assert timestamp_str.endswith("Z")
            
            # Should be parseable as datetime
            try:
                datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                pytest.fail("Timestamp is not in valid ISO format")
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test that health check responds within acceptable time."""
        # Mock all services with slight delay
        async def mock_slow_check():
            await asyncio.sleep(0.1)  # 100ms delay
            return {"status": "healthy"}
        
        with patch.object(health_service, 'check_database_health', side_effect=mock_slow_check), \
             patch.object(health_service, 'check_redis_health', side_effect=mock_slow_check), \
             patch.object(health_service, 'check_celery_health', side_effect=mock_slow_check):
            
            start_time = time.time()
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
            end_time = time.time()
            
            assert response.status_code == 200
            
            # Health check should complete within 5 seconds
            response_time = end_time - start_time
            assert response_time < 5.0, f"Health check took {response_time:.2f} seconds, should be < 5.0"


class TestHealthService:
    """Test cases for health service components."""
    
    @pytest.mark.asyncio
    async def test_database_health_check_success(self):
        """Test successful database health check."""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client, \
             patch('asyncio.wait_for') as mock_wait_for:
            # Mock successful database connection
            mock_instance = MagicMock()
            mock_instance.admin.command = AsyncMock(return_value=True)
            mock_client.return_value = mock_instance
            mock_wait_for.return_value = True
            
            result = await health_service.check_database_health()
            
            assert result["status"] == "healthy"
            assert "error" not in result
    
    @pytest.mark.asyncio
    async def test_database_health_check_failure(self):
        """Test database health check failure."""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client, \
             patch('asyncio.wait_for') as mock_wait_for:
            # Mock database connection failure
            mock_instance = MagicMock()
            mock_instance.admin.command = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.return_value = mock_instance
            mock_wait_for.side_effect = Exception("Connection failed")
            
            result = await health_service.check_database_health()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_database_health_check_timeout(self):
        """Test database health check timeout."""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
            # Mock database connection timeout
            mock_instance = MagicMock()
            mock_instance.admin.command = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_client.return_value = mock_instance
            
            result = await health_service.check_database_health()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "timeout" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_redis_health_check_success(self):
        """Test successful Redis health check."""
        with patch('redis.asyncio.Redis.from_url') as mock_redis:
            # Mock successful Redis connection
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            mock_redis.return_value = mock_instance
            
            result = await health_service.check_redis_health()
            
            assert result["status"] == "healthy"
            assert "error" not in result
            
            # Verify client was closed
            mock_instance.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_health_check_failure(self):
        """Test Redis health check failure."""
        with patch('redis.asyncio.Redis.from_url') as mock_redis:
            # Mock Redis connection failure
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(side_effect=Exception("Connection failed"))
            mock_instance.close = AsyncMock()
            mock_redis.return_value = mock_instance
            
            result = await health_service.check_redis_health()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_celery_health_check_success(self):
        """Test successful Celery health check."""
        with patch('celery.Celery') as mock_celery:
            # Mock successful Celery connection
            mock_instance = MagicMock()
            mock_inspect = MagicMock()
            mock_inspect.active = MagicMock(return_value={"worker1": []})
            mock_instance.control.inspect.return_value = mock_inspect
            mock_celery.return_value = mock_instance
            
            with patch('asyncio.to_thread', return_value={"worker1": []}):
                result = await health_service.check_celery_health()
            
            assert result["status"] == "healthy"
            assert "error" not in result
            assert result["workers"] == 1
    
    @pytest.mark.asyncio
    async def test_celery_health_check_no_workers(self):
        """Test Celery health check with no workers."""
        with patch('celery.Celery') as mock_celery:
            # Mock no active workers
            mock_instance = MagicMock()
            mock_inspect = MagicMock()
            mock_inspect.active = MagicMock(return_value=None)
            mock_instance.control.inspect.return_value = mock_inspect
            mock_celery.return_value = mock_instance
            
            with patch('asyncio.to_thread', return_value=None):
                result = await health_service.check_celery_health()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "No active Celery workers" in result["error"]
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_all_healthy(self):
        """Test comprehensive health check when all services are healthy."""
        with patch.object(health_service, 'check_database_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "healthy", "workers": 2}):
            
            result = await health_service.get_comprehensive_health()
            
            assert result["status"] == "healthy"
            assert result["services"]["database"] == "healthy"
            assert result["services"]["redis"] == "healthy"
            assert result["services"]["celery"] == "healthy"
            assert "errors" not in result
            assert "celery_workers" in result
            assert result["celery_workers"] == 2
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_with_errors(self):
        """Test comprehensive health check when services have errors."""
        with patch.object(health_service, 'check_database_health', return_value={"status": "unhealthy", "error": "DB error"}), \
             patch.object(health_service, 'check_redis_health', return_value={"status": "healthy"}), \
             patch.object(health_service, 'check_celery_health', return_value={"status": "unhealthy", "error": "Celery error"}):
            
            result = await health_service.get_comprehensive_health()
            
            assert result["status"] == "unhealthy"
            assert result["services"]["database"] == "unhealthy"
            assert result["services"]["redis"] == "healthy"
            assert result["services"]["celery"] == "unhealthy"
            assert "errors" in result
            assert len(result["errors"]) == 2
            assert "DB error" in result["errors"]
            assert "Celery error" in result["errors"] 