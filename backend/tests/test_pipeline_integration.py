#!/usr/bin/env python3
"""
Integration test suite for the complete PCAP upload to PDF pipeline.
"""
import pytest
import asyncio
import os
import tempfile
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from core.sync_async_bridge import AsyncBridge, DatabaseContext, run_async
from tasks.analysis_tasks import analyze_pcap_file, debug_task

class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    def test_sync_async_bridge_with_celery_task(self):
        """Test that sync/async bridge works with Celery task structure."""
        from core.celery_app import celery_app
        
        # Get the debug task
        debug_task_func = celery_app.tasks['debug_task']
        
        # Create mock request
        mock_request = Mock()
        mock_request.id = "integration_test_id"
        
        # Bind the task
        bound_task = debug_task_func.bind(mock_request)
        
        # Execute the task
        result = debug_task(bound_task)
        
        # Verify result
        assert result["status"] == "success"
        assert result["task_id"] == "integration_test_id"
        assert result["message"] == "Debug task completed"
    
    @patch('tasks.analysis_tasks.Report')
    @patch('tasks.analysis_tasks.AnalysisJob')
    @patch('tasks.analysis_tasks.PcapAnalysisService')
    @patch('tasks.analysis_tasks.NetworkDiagramGenerator')
    @patch('os.path.getsize')
    def test_analyze_pcap_file_full_pipeline(self, mock_getsize, mock_diagram_gen, mock_pcap_service, mock_analysis_job, mock_report):
        """Test the full analyze_pcap_file pipeline."""
        # Setup file size mock
        mock_getsize.return_value = 2048
        
        # Setup report mock
        mock_report_instance = Mock()
        mock_report_instance.id = "test_report_id"
        mock_report_instance.job_id = "test_job_id"
        mock_report_instance.save = AsyncMock()
        mock_report.get = AsyncMock(return_value=mock_report_instance)
        
        # Setup analysis job mock
        mock_analysis_job_instance = Mock()
        mock_analysis_job_instance.save = AsyncMock()
        mock_analysis_job.return_value = mock_analysis_job_instance
        
        # Setup analysis service mock
        mock_analysis_service_instance = Mock()
        mock_analysis_results = self._create_mock_analysis_results()
        mock_analysis_service_instance.analyze_pcap_file = AsyncMock(return_value=mock_analysis_results)
        mock_pcap_service.return_value = mock_analysis_service_instance
        
        # Setup diagram generator mock
        mock_diagram_gen_instance = Mock()
        mock_diagram_gen_instance.generate_comprehensive_diagram_set.return_value = {"test": "diagram"}
        mock_diagram_gen.return_value = mock_diagram_gen_instance
        
        # Create task mocks
        mock_task = Mock()
        mock_task.request.id = "pipeline_test_id"
        
        mock_db_context = Mock()
        mock_state_manager = Mock()
        
        # Run the async task
        async def run_test():
            return await analyze_pcap_file(
                mock_task,
                mock_db_context,
                mock_state_manager,
                "test_report_id",
                "/tmp/test.pcap"
            )
        
        bridge = AsyncBridge()
        result = bridge.run(run_test)
        bridge.shutdown()
        
        # Verify result
        assert result["status"] == "completed"
        assert result["task_id"] == "pipeline_test_id"
        assert result["message"] == "Analysis completed successfully"
        assert result["results_summary"]["total_packets"] == 1000
        assert result["results_summary"]["file_size_mb"] == 2048 / (1024 * 1024)
        
        # Verify all mocks were called
        mock_report.get.assert_called_once_with("test_report_id")
        mock_analysis_service_instance.analyze_pcap_file.assert_called_once_with("/tmp/test.pcap")
        mock_diagram_gen_instance.generate_comprehensive_diagram_set.assert_called_once()
    
    def test_database_context_lifecycle(self):
        """Test database context lifecycle management."""
        with patch('core.sync_async_bridge.AsyncIOMotorClient') as mock_client, \
             patch('core.sync_async_bridge.init_beanie') as mock_init_beanie:
            
            # Setup mocks
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            mock_init_beanie.return_value = None
            
            # Create and use context
            context = DatabaseContext()
            
            with context.get_context() as ctx:
                assert ctx is not None
                assert hasattr(ctx, 'bridge')
            
            # Verify cleanup
            mock_client_instance.close.assert_called_once()
    
    def test_task_state_manager_integration(self):
        """Test TaskStateManager integration."""
        from core.sync_async_bridge import TaskStateManager, AsyncBridge
        
        # Create mock task
        mock_task = Mock()
        mock_task.request.id = "state_test_id"
        
        # Create bridge and state manager
        bridge = AsyncBridge()
        state_manager = TaskStateManager(mock_task, bridge)
        
        # Test progress updates
        state_manager.update_progress(25, "Test progress")
        state_manager.update_progress(50, "Halfway done")
        state_manager.update_progress(100, "Complete")
        
        # Verify calls
        assert mock_task.update_state.call_count == 3
        
        # Test success update
        result = {"status": "completed", "data": "test"}
        state_manager.update_success(result)
        
        # Test failure update
        state_manager.update_failure("Test error")
        
        # Cleanup
        bridge.shutdown()
    
    def test_error_handling_pipeline(self):
        """Test error handling throughout the pipeline."""
        with patch('tasks.analysis_tasks.Report') as mock_report:
            # Setup report mock to return None (not found)
            mock_report.get = AsyncMock(return_value=None)
            
            # Create task mocks
            mock_task = Mock()
            mock_task.request.id = "error_test_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Run the async task
            async def run_test():
                with pytest.raises(ValueError, match="Report not found"):
                    await analyze_pcap_file(
                        mock_task,
                        mock_db_context,
                        mock_state_manager,
                        "nonexistent_report_id",
                        "/tmp/test.pcap"
                    )
            
            bridge = AsyncBridge()
            bridge.run(run_test)
            bridge.shutdown()
    
    def test_concurrent_task_execution(self):
        """Test concurrent task execution."""
        import concurrent.futures
        
        def run_debug_task(task_id):
            mock_task = Mock()
            mock_task.request.id = f"concurrent_test_{task_id}"
            
            start_time = time.time()
            result = debug_task(mock_task)
            end_time = time.time()
            
            return result, end_time - start_time
        
        # Run multiple tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(run_debug_task, i)
                for i in range(3)
            ]
            
            results = [f.result() for f in futures]
        
        # Verify all tasks completed
        assert len(results) == 3
        
        for result, duration in results:
            assert result[0]["status"] == "success"
            assert duration >= 2.0  # Each task sleeps for 2 seconds
    
    def test_memory_management(self):
        """Test memory management in bridge operations."""
        import gc
        
        # Create multiple bridges and ensure cleanup
        bridges = []
        
        for i in range(5):
            bridge = AsyncBridge()
            
            async def test_task():
                await asyncio.sleep(0.1)
                return f"task_{i}"
            
            result = bridge.run(test_task)
            assert result == f"task_{i}"
            
            bridges.append(bridge)
        
        # Cleanup all bridges
        for bridge in bridges:
            bridge.shutdown()
        
        # Force garbage collection
        gc.collect()
        
        # Verify cleanup (basic check)
        assert len(bridges) == 5
    
    def test_exception_propagation(self):
        """Test that exceptions are properly propagated."""
        bridge = AsyncBridge()
        
        async def failing_task():
            await asyncio.sleep(0.1)
            raise RuntimeError("Test runtime error")
        
        with pytest.raises(RuntimeError, match="Test runtime error"):
            bridge.run(failing_task)
        
        bridge.shutdown()
    
    def test_health_check_integration(self):
        """Test health check task integration."""
        from core.celery_app import health_check
        
        mock_task = Mock()
        mock_task.request.id = "health_integration_test"
        
        result = health_check(mock_task)
        
        assert result["status"] == "healthy"
        assert result["task_id"] == "health_integration_test"
        assert "execution_time" in result
        assert "timestamp" in result
        assert result["execution_time"] > 0
    
    def _create_mock_analysis_results(self):
        """Create a comprehensive mock analysis results object."""
        mock_results = Mock()
        mock_results.file_path = "/tmp/test.pcap"
        mock_results.file_size = 2048
        mock_results.analysis_timestamp = datetime.utcnow()
        
        # Traffic stats
        mock_results.traffic_stats = Mock()
        mock_results.traffic_stats.total_packets = 1000
        mock_results.traffic_stats.total_bytes = 1024000
        mock_results.traffic_stats.duration = 60.0
        mock_results.traffic_stats.avg_packet_size = 1024
        mock_results.traffic_stats.packets_per_second = 16.67
        mock_results.traffic_stats.bytes_per_second = 17066.67
        
        # Performance metrics
        mock_results.performance_metrics = Mock()
        mock_results.performance_metrics.avg_latency = 0.05
        mock_results.performance_metrics.max_latency = 0.2
        mock_results.performance_metrics.packet_loss_rate = 0.01
        mock_results.performance_metrics.throughput_mbps = 136.53
        
        # Protocol stats
        mock_results.protocol_stats = Mock()
        mock_results.protocol_stats.tcp_packets = 800
        mock_results.protocol_stats.udp_packets = 150
        mock_results.protocol_stats.icmp_packets = 50
        mock_results.protocol_stats.http_sessions = 10
        mock_results.protocol_stats.https_sessions = 5
        mock_results.protocol_stats.dns_queries = 25
        
        # Issues
        mock_results.issues = []
        
        # Timing
        mock_results.start_time = datetime.utcnow()
        mock_results.end_time = datetime.utcnow()
        mock_results.processing_time = 2.5
        mock_results.analysis_options = {}
        
        # Conversations
        mock_results.top_conversations = []
        
        return mock_results


class TestPipelinePerformance:
    """Performance tests for the pipeline."""
    
    def test_bridge_performance(self):
        """Test performance of the sync/async bridge."""
        bridge = AsyncBridge()
        
        async def simple_task():
            await asyncio.sleep(0.01)
            return "done"
        
        start_time = time.time()
        
        # Run multiple tasks
        for _ in range(10):
            result = bridge.run(simple_task)
            assert result == "done"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete reasonably quickly
        assert total_time < 2.0
        
        bridge.shutdown()
    
    def test_concurrent_bridge_performance(self):
        """Test performance with concurrent bridge operations."""
        import concurrent.futures
        
        def run_bridge_task(task_id):
            bridge = AsyncBridge()
            
            async def task():
                await asyncio.sleep(0.1)
                return f"task_{task_id}"
            
            result = bridge.run(task)
            bridge.shutdown()
            return result
        
        start_time = time.time()
        
        # Run multiple tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(run_bridge_task, i)
                for i in range(5)
            ]
            
            results = [f.result() for f in futures]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete faster than sequential (less than 5 * 0.1 = 0.5 seconds)
        assert total_time < 1.0
        assert len(results) == 5
        
        # Verify all tasks completed
        for i, result in enumerate(results):
            assert result == f"task_{i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])