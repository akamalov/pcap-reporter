"""
Protocol Analyzers.

Specialized analyzers for different network protocols including TCP, UDP, HTTP, and DNS.
Each analyzer provides deep protocol-specific insights and metrics.
"""

import asyncio
import re
import statistics
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse

from models.packet_data import PacketData, PacketStream, ConversationFlow
from models.protocol_analysis import (
    TCPAnalysisResult, UDPAnalysisResult, HTTPAnalysisResult, DNSAnalysisResult,
    TCPConnectionState, HTTPTransaction, DNSQuery, DNSResponse,
    ProtocolAnalysisSummary
)


class TCPAnalyzer:
    """TCP protocol analyzer for connection analysis and performance metrics."""
    
    def __init__(self):
        self.connection_states = {}
        self.rtt_samples = []
        
    async def analyze_stream(self, packets: List[PacketData]) -> TCPAnalysisResult:
        """Analyze TCP packet stream for connection metrics and performance."""
        if not packets:
            return TCPAnalysisResult()
            
        result = TCPAnalysisResult()
        
        # Basic packet counting and classification
        await self._analyze_packet_statistics(packets, result)
        
        # Connection state analysis
        await self._analyze_connection_state(packets, result)
        
        # Timing analysis
        await self._analyze_timing_metrics(packets, result)
        
        # Performance analysis
        await self._analyze_performance_metrics(packets, result)
        
        # Quality assessment
        await self._assess_connection_quality(result)
        
        return result
    
    async def _analyze_packet_statistics(self, packets: List[PacketData], result: TCPAnalysisResult):
        """Analyze basic packet statistics."""
        result.total_packets = len(packets)
        
        # Determine client/server based on who initiated (SYN packet)
        client_ip = None
        server_ip = None
        
        # Find the SYN packet to determine client
        for packet in packets:
            if packet.tcp_flags and "SYN" in packet.tcp_flags.upper() and "ACK" not in packet.tcp_flags.upper():
                client_ip = packet.src_ip
                server_ip = packet.dst_ip
                break
        
        # Fallback: use first packet's source as client
        if client_ip is None:
            client_ip = packets[0].src_ip
            server_ip = packets[0].dst_ip
        
        for packet in packets:
            result.total_bytes += packet.packet_size
            
            # Classify packet direction
            if packet.src_ip == client_ip:
                result.client_packets += 1
                result.client_bytes += packet.packet_size
            else:
                result.server_packets += 1
                result.server_bytes += packet.packet_size
            
            # Count flag types
            if packet.tcp_flags:
                flags = packet.tcp_flags.upper()
                if "SYN" in flags and "ACK" not in flags:
                    result.syn_packets += 1
                elif "SYN" in flags and "ACK" in flags:
                    result.syn_ack_packets += 1
                elif "ACK" in flags:
                    result.ack_packets += 1
                if "FIN" in flags:
                    result.fin_packets += 1
                if "RST" in flags:
                    result.rst_packets += 1
            
            # Window size analysis
            if packet.tcp_window:
                if result.initial_window_size == 0:
                    result.initial_window_size = packet.tcp_window
                result.max_window_size = max(result.max_window_size, packet.tcp_window)
                result.min_window_size = min(result.min_window_size or packet.tcp_window, packet.tcp_window)
                
                if packet.tcp_window == 0:
                    result.zero_window_packets += 1
    
    async def _analyze_connection_state(self, packets: List[PacketData], result: TCPAnalysisResult):
        """Analyze TCP connection state progression."""
        if result.syn_packets > 0 and result.syn_ack_packets > 0 and result.ack_packets > 0:
            result.connection_state = TCPConnectionState.ESTABLISHED
        elif result.syn_packets > 0 and result.syn_ack_packets == 0:
            result.connection_state = TCPConnectionState.SYN_SENT
        elif result.rst_packets > 0:
            result.connection_state = TCPConnectionState.RESET
        elif result.fin_packets > 0:
            result.connection_state = TCPConnectionState.CLOSED
        
        # Calculate connection duration
        if len(packets) > 1:
            start_time = datetime.fromisoformat(packets[0].timestamp.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(packets[-1].timestamp.replace('Z', '+00:00'))
            result.connection_duration = (end_time - start_time).total_seconds()
    
    async def _analyze_timing_metrics(self, packets: List[PacketData], result: TCPAnalysisResult):
        """Analyze timing and RTT metrics."""
        # Calculate handshake RTT (SYN to SYN-ACK to ACK)
        syn_time = None
        syn_ack_time = None
        
        for packet in packets:
            if packet.tcp_flags:
                flags = packet.tcp_flags.upper()
                if "SYN" in flags and "ACK" not in flags and syn_time is None:
                    syn_time = datetime.fromisoformat(packet.timestamp.replace('Z', '+00:00'))
                elif "SYN" in flags and "ACK" in flags and syn_ack_time is None:
                    syn_ack_time = datetime.fromisoformat(packet.timestamp.replace('Z', '+00:00'))
                    if syn_time:
                        result.handshake_rtt = (syn_ack_time - syn_time).total_seconds()
                        break
        
        # Calculate RTT samples from ACK timing (simplified)
        rtt_samples = []
        for i in range(1, len(packets)):
            if packets[i].tcp_flags and "ACK" in packets[i].tcp_flags.upper():
                time_diff = (
                    datetime.fromisoformat(packets[i].timestamp.replace('Z', '+00:00')) -
                    datetime.fromisoformat(packets[i-1].timestamp.replace('Z', '+00:00'))
                ).total_seconds()
                if 0.001 <= time_diff <= 1.0:  # Reasonable RTT range
                    rtt_samples.append(time_diff)
        
        if rtt_samples:
            result.avg_rtt = statistics.mean(rtt_samples)
            result.min_rtt = min(rtt_samples)
            result.max_rtt = max(rtt_samples)
            if len(rtt_samples) > 1:
                result.rtt_variance = statistics.variance(rtt_samples)
    
    async def _analyze_performance_metrics(self, packets: List[PacketData], result: TCPAnalysisResult):
        """Analyze performance metrics including retransmissions and throughput."""
        # Detect retransmissions by tracking sequence numbers
        seq_numbers = defaultdict(list)
        
        for packet in packets:
            if packet.tcp_seq is not None:
                key = (packet.src_ip, packet.dst_ip, packet.src_port, packet.dst_port)
                seq_numbers[key].append((packet.tcp_seq, packet.frame_number))
        
        # Count retransmissions (same sequence number seen multiple times)
        for seq_list in seq_numbers.values():
            seq_counts = Counter(seq for seq, _ in seq_list)
            result.retransmissions += sum(count - 1 for count in seq_counts.values() if count > 1)
        
        if result.total_packets > 0:
            result.retransmission_rate = result.retransmissions / result.total_packets
        
        # Detect out-of-order packets
        for seq_list in seq_numbers.values():
            sorted_seqs = [seq for seq, _ in sorted(seq_list, key=lambda x: x[1])]  # Sort by frame number
            for i in range(1, len(sorted_seqs)):
                if sorted_seqs[i] < sorted_seqs[i-1]:
                    result.out_of_order_packets += 1
        
        # Calculate throughput
        if result.connection_duration > 0:
            result.avg_throughput_bps = (result.total_bytes * 8) / result.connection_duration
            result.client_throughput_bps = (result.client_bytes * 8) / result.connection_duration
            result.server_throughput_bps = (result.server_bytes * 8) / result.connection_duration
        
        # Window scaling factor estimation
        if result.max_window_size > 65535:
            result.window_scaling_factor = (result.max_window_size // 65536) + 1
    
    async def _assess_connection_quality(self, result: TCPAnalysisResult):
        """Assess overall connection quality based on metrics."""
        quality_score = 100
        
        # Penalize high retransmission rate
        if result.retransmission_rate > 0.05:  # > 5%
            quality_score -= 30
        elif result.retransmission_rate > 0.01:  # > 1%
            quality_score -= 15
        
        # Penalize high RTT
        if result.avg_rtt > 0.5:  # > 500ms
            quality_score -= 25
        elif result.avg_rtt > 0.1:  # > 100ms
            quality_score -= 10
        
        # Penalize out-of-order packets
        if result.out_of_order_packets > 0:
            quality_score -= min(20, result.out_of_order_packets * 2)
        
        # Penalize zero window events
        if result.zero_window_packets > 0:
            quality_score -= min(15, result.zero_window_packets * 3)
        
        # Assign quality rating
        if quality_score >= 90:
            result.connection_quality = "excellent"
        elif quality_score >= 75:
            result.connection_quality = "good"
        elif quality_score >= 60:
            result.connection_quality = "fair"
        else:
            result.connection_quality = "poor"
        
        # Detect congestion indicators
        result.congestion_detected = (
            result.retransmission_rate > 0.02 or
            result.zero_window_packets > 0 or
            result.out_of_order_packets > result.total_packets * 0.01
        )


class UDPAnalyzer:
    """UDP protocol analyzer for flow analysis and performance metrics."""
    
    async def analyze_flow(self, packets: List[PacketData]) -> UDPAnalysisResult:
        """Analyze UDP packet flow for performance and characteristics."""
        if not packets:
            return UDPAnalysisResult()
        
        result = UDPAnalysisResult()
        
        # Basic flow statistics
        await self._analyze_flow_statistics(packets, result)
        
        # Timing analysis
        await self._analyze_timing_patterns(packets, result)
        
        # Size and fragmentation analysis
        await self._analyze_packet_sizes(packets, result)
        
        # Quality metrics
        await self._analyze_flow_quality(packets, result)
        
        return result
    
    async def _analyze_flow_statistics(self, packets: List[PacketData], result: UDPAnalysisResult):
        """Analyze basic UDP flow statistics."""
        result.total_packets = len(packets)
        result.total_bytes = sum(packet.packet_size for packet in packets)
        
        if len(packets) > 1:
            start_time = datetime.fromisoformat(packets[0].timestamp.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(packets[-1].timestamp.replace('Z', '+00:00'))
            result.flow_duration = (end_time - start_time).total_seconds()
        
        # Classify packets as requests/responses based on direction
        src_ips = set()
        dst_ips = set()
        for packet in packets:
            src_ips.add(packet.src_ip)
            dst_ips.add(packet.dst_ip)
        
        # Simple heuristic: if bidirectional, classify by port numbers
        if len(src_ips) > 1 or len(dst_ips) > 1:
            for packet in packets:
                if packet.dst_port < 1024:  # Well-known port = request
                    result.request_packets += 1
                else:
                    result.response_packets += 1
        else:
            result.unidirectional_packets = result.total_packets
    
    async def _analyze_timing_patterns(self, packets: List[PacketData], result: UDPAnalysisResult):
        """Analyze timing patterns and response times."""
        response_times = []
        inter_packet_gaps = []
        
        # Group packets by conversation
        conversations = defaultdict(list)
        for packet in packets:
            conv_key = tuple(sorted([(packet.src_ip, packet.src_port), (packet.dst_ip, packet.dst_port)]))
            conversations[conv_key].append(packet)
        
        # Calculate response times for each conversation
        for conv_packets in conversations.values():
            if len(conv_packets) >= 2:
                conv_packets.sort(key=lambda p: p.timestamp)
                
                # Calculate inter-packet gaps
                for i in range(1, len(conv_packets)):
                    time1 = datetime.fromisoformat(conv_packets[i-1].timestamp.replace('Z', '+00:00'))
                    time2 = datetime.fromisoformat(conv_packets[i].timestamp.replace('Z', '+00:00'))
                    gap = (time2 - time1).total_seconds()
                    inter_packet_gaps.append(gap)
                    
                    # If this looks like a request-response pair
                    if (conv_packets[i-1].dst_port < 1024 and conv_packets[i].src_port < 1024) or \
                       (conv_packets[i-1].src_port > 1024 and conv_packets[i].dst_port > 1024):
                        response_times.append(gap)
        
        # Calculate response time statistics
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.min_response_time = min(response_times)
            result.max_response_time = max(response_times)
            if len(response_times) > 1:
                result.response_time_variance = statistics.variance(response_times)
        
        # Calculate average inter-packet gap
        if inter_packet_gaps:
            result.avg_inter_packet_gap = statistics.mean(inter_packet_gaps)
    
    async def _analyze_packet_sizes(self, packets: List[PacketData], result: UDPAnalysisResult):
        """Analyze packet sizes and detect potential fragmentation."""
        packet_sizes = [packet.packet_size for packet in packets]
        payload_sizes = []
        for packet in packets:
            udp_length = getattr(packet, 'udp_length', None)
            if udp_length is not None:
                payload_sizes.append(udp_length)
            else:
                payload_sizes.append(packet.packet_size - 28)  # UDP header + IP header ≈ 28 bytes
        
        result.avg_packet_size = statistics.mean(packet_sizes)
        result.max_packet_size = max(packet_sizes)
        result.min_packet_size = min(packet_sizes)
        result.avg_payload_size = statistics.mean(payload_sizes)
        
        # Detect potential fragmentation (packets > 1400 bytes likely fragmented)
        result.large_packets = sum(1 for size in packet_sizes if size > 1400)
        result.potential_fragmentation = result.large_packets > 0
        
        # Detect burst patterns (multiple large packets in quick succession)
        large_packet_times = []
        for packet in packets:
            if packet.packet_size > 1400:
                large_packet_times.append(datetime.fromisoformat(packet.timestamp.replace('Z', '+00:00')))
        
        if len(large_packet_times) > 1:
            for i in range(1, len(large_packet_times)):
                gap = (large_packet_times[i] - large_packet_times[i-1]).total_seconds()
                if gap < 0.1:  # Less than 100ms apart
                    result.burst_detected = True
                    break
    
    async def _analyze_flow_quality(self, packets: List[PacketData], result: UDPAnalysisResult):
        """Analyze flow quality metrics."""
        # Calculate throughput
        if result.flow_duration > 0:
            result.avg_throughput_bps = (result.total_bytes * 8) / result.flow_duration
        
        # Detect potential packet loss (gaps in sequence or missing responses)
        # This is simplified since UDP doesn't have sequence numbers
        expected_responses = result.request_packets
        actual_responses = result.response_packets
        
        if expected_responses > 0:
            result.packet_loss_rate = max(0, (expected_responses - actual_responses) / expected_responses)
        
        # Detect duplicate packets (same size, same direction, close timing)
        duplicate_count = 0
        for i in range(len(packets)):
            for j in range(i + 1, min(i + 10, len(packets))):  # Check next 10 packets
                if (packets[i].src_ip == packets[j].src_ip and
                    packets[i].dst_ip == packets[j].dst_ip and
                    packets[i].packet_size == packets[j].packet_size):
                    time_diff = abs((
                        datetime.fromisoformat(packets[j].timestamp.replace('Z', '+00:00')) -
                        datetime.fromisoformat(packets[i].timestamp.replace('Z', '+00:00'))
                    ).total_seconds())
                    if time_diff < 0.01:  # Within 10ms
                        duplicate_count += 1
                        break
        
        if result.total_packets > 0:
            result.duplicate_rate = duplicate_count / result.total_packets


class HTTPAnalyzer:
    """HTTP protocol analyzer for web traffic analysis."""
    
    def __init__(self):
        self.user_agent_pattern = re.compile(r'User-Agent:\s*([^\r\n]+)', re.IGNORECASE)
        self.status_pattern = re.compile(r'HTTP/\d\.\d\s+(\d{3})', re.IGNORECASE)
    
    async def analyze_session(self, packets: List[PacketData]) -> HTTPAnalysisResult:
        """Analyze HTTP session for transactions and performance."""
        if not packets:
            return HTTPAnalysisResult()
        
        result = HTTPAnalysisResult()
        
        # Extract HTTP transactions
        await self._extract_transactions(packets, result)
        
        # Analyze performance metrics
        await self._analyze_performance(result)
        
        # Analyze status codes and errors
        await self._analyze_status_codes(result)
        
        # Analyze content and clients
        await self._analyze_content_patterns(result)
        
        return result
    
    async def _extract_transactions(self, packets: List[PacketData], result: HTTPAnalysisResult):
        """Extract HTTP transactions from packet data."""
        transactions = []
        pending_requests = {}  # Track requests waiting for responses
        
        for packet in packets:
            if packet.http_method:  # HTTP request
                transaction = HTTPTransaction()
                transaction.method = packet.http_method
                transaction.uri = getattr(packet, 'http_uri', '')
                transaction.host = getattr(packet, 'http_host', '')
                transaction.request_time = packet.timestamp
                transaction.request_size = packet.packet_size
                
                # Extract user agent if available
                user_agent = await self._extract_user_agent("")  # Simplified for now
                if user_agent:
                    transaction.user_agent = user_agent
                
                # Store as pending request
                request_key = (packet.src_ip, packet.dst_ip, packet.src_port, packet.dst_port)
                pending_requests[request_key] = transaction
                
                result.total_requests += 1
                result.request_bytes += packet.packet_size
                
                # Update method statistics
                result.methods[packet.http_method] = result.methods.get(packet.http_method, 0) + 1
                
            elif packet.http_status:  # HTTP response
                response_key = (packet.dst_ip, packet.src_ip, packet.dst_port, packet.src_port)
                
                if response_key in pending_requests:
                    transaction = pending_requests.pop(response_key)
                    transaction.status_code = packet.http_status
                    transaction.response_size = packet.packet_size
                    
                    # Calculate response time
                    request_time = datetime.fromisoformat(transaction.request_time.replace('Z', '+00:00'))
                    response_time = datetime.fromisoformat(packet.timestamp.replace('Z', '+00:00'))
                    transaction.response_time = (response_time - request_time).total_seconds()
                    
                    transactions.append(transaction)
                
                result.total_responses += 1
                result.response_bytes += packet.packet_size
                
                # Update status code statistics
                status_code = packet.http_status
                result.status_codes[status_code] = result.status_codes.get(status_code, 0) + 1
                
                if 200 <= status_code < 300:
                    result.success_count += 1
                elif status_code >= 400:
                    result.error_count += 1
        
        result.transactions = transactions
        result.total_bytes = result.request_bytes + result.response_bytes
    
    async def _analyze_performance(self, result: HTTPAnalysisResult):
        """Analyze HTTP performance metrics."""
        if not result.transactions:
            return
        
        response_times = [t.response_time for t in result.transactions if t.response_time > 0]
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.min_response_time = min(response_times)
            result.max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            n = len(sorted_times)
            if n > 0:
                result.response_time_p95 = sorted_times[int(n * 0.95)]
                result.response_time_p99 = sorted_times[int(n * 0.99)]
        
        # Calculate average sizes
        if result.total_requests > 0:
            result.avg_request_size = result.request_bytes / result.total_requests
        if result.total_responses > 0:
            result.avg_response_size = result.response_bytes / result.total_responses
    
    async def _analyze_status_codes(self, result: HTTPAnalysisResult):
        """Analyze HTTP status codes and error rates."""
        total_responses = result.total_responses
        if total_responses > 0:
            result.error_rate = result.error_count / total_responses
    
    async def _analyze_content_patterns(self, result: HTTPAnalysisResult):
        """Analyze content patterns, URLs, and clients."""
        url_counter = Counter()
        host_counter = Counter()
        user_agent_counter = Counter()
        
        for transaction in result.transactions:
            if transaction.uri:
                url_counter[transaction.uri] += 1
            if transaction.host:
                host_counter[transaction.host] += 1
            if transaction.user_agent:
                user_agent_counter[transaction.user_agent] += 1
        
        # Get top URLs and hosts
        result.top_urls = url_counter.most_common(10)
        result.top_hosts = host_counter.most_common(10)
        result.user_agents = dict(user_agent_counter)
    
    async def _extract_user_agent(self, packet_data: str) -> str:
        """Extract User-Agent from packet data (mock implementation)."""
        # This would normally parse the actual packet payload
        return "Mozilla/5.0 (Mock User Agent)"


class DNSAnalyzer:
    """DNS protocol analyzer for query analysis and performance."""
    
    async def analyze_traffic(self, packets: List[PacketData]) -> DNSAnalysisResult:
        """Analyze DNS traffic for queries, responses, and performance."""
        if not packets:
            return DNSAnalysisResult()
        
        result = DNSAnalysisResult()
        
        # Extract DNS queries and responses
        await self._extract_dns_transactions(packets, result)
        
        # Analyze performance metrics
        await self._analyze_dns_performance(result)
        
        # Analyze query patterns
        await self._analyze_query_patterns(result)
        
        # Security analysis
        await self._analyze_security_indicators(result)
        
        return result
    
    async def _extract_dns_transactions(self, packets: List[PacketData], result: DNSAnalysisResult):
        """Extract DNS queries and responses."""
        queries = []
        pending_queries = {}  # Track queries waiting for responses
        
        for packet in packets:
            if packet.dns_query:  # DNS query
                query = DNSQuery()
                query.domain = packet.dns_query
                query.query_type = getattr(packet, 'dns_type', 'A')
                query.query_time = packet.timestamp
                query.client_ip = packet.src_ip
                query.server_ip = packet.dst_ip
                
                # Store as pending query
                query_key = (packet.src_ip, packet.dst_ip, packet.src_port, packet.dst_port)
                pending_queries[query_key] = query
                
                result.total_queries += 1
                
                # Update query type statistics
                query_type = query.query_type
                result.query_types[query_type] = result.query_types.get(query_type, 0) + 1
                
            elif packet.dns_response:  # DNS response
                response_key = (packet.dst_ip, packet.src_ip, packet.dst_port, packet.src_port)
                
                if response_key in pending_queries:
                    query = pending_queries.pop(response_key)
                    
                    # Calculate response time
                    query_time = datetime.fromisoformat(query.query_time.replace('Z', '+00:00'))
                    response_time = datetime.fromisoformat(packet.timestamp.replace('Z', '+00:00'))
                    query.response_time = (response_time - query_time).total_seconds()
                    
                    # Add response details
                    query.answers = [packet.dns_response] if packet.dns_response else []
                    query.response_code = "NOERROR"  # Simplified
                    
                    queries.append(query)
                
                result.total_responses += 1
        
        # Handle timeouts (queries without responses)
        result.timeout_count = len(pending_queries)
        for query in pending_queries.values():
            query.response_code = "TIMEOUT"
            queries.append(query)
        
        result.queries = queries
    
    async def _analyze_dns_performance(self, result: DNSAnalysisResult):
        """Analyze DNS performance metrics."""
        response_times = [q.response_time for q in result.queries if q.response_time > 0]
        
        if response_times:
            result.avg_response_time = statistics.mean(response_times)
            result.min_response_time = min(response_times)
            result.max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            n = len(sorted_times)
            if n > 0:
                result.response_time_p95 = sorted_times[int(n * 0.95)]
                result.response_time_p99 = sorted_times[int(n * 0.99)]
        
        # Calculate success rate
        successful_queries = sum(1 for q in result.queries if q.response_code == "NOERROR")
        if result.total_queries > 0:
            result.success_rate = successful_queries / result.total_queries
        
        # Count different failure types
        for query in result.queries:
            if query.response_code == "NXDOMAIN":
                result.nxdomain_count += 1
            elif query.response_code == "SERVFAIL":
                result.servfail_count += 1
    
    async def _analyze_query_patterns(self, result: DNSAnalysisResult):
        """Analyze DNS query patterns and domains."""
        domain_counter = Counter()
        server_counter = Counter()
        server_times = defaultdict(list)
        
        for query in result.queries:
            if query.domain:
                domain_counter[query.domain] += 1
            if query.server_ip:
                server_counter[query.server_ip] += 1
                if query.response_time > 0:
                    server_times[query.server_ip].append(query.response_time)
        
        # Get top domains
        result.top_domains = domain_counter.most_common(10)
        result.unique_domains = len(domain_counter)
        
        # Analyze DNS servers
        result.dns_servers = dict(server_counter)
        for server_ip, times in server_times.items():
            if times:
                result.server_performance[server_ip] = statistics.mean(times)
        
        # Calculate query rate
        if result.queries:
            first_query = min(result.queries, key=lambda q: q.query_time)
            last_query = max(result.queries, key=lambda q: q.query_time)
            
            start_time = datetime.fromisoformat(first_query.query_time.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(last_query.query_time.replace('Z', '+00:00'))
            duration = (end_time - start_time).total_seconds()
            
            if duration > 0:
                result.query_rate_per_second = result.total_queries / duration
    
    async def _analyze_security_indicators(self, result: DNSAnalysisResult):
        """Analyze DNS traffic for security indicators."""
        for query in result.queries:
            domain = query.domain.lower()
            
            # Check for suspiciously long domain names
            if len(domain) > 50:
                result.long_domain_names.append(domain)
            
            # Simple DGA detection (many random-looking subdomains)
            if self._looks_like_dga(domain):
                result.potential_dga_domains.append(domain)
            
            # Check against simple suspicious patterns
            if self._is_suspicious_domain(domain):
                result.suspicious_domains.append(domain)
    
    def _looks_like_dga(self, domain: str) -> bool:
        """Simple heuristic to detect DGA-generated domains."""
        # Check for high consonant-to-vowel ratio
        vowels = set('aeiou')
        if len(domain) > 10:
            consonant_count = sum(1 for c in domain if c.isalpha() and c not in vowels)
            vowel_count = sum(1 for c in domain if c in vowels)
            if vowel_count > 0 and consonant_count / vowel_count > 4:
                return True
        return False
    
    def _is_suspicious_domain(self, domain: str) -> bool:
        """Check for suspicious domain patterns."""
        suspicious_patterns = [
            r'\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}',  # IP-like patterns
            r'[a-f0-9]{32,}',  # Long hex strings
            r'(.)\1{4,}',  # Repeated characters
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                return True
        return False


class ProtocolAnalysisEngine:
    """Main engine for coordinating protocol analysis."""
    
    def __init__(self):
        self.tcp_analyzer = TCPAnalyzer()
        self.udp_analyzer = UDPAnalyzer()
        self.http_analyzer = HTTPAnalyzer()
        self.dns_analyzer = DNSAnalyzer()
        
        # Protocol detection rules
        self.protocol_ports = {
            'http': [80, 8080, 8000],
            'https': [443, 8443],
            'dns': [53],
            'dhcp': [67, 68],
            'ftp': [21, 20],
            'ssh': [22],
            'telnet': [23],
            'smtp': [25, 587],
            'pop3': [110, 995],
            'imap': [143, 993],
            'snmp': [161, 162],
            'ntp': [123],
        }
    
    async def analyze_protocols(self, packets: List[PacketData]) -> Dict[str, Any]:
        """Analyze packets using appropriate protocol analyzers."""
        results = {}
        
        # Separate packets by protocol
        tcp_packets = [p for p in packets if p.protocol.upper() == 'TCP']
        udp_packets = [p for p in packets if p.protocol.upper() == 'UDP']
        http_packets = [p for p in packets if p.http_method or p.http_status]
        dns_packets = [p for p in packets if p.dns_query or p.dns_response]
        
        # Run analyzers in parallel
        analysis_tasks = []
        
        if tcp_packets:
            analysis_tasks.append(self._analyze_tcp(tcp_packets))
        if udp_packets:
            analysis_tasks.append(self._analyze_udp(udp_packets))
        if http_packets:
            analysis_tasks.append(self._analyze_http(http_packets))
        if dns_packets:
            analysis_tasks.append(self._analyze_dns(dns_packets))
        
        # Wait for all analyses to complete
        if analysis_tasks:
            analysis_results = await asyncio.gather(*analysis_tasks)
            
            # Combine results
            for result in analysis_results:
                results.update(result)
        
        return results
    
    async def _analyze_tcp(self, packets: List[PacketData]) -> Dict[str, TCPAnalysisResult]:
        """Analyze TCP packets."""
        result = await self.tcp_analyzer.analyze_stream(packets)
        return {'tcp': result}
    
    async def _analyze_udp(self, packets: List[PacketData]) -> Dict[str, UDPAnalysisResult]:
        """Analyze UDP packets."""
        result = await self.udp_analyzer.analyze_flow(packets)
        return {'udp': result}
    
    async def _analyze_http(self, packets: List[PacketData]) -> Dict[str, HTTPAnalysisResult]:
        """Analyze HTTP packets."""
        result = await self.http_analyzer.analyze_session(packets)
        return {'http': result}
    
    async def _analyze_dns(self, packets: List[PacketData]) -> Dict[str, DNSAnalysisResult]:
        """Analyze DNS packets."""
        result = await self.dns_analyzer.analyze_traffic(packets)
        return {'dns': result}
    
    def detect_protocols(self, packets: List[PacketData]) -> Set[str]:
        """Detect protocols present in packet data."""
        detected = set()
        
        for packet in packets:
            # Protocol from packet
            if packet.protocol:
                detected.add(packet.protocol.lower())
            
            # Application protocols by port
            for protocol, ports in self.protocol_ports.items():
                if packet.dst_port in ports or packet.src_port in ports:
                    detected.add(protocol)
            
            # Specific protocol indicators
            if packet.http_method or packet.http_status:
                detected.add('http')
            if packet.dns_query or packet.dns_response:
                detected.add('dns')
        
        return detected
    
    async def generate_summary(self, packets: List[PacketData]) -> Dict[str, Any]:
        """Generate comprehensive protocol analysis summary."""
        # Analyze all protocols
        analysis_results = await self.analyze_protocols(packets)
        
        # Calculate protocol distribution
        protocol_counts = Counter()
        for packet in packets:
            protocol_counts[packet.protocol.upper()] += 1
        
        summary = {
            'protocol_distribution': dict(protocol_counts),
            'total_packets': len(packets),
            'total_bytes': sum(p.packet_size for p in packets),
            'analysis_results': analysis_results,
            'detected_protocols': list(self.detect_protocols(packets))
        }
        
        return summary 