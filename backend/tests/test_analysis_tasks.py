#!/usr/bin/env python3
"""
Test suite for analysis tasks with robust error handling.
"""
import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from tasks.analysis_tasks import analyze_pcap_file, debug_task, cleanup_old_reports

class TestAnalysisTasksIntegration:
    """Integration tests for analysis tasks."""
    
    @patch('tasks.analysis_tasks.PcapAnalysisService')
    @patch('tasks.analysis_tasks.NetworkDiagramGenerator')
    @patch('tasks.analysis_tasks.Report')
    @patch('tasks.analysis_tasks.AnalysisJob')
    def test_analyze_pcap_file_task_structure(self, mock_analysis_job, mock_report, mock_diagram_gen, mock_pcap_service):
        """Test that analyze_pcap_file has correct task structure."""
        # Check that the task is properly decorated
        assert hasattr(analyze_pcap_file, 'delay')
        assert hasattr(analyze_pcap_file, 'apply_async')
        assert analyze_pcap_file.name == "analyze_pcap_file"
    
    def test_debug_task_structure(self):
        """Test that debug_task has correct task structure."""
        # Check that the task is properly decorated
        assert hasattr(debug_task, 'delay')
        assert hasattr(debug_task, 'apply_async')
        assert debug_task.name == "debug_task"
    
    def test_cleanup_old_reports_task_structure(self):
        """Test that cleanup_old_reports has correct task structure."""
        # Check that the task is properly decorated
        assert hasattr(cleanup_old_reports, 'delay')
        assert hasattr(cleanup_old_reports, 'apply_async')
        assert cleanup_old_reports.name == "cleanup_old_reports"


class TestDebugTask:
    """Test the debug task functionality."""
    
    def test_debug_task_execution(self):
        """Test debug task execution."""
        # Mock the task instance
        mock_task = Mock()
        mock_task.request.id = "test_debug_task_id"
        
        # Execute the task
        result = debug_task(mock_task)
        
        # Verify the result
        assert result["status"] == "success"
        assert result["task_id"] == "test_debug_task_id"
        assert result["message"] == "Debug task completed"
    
    def test_debug_task_with_actual_celery_task(self):
        """Test debug task with actual Celery task binding."""
        from core.celery_app import celery_app
        
        # Get the actual task
        task = celery_app.tasks['debug_task']
        
        # Create a mock request
        mock_request = Mock()
        mock_request.id = "celery_test_id"
        
        # Bind the task
        bound_task = task.bind(mock_request)
        
        # Execute
        result = debug_task(bound_task)
        
        assert result["status"] == "success"
        assert result["task_id"] == "celery_test_id"


class TestTaskErrorHandling:
    """Test error handling in tasks."""
    
    @patch('tasks.analysis_tasks.Report')
    def test_analyze_pcap_file_report_not_found(self, mock_report):
        """Test analyze_pcap_file when report is not found."""
        from core.sync_async_bridge import AsyncBridge, DatabaseContext, TaskStateManager
        
        # Mock report not found
        mock_report.get = AsyncMock(return_value=None)
        
        # Create mocks
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        
        mock_db_context = Mock()
        mock_state_manager = Mock()
        
        # Create the coroutine
        async def run_test():
            with pytest.raises(ValueError, match="Report not found"):
                await analyze_pcap_file(
                    mock_task,
                    mock_db_context,
                    mock_state_manager,
                    "nonexistent_report_id",
                    "/tmp/test.pcap"
                )
        
        # Run the test
        bridge = AsyncBridge()
        bridge.run(run_test)
        bridge.shutdown()
    
    def test_debug_task_exception_handling(self):
        """Test that debug task handles exceptions gracefully."""
        mock_task = Mock()
        mock_task.request.id = "test_task_id"
        
        # Mock time.sleep to raise an exception
        with patch('time.sleep', side_effect=Exception("Test exception")):
            with pytest.raises(Exception, match="Test exception"):
                debug_task(mock_task)


class TestTaskMocking:
    """Test task mocking for unit tests."""
    
    def test_mock_analyze_pcap_file(self):
        """Test mocking analyze_pcap_file for unit tests."""
        from core.sync_async_bridge import AsyncBridge, DatabaseContext, TaskStateManager
        
        # Create comprehensive mocks
        mock_task = Mock()
        mock_task.request.id = "mock_task_id"
        
        mock_db_context = Mock()
        mock_state_manager = Mock()
        
        # Mock all the models and services
        with patch('tasks.analysis_tasks.Report') as mock_report_class, \
             patch('tasks.analysis_tasks.AnalysisJob') as mock_analysis_job_class, \
             patch('tasks.analysis_tasks.PcapAnalysisService') as mock_pcap_service_class, \
             patch('tasks.analysis_tasks.NetworkDiagramGenerator') as mock_diagram_gen_class, \
             patch('os.path.getsize', return_value=1024):
            
            # Setup report mock
            mock_report = Mock()
            mock_report.id = "mock_report_id"
            mock_report.job_id = "mock_job_id"
            mock_report.save = AsyncMock()
            mock_report_class.get = AsyncMock(return_value=mock_report)
            
            # Setup analysis job mock
            mock_analysis_job = Mock()
            mock_analysis_job.save = AsyncMock()
            mock_analysis_job_class.return_value = mock_analysis_job
            
            # Setup analysis service mock
            mock_analysis_service = Mock()
            mock_analysis_results = Mock()
            mock_analysis_results.file_path = "/tmp/test.pcap"
            mock_analysis_results.file_size = 1024
            mock_analysis_results.analysis_timestamp = datetime.utcnow()
            mock_analysis_results.traffic_stats = Mock()
            mock_analysis_results.traffic_stats.total_packets = 100
            mock_analysis_results.traffic_stats.total_bytes = 50000
            mock_analysis_results.traffic_stats.duration = 10.0
            mock_analysis_results.traffic_stats.avg_packet_size = 500
            mock_analysis_results.traffic_stats.packets_per_second = 10
            mock_analysis_results.traffic_stats.bytes_per_second = 5000
            mock_analysis_results.performance_metrics = Mock()
            mock_analysis_results.performance_metrics.avg_latency = 0.1
            mock_analysis_results.performance_metrics.max_latency = 0.5
            mock_analysis_results.performance_metrics.packet_loss_rate = 0.0
            mock_analysis_results.performance_metrics.throughput_mbps = 40.0
            mock_analysis_results.protocol_stats = Mock()
            mock_analysis_results.protocol_stats.tcp_packets = 80
            mock_analysis_results.protocol_stats.udp_packets = 20
            mock_analysis_results.protocol_stats.icmp_packets = 0
            mock_analysis_results.protocol_stats.http_sessions = 5
            mock_analysis_results.protocol_stats.https_sessions = 3
            mock_analysis_results.protocol_stats.dns_queries = 10
            mock_analysis_results.issues = []
            mock_analysis_results.start_time = datetime.utcnow()
            mock_analysis_results.end_time = datetime.utcnow()
            mock_analysis_results.processing_time = 1.0
            mock_analysis_results.analysis_options = {}
            mock_analysis_results.top_conversations = []
            
            mock_analysis_service.analyze_pcap_file = AsyncMock(return_value=mock_analysis_results)
            mock_pcap_service_class.return_value = mock_analysis_service
            
            # Setup diagram generator mock
            mock_diagram_gen = Mock()
            mock_diagram_gen.generate_comprehensive_diagram_set.return_value = {"test": "diagram"}
            mock_diagram_gen_class.return_value = mock_diagram_gen
            
            # Create the coroutine
            async def run_test():
                result = await analyze_pcap_file(
                    mock_task,
                    mock_db_context,
                    mock_state_manager,
                    "test_report_id",
                    "/tmp/test.pcap"
                )
                return result
            
            # Run the test
            bridge = AsyncBridge()
            result = bridge.run(run_test)
            bridge.shutdown()
            
            # Verify the result
            assert result["status"] == "completed"
            assert result["task_id"] == "mock_task_id"
            assert result["message"] == "Analysis completed successfully"
            assert result["results_summary"]["total_packets"] == 100
            
            # Verify mocks were called
            mock_report_class.get.assert_called_once_with("test_report_id")
            mock_analysis_service.analyze_pcap_file.assert_called_once_with("/tmp/test.pcap")


class TestTaskConfiguration:
    """Test task configuration and registration."""
    
    def test_tasks_registered_with_celery(self):
        """Test that tasks are properly registered with Celery."""
        from core.celery_app import celery_app
        
        # Check that tasks are registered
        assert "analyze_pcap_file" in celery_app.tasks
        assert "debug_task" in celery_app.tasks
        assert "cleanup_old_reports" in celery_app.tasks
        assert "health_check" in celery_app.tasks
    
    def test_task_names_correct(self):
        """Test that task names are correct."""
        from core.celery_app import celery_app
        
        # Check task names
        assert celery_app.tasks["analyze_pcap_file"].name == "analyze_pcap_file"
        assert celery_app.tasks["debug_task"].name == "debug_task"
        assert celery_app.tasks["cleanup_old_reports"].name == "cleanup_old_reports"
        assert celery_app.tasks["health_check"].name == "health_check"
    
    def test_task_binding(self):
        """Test that tasks are properly bound."""
        from core.celery_app import celery_app
        
        # Check that tasks are bound (have self parameter)
        analyze_task = celery_app.tasks["analyze_pcap_file"]
        debug_task = celery_app.tasks["debug_task"]
        cleanup_task = celery_app.tasks["cleanup_old_reports"]
        health_task = celery_app.tasks["health_check"]
        
        # These should be bound tasks
        assert hasattr(analyze_task, 'bind')
        assert hasattr(debug_task, 'bind')
        assert hasattr(cleanup_task, 'bind')
        assert hasattr(health_task, 'bind')


class TestTaskTiming:
    """Test task timing and performance."""
    
    def test_debug_task_timing(self):
        """Test debug task timing."""
        import time
        
        mock_task = Mock()
        mock_task.request.id = "timing_test_id"
        
        start_time = time.time()
        result = debug_task(mock_task)
        end_time = time.time()
        
        # Should take at least 2 seconds (due to sleep)
        assert end_time - start_time >= 2.0
        assert result["status"] == "success"
    
    def test_health_check_timing(self):
        """Test health check timing."""
        from core.celery_app import health_check
        import time
        
        mock_task = Mock()
        mock_task.request.id = "health_timing_test_id"
        
        start_time = time.time()
        result = health_check(mock_task)
        end_time = time.time()
        
        # Should take at least 0.1 seconds (due to sleep)
        assert end_time - start_time >= 0.1
        assert result["status"] == "healthy"
        assert "execution_time" in result
        assert "timestamp" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])