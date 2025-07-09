"""
Integration tests for PCAP Analysis Service.

Tests the complete analysis pipeline including service integration,
task execution, and data flow between components.
"""

import pytest
import tempfile
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from services.pcap_analysis_service import PcapAnalysisService
from models.analysis_results import AnalysisResults, TrafficStats, PerformanceMetrics


class TestPcapAnalysisIntegration:
    """Integration tests for PCAP analysis service."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create analysis service instance."""
        return PcapAnalysisService()
    
    @pytest.fixture
    def sample_pcap_file(self):
        """Create a temporary PCAP file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            # Write minimal PCAP header to make it valid
            pcap_header = (
                b'\xd4\xc3\xb2\xa1'  # Magic number
                b'\x02\x00\x04\x00'  # Version major/minor
                b'\x00\x00\x00\x00'  # Timezone offset
                b'\x00\x00\x00\x00'  # Timestamp accuracy
                b'\x00\x00\x10\x00'  # Max packet length
                b'\x01\x00\x00\x00'  # Data link type (Ethernet)
            )
            tmp.write(pcap_header)
            tmp.flush()
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_end_to_end_analysis_flow(self, analysis_service, sample_pcap_file):
        """Test complete analysis flow from file to results."""
        # Mock file validation to pass
        with patch.object(analysis_service, '_validate_pcap_file') as mock_validate, \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues:
            
            # Setup mocks for successful analysis
            mock_validate.return_value = None
            mock_stats.return_value = {
                'total_packets': 1500,
                'total_bytes': 2048000,
                'duration': 120.0,
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 10:02:00.000000'
            }
            mock_protocols.return_value = {
                'tcp_packets': 1200,
                'udp_packets': 250,
                'icmp_packets': 50,
                'http_sessions': 35,
                'https_sessions': 15,
                'dns_queries': 100,
                'dhcp_packets': 10,
                'arp_packets': 15
            }
            mock_issues.return_value = [
                {
                    'type': 'high_latency',
                    'severity': 'medium',
                    'description': 'Average TCP handshake time is elevated',
                    'recommendation': 'Check network connectivity',
                    'confidence': 0.85
                }
            ]
            
            # Execute analysis
            results = await analysis_service.analyze_pcap_file(sample_pcap_file)
            
            # Verify results structure
            assert isinstance(results, AnalysisResults)
            assert results.total_packets == 1500
            assert results.total_bytes == 2048000
            assert results.duration == 120.0
            assert len(results.issues) == 1
            
            # Verify traffic stats
            assert results.traffic_stats.total_packets == 1500
            assert results.traffic_stats.avg_packet_size > 0
            assert results.traffic_stats.packets_per_second > 0
            
            # Verify protocol stats
            assert results.protocol_stats.tcp_packets == 1200
            assert results.protocol_stats.udp_packets == 250
            assert results.protocol_stats.dns_queries == 100
            
            # Verify performance metrics
            assert results.performance_metrics.throughput_mbps > 0
            assert results.performance_metrics.avg_latency >= 0
            
            # Verify issues
            assert results.issues[0].type == 'high_latency'
            assert results.issues[0].severity == 'medium'
    
    @pytest.mark.asyncio
    async def test_analysis_with_different_options(self, analysis_service, sample_pcap_file):
        """Test analysis with different configuration options."""
        options = {
            'analysis_type': 'security_focused',
            'include_conversations': True,
            'max_issues': 10
        }
        
        with patch.object(analysis_service, '_validate_pcap_file'), \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues:
            
            mock_stats.return_value = {
                'total_packets': 500,
                'total_bytes': 512000,
                'duration': 30.0,
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 10:00:30.000000'
            }
            mock_protocols.return_value = {
                'tcp_packets': 400,
                'udp_packets': 80,
                'icmp_packets': 20,
                'http_sessions': 10,
                'https_sessions': 5,
                'dns_queries': 25,
                'dhcp_packets': 2,
                'arp_packets': 3
            }
            mock_issues.return_value = []
            
            results = await analysis_service.analyze_pcap_file(sample_pcap_file, options)
            
            # Verify options were passed through
            assert results.analysis_options == options
            assert results.total_packets == 500
            assert len(results.issues) == 0
    
    @pytest.mark.asyncio
    async def test_analysis_error_handling(self, analysis_service):
        """Test error handling in analysis pipeline."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            await analysis_service.analyze_pcap_file("/nonexistent/file.pcap")
        
        # Test with invalid file size
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            tmp.write(b'')  # Empty file
            tmp.flush()
            
            with pytest.raises(ValueError, match="PCAP file is empty"):
                await analysis_service.analyze_pcap_file(tmp.name)
            
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, analysis_service):
        """Test handling of large PCAP files."""
        # Create a mock large file
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            # Write enough data to simulate a large file
            large_data = b'x' * (2 * 1024 * 1024 * 1024)  # 2GB
            
            # Mock the file size check
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = len(large_data)
                
                with pytest.raises(ValueError, match="PCAP file too large"):
                    await analysis_service.analyze_pcap_file(tmp.name)
            
            os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, analysis_service):
        """Test handling of concurrent analysis requests."""
        # Mock all analysis methods to simulate fast processing
        with patch.object(analysis_service, '_validate_pcap_file') as mock_validate, \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.stat') as mock_stat:
            
            # Setup mocks to pass validation and return consistent results
            mock_validate.return_value = None
            mock_exists.return_value = True
            mock_stat.return_value.st_size = 102400
            mock_stats.return_value = {
                'total_packets': 100,
                'total_bytes': 102400,
                'duration': 10.0,
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 10:00:10.000000'
            }
            mock_protocols.return_value = {
                'tcp_packets': 80,
                'udp_packets': 15,
                'icmp_packets': 5,
                'http_sessions': 5,
                'https_sessions': 2,
                'dns_queries': 10,
                'dhcp_packets': 1,
                'arp_packets': 2
            }
            mock_issues.return_value = []
            
            # Create multiple concurrent analysis tasks
            tasks = []
            for i in range(5):
                task = analysis_service.analyze_pcap_file(f"/test/file_{i}.pcap")
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all tasks completed successfully
            assert len(results) == 5
            for result in results:
                assert isinstance(result, AnalysisResults)
                assert result.total_packets == 100
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_results(self, analysis_service):
        """Test memory efficiency with large analysis results."""
        with patch.object(analysis_service, '_validate_pcap_file'), \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.stat') as mock_stat:
            
            # Setup file existence and size mocks
            mock_exists.return_value = True
            mock_stat.return_value.st_size = 1024000000  # 1GB
            
            # Simulate large dataset
            mock_stats.return_value = {
                'total_packets': 1000000,  # 1M packets
                'total_bytes': 1024000000,  # 1GB
                'duration': 3600.0,  # 1 hour
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 11:00:00.000000'
            }
            mock_protocols.return_value = {
                'tcp_packets': 800000,
                'udp_packets': 150000,
                'icmp_packets': 50000,
                'http_sessions': 25000,
                'https_sessions': 15000,
                'dns_queries': 75000,
                'dhcp_packets': 5000,
                'arp_packets': 10000
            }
            mock_issues.return_value = []
            
            # Execute analysis
            results = await analysis_service.analyze_pcap_file("/test/large_file.pcap")
            
            # Verify large dataset handling
            assert results.total_packets == 1000000
            assert results.total_bytes == 1024000000
            assert results.traffic_stats.packets_per_second > 0
            assert results.performance_metrics.throughput_mbps > 0


class TestServiceConfiguration:
    """Test service configuration and customization options."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create analysis service instance."""
        return PcapAnalysisService()
    
    @pytest.mark.asyncio
    async def test_analysis_types_basic(self, analysis_service):
        """Test basic analysis type configuration."""
        options = {'analysis_type': 'basic'}
        
        with patch.object(analysis_service, '_validate_pcap_file'), \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            mock_stats.return_value = {
                'total_packets': 100,
                'total_bytes': 1024,
                'duration': 1.0,
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 10:00:01.000000'
            }
            mock_protocols.return_value = {
                'tcp_packets': 80,
                'udp_packets': 15,
                'icmp_packets': 5,
                'http_sessions': 5,
                'https_sessions': 2,
                'dns_queries': 10,
                'dhcp_packets': 1,
                'arp_packets': 2
            }
            mock_issues.return_value = []
            
            results = await analysis_service.analyze_pcap_file("/test/basic.pcap", options)
            
            assert results.analysis_options['analysis_type'] == 'basic'
            assert results.total_packets == 100
    
    @pytest.mark.asyncio
    async def test_analysis_types_comprehensive(self, analysis_service):
        """Test comprehensive analysis type configuration."""
        options = {'analysis_type': 'comprehensive'}
        
        with patch.object(analysis_service, '_validate_pcap_file'), \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024000
            mock_stats.return_value = {
                'total_packets': 10000,
                'total_bytes': 1024000,
                'duration': 100.0,
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 10:01:40.000000'
            }
            mock_protocols.return_value = {
                'tcp_packets': 8000,
                'udp_packets': 1500,
                'icmp_packets': 500,
                'http_sessions': 500,
                'https_sessions': 200,
                'dns_queries': 1000,
                'dhcp_packets': 100,
                'arp_packets': 200
            }
            # Comprehensive analysis should detect more issues
            mock_issues.return_value = [
                {
                    'type': 'high_latency',
                    'severity': 'medium',
                    'description': 'Elevated response times detected',
                    'recommendation': 'Check network performance',
                    'confidence': 0.85
                },
                {
                    'type': 'packet_loss',
                    'severity': 'low',
                    'description': 'Minor packet loss observed',
                    'recommendation': 'Monitor network stability',
                    'confidence': 0.70
                }
            ]
            
            results = await analysis_service.analyze_pcap_file("/test/comprehensive.pcap", options)
            
            assert results.analysis_options['analysis_type'] == 'comprehensive'
            assert results.total_packets == 10000
            assert len(results.issues) == 2 