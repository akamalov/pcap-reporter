"""
Packet Processing Pipeline Service.

Advanced packet processing pipeline that uses tshark for high-speed packet extraction
and analysis, with support for filtering, stream reconstruction, and flow analysis.
"""

import asyncio
import subprocess
import json
import logging
import ipaddress
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from models.packet_data import (
    PacketData, PacketStream, ConversationFlow, FlowStatistics, PacketFilter
)

logger = logging.getLogger(__name__)


class PacketProcessingPipeline:
    """Advanced packet processing pipeline using tshark and custom analysis."""
    
    def __init__(self):
        """Initialize the packet processing pipeline."""
        self.tshark_path = "tshark"  # Assume tshark is in PATH
        self.max_packets_per_batch = 10000
        self.stream_timeout = 300  # 5 minutes
        
    async def extract_packets_with_tshark(
        self, 
        pcap_path: str, 
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None
    ) -> List[PacketData]:
        """
        Extract packets from PCAP file using tshark.
        
        Args:
            pcap_path: Path to the PCAP file
            filters: Optional list of display filters
            fields: Optional list of specific fields to extract
            
        Returns:
            List of PacketData objects
        """
        try:
            # Build tshark command
            cmd = [
                self.tshark_path,
                "-r", pcap_path,
                "-T", "json",
                "-e", "frame.number",
                "-e", "frame.time",
                "-e", "frame.len",
                "-e", "eth.src",
                "-e", "eth.dst",
                "-e", "ip.src",
                "-e", "ip.dst",
                "-e", "ip.proto",
                "-e", "tcp.srcport",
                "-e", "tcp.dstport",
                "-e", "tcp.flags",
                "-e", "tcp.seq",
                "-e", "tcp.ack",
                "-e", "tcp.window",
                "-e", "udp.srcport",
                "-e", "udp.dstport",
                "-e", "udp.length",
                "-e", "icmp.type",
                "-e", "icmp.code",
                "-e", "http.request.method",
                "-e", "http.host",
                "-e", "http.request.uri",
                "-e", "http.response.code",
                "-e", "dns.qry.name",
                "-e", "dns.resp.name",
                "-e", "dns.qry.type"
            ]
            
            # Add custom fields if specified
            if fields:
                for field in fields:
                    cmd.extend(["-e", field])
            
            # Add filters if specified
            if filters:
                filter_expr = " and ".join(filters)
                cmd.extend(["-Y", filter_expr])
            
            # Execute tshark
            logger.info(f"Executing tshark command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = f"tshark execution failed: {stderr.decode()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Parse JSON output
            if not stdout:
                logger.warning("No output from tshark")
                return []
            
            try:
                packet_data = json.loads(stdout.decode())
                return await self.process_packet_batch(packet_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tshark JSON output: {e}")
                raise RuntimeError(f"Invalid JSON output from tshark: {e}")
                
        except Exception as e:
            logger.error(f"Error extracting packets with tshark: {e}")
            raise
    
    async def process_packet_batch(self, packet_data: List[Dict]) -> List[PacketData]:
        """
        Process a batch of packet data from tshark JSON output.
        
        Args:
            packet_data: List of packet dictionaries from tshark
            
        Returns:
            List of PacketData objects
        """
        packets = []
        
        for packet_dict in packet_data:
            try:
                packet = await self._parse_packet_data(packet_dict)
                if packet:
                    packets.append(packet)
            except Exception as e:
                logger.warning(f"Failed to parse packet: {e}")
                continue
        
        logger.info(f"Processed {len(packets)} packets from {len(packet_data)} raw packets")
        return packets
    
    async def _parse_packet_data(self, packet_dict: Dict) -> Optional[PacketData]:
        """Parse individual packet data from tshark JSON."""
        try:
            source = packet_dict.get("_source", {})
            layers = source.get("layers", {})
            
            # Extract frame information
            frame = layers.get("frame", {})
            frame_number = int(frame.get("frame.number", [0])[0]) if frame.get("frame.number") else 0
            timestamp = frame.get("frame.time", [""])[0] if frame.get("frame.time") else ""
            packet_size = int(frame.get("frame.len", [0])[0]) if frame.get("frame.len") else 0
            
            # Extract IP information
            ip = layers.get("ip", {})
            src_ip = ip.get("ip.src", [""])[0] if ip.get("ip.src") else ""
            dst_ip = ip.get("ip.dst", [""])[0] if ip.get("ip.dst") else ""
            ip_proto = ip.get("ip.proto", [""])[0] if ip.get("ip.proto") else ""
            
            if not src_ip or not dst_ip:
                return None  # Skip non-IP packets for now
            
            # Determine protocol
            protocol = self._get_protocol_name(ip_proto)
            
            # Extract transport layer information
            src_port = None
            dst_port = None
            tcp_flags = None
            tcp_seq = None
            tcp_ack = None
            tcp_window = None
            udp_length = None
            icmp_type = None
            icmp_code = None
            
            if protocol == "TCP":
                tcp = layers.get("tcp", {})
                src_port = int(tcp.get("tcp.srcport", [0])[0]) if tcp.get("tcp.srcport") else None
                dst_port = int(tcp.get("tcp.dstport", [0])[0]) if tcp.get("tcp.dstport") else None
                tcp_flags = self._parse_tcp_flags(tcp.get("tcp.flags", [""])[0] if tcp.get("tcp.flags") else "")
                tcp_seq = int(tcp.get("tcp.seq", [0])[0]) if tcp.get("tcp.seq") else None
                tcp_ack = int(tcp.get("tcp.ack", [0])[0]) if tcp.get("tcp.ack") else None
                tcp_window = int(tcp.get("tcp.window", [0])[0]) if tcp.get("tcp.window") else None
                
            elif protocol == "UDP":
                udp = layers.get("udp", {})
                src_port = int(udp.get("udp.srcport", [0])[0]) if udp.get("udp.srcport") else None
                dst_port = int(udp.get("udp.dstport", [0])[0]) if udp.get("udp.dstport") else None
                udp_length = int(udp.get("udp.length", [0])[0]) if udp.get("udp.length") else None
                
            elif protocol == "ICMP":
                icmp = layers.get("icmp", {})
                icmp_type = int(icmp.get("icmp.type", [0])[0]) if icmp.get("icmp.type") else None
                icmp_code = int(icmp.get("icmp.code", [0])[0]) if icmp.get("icmp.code") else None
            
            # Extract application layer information
            http_method = None
            http_host = None
            http_uri = None
            http_status = None
            dns_query = None
            dns_response = None
            dns_type = None
            
            if "http" in layers:
                http = layers["http"]
                http_method = http.get("http.request.method", [""])[0] if http.get("http.request.method") else None
                http_host = http.get("http.host", [""])[0] if http.get("http.host") else None
                http_uri = http.get("http.request.uri", [""])[0] if http.get("http.request.uri") else None
                http_status_raw = http.get("http.response.code", [""])[0] if http.get("http.response.code") else None
                if http_status_raw:
                    try:
                        http_status = int(http_status_raw)
                    except:
                        pass
            
            if "dns" in layers:
                dns = layers["dns"]
                dns_query = dns.get("dns.qry.name", [""])[0] if dns.get("dns.qry.name") else None
                dns_response = dns.get("dns.resp.name", [""])[0] if dns.get("dns.resp.name") else None
                dns_type = dns.get("dns.qry.type", [""])[0] if dns.get("dns.qry.type") else None
            
            # Create PacketData object
            packet = PacketData(
                frame_number=frame_number,
                timestamp=timestamp,
                packet_size=packet_size,
                src_ip=src_ip,
                dst_ip=dst_ip,
                protocol=protocol,
                src_port=src_port,
                dst_port=dst_port,
                tcp_flags=tcp_flags,
                tcp_seq=tcp_seq,
                tcp_ack=tcp_ack,
                tcp_window=tcp_window,
                udp_length=udp_length,
                icmp_type=icmp_type,
                icmp_code=icmp_code,
                http_method=http_method,
                http_host=http_host,
                http_uri=http_uri,
                http_status=http_status,
                dns_query=dns_query,
                dns_response=dns_response,
                dns_type=dns_type
            )
            
            return packet
            
        except Exception as e:
            logger.warning(f"Failed to parse packet data: {e}")
            return None
    
    def _get_protocol_name(self, ip_proto: str) -> str:
        """Convert IP protocol number to name."""
        protocol_map = {
            "1": "ICMP",
            "6": "TCP",
            "17": "UDP",
            "2": "IGMP",
            "41": "IPv6",
            "47": "GRE",
            "50": "ESP",
            "51": "AH"
        }
        return protocol_map.get(ip_proto, "OTHER")
    
    def _parse_tcp_flags(self, flags_str: str) -> str:
        """Parse TCP flags from hex string to readable format."""
        if not flags_str or flags_str == "":
            return ""
        
        try:
            flags_int = int(flags_str, 16) if flags_str.startswith("0x") else int(flags_str)
            flag_names = []
            
            if flags_int & 0x01:  # FIN
                flag_names.append("FIN")
            if flags_int & 0x02:  # SYN
                flag_names.append("SYN")
            if flags_int & 0x04:  # RST
                flag_names.append("RST")
            if flags_int & 0x08:  # PSH
                flag_names.append("PSH")
            if flags_int & 0x10:  # ACK
                flag_names.append("ACK")
            if flags_int & 0x20:  # URG
                flag_names.append("URG")
            if flags_int & 0x40:  # ECE
                flag_names.append("ECE")
            if flags_int & 0x80:  # CWR
                flag_names.append("CWR")
                
            return ",".join(flag_names)
        except:
            return flags_str
    
    async def reconstruct_tcp_streams(self, packets: List[PacketData]) -> List[PacketStream]:
        """Reconstruct TCP streams from packet data."""
        streams = {}
        
        for packet in packets:
            if packet.protocol != "TCP":
                continue
                
            # Create stream key
            stream_key = packet.get_conversation_key()
            
            if stream_key not in streams:
                # Create new stream
                stream_id = f"tcp_stream_{len(streams) + 1}"
                
                # Determine client/server based on port numbers
                if packet.src_port and packet.dst_port:
                    if packet.src_port < packet.dst_port:
                        src_ip, src_port = packet.src_ip, packet.src_port
                        dst_ip, dst_port = packet.dst_ip, packet.dst_port
                    else:
                        src_ip, src_port = packet.dst_ip, packet.dst_port
                        dst_ip, dst_port = packet.src_ip, packet.src_port
                else:
                    src_ip, src_port = packet.src_ip, packet.src_port
                    dst_ip, dst_port = packet.dst_ip, packet.dst_port
                
                streams[stream_key] = PacketStream(
                    stream_id=stream_id,
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol="TCP"
                )
            
            # Add packet to stream
            streams[stream_key].add_packet(packet)
        
        # Analyze TCP handshakes
        for stream in streams.values():
            await self._analyze_tcp_handshake(stream)
        
        return list(streams.values())
    
    async def _analyze_tcp_handshake(self, stream: PacketStream):
        """Analyze TCP handshake completion in a stream."""
        if len(stream.packets) < 3:
            stream.handshake_complete = False
            return
        
        # Look for SYN, SYN-ACK, ACK sequence
        syn_seen = False
        syn_ack_seen = False
        ack_seen = False
        
        for packet in stream.packets[:10]:  # Check first 10 packets
            if packet.tcp_flags:
                flags = packet.tcp_flags.upper()
                if "SYN" in flags and "ACK" not in flags:
                    syn_seen = True
                elif "SYN" in flags and "ACK" in flags:
                    syn_ack_seen = True
                elif "ACK" in flags and syn_seen and syn_ack_seen:
                    ack_seen = True
                    break
        
        stream.handshake_complete = syn_seen and syn_ack_seen and ack_seen
        stream.connection_established = stream.handshake_complete
    
    async def reconstruct_udp_flows(self, packets: List[PacketData]) -> List[PacketStream]:
        """Reconstruct UDP flows from packet data."""
        flows = {}
        
        for packet in packets:
            if packet.protocol != "UDP":
                continue
                
            # Create flow key
            flow_key = packet.get_conversation_key()
            
            if flow_key not in flows:
                # Create new flow
                flow_id = f"udp_flow_{len(flows) + 1}"
                
                flows[flow_key] = PacketStream(
                    stream_id=flow_id,
                    src_ip=packet.src_ip,
                    dst_ip=packet.dst_ip,
                    src_port=packet.src_port,
                    dst_port=packet.dst_port,
                    protocol="UDP"
                )
            
            # Add packet to flow
            flows[flow_key].add_packet(packet)
        
        return list(flows.values())
    
    async def analyze_conversation_flows(self, packets: List[PacketData]) -> List[ConversationFlow]:
        """Analyze bidirectional conversation flows."""
        conversations = {}
        
        for packet in packets:
            conv_key = packet.get_conversation_key()
            
            if conv_key not in conversations:
                # Determine client/server based on port numbers and packet direction
                client_ip, client_port, server_ip, server_port = self._determine_client_server(packet)
                
                conversations[conv_key] = ConversationFlow(
                    conversation_id=f"conv_{len(conversations) + 1}",
                    client_ip=client_ip,
                    server_ip=server_ip,
                    client_port=client_port,
                    server_port=server_port,
                    protocol=packet.protocol,
                    start_time=packet.timestamp
                )
            
            # Update conversation statistics
            conv = conversations[conv_key]
            conv.packet_count += 1
            conv.total_bytes += packet.packet_size
            conv.end_time = packet.timestamp
            
            # Update directional statistics
            if packet.src_ip == conv.client_ip:
                conv.client_to_server_packets += 1
                conv.client_to_server_bytes += packet.packet_size
            else:
                conv.server_to_client_packets += 1
                conv.server_to_client_bytes += packet.packet_size
        
        return list(conversations.values())
    
    def _determine_client_server(self, packet: PacketData) -> Tuple[str, Optional[int], str, Optional[int]]:
        """Determine client and server based on packet characteristics."""
        # Simple heuristic: lower port number is usually the server
        if packet.src_port and packet.dst_port:
            if packet.src_port < packet.dst_port:
                return packet.dst_ip, packet.dst_port, packet.src_ip, packet.src_port
            else:
                return packet.src_ip, packet.src_port, packet.dst_ip, packet.dst_port
        else:
            # For protocols without ports, use IP order
            return packet.src_ip, packet.src_port, packet.dst_ip, packet.dst_port
    
    def filter_packets_by_protocol(self, packets: List[PacketData], protocol: str) -> List[PacketData]:
        """Filter packets by protocol."""
        return [p for p in packets if p.protocol.upper() == protocol.upper()]
    
    def filter_packets_by_port(self, packets: List[PacketData], port: int) -> List[PacketData]:
        """Filter packets by port (source or destination)."""
        return [p for p in packets if p.src_port == port or p.dst_port == port]
    
    def filter_packets_by_ip_range(self, packets: List[PacketData], ip_range: str) -> List[PacketData]:
        """Filter packets by IP address range."""
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            filtered_packets = []
            
            for packet in packets:
                try:
                    src_ip = ipaddress.ip_address(packet.src_ip)
                    dst_ip = ipaddress.ip_address(packet.dst_ip)
                    
                    if src_ip in network or dst_ip in network:
                        filtered_packets.append(packet)
                except:
                    continue
            
            return filtered_packets
        except:
            logger.warning(f"Invalid IP range: {ip_range}")
            return []
    
    async def calculate_stream_metrics(self, stream: PacketStream) -> Dict[str, Any]:
        """Calculate detailed metrics for a packet stream."""
        if not stream.packets:
            return {}
        
        duration = stream.get_duration()
        
        metrics = {
            "total_packets": len(stream.packets),
            "total_bytes": sum(p.packet_size for p in stream.packets),
            "duration": duration,
            "avg_packet_size": sum(p.packet_size for p in stream.packets) / len(stream.packets),
            "packets_per_second": len(stream.packets) / duration if duration > 0 else 0,
            "bytes_per_second": sum(p.packet_size for p in stream.packets) / duration if duration > 0 else 0
        }
        
        # Protocol-specific metrics
        if stream.protocol == "TCP":
            tcp_packets = [p for p in stream.packets if p.tcp_flags]
            metrics.update({
                "syn_packets": len([p for p in tcp_packets if "SYN" in (p.tcp_flags or "")]),
                "fin_packets": len([p for p in tcp_packets if "FIN" in (p.tcp_flags or "")]),
                "rst_packets": len([p for p in tcp_packets if "RST" in (p.tcp_flags or "")]),
                "handshake_complete": stream.handshake_complete
            })
        
        return metrics
    
    async def detect_protocol_anomalies(self, packets: List[PacketData]) -> List[Dict[str, Any]]:
        """Detect protocol-level anomalies in packet data."""
        anomalies = []
        
        for packet in packets:
            # Check for unusual port usage
            if packet.protocol == "TCP" and packet.src_port and packet.dst_port:
                # HTTP server port used as source (unusual)
                if packet.src_port == 80 and packet.dst_port > 1024:
                    anomalies.append({
                        "type": "unusual_port_usage",
                        "packet_number": packet.frame_number,
                        "description": "HTTP server port used as source port",
                        "severity": "medium"
                    })
                
                # Very large packet size for certain protocols
                if packet.src_port == 80 or packet.dst_port == 80:  # HTTP
                    if packet.packet_size > 1400:  # Larger than typical MTU
                        anomalies.append({
                            "type": "large_packet",
                            "packet_number": packet.frame_number,
                            "description": f"Unusually large HTTP packet: {packet.packet_size} bytes",
                            "severity": "low"
                        })
        
        return anomalies 