"""
Integration tests for Protocol Analysis components.

Tests the integration between protocol analyzers and the main analysis service,
ensuring end-to-end functionality works correctly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import List

from services.pcap_analysis_service import PcapAnalysisService
from services.protocol_analyzers import ProtocolAnalysisEngine
from models.packet_data import PacketData
from models.protocol_analysis import (
    TCPAnalysisResult, UDPAnalysisResult, HTTPAnalysisResult, DNSAnalysisResult
)
from models.analysis_results import AnalysisResults


class TestProtocolAnalysisIntegration:
    """Integration tests for protocol analysis functionality."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create PCAP analysis service for testing."""
        return PcapAnalysisService()
    
    @pytest.fixture
    def protocol_engine(self):
        """Create protocol analysis engine for testing."""
        return ProtocolAnalysisEngine()
    
    @pytest.fixture
    def mixed_traffic_packets(self):
        """Create mixed protocol traffic for testing."""
        return [
            # TCP handshake
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="93.184.216.34", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=74,
                tcp_flags="SYN", tcp_seq=1000, tcp_window=65535
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:00.050000",
                src_ip="93.184.216.34", dst_ip="192.168.1.100", protocol="TCP",
                src_port=80, dst_port=12345, packet_size=60,
                tcp_flags="SYN,ACK", tcp_seq=2000, tcp_ack=1001, tcp_window=65535
            ),
            PacketData(
                frame_number=3, timestamp="2025-01-15 10:00:00.100000",
                src_ip="192.168.1.100", dst_ip="93.184.216.34", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=54,
                tcp_flags="ACK", tcp_seq=1001, tcp_ack=2001, tcp_window=65535
            ),
            # HTTP request/response
            PacketData(
                frame_number=4, timestamp="2025-01-15 10:00:00.200000",
                src_ip="192.168.1.100", dst_ip="93.184.216.34", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=200,
                http_method="GET", http_uri="/index.html", http_host="example.com"
            ),
            PacketData(
                frame_number=5, timestamp="2025-01-15 10:00:00.400000",
                src_ip="93.184.216.34", dst_ip="192.168.1.100", protocol="TCP",
                src_port=80, dst_port=12345, packet_size=1500,
                http_status=200
            ),
            # DNS query/response
            PacketData(
                frame_number=6, timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=53421, dst_port=53, packet_size=64,
                dns_query="example.com", dns_type="A"
            ),
            PacketData(
                frame_number=7, timestamp="2025-01-15 10:00:01.020000",
                src_ip="8.8.8.8", dst_ip="192.168.1.100", protocol="UDP",
                src_port=53, dst_port=53421, packet_size=80,
                dns_response="93.184.216.34"
            ),
            # Additional UDP traffic
            PacketData(
                frame_number=8, timestamp="2025-01-15 10:00:02.000000",
                src_ip="192.168.1.100", dst_ip="192.168.1.1", protocol="UDP",
                src_port=68, dst_port=67, packet_size=300
            ),
        ]
    
    @pytest.mark.asyncio
    async def test_service_protocol_analysis_integration(self, analysis_service, mixed_traffic_packets):
        """Test integration between analysis service and protocol analyzers."""
        # Mock packet processing pipeline
        with patch.object(analysis_service.packet_pipeline, 'extract_packets_with_tshark') as mock_extract_pipeline:
            mock_extract_pipeline.return_value = mixed_traffic_packets
            
            # Mock file validation
            with patch.object(analysis_service, '_validate_pcap_file') as mock_validate:
                mock_validate.return_value = None
                
                # Mock Path.stat() for file size
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024000  # 1MB fake file size
                    
                    # Mock basic stats extraction
                    with patch.object(analysis_service, '_extract_basic_stats') as mock_basic_stats:
                        mock_basic_stats.return_value = {
                            'total_packets': 8,  # Match the test data
                            'total_bytes': 1024,
                            'duration': 2.0,
                            'start_time': '2025-01-15 10:00:00.000000',
                            'end_time': '2025-01-15 10:00:02.000000'
                        }
                        
                        # Mock tshark extraction
                        with patch.object(analysis_service, '_extract_packets_with_tshark') as mock_extract:
                            mock_extract.return_value = mixed_traffic_packets
                            
                            # Perform analysis
                            result = await analysis_service.analyze_pcap("/fake/path/test.pcap")
                            
                            # Verify analysis was performed
                            assert isinstance(result, AnalysisResults)
                            assert result.total_packets == 8
                            assert result.processing_time > 0
                            
                            # Verify protocol analysis was included
                            assert hasattr(result, 'protocol_analysis') or 'protocol_analysis' in result.__dict__
    
    @pytest.mark.asyncio
    async def test_comprehensive_protocol_detection(self, protocol_engine, mixed_traffic_packets):
        """Test comprehensive protocol detection across mixed traffic."""
        detected_protocols = protocol_engine.detect_protocols(mixed_traffic_packets)
        
        # Should detect multiple protocols
        assert "tcp" in detected_protocols
        assert "udp" in detected_protocols
        assert "http" in detected_protocols  # Port 80
        assert "dns" in detected_protocols   # Port 53
        assert "dhcp" in detected_protocols  # Port 67
    
    @pytest.mark.asyncio
    async def test_multi_protocol_analysis_results(self, protocol_engine, mixed_traffic_packets):
        """Test that multi-protocol analysis produces comprehensive results."""
        results = await protocol_engine.analyze_protocols(mixed_traffic_packets)
        
        # Verify all expected protocol results are present
        assert "tcp" in results
        assert "udp" in results
        assert "http" in results
        assert "dns" in results
        
        # Verify result types
        assert isinstance(results["tcp"], TCPAnalysisResult)
        assert isinstance(results["udp"], UDPAnalysisResult)
        assert isinstance(results["http"], HTTPAnalysisResult)
        assert isinstance(results["dns"], DNSAnalysisResult)
        
        # Verify TCP analysis captured handshake
        tcp_result = results["tcp"]
        assert tcp_result.syn_packets == 1
        assert tcp_result.syn_ack_packets == 1
        assert tcp_result.ack_packets == 1
        assert tcp_result.handshake_rtt > 0
        
        # Verify HTTP analysis captured transaction
        http_result = results["http"]
        assert http_result.total_requests == 1
        assert http_result.total_responses == 1
        assert len(http_result.transactions) == 1
        assert http_result.transactions[0].method == "GET"
        assert http_result.transactions[0].status_code == 200
        
        # Verify DNS analysis captured query/response
        dns_result = results["dns"]
        assert dns_result.total_queries == 1
        assert dns_result.total_responses == 1
        assert len(dns_result.queries) == 1
        assert dns_result.queries[0].domain == "example.com"
    
    @pytest.mark.asyncio
    async def test_protocol_performance_correlation(self, protocol_engine, mixed_traffic_packets):
        """Test correlation of performance metrics across protocols."""
        summary = await protocol_engine.generate_summary(mixed_traffic_packets)
        
        # Verify summary contains expected data
        assert "protocol_distribution" in summary
        assert "total_packets" in summary
        assert "analysis_results" in summary
        assert "detected_protocols" in summary
        
        # Verify protocol distribution
        protocol_dist = summary["protocol_distribution"]
        assert protocol_dist["TCP"] >= 5  # TCP packets
        assert protocol_dist["UDP"] >= 3  # UDP packets
        
        # Verify detected protocols list
        detected = summary["detected_protocols"]
        assert "tcp" in detected
        assert "udp" in detected
        assert "http" in detected
        assert "dns" in detected
    
    @pytest.mark.asyncio
    async def test_large_dataset_protocol_analysis(self, protocol_engine):
        """Test protocol analysis with larger dataset."""
        # Generate larger dataset
        large_dataset = []
        base_time = datetime.fromisoformat("2025-01-15 10:00:00.000000")
        
        for i in range(100):
            # Alternate between different protocol types
            if i % 4 == 0:  # TCP
                packet = PacketData(
                    frame_number=i+1,
                    timestamp=(base_time.replace(microsecond=i*10000)).isoformat(),
                    src_ip=f"192.168.1.{(i % 50) + 100}",
                    dst_ip="8.8.8.8",
                    protocol="TCP",
                    src_port=12345 + (i % 1000),
                    dst_port=80,
                    packet_size=100 + (i % 100)
                )
            elif i % 4 == 1:  # UDP DNS
                packet = PacketData(
                    frame_number=i+1,
                    timestamp=(base_time.replace(microsecond=i*10000)).isoformat(),
                    src_ip=f"192.168.1.{(i % 50) + 100}",
                    dst_ip="8.8.8.8",
                    protocol="UDP",
                    src_port=53000 + (i % 1000),
                    dst_port=53,
                    packet_size=64,
                    dns_query=f"site{i}.com",
                    dns_type="A"
                )
            elif i % 4 == 2:  # HTTP
                packet = PacketData(
                    frame_number=i+1,
                    timestamp=(base_time.replace(microsecond=i*10000)).isoformat(),
                    src_ip=f"192.168.1.{(i % 50) + 100}",
                    dst_ip="93.184.216.34",
                    protocol="TCP",
                    src_port=12345 + (i % 1000),
                    dst_port=80,
                    packet_size=200,
                    http_method="GET",
                    http_uri=f"/page{i}.html"
                )
            else:  # UDP general
                packet = PacketData(
                    frame_number=i+1,
                    timestamp=(base_time.replace(microsecond=i*10000)).isoformat(),
                    src_ip=f"192.168.1.{(i % 50) + 100}",
                    dst_ip="192.168.1.1",
                    protocol="UDP",
                    src_port=12345 + (i % 1000),
                    dst_port=123,  # NTP
                    packet_size=48
                )
            
            large_dataset.append(packet)
        
        # Analyze large dataset
        results = await protocol_engine.analyze_protocols(large_dataset)
        
        # Verify analysis handles large dataset
        assert "tcp" in results
        assert "udp" in results
        assert "http" in results
        assert "dns" in results
        
        # Verify reasonable performance metrics
        tcp_result = results["tcp"]
        assert tcp_result.total_packets > 0
        assert tcp_result.avg_throughput_bps >= 0
        
        udp_result = results["udp"]
        assert udp_result.total_packets > 0
        assert udp_result.avg_throughput_bps >= 0
    
    @pytest.mark.asyncio
    async def test_protocol_error_handling(self, protocol_engine):
        """Test protocol analysis error handling with malformed data."""
        # Create packets with missing or invalid data
        problematic_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=0  # Invalid size
            ),
            PacketData(
                frame_number=2, timestamp="invalid-timestamp",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12346, dst_port=53, packet_size=64
            ),
            PacketData(
                frame_number=3, timestamp="2025-01-15 10:00:00.200000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UNKNOWN",
                src_port=12347, dst_port=9999, packet_size=100
            ),
        ]
        
        # Analysis should handle errors gracefully
        try:
            results = await protocol_engine.analyze_protocols(problematic_packets)
            # Should not crash and should return some results
            assert isinstance(results, dict)
        except Exception as e:
            # If exceptions occur, they should be handled gracefully
            pytest.fail(f"Protocol analysis should handle errors gracefully: {e}")
    
    @pytest.mark.asyncio
    async def test_protocol_analysis_performance_metrics(self, protocol_engine, mixed_traffic_packets):
        """Test that protocol analysis generates meaningful performance metrics."""
        results = await protocol_engine.analyze_protocols(mixed_traffic_packets)
        
        # Test TCP performance metrics
        tcp_result = results["tcp"]
        assert tcp_result.handshake_rtt > 0
        assert tcp_result.avg_throughput_bps > 0
        assert tcp_result.connection_quality in ["excellent", "good", "fair", "poor"]
        
        # Test UDP performance metrics
        udp_result = results["udp"]
        assert udp_result.avg_response_time >= 0
        assert udp_result.avg_throughput_bps > 0
        assert udp_result.packet_loss_rate >= 0
        
        # Test HTTP performance metrics
        http_result = results["http"]
        assert http_result.avg_response_time > 0
        assert http_result.error_rate >= 0
        assert http_result.total_bytes > 0
        
        # Test DNS performance metrics
        dns_result = results["dns"]
        assert dns_result.avg_response_time > 0
        assert dns_result.success_rate >= 0
        assert dns_result.success_rate <= 1.0
    
    @pytest.mark.asyncio
    async def test_cross_protocol_timing_correlation(self, protocol_engine, mixed_traffic_packets):
        """Test timing correlations between different protocols."""
        # Generate summary with timing analysis
        summary = await protocol_engine.generate_summary(mixed_traffic_packets)
        
        # Verify summary structure
        assert "analysis_results" in summary
        analysis_results = summary["analysis_results"]
        
        # Verify timing data is available for correlation
        if "tcp" in analysis_results and "dns" in analysis_results:
            tcp_result = analysis_results["tcp"]
            dns_result = analysis_results["dns"]
            
            # Both should have timing information
            assert hasattr(tcp_result, 'handshake_rtt')
            assert hasattr(dns_result, 'avg_response_time')
            
            # Timing values should be reasonable
            assert 0 <= tcp_result.handshake_rtt <= 10  # Within 10 seconds
            assert 0 <= dns_result.avg_response_time <= 10  # Within 10 seconds 