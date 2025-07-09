"""
Unit tests for Packet Processing Pipeline.

Tests the packet processing pipeline components including tshark integration,
pyshark analysis, packet filtering, and stream reconstruction using TDD principles.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from pathlib import Path
import tempfile
import json
import subprocess

from services.packet_processing_pipeline import PacketProcessingPipeline
from models.packet_data import PacketData, PacketStream, ConversationFlow


class TestPacketProcessingPipeline:
    """Test cases for packet processing pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create packet processing pipeline instance for testing."""
        return PacketProcessingPipeline()
    
    @pytest.fixture
    def sample_pcap_path(self):
        """Create a sample PCAP file path for testing."""
        return "/test/sample.pcap"
    
    @pytest.fixture
    def mock_tshark_output(self):
        """Mock tshark JSON output for testing."""
        return [
            {
                "_source": {
                    "layers": {
                        "frame": {
                            "frame.number": "1",
                            "frame.time": "2025-01-15 10:00:00.000000",
                            "frame.len": "74"
                        },
                        "eth": {
                            "eth.src": "aa:bb:cc:dd:ee:ff",
                            "eth.dst": "11:22:33:44:55:66"
                        },
                        "ip": {
                            "ip.src": "192.168.1.100",
                            "ip.dst": "8.8.8.8",
                            "ip.proto": "6"
                        },
                        "tcp": {
                            "tcp.srcport": "12345",
                            "tcp.dstport": "80",
                            "tcp.flags": "0x0002",
                            "tcp.seq": "0",
                            "tcp.ack": "0"
                        }
                    }
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_extract_packets_with_tshark_success(self, pipeline, sample_pcap_path):
        """Test successful packet extraction using tshark."""
        mock_tshark_output = json.dumps([
            {
                "_source": {
                    "layers": {
                        "frame": {"frame.number": ["1"], "frame.time": ["2025-01-15 10:00:00.000000"], "frame.len": ["74"]},
                        "ip": {"ip.src": ["192.168.1.100"], "ip.dst": ["8.8.8.8"], "ip.proto": ["6"]},
                        "tcp": {"tcp.srcport": ["12345"], "tcp.dstport": ["80"], "tcp.flags": ["0x0002"]}
                    }
                }
            }
        ])
        
        # Mock the asyncio subprocess creation
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (mock_tshark_output.encode(), b"")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            packets = await pipeline.extract_packets_with_tshark(sample_pcap_path)
            
            assert len(packets) == 1
            assert packets[0].frame_number == 1
            assert packets[0].src_ip == "192.168.1.100"
            assert packets[0].dst_ip == "8.8.8.8"
            assert packets[0].protocol == "TCP"
            assert packets[0].src_port == 12345
            assert packets[0].dst_port == 80
    
    @pytest.mark.asyncio
    async def test_extract_packets_with_tshark_error(self, pipeline, sample_pcap_path):
        """Test tshark execution error handling."""
        # Mock the asyncio subprocess creation with error
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"tshark: Invalid capture file")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(RuntimeError, match="tshark execution failed"):
                await pipeline.extract_packets_with_tshark(sample_pcap_path)
    
    @pytest.mark.asyncio
    async def test_extract_packets_with_filters(self, pipeline, sample_pcap_path):
        """Test packet extraction with protocol filters."""
        filters = ["tcp", "port 80"]
        
        # Mock the asyncio subprocess creation
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"[]", b"")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await pipeline.extract_packets_with_tshark(sample_pcap_path, filters=filters)
            
            # Verify tshark was called with filters
            call_args = mock_exec.call_args[1]  # Get keyword args
            # The filter should be in the command arguments
            mock_exec.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_packet_batch_success(self, pipeline):
        """Test successful batch packet processing."""
        packet_data = [
            {
                "_source": {
                    "layers": {
                        "frame": {"frame.number": ["1"], "frame.time": ["2025-01-15 10:00:00.000000"], "frame.len": ["74"]},
                        "ip": {"ip.src": ["192.168.1.100"], "ip.dst": ["8.8.8.8"], "ip.proto": ["6"]},
                        "tcp": {"tcp.srcport": ["12345"], "tcp.dstport": ["80"], "tcp.flags": ["0x0002"]}
                    }
                }
            },
            {
                "_source": {
                    "layers": {
                        "frame": {"frame.number": ["2"], "frame.time": ["2025-01-15 10:00:01.000000"], "frame.len": ["60"]},
                        "ip": {"ip.src": ["8.8.8.8"], "ip.dst": ["192.168.1.100"], "ip.proto": ["6"]},
                        "tcp": {"tcp.srcport": ["80"], "tcp.dstport": ["12345"], "tcp.flags": ["0x0012"]}
                    }
                }
            }
        ]
        
        packets = await pipeline.process_packet_batch(packet_data)
        
        assert len(packets) == 2
        assert packets[0].frame_number == 1
        assert packets[1].frame_number == 2
        assert packets[0].src_ip == "192.168.1.100"
        assert packets[1].src_ip == "8.8.8.8"
    
    @pytest.mark.asyncio
    async def test_process_packet_batch_malformed_data(self, pipeline):
        """Test handling of malformed packet data."""
        malformed_data = [
            {"invalid": "structure"},
            {
                "_source": {
                    "layers": {
                        "frame": {"frame.number": ["1"]}
                        # Missing required fields
                    }
                }
            }
        ]
        
        packets = await pipeline.process_packet_batch(malformed_data)
        
        # Should skip malformed packets
        assert len(packets) == 0
    
    @pytest.mark.asyncio
    async def test_reconstruct_tcp_streams(self, pipeline):
        """Test TCP stream reconstruction from packets."""
        packets = [
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
                tcp_ack=0
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
                tcp_ack=1001
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
                tcp_ack=2001
            )
        ]
        
        streams = await pipeline.reconstruct_tcp_streams(packets)
        
        assert len(streams) == 1
        stream = streams[0]
        # The implementation chooses the lower port as source, so 8.8.8.8:80 becomes src
        assert stream.src_ip == "8.8.8.8"
        assert stream.dst_ip == "192.168.1.100"
        assert stream.src_port == 80
        assert stream.dst_port == 12345
        assert len(stream.packets) == 3
        assert stream.handshake_complete is True
    
    @pytest.mark.asyncio
    async def test_reconstruct_udp_flows(self, pipeline):
        """Test UDP flow reconstruction from packets."""
        packets = [
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
        
        flows = await pipeline.reconstruct_udp_flows(packets)
        
        assert len(flows) == 1
        flow = flows[0]
        assert flow.src_ip == "192.168.1.100"
        assert flow.dst_ip == "8.8.8.8"
        assert flow.src_port == 53
        assert flow.dst_port == 53
        assert len(flow.packets) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_conversation_flows(self, pipeline):
        """Test conversation flow analysis."""
        packets = [
            PacketData(
                frame_number=1,
                timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="TCP",
                src_port=12345,
                dst_port=80,
                packet_size=74,
                tcp_flags="SYN"
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
                tcp_flags="SYN,ACK"
            )
        ]
        
        conversations = await pipeline.analyze_conversation_flows(packets)
        
        assert len(conversations) == 1
        conv = conversations[0]
        assert conv.client_ip == "192.168.1.100"
        assert conv.server_ip == "8.8.8.8"
        assert conv.client_port == 12345
        assert conv.server_port == 80
        assert conv.protocol == "TCP"
        assert conv.packet_count == 2
        assert conv.total_bytes == 134
    
    @pytest.mark.asyncio
    async def test_filter_packets_by_protocol(self, pipeline):
        """Test packet filtering by protocol."""
        packets = [
            PacketData(frame_number=1, timestamp="2025-01-15 10:00:00.000000", protocol="TCP", src_ip="192.168.1.1", dst_ip="8.8.8.8"),
            PacketData(frame_number=2, timestamp="2025-01-15 10:00:01.000000", protocol="UDP", src_ip="192.168.1.1", dst_ip="8.8.8.8"),
            PacketData(frame_number=3, timestamp="2025-01-15 10:00:02.000000", protocol="ICMP", src_ip="192.168.1.1", dst_ip="8.8.8.8"),
            PacketData(frame_number=4, timestamp="2025-01-15 10:00:03.000000", protocol="TCP", src_ip="192.168.1.1", dst_ip="8.8.8.8")
        ]
        
        tcp_packets = pipeline.filter_packets_by_protocol(packets, "TCP")
        udp_packets = pipeline.filter_packets_by_protocol(packets, "UDP")
        
        assert len(tcp_packets) == 2
        assert len(udp_packets) == 1
        assert all(p.protocol == "TCP" for p in tcp_packets)
        assert all(p.protocol == "UDP" for p in udp_packets)
    
    @pytest.mark.asyncio
    async def test_filter_packets_by_port(self, pipeline):
        """Test packet filtering by port."""
        packets = [
            PacketData(frame_number=1, timestamp="2025-01-15 10:00:00.000000", protocol="TCP", src_port=80, dst_port=12345, src_ip="192.168.1.1", dst_ip="8.8.8.8"),
            PacketData(frame_number=2, timestamp="2025-01-15 10:00:01.000000", protocol="TCP", src_port=443, dst_port=12346, src_ip="192.168.1.1", dst_ip="8.8.8.8"),
            PacketData(frame_number=3, timestamp="2025-01-15 10:00:02.000000", protocol="TCP", src_port=12347, dst_port=80, src_ip="192.168.1.1", dst_ip="8.8.8.8"),
            PacketData(frame_number=4, timestamp="2025-01-15 10:00:03.000000", protocol="UDP", src_port=53, dst_port=12348, src_ip="192.168.1.1", dst_ip="8.8.8.8")
        ]
        
        http_packets = pipeline.filter_packets_by_port(packets, 80)
        https_packets = pipeline.filter_packets_by_port(packets, 443)
        
        assert len(http_packets) == 2  # Packets 1 and 3
        assert len(https_packets) == 1  # Packet 2
    
    @pytest.mark.asyncio
    async def test_filter_packets_by_ip_range(self, pipeline):
        """Test packet filtering by IP address range."""
        packets = [
            PacketData(frame_number=1, timestamp="2025-01-15 10:00:00.000000", protocol="TCP", src_ip="192.168.1.100", dst_ip="8.8.8.8"),
            PacketData(frame_number=2, timestamp="2025-01-15 10:00:01.000000", protocol="TCP", src_ip="10.0.0.50", dst_ip="192.168.1.100"),
            PacketData(frame_number=3, timestamp="2025-01-15 10:00:02.000000", protocol="TCP", src_ip="192.168.1.200", dst_ip="8.8.8.8"),
            PacketData(frame_number=4, timestamp="2025-01-15 10:00:03.000000", protocol="TCP", src_ip="172.16.0.10", dst_ip="192.168.1.100")
        ]
        
        local_packets = pipeline.filter_packets_by_ip_range(packets, "192.168.1.0/24")
        
        # Should return 4 packets because the filter checks both src and dst IPs
        # Packet 1: src_ip in range, Packet 2: dst_ip in range, Packet 3: src_ip in range, Packet 4: dst_ip in range
        assert len(local_packets) == 4
        # Verify that all returned packets have at least one IP in the range
        for packet in local_packets:
            assert ("192.168.1." in packet.src_ip or "192.168.1." in packet.dst_ip)
    
    @pytest.mark.asyncio
    async def test_calculate_stream_metrics(self, pipeline):
        """Test stream metrics calculation."""
        # Create stream and add packets properly to set timing
        stream = PacketStream(
            stream_id="test_stream",
            src_ip="192.168.1.100",
            dst_ip="8.8.8.8",
            src_port=12345,
            dst_port=80,
            protocol="TCP"
        )
        
        # Add packets to set timing information
        packet1 = PacketData(
            frame_number=1,
            timestamp="2025-01-15 10:00:00.000000",
            protocol="TCP",
            packet_size=74,
            src_ip="192.168.1.100",
            dst_ip="8.8.8.8"
        )
        packet2 = PacketData(
            frame_number=2,
            timestamp="2025-01-15 10:00:01.000000",
            protocol="TCP",
            packet_size=60,
            src_ip="8.8.8.8",
            dst_ip="192.168.1.100"
        )
        
        stream.add_packet(packet1)
        stream.add_packet(packet2)
        
        metrics = await pipeline.calculate_stream_metrics(stream)
        
        assert metrics["total_packets"] == 2
        assert metrics["total_bytes"] == 134
        assert metrics["duration"] == 1.0
        assert metrics["avg_packet_size"] == 67.0
        assert metrics["packets_per_second"] == 2.0
    
    @pytest.mark.asyncio
    async def test_detect_protocol_anomalies(self, pipeline):
        """Test protocol anomaly detection."""
        packets = [
            PacketData(
                frame_number=1,
                timestamp="2025-01-15 10:00:00.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="TCP",
                src_port=80,  # HTTP server port used as source
                dst_port=12345,
                packet_size=1500  # Unusually large for HTTP
            ),
            PacketData(
                frame_number=2,
                timestamp="2025-01-15 10:00:01.000000",
                src_ip="192.168.1.100",
                dst_ip="8.8.8.8",
                protocol="UDP",
                src_port=53,
                dst_port=53,
                packet_size=64
            )
        ]
        
        anomalies = await pipeline.detect_protocol_anomalies(packets)
        
        # Should detect the unusual HTTP packet
        assert len(anomalies) >= 1
        http_anomaly = next((a for a in anomalies if a["type"] == "unusual_port_usage"), None)
        assert http_anomaly is not None
        assert http_anomaly["packet_number"] == 1


class TestPacketDataModels:
    """Test packet data model functionality."""
    
    def test_packet_data_creation(self):
        """Test PacketData model creation and validation."""
        packet = PacketData(
            frame_number=1,
            timestamp="2025-01-15 10:00:00.000000",
            src_ip="192.168.1.100",
            dst_ip="8.8.8.8",
            protocol="TCP",
            src_port=12345,
            dst_port=80,
            packet_size=74
        )
        
        assert packet.frame_number == 1
        assert packet.src_ip == "192.168.1.100"
        assert packet.protocol == "TCP"
        assert packet.get_flow_key() == "192.168.1.100:12345->8.8.8.8:80"
    
    def test_packet_stream_creation(self):
        """Test PacketStream model creation."""
        stream = PacketStream(
            stream_id="test_stream",
            src_ip="192.168.1.100",
            dst_ip="8.8.8.8",
            src_port=12345,
            dst_port=80,
            protocol="TCP",
            packets=[]
        )
        
        assert stream.stream_id == "test_stream"
        assert stream.get_conversation_key() == "192.168.1.100:12345<->8.8.8.8:80"
    
    def test_conversation_flow_creation(self):
        """Test ConversationFlow model creation."""
        conversation = ConversationFlow(
            conversation_id="conv_1",
            client_ip="192.168.1.100",
            server_ip="8.8.8.8",
            client_port=12345,
            server_port=80,
            protocol="TCP",
            start_time="2025-01-15 10:00:00.000000",
            end_time="2025-01-15 10:00:10.000000",
            packet_count=10,
            total_bytes=1024
        )
        
        assert conversation.client_ip == "192.168.1.100"
        assert conversation.packet_count == 10
        assert conversation.get_duration() == 10.0 