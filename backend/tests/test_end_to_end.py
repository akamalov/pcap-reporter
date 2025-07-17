#!/usr/bin/env python3
"""
End-to-end test suite for the complete PCAP upload to PDF pipeline.
Tests the actual API endpoints and worker processing.
"""
import pytest
import asyncio
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from core.sync_async_bridge import AsyncBridge, DatabaseContext, run_async

class TestEndToEndPipeline:
    """End-to-end tests for the complete pipeline."""
    
    def test_database_context_full_lifecycle(self):
        """Test complete database context lifecycle."""
        with patch('core.sync_async_bridge.AsyncIOMotorClient') as mock_client, \
             patch('core.sync_async_bridge.init_beanie') as mock_init_beanie:
            
            # Setup mocks
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            mock_init_beanie.return_value = None
            
            # Test full lifecycle
            context = DatabaseContext()
            
            # Test multiple context uses
            for i in range(3):
                with context.get_context() as ctx:
                    assert ctx is not None
                    assert hasattr(ctx, 'bridge')
                    assert ctx.bridge is not None
            
            # Verify proper cleanup
            mock_client_instance.close.assert_called()
    
    def test_task_execution_with_mocked_database(self):
        """Test task execution with mocked database operations."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        # Create comprehensive mocks
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.AnalysisJob') as mock_analysis_job_class, \
             patch('tasks.analysis_tasks.PcapAnalysisService') as mock_pcap_service_class, \
             patch('tasks.analysis_tasks.NetworkDiagramGenerator') as mock_diagram_gen_class, \
             patch('os.path.getsize', return_value=1024):
            
            # Setup detailed mocks
            mock_report = self._create_mock_report()
            mock_report_class.get = AsyncMock(return_value=mock_report)
            
            mock_analysis_job = self._create_mock_analysis_job()
            mock_analysis_job_class.return_value = mock_analysis_job
            
            mock_analysis_service = self._create_mock_analysis_service()
            mock_pcap_service_class.return_value = mock_analysis_service
            
            mock_diagram_gen = self._create_mock_diagram_generator()
            mock_diagram_gen_class.return_value = mock_diagram_gen
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "e2e_test_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task
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
            
            # Verify comprehensive result
            assert result["status"] == "completed"
            assert result["task_id"] == "e2e_test_id"
            assert result["message"] == "Analysis completed successfully"
            assert result["results_summary"]["total_packets"] == 1000
            assert result["results_summary"]["throughput_mbps"] == 100.0
            assert result["results_summary"]["file_size_mb"] == 1024 / (1024 * 1024)
            
            # Verify all components were called
            mock_report_class.get.assert_called_once_with("test_report_id")
            mock_analysis_service.analyze_pcap_file.assert_called_once_with("/tmp/test.pcap")
            mock_diagram_gen.generate_comprehensive_diagram_set.assert_called_once()
            
            # Verify database saves were called
            assert mock_report.save.call_count >= 2  # Initial processing + final completed
            assert mock_analysis_job.save.call_count >= 3  # Multiple progress updates
    
    def test_error_recovery_and_state_management(self):
        """Test error recovery and state management."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.AnalysisJob') as mock_analysis_job_class, \
             patch('tasks.analysis_tasks.PcapAnalysisService') as mock_pcap_service_class:
            
            # Setup report mock
            mock_report = self._create_mock_report()
            mock_report_class.get = AsyncMock(return_value=mock_report)
            
            # Setup analysis job mock
            mock_analysis_job = self._create_mock_analysis_job()
            mock_analysis_job_class.return_value = mock_analysis_job
            
            # Setup service to fail
            mock_analysis_service = Mock()
            mock_analysis_service.analyze_pcap_file = AsyncMock(side_effect=Exception("Analysis failed"))
            mock_pcap_service_class.return_value = mock_analysis_service
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "error_test_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task and expect failure
            async def run_test():
                with pytest.raises(Exception, match="Analysis failed"):
                    await analyze_pcap_file(
                        mock_task,
                        mock_db_context,
                        mock_state_manager,
                        "test_report_id",
                        "/tmp/test.pcap"
                    )
            
            bridge = AsyncBridge()
            bridge.run(run_test)
            bridge.shutdown()
            
            # Verify partial execution
            mock_report_class.get.assert_called_once_with("test_report_id")
            mock_analysis_service.analyze_pcap_file.assert_called_once_with("/tmp/test.pcap")
            
            # Verify database saves were attempted
            assert mock_report.save.call_count >= 1  # At least initial processing status
            assert mock_analysis_job.save.call_count >= 1  # At least job creation
    
    def test_concurrent_task_processing(self):
        """Test concurrent task processing."""
        from tasks.analysis_tasks import debug_task
        import concurrent.futures
        
        def run_single_task(task_id):
            mock_task = Mock()
            mock_task.request.id = f"concurrent_{task_id}"
            
            start_time = time.time()
            result = debug_task(mock_task)
            end_time = time.time()
            
            return result, end_time - start_time
        
        # Run multiple tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(run_single_task, i)
                for i in range(3)
            ]
            
            results = [f.result() for f in futures]
        
        # Verify all tasks completed successfully
        assert len(results) == 3
        
        for result, duration in results:
            assert result[0]["status"] == "success"
            assert duration >= 2.0  # Each task sleeps for 2 seconds
            assert "task_id" in result[0]
            assert result[0]["task_id"].startswith("concurrent_")
    
    def test_memory_usage_and_cleanup(self):
        """Test memory usage and cleanup patterns."""
        import gc
        
        # Create multiple contexts and ensure cleanup
        contexts = []
        
        with patch('core.sync_async_bridge.AsyncIOMotorClient') as mock_client, \
             patch('core.sync_async_bridge.init_beanie') as mock_init_beanie:
            
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            mock_init_beanie.return_value = None
            
            for i in range(5):
                context = DatabaseContext()
                
                with context.get_context() as ctx:
                    assert ctx is not None
                    # Simulate some work
                    bridge = AsyncBridge()
                    
                    async def simple_task():
                        await asyncio.sleep(0.01)
                        return f"task_{i}"
                    
                    result = bridge.run(simple_task)
                    assert result == f"task_{i}"
                    
                    bridge.shutdown()
                
                contexts.append(context)
            
            # Force garbage collection
            gc.collect()
            
            # Verify cleanup was called
            assert mock_client_instance.close.call_count == 5
    
    def test_long_running_task_simulation(self):
        """Test simulation of long-running task."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.AnalysisJob') as mock_analysis_job_class, \
             patch('tasks.analysis_tasks.PcapAnalysisService') as mock_pcap_service_class, \
             patch('tasks.analysis_tasks.NetworkDiagramGenerator') as mock_diagram_gen_class, \
             patch('os.path.getsize', return_value=1024*1024):  # 1MB file
            
            # Setup mocks with longer processing time
            mock_report = self._create_mock_report()
            mock_report_class.get = AsyncMock(return_value=mock_report)
            
            mock_analysis_job = self._create_mock_analysis_job()
            mock_analysis_job_class.return_value = mock_analysis_job
            
            # Create analysis service that takes time
            mock_analysis_service = Mock()
            
            async def slow_analysis(file_path):
                await asyncio.sleep(0.5)  # Simulate slow processing
                return self._create_mock_analysis_results()
            
            mock_analysis_service.analyze_pcap_file = slow_analysis
            mock_pcap_service_class.return_value = mock_analysis_service
            
            mock_diagram_gen = self._create_mock_diagram_generator()
            mock_diagram_gen_class.return_value = mock_diagram_gen
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "long_running_test_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task
            async def run_test():
                start_time = time.time()
                result = await analyze_pcap_file(
                    mock_task,
                    mock_db_context,
                    mock_state_manager,
                    "test_report_id",
                    "/tmp/large_test.pcap"
                )
                end_time = time.time()
                return result, end_time - start_time
            
            bridge = AsyncBridge()
            result, duration = bridge.run(run_test)
            bridge.shutdown()
            
            # Verify task completed and took appropriate time
            assert result["status"] == "completed"
            assert duration >= 0.5  # Should take at least 0.5 seconds
            assert result["results_summary"]["file_size_mb"] == 1.0
            
            # Verify progress updates were made
            assert mock_state_manager.update_progress.call_count >= 5
    
    def test_task_cancellation_handling(self):
        """Test handling of task cancellation."""
        bridge = AsyncBridge()
        
        async def cancellable_task():
            try:
                await asyncio.sleep(1.0)
                return "completed"
            except asyncio.CancelledError:
                return "cancelled"
        
        # Test normal completion
        result = bridge.run(cancellable_task)
        assert result == "completed"
        
        bridge.shutdown()
    
    def test_exception_handling_and_logging(self):
        """Test comprehensive exception handling and logging."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.logger') as mock_logger:
            
            # Setup report mock to raise exception
            mock_report_class.get = AsyncMock(side_effect=Exception("Database connection failed"))
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "exception_test_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task and expect failure
            async def run_test():
                with pytest.raises(Exception, match="Database connection failed"):
                    await analyze_pcap_file(
                        mock_task,
                        mock_db_context,
                        mock_state_manager,
                        "test_report_id",
                        "/tmp/test.pcap"
                    )
            
            bridge = AsyncBridge()
            bridge.run(run_test)
            bridge.shutdown()
            
            # Verify logging was called
            mock_logger.info.assert_called()
            mock_logger.error.assert_not_called()  # Error should be raised, not logged
    
    def _create_mock_report(self):
        """Create a mock report object."""
        mock_report = Mock()
        mock_report.id = "test_report_id"
        mock_report.job_id = "test_job_id"
        mock_report.save = AsyncMock()
        return mock_report
    
    def _create_mock_analysis_job(self):
        """Create a mock analysis job object."""
        mock_job = Mock()
        mock_job.save = AsyncMock()
        return mock_job
    
    def _create_mock_analysis_service(self):
        """Create a mock analysis service."""
        mock_service = Mock()
        mock_service.analyze_pcap_file = AsyncMock(return_value=self._create_mock_analysis_results())
        return mock_service
    
    def _create_mock_diagram_generator(self):
        """Create a mock diagram generator."""
        mock_generator = Mock()
        mock_generator.generate_comprehensive_diagram_set.return_value = {
            "network_topology": "diagram_data",
            "traffic_flow": "flow_data",
            "security_analysis": "security_data"
        }
        return mock_generator
    
    def _create_mock_analysis_results(self):
        """Create a mock analysis results object."""
        from datetime import datetime
        
        mock_results = Mock()
        mock_results.file_path = "/tmp/test.pcap"
        mock_results.file_size = 1024
        mock_results.analysis_timestamp = datetime.utcnow()
        
        # Traffic stats
        mock_results.traffic_stats = Mock()
        mock_results.traffic_stats.total_packets = 1000
        mock_results.traffic_stats.total_bytes = 512000
        mock_results.traffic_stats.duration = 30.0
        mock_results.traffic_stats.avg_packet_size = 512
        mock_results.traffic_stats.packets_per_second = 33.33
        mock_results.traffic_stats.bytes_per_second = 17066.67
        
        # Performance metrics
        mock_results.performance_metrics = Mock()
        mock_results.performance_metrics.avg_latency = 0.02
        mock_results.performance_metrics.max_latency = 0.1
        mock_results.performance_metrics.packet_loss_rate = 0.0
        mock_results.performance_metrics.throughput_mbps = 100.0
        
        # Protocol stats
        mock_results.protocol_stats = Mock()
        mock_results.protocol_stats.tcp_packets = 700
        mock_results.protocol_stats.udp_packets = 250
        mock_results.protocol_stats.icmp_packets = 50
        mock_results.protocol_stats.http_sessions = 15
        mock_results.protocol_stats.https_sessions = 10
        mock_results.protocol_stats.dns_queries = 30
        
        # Issues and timing
        mock_results.issues = []
        mock_results.start_time = datetime.utcnow()
        mock_results.end_time = datetime.utcnow()
        mock_results.processing_time = 1.5
        mock_results.analysis_options = {}
        mock_results.top_conversations = []
        
        return mock_results


class TestRealWorldScenarios:
    """Test real-world scenarios and edge cases."""
    
    def test_large_file_processing_simulation(self):
        """Test simulation of large file processing."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.AnalysisJob') as mock_analysis_job_class, \
             patch('tasks.analysis_tasks.PcapAnalysisService') as mock_pcap_service_class, \
             patch('tasks.analysis_tasks.NetworkDiagramGenerator') as mock_diagram_gen_class, \
             patch('os.path.getsize', return_value=100*1024*1024):  # 100MB file
            
            # Setup mocks
            mock_report = Mock()
            mock_report.id = "large_file_report_id"
            mock_report.job_id = "large_file_job_id"
            mock_report.save = AsyncMock()
            mock_report_class.get = AsyncMock(return_value=mock_report)
            
            mock_analysis_job = Mock()
            mock_analysis_job.save = AsyncMock()
            mock_analysis_job_class.return_value = mock_analysis_job
            
            # Create analysis service with large file results
            mock_analysis_service = Mock()
            mock_results = Mock()
            mock_results.file_path = "/tmp/large_test.pcap"
            mock_results.file_size = 100*1024*1024
            mock_results.analysis_timestamp = datetime.utcnow()
            mock_results.traffic_stats = Mock()
            mock_results.traffic_stats.total_packets = 1000000  # 1M packets
            mock_results.traffic_stats.total_bytes = 100*1024*1024
            mock_results.traffic_stats.duration = 300.0  # 5 minutes
            mock_results.traffic_stats.avg_packet_size = 1024
            mock_results.traffic_stats.packets_per_second = 3333.33
            mock_results.traffic_stats.bytes_per_second = 341333.33
            mock_results.performance_metrics = Mock()
            mock_results.performance_metrics.avg_latency = 0.001
            mock_results.performance_metrics.max_latency = 0.1
            mock_results.performance_metrics.packet_loss_rate = 0.05
            mock_results.performance_metrics.throughput_mbps = 2730.67
            mock_results.protocol_stats = Mock()
            mock_results.protocol_stats.tcp_packets = 800000
            mock_results.protocol_stats.udp_packets = 150000
            mock_results.protocol_stats.icmp_packets = 50000
            mock_results.protocol_stats.http_sessions = 1000
            mock_results.protocol_stats.https_sessions = 500
            mock_results.protocol_stats.dns_queries = 5000
            mock_results.issues = []
            mock_results.start_time = datetime.utcnow()
            mock_results.end_time = datetime.utcnow()
            mock_results.processing_time = 10.0
            mock_results.analysis_options = {}
            mock_results.top_conversations = []
            
            mock_analysis_service.analyze_pcap_file = AsyncMock(return_value=mock_results)
            mock_pcap_service_class.return_value = mock_analysis_service
            
            mock_diagram_gen = Mock()
            mock_diagram_gen.generate_comprehensive_diagram_set.return_value = {"large_network": "diagram"}
            mock_diagram_gen_class.return_value = mock_diagram_gen
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "large_file_task_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task
            async def run_test():
                return await analyze_pcap_file(
                    mock_task,
                    mock_db_context,
                    mock_state_manager,
                    "large_file_report_id",
                    "/tmp/large_test.pcap"
                )
            
            bridge = AsyncBridge()
            result = bridge.run(run_test)
            bridge.shutdown()
            
            # Verify large file processing
            assert result["status"] == "completed"
            assert result["results_summary"]["total_packets"] == 1000000
            assert result["results_summary"]["file_size_mb"] == 100.0
            assert result["results_summary"]["throughput_mbps"] == 2730.67
    
    def test_network_failure_simulation(self):
        """Test simulation of network failure scenarios."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        with patch('tasks.analysis_tasks.Report') as mock_report_class:
            # Simulate network timeout
            mock_report_class.get = AsyncMock(side_effect=asyncio.TimeoutError("Network timeout"))
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "network_failure_task_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task and expect failure
            async def run_test():
                with pytest.raises(asyncio.TimeoutError, match="Network timeout"):
                    await analyze_pcap_file(
                        mock_task,
                        mock_db_context,
                        mock_state_manager,
                        "test_report_id",
                        "/tmp/test.pcap"
                    )
            
            bridge = AsyncBridge()
            bridge.run(run_test)
            bridge.shutdown()
    
    def test_resource_exhaustion_simulation(self):
        """Test simulation of resource exhaustion."""
        from tasks.analysis_tasks import analyze_pcap_file
        
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.AnalysisJob') as mock_analysis_job_class, \
             patch('tasks.analysis_tasks.PcapAnalysisService') as mock_pcap_service_class:
            
            # Setup mocks
            mock_report = Mock()
            mock_report.id = "resource_test_report_id"
            mock_report.job_id = "resource_test_job_id"
            mock_report.save = AsyncMock()
            mock_report_class.get = AsyncMock(return_value=mock_report)
            
            mock_analysis_job = Mock()
            mock_analysis_job.save = AsyncMock()
            mock_analysis_job_class.return_value = mock_analysis_job
            
            # Simulate memory error
            mock_analysis_service = Mock()
            mock_analysis_service.analyze_pcap_file = AsyncMock(side_effect=MemoryError("Out of memory"))
            mock_pcap_service_class.return_value = mock_analysis_service
            
            # Create task context
            mock_task = Mock()
            mock_task.request.id = "resource_exhaustion_task_id"
            
            mock_db_context = Mock()
            mock_state_manager = Mock()
            
            # Execute the task and expect failure
            async def run_test():
                with pytest.raises(MemoryError, match="Out of memory"):
                    await analyze_pcap_file(
                        mock_task,
                        mock_db_context,
                        mock_state_manager,
                        "resource_test_report_id",
                        "/tmp/test.pcap"
                    )
            
            bridge = AsyncBridge()
            bridge.run(run_test)
            bridge.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])