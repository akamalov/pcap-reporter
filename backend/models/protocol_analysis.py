"""
Protocol Analysis Data Models.

Defines data structures for protocol-specific analysis results including
TCP, UDP, HTTP, and DNS analysis components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class TCPConnectionState(Enum):
    """TCP connection states."""
    UNKNOWN = "unknown"
    SYN_SENT = "syn_sent"
    SYN_RECEIVED = "syn_received"
    ESTABLISHED = "established"
    FIN_WAIT_1 = "fin_wait_1"
    FIN_WAIT_2 = "fin_wait_2"
    CLOSE_WAIT = "close_wait"
    CLOSING = "closing"
    LAST_ACK = "last_ack"
    TIME_WAIT = "time_wait"
    CLOSED = "closed"
    RESET = "reset"


@dataclass
class TCPAnalysisResult:
    """TCP protocol analysis results."""
    
    # Connection state and handshake
    connection_state: TCPConnectionState = TCPConnectionState.UNKNOWN
    handshake_rtt: float = 0.0  # Round-trip time for handshake in seconds
    connection_duration: float = 0.0  # Total connection duration in seconds
    
    # Packet statistics
    total_packets: int = 0
    client_packets: int = 0
    server_packets: int = 0
    syn_packets: int = 0
    syn_ack_packets: int = 0
    ack_packets: int = 0
    fin_packets: int = 0
    rst_packets: int = 0
    
    # Byte statistics
    total_bytes: int = 0
    client_bytes: int = 0
    server_bytes: int = 0
    
    # Window and flow control
    initial_window_size: int = 0
    max_window_size: int = 0
    min_window_size: int = 0
    window_scaling_factor: int = 0
    
    # Performance metrics
    retransmissions: int = 0
    retransmission_rate: float = 0.0
    out_of_order_packets: int = 0
    duplicate_acks: int = 0
    zero_window_packets: int = 0
    
    # Timing analysis
    avg_rtt: float = 0.0
    min_rtt: float = 0.0
    max_rtt: float = 0.0
    rtt_variance: float = 0.0
    
    # Throughput metrics
    avg_throughput_bps: float = 0.0
    peak_throughput_bps: float = 0.0
    client_throughput_bps: float = 0.0
    server_throughput_bps: float = 0.0
    
    # Quality indicators
    connection_quality: str = "unknown"  # excellent, good, fair, poor
    congestion_detected: bool = False
    fast_retransmit_count: int = 0


@dataclass
class UDPAnalysisResult:
    """UDP protocol analysis results."""
    
    # Basic flow statistics
    total_packets: int = 0
    total_bytes: int = 0
    flow_duration: float = 0.0
    
    # Packet distribution
    request_packets: int = 0
    response_packets: int = 0
    unidirectional_packets: int = 0
    
    # Size analysis
    avg_packet_size: float = 0.0
    max_packet_size: int = 0
    min_packet_size: int = 0
    avg_payload_size: float = 0.0
    
    # Timing analysis
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    response_time_variance: float = 0.0
    
    # Quality metrics
    packet_loss_rate: float = 0.0
    out_of_order_rate: float = 0.0
    duplicate_rate: float = 0.0
    
    # Flow characteristics
    potential_fragmentation: bool = False
    large_packets: int = 0  # Packets > 1400 bytes
    burst_detected: bool = False
    avg_inter_packet_gap: float = 0.0
    
    # Throughput
    avg_throughput_bps: float = 0.0
    peak_throughput_bps: float = 0.0


@dataclass
class HTTPTransaction:
    """Individual HTTP request-response transaction."""
    
    # Request details
    method: str = ""
    uri: str = ""
    host: str = ""
    user_agent: str = ""
    referer: str = ""
    content_type: str = ""
    
    # Response details
    status_code: int = 0
    response_size: int = 0
    content_encoding: str = ""
    server: str = ""
    
    # Timing
    request_time: str = ""  # ISO format timestamp
    response_time: float = 0.0  # Response time in seconds
    
    # Request/response sizes
    request_size: int = 0
    headers_size: int = 0
    body_size: int = 0
    
    # Quality indicators
    keep_alive: bool = False
    compressed: bool = False
    cached: bool = False


@dataclass
class HTTPAnalysisResult:
    """HTTP protocol analysis results."""
    
    # Transaction summary
    transactions: List[HTTPTransaction] = field(default_factory=list)
    total_requests: int = 0
    total_responses: int = 0
    
    # Performance metrics
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    
    # Size metrics
    total_bytes: int = 0
    request_bytes: int = 0
    response_bytes: int = 0
    avg_request_size: float = 0.0
    avg_response_size: float = 0.0
    
    # Status code analysis
    status_codes: Dict[int, int] = field(default_factory=dict)
    success_count: int = 0  # 2xx responses
    error_count: int = 0  # 4xx + 5xx responses
    error_rate: float = 0.0
    
    # Method distribution
    methods: Dict[str, int] = field(default_factory=dict)
    
    # Popular resources
    top_urls: List[tuple] = field(default_factory=list)  # (url, count)
    top_hosts: List[tuple] = field(default_factory=list)  # (host, count)
    
    # Client analysis
    user_agents: Dict[str, int] = field(default_factory=dict)
    unique_clients: int = 0
    
    # Protocol versions
    http_versions: Dict[str, int] = field(default_factory=dict)
    
    # Performance characteristics
    keep_alive_usage: float = 0.0  # Percentage of connections using keep-alive
    compression_usage: float = 0.0  # Percentage of responses compressed
    cache_hit_rate: float = 0.0


@dataclass
class DNSQuery:
    """Individual DNS query record."""
    
    domain: str = ""
    query_type: str = ""  # A, AAAA, MX, CNAME, etc.
    query_time: str = ""  # ISO format timestamp
    response_time: float = 0.0  # Response time in seconds
    response_code: str = ""  # NOERROR, NXDOMAIN, etc.
    answer_count: int = 0
    authority_count: int = 0
    additional_count: int = 0
    
    # Response data
    answers: List[str] = field(default_factory=list)
    authoritative: bool = False
    recursive_desired: bool = True
    recursive_available: bool = True
    
    # Client/server info
    client_ip: str = ""
    server_ip: str = ""
    query_id: int = 0


@dataclass
class DNSResponse:
    """DNS response details."""
    
    query_id: int = 0
    response_code: str = ""
    answer_count: int = 0
    authority_count: int = 0
    additional_count: int = 0
    answers: List[str] = field(default_factory=list)
    response_time: float = 0.0


@dataclass
class DNSAnalysisResult:
    """DNS protocol analysis results."""
    
    # Query/response summary
    queries: List[DNSQuery] = field(default_factory=list)
    total_queries: int = 0
    total_responses: int = 0
    
    # Performance metrics
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    
    # Success/failure rates
    success_rate: float = 0.0
    timeout_count: int = 0
    nxdomain_count: int = 0
    servfail_count: int = 0
    
    # Query type distribution
    query_types: Dict[str, int] = field(default_factory=dict)
    
    # Domain analysis
    top_domains: List[tuple] = field(default_factory=list)  # (domain, count)
    unique_domains: int = 0
    
    # Server analysis
    dns_servers: Dict[str, int] = field(default_factory=dict)  # server_ip: query_count
    server_performance: Dict[str, float] = field(default_factory=dict)  # server_ip: avg_response_time
    
    # Protocol characteristics
    recursive_queries: int = 0
    authoritative_responses: int = 0
    truncated_responses: int = 0
    
    # Security indicators
    suspicious_domains: List[str] = field(default_factory=list)
    potential_dga_domains: List[str] = field(default_factory=list)  # Domain Generation Algorithm
    long_domain_names: List[str] = field(default_factory=list)
    
    # Traffic patterns
    query_rate_per_second: float = 0.0
    peak_query_rate: float = 0.0
    burst_periods: List[tuple] = field(default_factory=list)  # (start_time, end_time, rate)


@dataclass
class ProtocolAnalysisSummary:
    """Overall protocol analysis summary."""
    
    # Protocol distribution
    protocol_distribution: Dict[str, int] = field(default_factory=dict)
    total_packets: int = 0
    total_bytes: int = 0
    analysis_duration: float = 0.0
    
    # Individual protocol results
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    
    # Top-level insights
    dominant_protocol: str = ""
    performance_score: float = 0.0  # 0-100 overall performance score
    security_alerts: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    
    # Cross-protocol correlations
    protocol_interactions: Dict[str, List[str]] = field(default_factory=dict)
    timing_correlations: Dict[str, float] = field(default_factory=dict) 