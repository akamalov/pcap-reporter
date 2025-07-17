#!/usr/bin/env python3
"""
Test suite for sync/async bridge functionality.
"""
import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch

from core.sync_async_bridge import AsyncBridge, DatabaseContext, TaskStateManager, run_async

class TestAsyncBridge:
    """Test the AsyncBridge class."""
    
    def test_bridge_initialization(self):
        """Test that AsyncBridge initializes correctly."""
        bridge = AsyncBridge(max_workers=2)
        assert bridge.max_workers == 2
        assert bridge.executor is not None
        bridge.shutdown()
    
    def test_run_simple_async_function(self):
        """Test running a simple async function."""
        bridge = AsyncBridge()
        
        async def simple_async():
            await asyncio.sleep(0.1)
            return "async_result"
        
        result = bridge.run(simple_async)
        assert result == "async_result"
        bridge.shutdown()
    
    def test_run_async_function_with_args(self):
        """Test running async function with arguments."""
        bridge = AsyncBridge()
        
        async def async_with_args(x, y, z=None):
            await asyncio.sleep(0.1)
            return f"{x}_{y}_{z}"
        
        result = bridge.run(async_with_args, "a", "b", z="c")
        assert result == "a_b_c"
        bridge.shutdown()
    
    def test_run_async_function_with_exception(self):
        """Test that exceptions are properly propagated."""
        bridge = AsyncBridge()
        
        async def failing_async():
            await asyncio.sleep(0.1)
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError, match="Test exception"):
            bridge.run(failing_async)
        
        bridge.shutdown()
    
    def test_multiple_concurrent_calls(self):
        """Test multiple concurrent calls to the bridge."""
        bridge = AsyncBridge(max_workers=3)
        
        async def async_task(task_id):
            await asyncio.sleep(0.1)
            return f"task_{task_id}"
        
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(bridge.run, async_task, i)
                for i in range(3)
            ]
            
            results = [f.result() for f in futures]
            
        assert len(results) == 3
        assert all(result.startswith("task_") for result in results)
        bridge.shutdown()


class TestDatabaseContext:
    """Test the DatabaseContext class."""
    
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    @patch('beanie.init_beanie')
    def test_database_context_initialization(self, mock_init_beanie, mock_client):
        """Test DatabaseContext initialization."""
        context = DatabaseContext()
        
        # Mock the database connection
        mock_client.return_value = Mock()
        mock_init_beanie.return_value = None
        
        with context.get_context() as ctx:
            assert ctx is not None
            assert hasattr(ctx, 'bridge')
    
    @patch('motor.motor_asyncio.AsyncIOMotorClient')
    @patch('beanie.init_beanie')
    def test_database_context_cleanup(self, mock_init_beanie, mock_client):
        """Test DatabaseContext cleanup."""
        context = DatabaseContext()
        
        # Mock the database connection
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_init_beanie.return_value = None
        
        with context.get_context():
            pass
        
        # Verify cleanup was called
        mock_client_instance.close.assert_called_once()


class TestTaskStateManager:
    """Test the TaskStateManager class."""
    
    def test_task_state_manager_initialization(self):
        """Test TaskStateManager initialization."""
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        mock_bridge = Mock()
        
        manager = TaskStateManager(mock_task, mock_bridge)
        assert manager.task_id == "test_task_id"
        assert manager.task_instance == mock_task
        assert manager.bridge == mock_bridge
    
    def test_update_progress_success(self):
        """Test successful progress update."""
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        mock_bridge = Mock()
        
        manager = TaskStateManager(mock_task, mock_bridge)
        manager.update_progress(50, "Test progress")
        
        mock_task.update_state.assert_called_once_with(
            state="PROGRESS",
            meta={
                "progress": 50,
                "message": "Test progress",
                "task_id": "test_task_id"
            }
        )
    
    def test_update_progress_with_exception(self):
        """Test progress update with exception."""
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        mock_task.update_state.side_effect = Exception("Update failed")
        mock_bridge = Mock()
        
        manager = TaskStateManager(mock_task, mock_bridge)
        # Should not raise exception
        manager.update_progress(50, "Test progress")
    
    def test_update_success(self):
        """Test success state update."""
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        mock_bridge = Mock()
        
        manager = TaskStateManager(mock_task, mock_bridge)
        result = {"status": "completed", "data": "test"}
        manager.update_success(result)
        
        mock_task.update_state.assert_called_once_with(
            state="SUCCESS",
            meta=result
        )
    
    def test_update_failure(self):
        """Test failure state update."""
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        mock_bridge = Mock()
        
        manager = TaskStateManager(mock_task, mock_bridge)
        manager.update_failure("Test error")
        
        mock_task.update_state.assert_called_once_with(
            state="FAILURE",
            meta={
                "error": "Test error",
                "task_id": "test_task_id"
            }
        )


class TestGlobalBridge:
    """Test global bridge functionality."""
    
    def test_get_global_bridge(self):
        """Test getting the global bridge."""
        from core.sync_async_bridge import get_global_bridge
        
        bridge1 = get_global_bridge()
        bridge2 = get_global_bridge()
        
        # Should return the same instance
        assert bridge1 is bridge2
        
        # Cleanup
        from core.sync_async_bridge import shutdown_global_bridge
        shutdown_global_bridge()
    
    def test_run_async_function(self):
        """Test run_async function."""
        async def test_async():
            await asyncio.sleep(0.1)
            return "test_result"
        
        result = run_async(test_async)
        assert result == "test_result"
        
        # Cleanup
        from core.sync_async_bridge import shutdown_global_bridge
        shutdown_global_bridge()
    
    def test_shutdown_global_bridge(self):
        """Test shutting down the global bridge."""
        from core.sync_async_bridge import get_global_bridge, shutdown_global_bridge
        
        bridge = get_global_bridge()
        assert bridge is not None
        
        shutdown_global_bridge()
        
        # Should create a new bridge after shutdown
        new_bridge = get_global_bridge()
        assert new_bridge is not bridge
        
        # Cleanup
        shutdown_global_bridge()


class TestEventLoopIsolation:
    """Test event loop isolation."""
    
    def test_event_loop_isolation(self):
        """Test that each bridge call gets its own event loop."""
        bridge = AsyncBridge()
        
        loop_ids = []
        
        async def get_loop_id():
            loop = asyncio.get_event_loop()
            loop_ids.append(id(loop))
            return id(loop)
        
        # Run multiple times
        for _ in range(3):
            bridge.run(get_loop_id)
        
        # Each call should have its own loop
        assert len(set(loop_ids)) == 3
        bridge.shutdown()
    
    def test_no_event_loop_conflicts(self):
        """Test that there are no event loop conflicts."""
        bridge = AsyncBridge()
        
        async def test_nested_async():
            # This should work without event loop conflicts
            await asyncio.sleep(0.1)
            
            # Test that we can create tasks
            task = asyncio.create_task(asyncio.sleep(0.1))
            await task
            
            return "success"
        
        result = bridge.run(test_nested_async)
        assert result == "success"
        bridge.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])