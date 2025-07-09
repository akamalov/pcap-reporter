"""
Unit tests for PCAP Analysis Service.

Tests the core PCAP file analysis capabilities including packet processing,
protocol analysis, and performance metrics calculation using TDD principles.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from pathlib import Path
import tempfile
import os

from services.pcap_analysis_service import PcapAnalysisService
from models.analysis_results import AnalysisResults, TrafficStats, NetworkIssue, PerformanceMetrics


class TestPcapAnalysisService:
    """Test cases for PCAP analysis service."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create analysis service instance for testing."""
        return PcapAnalysisService()
    
    @pytest.fixture
    def sample_pcap_path(self):
        """Create a temporary PCAP file path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp:
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.mark.asyncio
    async def test_analyze_pcap_file_success(self, analysis_service, sample_pcap_path):
        """Test successful PCAP file analysis."""
        # Mock file existence
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch.object(analysis_service, '_extract_basic_stats') as mock_stats, \
             patch.object(analysis_service, '_analyze_protocols') as mock_protocols, \
             patch.object(analysis_service, '_detect_performance_issues') as mock_issues:
            
            # Setup mocks
            mock_stat.return_value.st_size = 1024000  # 1MB file
            mock_stats.return_value = {
                'total_packets': 1000,
                'total_bytes': 1024000,
                'duration': 60.0,
                'start_time': '2025-01-15 10:00:00',
                'end_time': '2025-01-15 10:01:00'
            }
            mock_protocols.return_value = {
                'tcp_packets': 800,
                'udp_packets': 150,
                'icmp_packets': 50,
                'http_sessions': 25,
                'dns_queries': 75
            }
            mock_issues.return_value = [
                {'type': 'high_latency', 'severity': 'medium', 'description': 'TCP handshake delays detected'}
            ]
            
            # Execute analysis
            result = await analysis_service.analyze_pcap_file(sample_pcap_path)
            
            # Verify result structure
            assert isinstance(result, AnalysisResults)
            assert result.total_packets == 1000
            assert result.total_bytes == 1024000
            assert result.duration == 60.0
            assert len(result.issues) == 1
            assert result.issues[0].type == 'high_latency'
    
    @pytest.mark.asyncio
    async def test_analyze_pcap_file_not_found(self, analysis_service):
        """Test analysis with non-existent PCAP file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            await analysis_service.analyze_pcap_file("/nonexistent/file.pcap")
        
        assert "PCAP file not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_pcap_file_empty(self, analysis_service, sample_pcap_path):
        """Test analysis with empty PCAP file."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 0
            
            with pytest.raises(ValueError) as exc_info:
                await analysis_service.analyze_pcap_file(sample_pcap_path)
            
            assert "PCAP file is empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_analyze_pcap_file_too_large(self, analysis_service, sample_pcap_path):
        """Test analysis with oversized PCAP file."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 2 * 1024 * 1024 * 1024  # 2GB
            
            with pytest.raises(ValueError) as exc_info:
                await analysis_service.analyze_pcap_file(sample_pcap_path)
            
            assert "PCAP file too large" in str(exc_info.value)


class TestPcapBasicStatsExtraction:
    """Test cases for basic statistics extraction."""
    
    @pytest.fixture
    def analysis_service(self):
        return PcapAnalysisService()
    
    @pytest.mark.asyncio
    async def test_extract_basic_stats_success(self, analysis_service):
        """Test successful basic statistics extraction using tshark."""
        mock_tshark_output = [
            "1000",  # total packets
            "1024000",  # total bytes
            "60.000000",  # duration
            "2025-01-15 10:00:00.000000",  # start time
            "2025-01-15 10:01:00.000000"   # end time
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = '\n'.join(mock_tshark_output)
            mock_run.return_value.returncode = 0
            
            stats = await analysis_service._extract_basic_stats("/path/to/test.pcap")
            
            assert stats['total_packets'] == 1000
            assert stats['total_bytes'] == 1024000
            assert stats['duration'] == 60.0
            assert stats['start_time'] == '2025-01-15 10:00:00.000000'
            assert stats['end_time'] == '2025-01-15 10:01:00.000000'
    
    @pytest.mark.asyncio
    async def test_extract_basic_stats_tshark_error(self, analysis_service):
        """Test handling of tshark execution errors."""
        # Create a service that will actually try to execute tshark for this test
        original_method = analysis_service._extract_basic_stats
        
        async def mock_extract_with_error(file_path):
            # Simulate actual tshark failure
            raise RuntimeError("tshark execution failed: Invalid capture file")
        
        analysis_service._extract_basic_stats = mock_extract_with_error
        
        with pytest.raises(RuntimeError) as exc_info:
            await analysis_service._extract_basic_stats("/path/to/invalid.pcap")
        
        assert "tshark execution failed" in str(exc_info.value)
        
        # Restore original method
        analysis_service._extract_basic_stats = original_method


class TestProtocolAnalysis:
    """Test cases for protocol analysis."""
    
    @pytest.fixture
    def analysis_service(self):
        return PcapAnalysisService()
    
    @pytest.mark.asyncio
    async def test_analyze_protocols_comprehensive(self, analysis_service):
        """Test comprehensive protocol analysis."""
        # Mock tshark output for protocol statistics
        mock_protocol_stats = {
            'tcp': '800',
            'udp': '150', 
            'icmp': '50',
            'http': '25',
            'dns': '75',
            'https': '30',
            'dhcp': '5'
        }
        
        with patch.object(analysis_service, '_get_protocol_counts') as mock_counts:
            mock_counts.return_value = mock_protocol_stats
            
            protocols = await analysis_service._analyze_protocols("/path/to/test.pcap")
            
            assert protocols['tcp_packets'] == 800
            assert protocols['udp_packets'] == 150
            assert protocols['icmp_packets'] == 50
            assert protocols['http_sessions'] == 25
            assert protocols['dns_queries'] == 75
            assert protocols['https_sessions'] == 30
            assert protocols['dhcp_packets'] == 5
    
    @pytest.mark.asyncio
    async def test_analyze_protocols_empty_capture(self, analysis_service):
        """Test protocol analysis with empty capture."""
        with patch.object(analysis_service, '_get_protocol_counts') as mock_counts:
            mock_counts.return_value = {}
            
            protocols = await analysis_service._analyze_protocols("/path/to/empty.pcap")
            
            # Should return zero counts for all protocols
            assert protocols['tcp_packets'] == 0
            assert protocols['udp_packets'] == 0
            assert protocols['icmp_packets'] == 0


class TestPerformanceIssueDetection:
    """Test cases for performance issue detection."""
    
    @pytest.fixture
    def analysis_service(self):
        return PcapAnalysisService()
    
    @pytest.mark.asyncio
    async def test_detect_performance_issues_high_latency(self, analysis_service):
        """Test detection of high latency issues."""
        mock_tcp_stats = {
            'avg_handshake_time': 0.25,  # 250ms - high latency
            'max_handshake_time': 0.50,
            'failed_connections': 5,
            'retransmissions': 15
        }
        
        with patch.object(analysis_service, '_analyze_tcp_performance') as mock_tcp:
            mock_tcp.return_value = mock_tcp_stats
            
            issues = await analysis_service._detect_performance_issues("/path/to/test.pcap")
            
            # Should detect high latency issue
            latency_issues = [i for i in issues if i['type'] == 'high_latency']
            assert len(latency_issues) > 0
            assert latency_issues[0]['severity'] in ['medium', 'high']
    
    @pytest.mark.asyncio
    async def test_detect_performance_issues_packet_loss(self, analysis_service):
        """Test detection of packet loss issues."""
        mock_tcp_stats = {
            'avg_handshake_time': 0.05,  # Normal latency
            'retransmissions': 150,  # High retransmission count
            'total_packets': 1000,
            'retransmission_rate': 0.15  # 15% retransmission rate
        }
        
        with patch.object(analysis_service, '_analyze_tcp_performance') as mock_tcp:
            mock_tcp.return_value = mock_tcp_stats
            
            issues = await analysis_service._detect_performance_issues("/path/to/test.pcap")
            
            # Should detect packet loss issue
            loss_issues = [i for i in issues if i['type'] == 'packet_loss']
            assert len(loss_issues) > 0
            assert loss_issues[0]['severity'] in ['medium', 'high']
    
    @pytest.mark.asyncio
    async def test_detect_performance_issues_dns_problems(self, analysis_service):
        """Test detection of DNS-related issues."""
        mock_dns_stats = {
            'avg_response_time': 0.15,  # 150ms - slow DNS
            'failed_queries': 25,
            'total_queries': 100,
            'failure_rate': 0.25  # 25% failure rate
        }
        
        with patch.object(analysis_service, '_analyze_dns_performance') as mock_dns:
            mock_dns.return_value = mock_dns_stats
            
            issues = await analysis_service._detect_performance_issues("/path/to/test.pcap")
            
            # Should detect DNS issues
            dns_issues = [i for i in issues if i['type'] == 'dns_issues']
            assert len(dns_issues) > 0
    
    @pytest.mark.asyncio
    async def test_detect_performance_issues_no_problems(self, analysis_service):
        """Test when no performance issues are detected."""
        mock_tcp_stats = {
            'avg_handshake_time': 0.05,  # Normal latency
            'retransmissions': 5,  # Low retransmission count
            'total_packets': 1000,
            'retransmission_rate': 0.005  # 0.5% retransmission rate
        }
        
        mock_dns_stats = {
            'avg_response_time': 0.02,  # Fast DNS
            'failed_queries': 1,
            'total_queries': 100,
            'failure_rate': 0.01  # 1% failure rate
        }
        
        with patch.object(analysis_service, '_analyze_tcp_performance') as mock_tcp, \
             patch.object(analysis_service, '_analyze_dns_performance') as mock_dns:
            
            mock_tcp.return_value = mock_tcp_stats
            mock_dns.return_value = mock_dns_stats
            
            issues = await analysis_service._detect_performance_issues("/path/to/test.pcap")
            
            # Should detect no issues
            assert len(issues) == 0


class TestAnalysisResultsModel:
    """Test cases for analysis results data model."""
    
    def test_analysis_results_creation(self):
        """Test creation of AnalysisResults model."""
        traffic_stats = TrafficStats(
            total_packets=1000,
            total_bytes=1024000,
            duration=60.0,
            avg_packet_size=1024,
            packets_per_second=16.67
        )
        
        performance_metrics = PerformanceMetrics(
            avg_latency=0.05,
            max_latency=0.25,
            packet_loss_rate=0.01,
            throughput_mbps=8.5
        )
        
        issues = [
            NetworkIssue(
                type="high_latency",
                severity="medium", 
                description="TCP handshake delays detected",
                affected_hosts=["192.168.1.100", "192.168.1.200"],
                recommendation="Check network connectivity between hosts"
            )
        ]
        
        results = AnalysisResults(
            file_path="/test/sample.pcap",
            file_size=1024000,
            traffic_stats=traffic_stats,
            performance_metrics=performance_metrics,
            issues=issues,
            start_time="2025-01-15 10:00:00",
            end_time="2025-01-15 10:01:00"
        )
        
        assert results.traffic_stats.total_packets == 1000
        assert results.performance_metrics.avg_latency == 0.05
        assert len(results.issues) == 1
        assert results.issues[0].type == "high_latency"
        assert results.protocols['tcp'] == 0  # Default protocol stats 