"""
Data models for packet processing and analysis.

Defines structures for storing packet data, streams, and conversation flows
used in the packet processing pipeline.
"""

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import ipaddress


class PacketData(BaseModel):
    """Individual packet data structure."""
    
    # Frame information
    frame_number: int
    timestamp: str
    packet_size: int = Field(default=0)
    
    # Network layer
    src_ip: str
    dst_ip: str
    protocol: str
    
    # Transport layer
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    
    # TCP specific
    tcp_flags: Optional[str] = None
    tcp_seq: Optional[int] = None
    tcp_ack: Optional[int] = None
    tcp_window: Optional[int] = None
    
    # UDP specific
    udp_length: Optional[int] = None
    
    # ICMP specific
    icmp_type: Optional[int] = None
    icmp_code: Optional[int] = None
    
    # Application layer
    http_method: Optional[str] = None
    http_host: Optional[str] = None
    http_uri: Optional[str] = None
    http_status: Optional[int] = None
    
    dns_query: Optional[str] = None
    dns_response: Optional[str] = None
    dns_type: Optional[str] = None
    
    # Additional metadata
    payload_size: Optional[int] = None
    is_encrypted: Optional[bool] = None
    vlan_id: Optional[int] = None
    
    def get_flow_key(self) -> str:
        """Generate a unique flow key for this packet."""
        if self.src_port and self.dst_port:
            return f"{self.src_ip}:{self.src_port}->{self.dst_ip}:{self.dst_port}"
        return f"{self.src_ip}->{self.dst_ip}"
    
    def get_conversation_key(self) -> str:
        """Generate a bidirectional conversation key."""
        if self.src_port and self.dst_port:
            # Sort IPs and ports to ensure consistent key regardless of direction
            if (self.src_ip, self.src_port) < (self.dst_ip, self.dst_port):
                return f"{self.src_ip}:{self.src_port}<->{self.dst_ip}:{self.dst_port}"
            else:
                return f"{self.dst_ip}:{self.dst_port}<->{self.src_ip}:{self.src_port}"
        else:
            # For protocols without ports
            if self.src_ip < self.dst_ip:
                return f"{self.src_ip}<->{self.dst_ip}"
            else:
                return f"{self.dst_ip}<->{self.src_ip}"
    
    def is_tcp_handshake(self) -> bool:
        """Check if this packet is part of TCP handshake."""
        if self.protocol != "TCP" or not self.tcp_flags:
            return False
        
        flags = self.tcp_flags.upper()
        return "SYN" in flags or ("SYN" in flags and "ACK" in flags)
    
    def is_tcp_teardown(self) -> bool:
        """Check if this packet is part of TCP teardown."""
        if self.protocol != "TCP" or not self.tcp_flags:
            return False
        
        flags = self.tcp_flags.upper()
        return "FIN" in flags or "RST" in flags
    
    def get_timestamp_ms(self) -> float:
        """Convert timestamp to milliseconds since epoch."""
        try:
            dt = datetime.fromisoformat(self.timestamp.replace(' ', 'T'))
            return dt.timestamp() * 1000
        except:
            return 0.0


class PacketStream(BaseModel):
    """Represents a stream of related packets (TCP connection or UDP flow)."""
    
    stream_id: str
    src_ip: str
    dst_ip: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: str
    
    # Stream metadata
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    packets: List[PacketData] = Field(default_factory=list)
    
    # TCP specific
    handshake_complete: Optional[bool] = None
    connection_established: Optional[bool] = None
    connection_closed: Optional[bool] = None
    
    # Stream statistics
    total_bytes: int = Field(default=0)
    packet_count: int = Field(default=0)
    retransmissions: int = Field(default=0)
    out_of_order: int = Field(default=0)
    
    # Application layer data
    application_protocol: Optional[str] = None
    payload_data: Optional[bytes] = None
    
    def get_conversation_key(self) -> str:
        """Generate conversation key for this stream."""
        if self.src_port and self.dst_port:
            if (self.src_ip, self.src_port) < (self.dst_ip, self.dst_port):
                return f"{self.src_ip}:{self.src_port}<->{self.dst_ip}:{self.dst_port}"
            else:
                return f"{self.dst_ip}:{self.dst_port}<->{self.src_ip}:{self.src_port}"
        return f"{self.src_ip}<->{self.dst_ip}"
    
    def add_packet(self, packet: PacketData):
        """Add a packet to this stream."""
        self.packets.append(packet)
        self.packet_count += 1
        self.total_bytes += packet.packet_size
        
        # Update timing
        if not self.start_time or packet.timestamp < self.start_time:
            self.start_time = packet.timestamp
        if not self.end_time or packet.timestamp > self.end_time:
            self.end_time = packet.timestamp
    
    def get_duration(self) -> float:
        """Get stream duration in seconds."""
        if not self.start_time or not self.end_time:
            return 0.0
        
        try:
            start_dt = datetime.fromisoformat(self.start_time.replace(' ', 'T'))
            end_dt = datetime.fromisoformat(self.end_time.replace(' ', 'T'))
            return (end_dt - start_dt).total_seconds()
        except:
            return 0.0
    
    def get_throughput_bps(self) -> float:
        """Calculate throughput in bytes per second."""
        duration = self.get_duration()
        return self.total_bytes / duration if duration > 0 else 0.0
    
    def get_packet_rate(self) -> float:
        """Calculate packet rate in packets per second."""
        duration = self.get_duration()
        return self.packet_count / duration if duration > 0 else 0.0


class ConversationFlow(BaseModel):
    """Represents a bidirectional conversation between two endpoints."""
    
    conversation_id: str
    client_ip: str
    server_ip: str
    client_port: Optional[int] = None
    server_port: Optional[int] = None
    protocol: str
    
    # Timing information
    start_time: str
    end_time: Optional[str] = None
    
    # Flow statistics
    packet_count: int = Field(default=0)
    total_bytes: int = Field(default=0)
    
    # Directional statistics
    client_to_server_packets: int = Field(default=0)
    server_to_client_packets: int = Field(default=0)
    client_to_server_bytes: int = Field(default=0)
    server_to_client_bytes: int = Field(default=0)
    
    # Quality metrics
    avg_response_time: Optional[float] = None
    packet_loss_rate: Optional[float] = None
    retransmission_rate: Optional[float] = None
    
    # Application layer
    application_protocol: Optional[str] = None
    service_name: Optional[str] = None
    
    # Security indicators
    suspicious_activity: bool = Field(default=False)
    anomaly_score: float = Field(default=0.0)
    
    def get_duration(self) -> float:
        """Get conversation duration in seconds."""
        if not self.end_time:
            return 0.0
        
        try:
            start_dt = datetime.fromisoformat(self.start_time.replace(' ', 'T'))
            end_dt = datetime.fromisoformat(self.end_time.replace(' ', 'T'))
            return (end_dt - start_dt).total_seconds()
        except:
            return 0.0
    
    def get_throughput_bps(self) -> float:
        """Calculate total throughput in bytes per second."""
        duration = self.get_duration()
        return self.total_bytes / duration if duration > 0 else 0.0
    
    def get_asymmetry_ratio(self) -> float:
        """Calculate traffic asymmetry ratio (0.5 = balanced, 0.0/1.0 = one-way)."""
        if self.total_bytes == 0:
            return 0.5
        
        return self.client_to_server_bytes / self.total_bytes
    
    def is_interactive(self) -> bool:
        """Determine if this is an interactive conversation based on packet patterns."""
        if self.packet_count < 4:  # Need minimum packets for interaction
            return False
        
        # Interactive if packets go both ways
        return (self.client_to_server_packets > 0 and 
                self.server_to_client_packets > 0)
    
    def get_conversation_key(self) -> str:
        """Generate unique key for this conversation."""
        if self.client_port and self.server_port:
            return f"{self.client_ip}:{self.client_port}<->{self.server_ip}:{self.server_port}"
        return f"{self.client_ip}<->{self.server_ip}"


class FlowStatistics(BaseModel):
    """Statistics for a collection of flows."""
    
    total_flows: int = Field(default=0)
    total_packets: int = Field(default=0)
    total_bytes: int = Field(default=0)
    
    # Protocol breakdown
    tcp_flows: int = Field(default=0)
    udp_flows: int = Field(default=0)
    icmp_flows: int = Field(default=0)
    other_flows: int = Field(default=0)
    
    # Timing statistics
    avg_flow_duration: float = Field(default=0.0)
    max_flow_duration: float = Field(default=0.0)
    min_flow_duration: float = Field(default=0.0)
    
    # Traffic patterns
    top_talkers: List[Dict[str, Any]] = Field(default_factory=list)
    port_distribution: Dict[int, int] = Field(default_factory=dict)
    protocol_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Quality metrics
    flows_with_retransmissions: int = Field(default=0)
    flows_with_packet_loss: int = Field(default=0)
    average_throughput: float = Field(default=0.0)


class PacketFilter(BaseModel):
    """Configuration for packet filtering."""
    
    # Protocol filters
    protocols: Optional[List[str]] = None
    
    # IP filters
    src_ips: Optional[List[str]] = None
    dst_ips: Optional[List[str]] = None
    ip_ranges: Optional[List[str]] = None
    
    # Port filters
    src_ports: Optional[List[int]] = None
    dst_ports: Optional[List[int]] = None
    port_ranges: Optional[List[str]] = None
    
    # Size filters
    min_packet_size: Optional[int] = None
    max_packet_size: Optional[int] = None
    
    # Time filters
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    # Application filters
    http_methods: Optional[List[str]] = None
    dns_query_types: Optional[List[str]] = None
    
    def matches_packet(self, packet: PacketData) -> bool:
        """Check if a packet matches this filter."""
        
        # Protocol filter
        if self.protocols and packet.protocol not in self.protocols:
            return False
        
        # IP filters
        if self.src_ips and packet.src_ip not in self.src_ips:
            return False
        
        if self.dst_ips and packet.dst_ip not in self.dst_ips:
            return False
        
        # IP range filters
        if self.ip_ranges:
            ip_in_range = False
            for ip_range in self.ip_ranges:
                try:
                    network = ipaddress.ip_network(ip_range, strict=False)
                    if (ipaddress.ip_address(packet.src_ip) in network or 
                        ipaddress.ip_address(packet.dst_ip) in network):
                        ip_in_range = True
                        break
                except:
                    continue
            if not ip_in_range:
                return False
        
        # Port filters
        if self.src_ports and packet.src_port not in self.src_ports:
            return False
        
        if self.dst_ports and packet.dst_port not in self.dst_ports:
            return False
        
        # Size filters
        if self.min_packet_size and packet.packet_size < self.min_packet_size:
            return False
        
        if self.max_packet_size and packet.packet_size > self.max_packet_size:
            return False
        
        # Time filters
        if self.start_time and packet.timestamp < self.start_time:
            return False
        
        if self.end_time and packet.timestamp > self.end_time:
            return False
        
        # Application filters
        if self.http_methods and packet.http_method not in self.http_methods:
            return False
        
        if self.dns_query_types and packet.dns_type not in self.dns_query_types:
            return False
        
        return True 