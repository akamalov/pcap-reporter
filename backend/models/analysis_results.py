"""
Data models for PCAP analysis results.

Defines the structure for storing and returning network analysis results
including traffic statistics, performance metrics, and detected issues.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SeverityLevel(str, Enum):
    """Severity levels for network issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Types of network issues that can be detected."""
    HIGH_LATENCY = "high_latency"
    PACKET_LOSS = "packet_loss"
    DNS_ISSUES = "dns_issues"
    TCP_ERRORS = "tcp_errors"
    CONNECTION_FAILURES = "connection_failures"
    BANDWIDTH_ISSUES = "bandwidth_issues"
    SECURITY_ANOMALIES = "security_anomalies"
    PROTOCOL_ERRORS = "protocol_errors"


class TrafficStats(BaseModel):
    """Basic traffic statistics from PCAP analysis."""
    total_packets: int = Field(..., description="Total number of packets")
    total_bytes: int = Field(..., description="Total bytes transferred")
    duration: float = Field(..., description="Capture duration in seconds")
    avg_packet_size: float = Field(..., description="Average packet size in bytes")
    packets_per_second: float = Field(..., description="Average packets per second")
    bytes_per_second: float = Field(default=0.0, description="Average bytes per second")


class PerformanceMetrics(BaseModel):
    """Network performance metrics."""
    avg_latency: float = Field(..., description="Average latency in seconds")
    max_latency: float = Field(..., description="Maximum latency in seconds")
    min_latency: float = Field(default=0.0, description="Minimum latency in seconds")
    packet_loss_rate: float = Field(..., description="Packet loss rate (0.0 to 1.0)")
    throughput_mbps: float = Field(..., description="Throughput in Mbps")
    jitter: float = Field(default=0.0, description="Jitter in seconds")
    retransmission_rate: float = Field(default=0.0, description="TCP retransmission rate")


class NetworkIssue(BaseModel):
    """Represents a detected network issue."""
    type: IssueType = Field(..., description="Type of issue detected")
    severity: SeverityLevel = Field(..., description="Severity level of the issue")
    description: str = Field(..., description="Human-readable description")
    affected_hosts: List[str] = Field(default_factory=list, description="List of affected IP addresses")
    affected_protocols: List[str] = Field(default_factory=list, description="List of affected protocols")
    recommendation: str = Field(default="", description="Recommended solution")
    confidence: float = Field(default=1.0, description="Confidence level (0.0 to 1.0)")
    first_seen: Optional[str] = Field(default=None, description="Timestamp when first detected")
    last_seen: Optional[str] = Field(default=None, description="Timestamp when last detected")
    count: int = Field(default=1, description="Number of occurrences")


class ProtocolStats(BaseModel):
    """Protocol-specific statistics."""
    tcp_packets: int = Field(default=0, description="Number of TCP packets")
    udp_packets: int = Field(default=0, description="Number of UDP packets")
    icmp_packets: int = Field(default=0, description="Number of ICMP packets")
    http_sessions: int = Field(default=0, description="Number of HTTP sessions")
    https_sessions: int = Field(default=0, description="Number of HTTPS sessions")
    dns_queries: int = Field(default=0, description="Number of DNS queries")
    dhcp_packets: int = Field(default=0, description="Number of DHCP packets")
    arp_packets: int = Field(default=0, description="Number of ARP packets")
    other_packets: int = Field(default=0, description="Number of other protocol packets")


class TCPAnalysis(BaseModel):
    """TCP-specific analysis results."""
    total_connections: int = Field(default=0, description="Total TCP connections")
    successful_connections: int = Field(default=0, description="Successful TCP connections")
    failed_connections: int = Field(default=0, description="Failed TCP connections")
    avg_handshake_time: float = Field(default=0.0, description="Average TCP handshake time")
    max_handshake_time: float = Field(default=0.0, description="Maximum TCP handshake time")
    retransmissions: int = Field(default=0, description="Total retransmissions")
    duplicate_acks: int = Field(default=0, description="Duplicate ACK count")
    zero_windows: int = Field(default=0, description="Zero window events")
    reset_connections: int = Field(default=0, description="Reset connections")


class DNSAnalysis(BaseModel):
    """DNS-specific analysis results."""
    total_queries: int = Field(default=0, description="Total DNS queries")
    successful_queries: int = Field(default=0, description="Successful DNS queries")
    failed_queries: int = Field(default=0, description="Failed DNS queries")
    avg_response_time: float = Field(default=0.0, description="Average DNS response time")
    max_response_time: float = Field(default=0.0, description="Maximum DNS response time")
    timeout_queries: int = Field(default=0, description="Timed out queries")
    nxdomain_responses: int = Field(default=0, description="NXDOMAIN responses")
    servfail_responses: int = Field(default=0, description="SERVFAIL responses")


class ConversationFlow(BaseModel):
    """Represents a conversation between two endpoints."""
    src_ip: str = Field(..., description="Source IP address")
    dst_ip: str = Field(..., description="Destination IP address")
    src_port: int = Field(..., description="Source port")
    dst_port: int = Field(..., description="Destination port")
    protocol: str = Field(..., description="Protocol (TCP/UDP)")
    packets_sent: int = Field(default=0, description="Packets sent from source")
    packets_received: int = Field(default=0, description="Packets received by source")
    bytes_sent: int = Field(default=0, description="Bytes sent from source")
    bytes_received: int = Field(default=0, description="Bytes received by source")
    duration: float = Field(default=0.0, description="Conversation duration")
    start_time: Optional[str] = Field(default=None, description="Conversation start time")
    end_time: Optional[str] = Field(default=None, description="Conversation end time")


class AnalysisResults(BaseModel):
    """Complete PCAP analysis results."""
    # Basic information
    file_path: str = Field(..., description="Path to analyzed PCAP file")
    file_size: int = Field(..., description="PCAP file size in bytes")
    analysis_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), 
                                   description="When analysis was performed")
    
    # Traffic statistics
    traffic_stats: TrafficStats = Field(..., description="Basic traffic statistics")
    performance_metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    protocol_stats: ProtocolStats = Field(default_factory=ProtocolStats, description="Protocol statistics")
    
    # Analysis results
    issues: List[NetworkIssue] = Field(default_factory=list, description="Detected network issues")
    tcp_analysis: Optional[TCPAnalysis] = Field(default=None, description="TCP-specific analysis")
    dns_analysis: Optional[DNSAnalysis] = Field(default=None, description="DNS-specific analysis")
    
    # Communication flows
    top_conversations: List[ConversationFlow] = Field(default_factory=list, 
                                                     description="Top network conversations")
    
    # Time range
    start_time: str = Field(..., description="Capture start time")
    end_time: str = Field(..., description="Capture end time")
    
    # Additional metadata
    analysis_options: Dict[str, Any] = Field(default_factory=dict, description="Analysis configuration used")
    processing_time: float = Field(default=0.0, description="Analysis processing time in seconds")
    
    # Legacy compatibility properties
    @property
    def total_packets(self) -> int:
        """Legacy compatibility: total packets."""
        return self.traffic_stats.total_packets
    
    @property
    def total_bytes(self) -> int:
        """Legacy compatibility: total bytes."""
        return self.traffic_stats.total_bytes
    
    @property
    def duration(self) -> float:
        """Legacy compatibility: duration."""
        return self.traffic_stats.duration
    
    @property
    def protocols(self) -> Dict[str, int]:
        """Legacy compatibility: protocol counts."""
        return {
            'tcp': self.protocol_stats.tcp_packets,
            'udp': self.protocol_stats.udp_packets,
            'icmp': self.protocol_stats.icmp_packets,
            'http': self.protocol_stats.http_sessions,
            'https': self.protocol_stats.https_sessions,
            'dns': self.protocol_stats.dns_queries,
            'dhcp': self.protocol_stats.dhcp_packets,
            'arp': self.protocol_stats.arp_packets
        }


class AnalysisProgress(BaseModel):
    """Progress information for ongoing analysis."""
    stage: str = Field(..., description="Current analysis stage")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    current_step: str = Field(default="", description="Current processing step")
    estimated_remaining: float = Field(default=0.0, description="Estimated remaining time in seconds")
    packets_processed: int = Field(default=0, description="Number of packets processed so far")
    total_packets: int = Field(default=0, description="Total packets to process")


class AnalysisError(BaseModel):
    """Error information for failed analysis."""
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(),
                          description="When error occurred")
    recoverable: bool = Field(default=False, description="Whether error is recoverable") 