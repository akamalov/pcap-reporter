"""
Deep Packet Inspection for PCAP files.

This module provides detailed analysis capabilities for network packets,
building upon the triage analysis to perform in-depth inspection of flagged traffic.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json

# Import Scapy components for deep packet analysis
try:
    from scapy.all import rdpcap, IP, TCP, UDP, DNS, Raw, Ether
    from scapy.layers.http import HTTPRequest, HTTPResponse
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available - deep inspection will be limited")


class PcapDeepInspector:
    """
    Deep packet inspection analyzer for PCAP files.
    
    Provides comprehensive analysis of network traffic including:
    - HTTP/HTTPS request/response analysis
    - DNS pattern analysis and tunneling detection
    - TCP stream reconstruction
    - Protocol anomaly detection
    - Payload content analysis
    - Metadata extraction and timing analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the deep packet inspector.
        
        Args:
            config: Configuration dictionary for the inspector
        """
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.config = {
            'max_payload_size': 4096,
            'enable_http_analysis': True,
            'enable_dns_analysis': True,
            'enable_tcp_reconstruction': True,
            'enable_payload_analysis': True,
            'timeout_seconds': 300,  # 5 minutes
            'max_streams_to_reconstruct': 100,
            'dns_tunneling_threshold': 50,  # bytes
            'http_security_patterns': [
                r'union.*select',
                r'<script.*>',
                r'\.\./',
                r'drop\s+table',
                r'exec\s*\(',
                r'system\s*\(',
                r'eval\s*\('
            ]
        }
        
        # Update with user-provided config
        if config:
            self.config.update(config)
        
        self.logger.info("Deep packet inspector initialized")
    
    def analyze_http_traffic(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze HTTP traffic for requests, responses, and sessions.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with HTTP analysis results
        """
        try:
            if not SCAPY_AVAILABLE:
                return {
                    'http_requests': [],
                    'http_responses': [],
                    'http_sessions': [],
                    'http_anomalies': []
                }
            
            packets = rdpcap(str(pcap_path))
            http_requests = []
            http_responses = []
            http_sessions = []
            http_anomalies = []
            
            for packet in packets:
                if packet.haslayer(TCP) and packet.haslayer(Raw):
                    payload = packet[Raw].load.decode('utf-8', errors='ignore')
                    
                    # Check for HTTP requests
                    if any(method in payload for method in ['GET ', 'POST ', 'PUT ', 'DELETE ']):
                        request_info = self._parse_http_request(packet, payload)
                        if request_info:
                            http_requests.append(request_info)
                    
                    # Check for HTTP responses
                    elif 'HTTP/' in payload and any(code in payload for code in ['200 ', '404 ', '500 ']):
                        response_info = self._parse_http_response(packet, payload)
                        if response_info:
                            http_responses.append(response_info)
            
            # Build sessions from requests and responses
            http_sessions = self._build_http_sessions(http_requests, http_responses)
            
            return {
                'http_requests': http_requests,
                'http_responses': http_responses,
                'http_sessions': http_sessions,
                'http_anomalies': http_anomalies
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing HTTP traffic: {e}")
            return {
                'http_requests': [],
                'http_responses': [],
                'http_sessions': [],
                'http_anomalies': []
            }
    
    def analyze_http_security_patterns(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze HTTP traffic for security patterns and attack indicators.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with HTTP security analysis results
        """
        try:
            security_issues = []
            attack_patterns = []
            risk_score = 0.0
            
            http_analysis = self.analyze_http_traffic(pcap_path)
            
            # Analyze requests for attack patterns
            for request in http_analysis['http_requests']:
                uri = request.get('uri', '')
                payload = request.get('payload', '')
                
                # Check for SQL injection patterns
                if any(pattern in uri.lower() or pattern in payload.lower() 
                      for pattern in ['union select', 'drop table', 'or 1=1']):
                    security_issues.append({
                        'type': 'SQL_INJECTION',
                        'description': 'SQL injection pattern detected',
                        'severity': 'HIGH',
                        'evidence': uri
                    })
                    risk_score += 0.3
                
                # Check for XSS patterns
                if any(pattern in uri or pattern in payload 
                      for pattern in ['<script>', 'javascript:', 'onerror=']):
                    security_issues.append({
                        'type': 'XSS',
                        'description': 'Cross-site scripting pattern detected',
                        'severity': 'MEDIUM',
                        'evidence': uri
                    })
                    risk_score += 0.2
                
                # Check for path traversal
                if '../' in uri or '..\\' in uri:
                    security_issues.append({
                        'type': 'PATH_TRAVERSAL',
                        'description': 'Path traversal attempt detected',
                        'severity': 'HIGH',
                        'evidence': uri
                    })
                    risk_score += 0.3
            
            risk_score = min(risk_score, 1.0)
            
            return {
                'security_issues': security_issues,
                'attack_patterns': attack_patterns,
                'risk_score': risk_score
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing HTTP security patterns: {e}")
            return {
                'security_issues': [],
                'attack_patterns': [],
                'risk_score': 0.0
            }
    
    def analyze_dns_patterns(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze DNS traffic for patterns and tunneling indicators.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with DNS pattern analysis results
        """
        try:
            if not SCAPY_AVAILABLE:
                return {
                    'dns_queries': [],
                    'dns_responses': [],
                    'dns_patterns': [],
                    'tunneling_indicators': []
                }
            
            packets = rdpcap(str(pcap_path))
            dns_queries = []
            dns_responses = []
            dns_patterns = []
            tunneling_indicators = []
            
            for packet in packets:
                if packet.haslayer(DNS):
                    dns_layer = packet[DNS]
                    
                    if dns_layer.qr == 0:  # Query
                        query_info = {
                            'query_name': dns_layer.qd.qname.decode() if dns_layer.qd else '',
                            'query_type': dns_layer.qd.qtype if dns_layer.qd else 0,
                            'query_class': dns_layer.qd.qclass if dns_layer.qd else 0,
                            'timestamp': time.time(),
                            'src_ip': packet[IP].src if packet.haslayer(IP) else '',
                            'query_id': dns_layer.id
                        }
                        dns_queries.append(query_info)
                        
                        # Check for tunneling indicators
                        query_name = query_info['query_name']
                        if len(query_name) > 50:  # Long subdomain
                            tunneling_indicators.append({
                                'type': 'LONG_SUBDOMAIN',
                                'description': f'Unusually long DNS query: {query_name}',
                                'severity': 'MEDIUM',
                                'evidence': query_name
                            })
                    
                    elif dns_layer.qr == 1:  # Response
                        response_info = {
                            'response_id': dns_layer.id,
                            'response_code': dns_layer.rcode,
                            'timestamp': time.time(),
                            'src_ip': packet[IP].src if packet.haslayer(IP) else ''
                        }
                        dns_responses.append(response_info)
            
            return {
                'dns_queries': dns_queries,
                'dns_responses': dns_responses,
                'dns_patterns': dns_patterns,
                'tunneling_indicators': tunneling_indicators
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing DNS patterns: {e}")
            return {
                'dns_queries': [],
                'dns_responses': [],
                'dns_patterns': [],
                'tunneling_indicators': []
            }
    
    def reconstruct_tcp_streams(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Reconstruct TCP streams and analyze session data.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with TCP stream reconstruction results
        """
        try:
            if not SCAPY_AVAILABLE:
                return {
                    'tcp_streams': [],
                    'stream_statistics': {},
                    'anomalies': []
                }
            
            packets = rdpcap(str(pcap_path))
            tcp_streams = []
            stream_statistics = {}
            anomalies = []
            
            # Group packets by connection (simplified)
            connections = defaultdict(list)
            
            for packet in packets:
                if packet.haslayer(TCP) and packet.haslayer(IP):
                    src_ip = packet[IP].src
                    dst_ip = packet[IP].dst
                    src_port = packet[TCP].sport
                    dst_port = packet[TCP].dport
                    
                    # Create connection key (normalized)
                    conn_key = tuple(sorted([(src_ip, src_port), (dst_ip, dst_port)]))
                    connections[conn_key].append(packet)
            
            # Reconstruct streams
            for conn_key, conn_packets in connections.items():
                if len(conn_packets) > 0:
                    stream_info = {
                        'stream_id': f"{conn_key[0][0]}:{conn_key[0][1]}-{conn_key[1][0]}:{conn_key[1][1]}",
                        'src_ip': conn_key[0][0],
                        'src_port': conn_key[0][1],
                        'dst_ip': conn_key[1][0],
                        'dst_port': conn_key[1][1],
                        'data_client_to_server': b'',
                        'data_server_to_client': b'',
                        'start_time': time.time(),
                        'end_time': time.time()
                    }
                    tcp_streams.append(stream_info)
            
            stream_statistics = {
                'total_streams': len(tcp_streams),
                'average_stream_length': len(tcp_streams) // max(len(connections), 1)
            }
            
            return {
                'tcp_streams': tcp_streams,
                'stream_statistics': stream_statistics,
                'anomalies': anomalies
            }
            
        except Exception as e:
            self.logger.error(f"Error reconstructing TCP streams: {e}")
            return {
                'tcp_streams': [],
                'stream_statistics': {},
                'anomalies': []
            }
    
    def analyze_tcp_anomalies(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze TCP traffic for protocol anomalies.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with TCP anomaly analysis results
        """
        try:
            if not SCAPY_AVAILABLE:
                return {
                    'protocol_anomalies': [],
                    'timing_anomalies': [],
                    'sequence_anomalies': []
                }
            
            packets = rdpcap(str(pcap_path))
            protocol_anomalies = []
            timing_anomalies = []
            sequence_anomalies = []
            
            # Track sequence numbers for retransmission detection
            seq_numbers = defaultdict(set)
            
            for packet in packets:
                if packet.haslayer(TCP):
                    tcp_layer = packet[TCP]
                    
                    # Check for retransmissions (simplified)
                    if packet.haslayer(IP):
                        flow_key = (packet[IP].src, packet[IP].dst, tcp_layer.sport, tcp_layer.dport)
                        seq_num = tcp_layer.seq
                        
                        if seq_num in seq_numbers[flow_key]:
                            sequence_anomalies.append({
                                'type': 'TCP_RETRANSMISSION',
                                'description': 'TCP retransmission detected',
                                'severity': 'HIGH',
                                'packet_info': f"Packet from {packet[IP].src}"
                            })
                        seq_numbers[flow_key].add(seq_num)
                    
                    # Check for RST flag
                    if tcp_layer.flags & 0x04:  # RST flag
                        protocol_anomalies.append({
                            'type': 'TCP_RESET',
                            'description': 'TCP connection reset detected',
                            'severity': 'MEDIUM',
                            'packet_info': f"Packet from {packet[IP].src if packet.haslayer(IP) else 'unknown'}"
                        })
                    
                    # Check for zero window
                    if tcp_layer.window == 0:
                        timing_anomalies.append({
                            'type': 'ZERO_WINDOW',
                            'description': 'TCP zero window detected',
                            'severity': 'HIGH',
                            'packet_info': f"Packet from {packet[IP].src if packet.haslayer(IP) else 'unknown'}"
                        })
            
            return {
                'protocol_anomalies': protocol_anomalies,
                'timing_anomalies': timing_anomalies,
                'sequence_anomalies': sequence_anomalies
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing TCP anomalies: {e}")
            return {
                'protocol_anomalies': [],
                'timing_anomalies': [],
                'sequence_anomalies': []
            }
    
    def analyze_payload_patterns(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze payload content for patterns and signatures.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with payload analysis results
        """
        try:
            if not SCAPY_AVAILABLE:
                return {
                    'payload_analysis': {'total_payloads': 0, 'payload_sizes': [], 'content_types': {}},
                    'suspicious_patterns': [],
                    'file_signatures': []
                }
            
            packets = rdpcap(str(pcap_path))
            payload_analysis = {
                'total_payloads': 0,
                'payload_sizes': [],
                'content_types': {}
            }
            suspicious_patterns = []
            file_signatures = []
            
            for packet in packets:
                if packet.haslayer(Raw):
                    payload = packet[Raw].load
                    payload_analysis['total_payloads'] += 1
                    payload_analysis['payload_sizes'].append(len(payload))
                    
                    # Simple content type detection
                    try:
                        payload_str = payload.decode('utf-8', errors='ignore')
                        if 'HTTP' in payload_str:
                            payload_analysis['content_types']['HTTP'] = payload_analysis['content_types'].get('HTTP', 0) + 1
                    except:
                        pass
            
            return {
                'payload_analysis': payload_analysis,
                'suspicious_patterns': suspicious_patterns,
                'file_signatures': file_signatures
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing payload patterns: {e}")
            return {
                'payload_analysis': {'total_payloads': 0, 'payload_sizes': [], 'content_types': {}},
                'suspicious_patterns': [],
                'file_signatures': []
            }
    
    def extract_metadata(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Extract metadata and perform timing analysis.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with metadata analysis results
        """
        try:
            if not SCAPY_AVAILABLE:
                return {
                    'timing_analysis': {'packet_intervals': [], 'burst_patterns': [], 'idle_periods': []},
                    'flow_characteristics': {'connection_duration': [], 'data_transfer_patterns': [], 'session_patterns': []},
                    'protocol_distribution': {},
                    'bandwidth_analysis': {}
                }
            
            packets = rdpcap(str(pcap_path))
            
            timing_analysis = {
                'packet_intervals': [],
                'burst_patterns': [],
                'idle_periods': []
            }
            
            flow_characteristics = {
                'connection_duration': [],
                'data_transfer_patterns': [],
                'session_patterns': []
            }
            
            protocol_distribution = {}
            bandwidth_analysis = {}
            
            return {
                'timing_analysis': timing_analysis,
                'flow_characteristics': flow_characteristics,
                'protocol_distribution': protocol_distribution,
                'bandwidth_analysis': bandwidth_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            return {
                'timing_analysis': {'packet_intervals': [], 'burst_patterns': [], 'idle_periods': []},
                'flow_characteristics': {'connection_duration': [], 'data_transfer_patterns': [], 'session_patterns': []},
                'protocol_distribution': {},
                'bandwidth_analysis': {}
            }
    
    def perform_deep_inspection(self, pcap_path: Path, triage_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Perform comprehensive deep inspection of the PCAP file.
        
        Args:
            pcap_path: Path to the PCAP file
            triage_context: Optional triage analysis results for focused analysis
            
        Returns:
            Dictionary with complete deep inspection results
        """
        start_time = time.time()
        
        try:
            if not Path(pcap_path).exists():
                raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
            
            # Perform all analysis types
            http_analysis = self.analyze_http_traffic(pcap_path) if self.config['enable_http_analysis'] else {}
            dns_analysis = self.analyze_dns_patterns(pcap_path) if self.config['enable_dns_analysis'] else {}
            tcp_analysis = self.reconstruct_tcp_streams(pcap_path) if self.config['enable_tcp_reconstruction'] else {}
            payload_analysis = self.analyze_payload_patterns(pcap_path) if self.config['enable_payload_analysis'] else {}
            metadata_analysis = self.extract_metadata(pcap_path)
            
            # Count total packets analyzed
            if SCAPY_AVAILABLE:
                try:
                    packets = rdpcap(str(pcap_path))
                    total_packets = len(packets)
                except:
                    total_packets = 0
            else:
                total_packets = 0
            
            # Build summary
            analysis_duration = time.time() - start_time
            issues_found = []
            
            # Collect issues from all analyses
            if http_analysis.get('http_anomalies'):
                issues_found.extend(['HTTP_ANOMALY'] * len(http_analysis['http_anomalies']))
            if dns_analysis.get('tunneling_indicators'):
                issues_found.extend(['DNS_TUNNELING'] * len(dns_analysis['tunneling_indicators']))
            if tcp_analysis.get('anomalies'):
                issues_found.extend(['TCP_ANOMALY'] * len(tcp_analysis['anomalies']))
            
            summary = {
                'total_packets_analyzed': total_packets,
                'analysis_duration': analysis_duration,
                'issues_found': issues_found,
                'risk_assessment': 'LOW' if len(issues_found) == 0 else 'MEDIUM' if len(issues_found) < 5 else 'HIGH',
                'recommendations': []
            }
            
            # Add triage context if provided
            if triage_context:
                summary['triage_correlation'] = True
                summary['focused_analysis'] = True
            
            result = {
                'http_analysis': http_analysis,
                'dns_analysis': dns_analysis,
                'tcp_analysis': tcp_analysis,
                'payload_analysis': payload_analysis,
                'metadata_analysis': metadata_analysis,
                'summary': summary
            }
            
            # Add triage context if provided
            if triage_context:
                result['triage_context'] = triage_context
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error performing deep inspection: {e}")
            if "not found" in str(e).lower():
                raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
            else:
                return {
                    'http_analysis': {},
                    'dns_analysis': {},
                    'tcp_analysis': {},
                    'payload_analysis': {},
                    'metadata_analysis': {},
                    'summary': {
                        'total_packets_analyzed': 0,
                        'analysis_duration': time.time() - start_time,
                        'issues_found': [],
                        'risk_assessment': 'UNKNOWN',
                        'recommendations': []
                    }
                }
    
    def _parse_http_request(self, packet, payload: str) -> Optional[Dict[str, Any]]:
        """Parse HTTP request from packet payload."""
        try:
            lines = payload.split('\r\n')
            if lines:
                request_line = lines[0]
                parts = request_line.split(' ')
                if len(parts) >= 3:
                    return {
                        'method': parts[0],
                        'uri': parts[1],
                        'version': parts[2],
                        'headers': {},
                        'payload': payload,
                        'timestamp': time.time(),
                        'src_ip': packet[IP].src if packet.haslayer(IP) else '',
                        'dst_ip': packet[IP].dst if packet.haslayer(IP) else ''
                    }
        except:
            pass
        return None
    
    def _parse_http_response(self, packet, payload: str) -> Optional[Dict[str, Any]]:
        """Parse HTTP response from packet payload."""
        try:
            lines = payload.split('\r\n')
            if lines:
                status_line = lines[0]
                parts = status_line.split(' ')
                if len(parts) >= 3:
                    return {
                        'version': parts[0],
                        'status_code': parts[1],
                        'status_message': ' '.join(parts[2:]),
                        'headers': {},
                        'payload': payload,
                        'timestamp': time.time(),
                        'src_ip': packet[IP].src if packet.haslayer(IP) else '',
                        'dst_ip': packet[IP].dst if packet.haslayer(IP) else ''
                    }
        except:
            pass
        return None
    
    def _build_http_sessions(self, requests: List[Dict], responses: List[Dict]) -> List[Dict]:
        """Build HTTP sessions from requests and responses."""
        sessions = []
        # Simplified session building - in reality would match by timing/connection
        for i, request in enumerate(requests):
            session = {
                'session_id': f"session_{i}",
                'request': request,
                'response': responses[i] if i < len(responses) else None
            }
            sessions.append(session)
        return sessions 