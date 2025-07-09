"""
Unit tests for Protocol Analyzers.

Tests the specialized protocol analysis components for TCP, UDP, HTTP, and DNS
using Test-Driven Development principles.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from typing import List, Dict, Any

from services.protocol_analyzers import (
    TCPAnalyzer, UDPAnalyzer, HTTPAnalyzer, DNSAnalyzer, ProtocolAnalysisEngine
)
from models.packet_data import PacketData, PacketStream, ConversationFlow
from models.protocol_analysis import (
    TCPAnalysisResult, UDPAnalysisResult, HTTPAnalysisResult, DNSAnalysisResult,
    TCPConnectionState, HTTPTransaction, DNSQuery, DNSResponse
)


class TestTCPAnalyzer:
    """Test cases for TCP protocol analyzer."""
    
    @pytest.fixture
    def tcp_analyzer(self):
        """Create TCP analyzer instance for testing."""
        return TCPAnalyzer()
    
    @pytest.fixture
    def tcp_packets(self):
        """Create sample TCP packets for testing."""
        return [
            PacketData(
                frame_number=1,
                timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="TCP",
                src_port=12345,
                dst_port=80,
                packet_size=74,
                tcp_flags="SYN",
                tcp_seq=1000,
                tcp_ack=0,
                tcp_window=65535
            ),
            PacketData(
                frame_number=2,
                timestamp="2025-01-15 10:00:00.100000",
                src_ip="8.8.8.8",
                dst_ip="192.168.1.100",
                protocol="TCP",
                src_port=80,
                dst_port=12345,
                packet_size=60,
                tcp_flags="SYN,ACK",
                tcp_seq=2000,
                tcp_ack=1001,
                tcp_window=65535
            ),
            PacketData(
                frame_number=3,
                timestamp="2025-01-15 10:00:00.200000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="TCP",
                src_port=12345,
                dst_port=80,
                packet_size=54,
                tcp_flags="ACK",
                tcp_seq=1001,
                tcp_ack=2001,
                tcp_window=65535
            )
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_tcp_stream_handshake(self, tcp_analyzer, tcp_packets):
        """Test TCP handshake analysis."""
        result = await tcp_analyzer.analyze_stream(tcp_packets)
        
        assert isinstance(result, TCPAnalysisResult)
        assert result.connection_state == TCPConnectionState.ESTABLISHED
        assert result.handshake_rtt > 0
        assert result.syn_packets == 1
        assert result.syn_ack_packets == 1
        assert result.ack_packets == 1
        assert result.initial_window_size == 65535
        assert result.retransmissions == 0
    
    @pytest.mark.asyncio
    async def test_analyze_tcp_connection_metrics(self, tcp_analyzer, tcp_packets):
        """Test TCP connection metrics calculation."""
        result = await tcp_analyzer.analyze_stream(tcp_packets)
        
        # Verify timing metrics (handshake RTT is SYN to SYN-ACK, not full handshake)
        assert result.handshake_rtt == 0.1  # 100ms SYN to SYN-ACK time
        assert result.connection_duration > 0
        
        # Verify packet counts
        assert result.total_packets == 3
        assert result.client_packets == 2
        assert result.server_packets == 1
        
        # Verify byte counts
        assert result.total_bytes == 188  # 74 + 60 + 54
        assert result.client_bytes == 128  # 74 + 54
        assert result.server_bytes == 60
    
    @pytest.mark.asyncio
    async def test_detect_tcp_retransmissions(self, tcp_analyzer):
        """Test TCP retransmission detection."""
        packets_with_retrans = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=100,
                tcp_seq=1000, tcp_ack=0
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=100,
                tcp_seq=1000, tcp_ack=0  # Same sequence number = retransmission
            )
        ]
        
        result = await tcp_analyzer.analyze_stream(packets_with_retrans)
        
        assert result.retransmissions == 1
        assert result.retransmission_rate > 0
    
    @pytest.mark.asyncio
    async def test_detect_tcp_out_of_order(self, tcp_analyzer):
        """Test TCP out-of-order packet detection."""
        out_of_order_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, tcp_seq=1000, packet_size=100
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:00.100000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, tcp_seq=1200, packet_size=100  # Gap in sequence
            ),
            PacketData(
                frame_number=3, timestamp="2025-01-15 10:00:00.200000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, tcp_seq=1100, packet_size=100  # Out of order
            )
        ]
        
        result = await tcp_analyzer.analyze_stream(out_of_order_packets)
        
        assert result.out_of_order_packets > 0
    
    @pytest.mark.asyncio
    async def test_calculate_tcp_window_scaling(self, tcp_analyzer):
        """Test TCP window scaling analysis."""
        packets_with_scaling = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, tcp_window=32768, packet_size=74
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:00.100000",
                src_ip="8.8.8.8", dst_ip="192.168.1.100", protocol="TCP",
                src_port=80, dst_port=12345, tcp_window=65535, packet_size=60
            )
        ]
        
        result = await tcp_analyzer.analyze_stream(packets_with_scaling)
        
        assert result.window_scaling_factor >= 0
        assert result.max_window_size == 65535
        assert result.min_window_size == 32768


class TestUDPAnalyzer:
    """Test cases for UDP protocol analyzer."""
    
    @pytest.fixture
    def udp_analyzer(self):
        """Create UDP analyzer instance for testing."""
        return UDPAnalyzer()
    
    @pytest.fixture
    def udp_packets(self):
        """Create sample UDP packets for testing."""
        return [
            PacketData(
                frame_number=1,
                timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="UDP",
                src_port=53,
                dst_port=53,
                packet_size=64,
                udp_length=32
            ),
            PacketData(
                frame_number=2,
                timestamp="2025-01-15 10:00:00.050000",
                src_ip="8.8.8.8",
                dst_ip="192.168.1.100",
                protocol="UDP",
                src_port=53,
                dst_port=53,
                packet_size=128,
                udp_length=96
            )
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_udp_flow_basic(self, udp_analyzer, udp_packets):
        """Test basic UDP flow analysis."""
        result = await udp_analyzer.analyze_flow(udp_packets)
        
        assert isinstance(result, UDPAnalysisResult)
        assert result.total_packets == 2
        assert result.total_bytes == 192  # 64 + 128
        assert result.flow_duration > 0
        assert result.request_packets == 2  # Both packets to port 53 (DNS)
        assert result.response_packets == 0
    
    @pytest.mark.asyncio
    async def test_analyze_udp_packet_sizes(self, udp_analyzer, udp_packets):
        """Test UDP packet size analysis."""
        result = await udp_analyzer.analyze_flow(udp_packets)
        
        assert result.avg_packet_size == 96.0  # (64 + 128) / 2
        assert result.max_packet_size == 128
        assert result.min_packet_size == 64
        assert result.avg_payload_size == 64.0  # (32 + 96) / 2
    
    @pytest.mark.asyncio
    async def test_detect_udp_fragmentation(self, udp_analyzer):
        """Test UDP fragmentation detection."""
        large_udp_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12345, dst_port=80, packet_size=1500, udp_length=1472
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:00.001000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12345, dst_port=80, packet_size=1500, udp_length=1472
            )
        ]
        
        result = await udp_analyzer.analyze_flow(large_udp_packets)
        
        assert result.potential_fragmentation is True
        assert result.large_packets > 0
    
    @pytest.mark.asyncio
    async def test_calculate_udp_response_time(self, udp_analyzer, udp_packets):
        """Test UDP response time calculation."""
        result = await udp_analyzer.analyze_flow(udp_packets)
        
        # Response time should be 50ms (time between request and response)
        assert result.avg_response_time == 0.05
        assert result.min_response_time == 0.05
        assert result.max_response_time == 0.05


class TestHTTPAnalyzer:
    """Test cases for HTTP protocol analyzer."""
    
    @pytest.fixture
    def http_analyzer(self):
        """Create HTTP analyzer instance for testing."""
        return HTTPAnalyzer()
    
    @pytest.fixture
    def http_packets(self):
        """Create sample HTTP packets for testing."""
        return [
            PacketData(
                frame_number=1,
                timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="TCP",
                src_port=12345,
                dst_port=80,
                packet_size=200,
                http_method="GET",
                http_host="example.com",
                http_uri="/api/users"
            ),
            PacketData(
                frame_number=2,
                timestamp="2025-01-15 10:00:00.500000",
                src_ip="8.8.8.8",
                dst_ip="192.168.1.100",
                protocol="TCP",
                src_port=80,
                dst_port=12345,
                packet_size=1500,
                http_status=200
            )
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_http_transactions(self, http_analyzer, http_packets):
        """Test HTTP transaction analysis."""
        result = await http_analyzer.analyze_session(http_packets)
        
        assert isinstance(result, HTTPAnalysisResult)
        assert len(result.transactions) == 1
        
        transaction = result.transactions[0]
        assert transaction.method == "GET"
        assert transaction.uri == "/api/users"
        assert transaction.host == "example.com"
        assert transaction.status_code == 200
        assert transaction.response_time == 0.5  # 500ms
    
    @pytest.mark.asyncio
    async def test_analyze_http_performance_metrics(self, http_analyzer, http_packets):
        """Test HTTP performance metrics calculation."""
        result = await http_analyzer.analyze_session(http_packets)
        
        assert result.total_requests == 1
        assert result.total_responses == 1
        assert result.avg_response_time == 0.5
        assert result.total_bytes == 1700  # 200 + 1500
        assert result.request_bytes == 200
        assert result.response_bytes == 1500
    
    @pytest.mark.asyncio
    async def test_detect_http_errors(self, http_analyzer):
        """Test HTTP error detection."""
        error_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, http_method="GET", http_uri="/not-found",
                packet_size=150
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:00.100000",
                src_ip="8.8.8.8", dst_ip="192.168.1.100", protocol="TCP",
                src_port=80, dst_port=12345, http_status=404, packet_size=300
            )
        ]
        
        result = await http_analyzer.analyze_session(error_packets)
        
        assert result.error_count == 1
        assert result.error_rate == 1.0  # 100% error rate
        assert len(result.status_codes) == 1
        assert 404 in result.status_codes
    
    @pytest.mark.asyncio
    async def test_analyze_http_user_agents(self, http_analyzer):
        """Test HTTP User-Agent analysis."""
        ua_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, http_method="GET",
                packet_size=250
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:00.100000",
                src_ip="8.8.8.8", dst_ip="192.168.1.100", protocol="TCP",
                src_port=80, dst_port=12345, http_status=200,
                packet_size=500
            )
        ]
        
        # Mock User-Agent extraction
        with patch.object(http_analyzer, '_extract_user_agent', return_value="Mozilla/5.0 (Chrome)"):
            result = await http_analyzer.analyze_session(ua_packets)
            
            assert len(result.user_agents) == 1
            assert "Mozilla/5.0 (Chrome)" in result.user_agents


class TestDNSAnalyzer:
    """Test cases for DNS protocol analyzer."""
    
    @pytest.fixture
    def dns_analyzer(self):
        """Create DNS analyzer instance for testing."""
        return DNSAnalyzer()
    
    @pytest.fixture
    def dns_packets(self):
        """Create sample DNS packets for testing."""
        return [
            PacketData(
                frame_number=1,
                timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="UDP",
                src_port=12345,
                dst_port=53,
                packet_size=64,
                dns_query="example.com",
                dns_type="A"
            ),
            PacketData(
                frame_number=2,
                timestamp="2025-01-15 10:00:00.050000",
                src_ip="8.8.8.8",
                dst_ip="192.168.1.100",
                protocol="UDP",
                src_port=53,
                dst_port=12345,
                packet_size=128,
                dns_response="93.184.216.34"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_dns_queries(self, dns_analyzer, dns_packets):
        """Test DNS query analysis."""
        result = await dns_analyzer.analyze_traffic(dns_packets)
        
        assert isinstance(result, DNSAnalysisResult)
        assert result.total_queries == 1
        assert result.total_responses == 1
        assert result.avg_response_time == 0.05  # 50ms
        
        assert len(result.queries) == 1
        query = result.queries[0]
        assert query.domain == "example.com"
        assert query.query_type == "A"
        assert query.response_time == 0.05
    
    @pytest.mark.asyncio
    async def test_analyze_dns_performance(self, dns_analyzer, dns_packets):
        """Test DNS performance analysis."""
        result = await dns_analyzer.analyze_traffic(dns_packets)
        
        assert result.success_rate == 1.0  # 100% success
        assert result.avg_response_time == 0.05
        assert result.min_response_time == 0.05
        assert result.max_response_time == 0.05
        assert result.timeout_count == 0
    
    @pytest.mark.asyncio
    async def test_detect_dns_failures(self, dns_analyzer):
        """Test DNS failure detection."""
        failed_dns_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12345, dst_port=53, dns_query="nonexistent.com",
                dns_type="A", packet_size=64
            ),
            # No response packet = timeout/failure
        ]
        
        result = await dns_analyzer.analyze_traffic(failed_dns_packets)
        
        assert result.total_queries == 1
        assert result.total_responses == 0
        assert result.timeout_count == 1
        assert result.success_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_dns_query_types(self, dns_analyzer):
        """Test DNS query type distribution analysis."""
        mixed_dns_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12345, dst_port=53, dns_query="example.com",
                dns_type="A", packet_size=64
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12346, dst_port=53, dns_query="example.com",
                dns_type="AAAA", packet_size=64
            ),
            PacketData(
                frame_number=3, timestamp="2025-01-15 10:00:02.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12347, dst_port=53, dns_query="mail.example.com",
                dns_type="MX", packet_size=64
            )
        ]
        
        result = await dns_analyzer.analyze_traffic(mixed_dns_packets)
        
        assert result.query_types["A"] == 1
        assert result.query_types["AAAA"] == 1
        assert result.query_types["MX"] == 1
        assert len(result.top_domains) > 0


class TestProtocolAnalysisEngine:
    """Test cases for the protocol analysis engine."""
    
    @pytest.fixture
    def analysis_engine(self):
        """Create protocol analysis engine instance for testing."""
        return ProtocolAnalysisEngine()
    
    @pytest.mark.asyncio
    async def test_analyze_mixed_protocols(self, analysis_engine):
        """Test analysis of mixed protocol traffic."""
        mixed_packets = [
            # TCP packet
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12345, dst_port=80, packet_size=100
            ),
            # UDP packet
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP",
                src_port=12346, dst_port=53, packet_size=64
            ),
            # HTTP packet
            PacketData(
                frame_number=3, timestamp="2025-01-15 10:00:02.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP",
                src_port=12347, dst_port=80, http_method="GET", packet_size=200
            )
        ]
        
        results = await analysis_engine.analyze_protocols(mixed_packets)
        
        assert "tcp" in results
        assert "udp" in results
        assert "http" in results
        
        # Verify each analyzer was called appropriately
        assert isinstance(results["tcp"], TCPAnalysisResult)
        assert isinstance(results["udp"], UDPAnalysisResult)
        assert isinstance(results["http"], HTTPAnalysisResult)
    
    @pytest.mark.asyncio
    async def test_protocol_detection_accuracy(self, analysis_engine):
        """Test protocol detection accuracy."""
        test_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP", 
                dst_port=80, src_port=12345, packet_size=100
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP", 
                dst_port=443, src_port=12346, packet_size=100
            ),
            PacketData(
                frame_number=3, timestamp="2025-01-15 10:00:02.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP", 
                dst_port=53, src_port=12347, packet_size=64
            ),
            PacketData(
                frame_number=4, timestamp="2025-01-15 10:00:03.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP", 
                dst_port=67, src_port=12348, packet_size=300
            ),
        ]
        
        detected_protocols = analysis_engine.detect_protocols(test_packets)
        
        assert "http" in detected_protocols  # Port 80
        assert "https" in detected_protocols  # Port 443
        assert "dns" in detected_protocols  # Port 53
        assert "dhcp" in detected_protocols  # Port 67
    
    @pytest.mark.asyncio
    async def test_generate_protocol_summary(self, analysis_engine):
        """Test protocol analysis summary generation."""
        sample_packets = [
            PacketData(
                frame_number=1, timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="TCP", 
                dst_port=80, src_port=12345, packet_size=100
            ),
            PacketData(
                frame_number=2, timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100", dst_ip="8.8.8.8", protocol="UDP", 
                dst_port=53, src_port=12346, packet_size=64
            ),
        ]
        
        summary = await analysis_engine.generate_summary(sample_packets)
        
        assert "protocol_distribution" in summary
        assert "total_packets" in summary
        assert "analysis_results" in summary
        assert summary["total_packets"] == 2 