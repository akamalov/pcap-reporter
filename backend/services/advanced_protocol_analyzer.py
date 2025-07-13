"""
Advanced Protocol Analyzer for Deep Packet Inspection.

Provides comprehensive protocol analysis including:
- Advanced application layer protocol detection
- Encrypted traffic analysis and TLS inspection
- Data exfiltration detection
- Malware behavior analysis
- Network covert channel detection
- Protocol anomaly detection
"""

import asyncio
import logging
import hashlib
import base64
import re
import struct
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Import Scapy components for deep packet analysis
try:
    from scapy.all import rdpcap, IP, TCP, UDP, DNS, Raw, Ether, ICMP, ARP
    from scapy.layers.http import HTTPRequest, HTTPResponse
    from scapy.layers.tls import TLS, TLSClientHello, TLSServerHello
    from scapy.layers.netbios import NBTSession
    from scapy.layers.dhcp import DHCP, BOOTP
    from scapy.layers.smtp import SMTP
    from scapy.layers.ftp import FTP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available - advanced protocol analysis will be limited")

logger = logging.getLogger(__name__)


@dataclass
class ProtocolBehavior:
    """Protocol behavior analysis result."""
    protocol: str
    normal_behavior: bool
    anomalies: List[str]
    risk_score: float
    metadata: Dict[str, Any]


@dataclass
class EncryptedTrafficAnalysis:
    """Encrypted traffic analysis result."""
    tls_version: Optional[str]
    cipher_suite: Optional[str]
    certificate_info: Dict[str, Any]
    session_duration: float
    data_volume: int
    suspicious_patterns: List[str]


@dataclass
class DataExfiltrationIndicator:
    """Data exfiltration detection result."""
    indicator_type: str
    severity: str
    description: str
    source_ip: str
    destination_ip: str
    protocol: str
    data_volume: int
    suspicious_timing: bool


class AdvancedProtocolAnalyzer:
    """Advanced protocol analyzer for deep packet inspection."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the advanced protocol analyzer."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = {
            'max_payload_size': 8192,
            'enable_tls_analysis': True,
            'enable_dns_tunneling_detection': True,
            'enable_http_security_analysis': True,
            'enable_data_exfiltration_detection': True,
            'enable_covert_channel_detection': True,
            'enable_malware_behavior_analysis': True,
            'max_streams_to_analyze': 500,
            'analysis_timeout': 300,
            
            # Thresholds
            'dns_tunneling_threshold': 100,  # bytes per query
            'large_upload_threshold': 10_000_000,  # 10MB
            'suspicious_connection_count': 100,
            'encryption_entropy_threshold': 7.5,
            'covert_timing_threshold': 0.001,  # seconds
            
            # Security patterns
            'malware_patterns': [
                rb'MZ\x90\x00',  # PE header
                rb'\x7fELF',     # ELF header
                rb'PK\x03\x04',  # ZIP header (potential malware)
                rb'\xd0\xcf\x11\xe0',  # OLE header
            ],
            
            'sql_injection_patterns': [
                r'union.*select',
                r'drop\s+table',
                r'insert\s+into',
                r'delete\s+from',
                r'exec\s*\(',
                r'sp_executesql',
            ],
            
            'xss_patterns': [
                r'<script.*?>',
                r'javascript:',
                r'vbscript:',
                r'onload\s*=',
                r'onerror\s*=',
            ],
            
            'data_exfiltration_patterns': [
                r'base64',
                r'[A-Za-z0-9+/]{100,}={0,2}',  # Base64 encoded data
                r'[0-9a-fA-F]{64,}',  # Hex encoded data
            ]
        }
        
        if config:
            self.config.update(config)
        
        # Analysis state
        self.tcp_streams = {}
        self.dns_queries = []
        self.tls_sessions = {}
        self.http_sessions = []
        self.suspicious_flows = []
        
        self.logger.info("Advanced protocol analyzer initialized")
    
    async def analyze_protocols(self, pcap_path: str) -> Dict[str, Any]:
        """
        Perform comprehensive protocol analysis.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Comprehensive analysis results
        """
        if not SCAPY_AVAILABLE:
            self.logger.warning("Scapy not available - returning limited analysis")
            return {'error': 'Scapy not available for advanced analysis'}
        
        try:
            start_time = time.time()
            
            # Load packets
            packets = rdpcap(pcap_path)
            self.logger.info(f"Loaded {len(packets)} packets for analysis")
            
            # Initialize analysis results
            results = {
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'total_packets': len(packets),
                'processing_time': 0,
                'protocol_behaviors': [],
                'encrypted_traffic': [],
                'data_exfiltration_indicators': [],
                'malware_indicators': [],
                'covert_channels': [],
                'security_issues': [],
                'network_statistics': {}
            }
            
            # Perform different types of analysis
            await self._analyze_tcp_streams(packets, results)
            await self._analyze_dns_traffic(packets, results)
            await self._analyze_tls_traffic(packets, results)
            await self._analyze_http_traffic(packets, results)
            await self._detect_data_exfiltration(packets, results)
            await self._detect_malware_behavior(packets, results)
            await self._detect_covert_channels(packets, results)
            await self._analyze_protocol_anomalies(packets, results)
            
            # Calculate processing time
            results['processing_time'] = time.time() - start_time
            
            self.logger.info(f"Advanced protocol analysis completed in {results['processing_time']:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in advanced protocol analysis: {e}")
            return {'error': str(e)}
    
    async def _analyze_tcp_streams(self, packets: List, results: Dict[str, Any]):
        """Analyze TCP streams for reconstruction and behavior analysis."""
        try:
            tcp_packets = [pkt for pkt in packets if pkt.haslayer(TCP)]
            
            # Group packets by TCP stream
            streams = defaultdict(list)
            for pkt in tcp_packets:
                if pkt.haslayer(IP):
                    stream_key = (
                        pkt[IP].src, pkt[TCP].sport,
                        pkt[IP].dst, pkt[TCP].dport
                    )
                    streams[stream_key].append(pkt)
            
            stream_analysis = []
            for stream_key, stream_packets in list(streams.items())[:self.config['max_streams_to_analyze']]:
                stream_info = await self._analyze_single_tcp_stream(stream_key, stream_packets)
                if stream_info:
                    stream_analysis.append(stream_info)
            
            results['tcp_streams'] = {
                'total_streams': len(streams),
                'analyzed_streams': len(stream_analysis),
                'stream_details': stream_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing TCP streams: {e}")
    
    async def _analyze_single_tcp_stream(self, stream_key: Tuple, packets: List) -> Optional[Dict[str, Any]]:
        """Analyze a single TCP stream."""
        try:
            if not packets:
                return None
            
            src_ip, src_port, dst_ip, dst_port = stream_key
            
            # Basic stream statistics
            total_bytes = sum(len(pkt[Raw].load) if pkt.haslayer(Raw) else 0 for pkt in packets)
            duration = packets[-1].time - packets[0].time if len(packets) > 1 else 0
            
            # Payload analysis
            payloads = [pkt[Raw].load for pkt in packets if pkt.haslayer(Raw)]
            combined_payload = b''.join(payloads)
            
            # Detect application protocol
            detected_protocol = await self._detect_application_protocol(combined_payload, dst_port)
            
            # Security analysis
            security_issues = await self._analyze_stream_security(combined_payload, detected_protocol)
            
            return {
                'stream_id': f"{src_ip}:{src_port}->{dst_ip}:{dst_port}",
                'packet_count': len(packets),
                'total_bytes': total_bytes,
                'duration': duration,
                'detected_protocol': detected_protocol,
                'security_issues': security_issues,
                'entropy': self._calculate_entropy(combined_payload) if combined_payload else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing TCP stream: {e}")
            return None
    
    async def _analyze_dns_traffic(self, packets: List, results: Dict[str, Any]):
        """Analyze DNS traffic for tunneling and suspicious patterns."""
        try:
            dns_packets = [pkt for pkt in packets if pkt.haslayer(DNS)]
            
            dns_analysis = {
                'total_queries': 0,
                'unique_domains': set(),
                'tunneling_indicators': [],
                'suspicious_queries': [],
                'query_types': defaultdict(int)
            }
            
            for pkt in dns_packets:
                dns_layer = pkt[DNS]
                
                if dns_layer.qr == 0:  # Query
                    dns_analysis['total_queries'] += 1
                    
                    if dns_layer.qd:
                        domain = dns_layer.qd.qname.decode('utf-8', errors='ignore')
                        dns_analysis['unique_domains'].add(domain)
                        dns_analysis['query_types'][dns_layer.qd.qtype] += 1
                        
                        # Check for DNS tunneling
                        if len(domain) > self.config['dns_tunneling_threshold']:
                            dns_analysis['tunneling_indicators'].append({
                                'domain': domain,
                                'length': len(domain),
                                'timestamp': pkt.time,
                                'reason': 'Unusually long domain name'
                            })
                        
                        # Check for suspicious patterns
                        if self._is_suspicious_domain(domain):
                            dns_analysis['suspicious_queries'].append({
                                'domain': domain,
                                'timestamp': pkt.time,
                                'patterns': self._get_suspicious_patterns(domain)
                            })
            
            # Convert set to list for JSON serialization
            dns_analysis['unique_domains'] = list(dns_analysis['unique_domains'])
            dns_analysis['query_types'] = dict(dns_analysis['query_types'])
            
            results['dns_analysis'] = dns_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing DNS traffic: {e}")
    
    async def _analyze_tls_traffic(self, packets: List, results: Dict[str, Any]):
        """Analyze TLS traffic for certificate information and security."""
        try:
            tls_packets = [pkt for pkt in packets if pkt.haslayer(TLS)]
            
            tls_analysis = {
                'tls_sessions': 0,
                'tls_versions': defaultdict(int),
                'cipher_suites': defaultdict(int),
                'certificate_info': [],
                'security_issues': []
            }
            
            for pkt in tls_packets:
                # Analyze TLS handshake
                if pkt.haslayer(TLSClientHello):
                    client_hello = pkt[TLSClientHello]
                    tls_analysis['tls_sessions'] += 1
                    
                    # Extract TLS version
                    if hasattr(client_hello, 'version'):
                        version = client_hello.version
                        tls_analysis['tls_versions'][version] += 1
                    
                    # Check for weak TLS versions
                    if hasattr(client_hello, 'version') and client_hello.version < 0x0303:
                        tls_analysis['security_issues'].append({
                            'type': 'weak_tls_version',
                            'description': f'Weak TLS version detected: {hex(client_hello.version)}',
                            'timestamp': pkt.time
                        })
                
                elif pkt.haslayer(TLSServerHello):
                    server_hello = pkt[TLSServerHello]
                    
                    # Extract cipher suite
                    if hasattr(server_hello, 'cipher'):
                        cipher = server_hello.cipher
                        tls_analysis['cipher_suites'][cipher] += 1
            
            # Convert defaultdicts to regular dicts
            tls_analysis['tls_versions'] = dict(tls_analysis['tls_versions'])
            tls_analysis['cipher_suites'] = dict(tls_analysis['cipher_suites'])
            
            results['tls_analysis'] = tls_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing TLS traffic: {e}")
    
    async def _analyze_http_traffic(self, packets: List, results: Dict[str, Any]):
        """Analyze HTTP traffic for security issues and patterns."""
        try:
            http_packets = [pkt for pkt in packets if pkt.haslayer(Raw) and pkt.haslayer(TCP)]
            
            http_analysis = {
                'http_requests': 0,
                'http_responses': 0,
                'security_issues': [],
                'suspicious_patterns': []
            }
            
            for pkt in http_packets:
                payload = pkt[Raw].load.decode('utf-8', errors='ignore')
                
                # Detect HTTP requests
                if payload.startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ')):
                    http_analysis['http_requests'] += 1
                    
                    # Check for security issues
                    security_issues = self._check_http_security_patterns(payload)
                    if security_issues:
                        http_analysis['security_issues'].extend(security_issues)
                
                # Detect HTTP responses
                elif payload.startswith('HTTP/'):
                    http_analysis['http_responses'] += 1
            
            results['http_analysis'] = http_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing HTTP traffic: {e}")
    
    async def _detect_data_exfiltration(self, packets: List, results: Dict[str, Any]):
        """Detect potential data exfiltration patterns."""
        try:
            indicators = []
            
            # Track upload volumes by destination
            upload_volumes = defaultdict(int)
            connection_counts = defaultdict(int)
            
            for pkt in packets:
                if pkt.haslayer(IP) and pkt.haslayer(Raw):
                    dst_ip = pkt[IP].dst
                    payload_size = len(pkt[Raw].load)
                    
                    # Track upload volume
                    upload_volumes[dst_ip] += payload_size
                    connection_counts[dst_ip] += 1
                    
                    # Check for encoded data patterns
                    payload_str = pkt[Raw].load.decode('utf-8', errors='ignore')
                    for pattern in self.config['data_exfiltration_patterns']:
                        if re.search(pattern, payload_str, re.IGNORECASE):
                            indicators.append(DataExfiltrationIndicator(
                                indicator_type='encoded_data',
                                severity='medium',
                                description=f'Potential encoded data pattern: {pattern}',
                                source_ip=pkt[IP].src,
                                destination_ip=dst_ip,
                                protocol='TCP' if pkt.haslayer(TCP) else 'UDP',
                                data_volume=payload_size,
                                suspicious_timing=False
                            ))
            
            # Check for large uploads
            for dst_ip, volume in upload_volumes.items():
                if volume > self.config['large_upload_threshold']:
                    indicators.append(DataExfiltrationIndicator(
                        indicator_type='large_upload',
                        severity='high',
                        description=f'Large data upload detected: {volume} bytes',
                        source_ip='multiple',
                        destination_ip=dst_ip,
                        protocol='TCP',
                        data_volume=volume,
                        suspicious_timing=False
                    ))
            
            results['data_exfiltration_indicators'] = [asdict(ind) for ind in indicators]
            
        except Exception as e:
            self.logger.error(f"Error detecting data exfiltration: {e}")
    
    async def _detect_malware_behavior(self, packets: List, results: Dict[str, Any]):
        """Detect potential malware behavior patterns."""
        try:
            indicators = []
            
            for pkt in packets:
                if pkt.haslayer(Raw):
                    payload = pkt[Raw].load
                    
                    # Check for malware signatures
                    for pattern in self.config['malware_patterns']:
                        if pattern in payload:
                            indicators.append({
                                'type': 'malware_signature',
                                'pattern': pattern.hex(),
                                'timestamp': pkt.time,
                                'src_ip': pkt[IP].src if pkt.haslayer(IP) else 'unknown',
                                'dst_ip': pkt[IP].dst if pkt.haslayer(IP) else 'unknown'
                            })
            
            results['malware_indicators'] = indicators
            
        except Exception as e:
            self.logger.error(f"Error detecting malware behavior: {e}")
    
    async def _detect_covert_channels(self, packets: List, results: Dict[str, Any]):
        """Detect potential covert communication channels."""
        try:
            covert_channels = []
            
            # Analyze ICMP packets for covert channels
            icmp_packets = [pkt for pkt in packets if pkt.haslayer(ICMP)]
            if len(icmp_packets) > 10:  # Threshold for suspicious ICMP activity
                icmp_sizes = [len(pkt[Raw].load) if pkt.haslayer(Raw) else 0 for pkt in icmp_packets]
                if icmp_sizes and max(icmp_sizes) > 64:  # Unusual ICMP payload size
                    covert_channels.append({
                        'type': 'icmp_covert_channel',
                        'description': 'Unusual ICMP packet sizes detected',
                        'packet_count': len(icmp_packets),
                        'max_payload_size': max(icmp_sizes)
                    })
            
            # Analyze DNS for covert channels
            dns_packets = [pkt for pkt in packets if pkt.haslayer(DNS)]
            for pkt in dns_packets:
                if pkt[DNS].qr == 0 and pkt[DNS].qd:  # Query
                    domain = pkt[DNS].qd.qname.decode('utf-8', errors='ignore')
                    
                    # Check for suspicious entropy in domain names
                    if len(domain) > 20 and self._calculate_entropy(domain.encode()) > 4.5:
                        covert_channels.append({
                            'type': 'dns_covert_channel',
                            'description': 'High entropy domain name suggesting covert communication',
                            'domain': domain,
                            'entropy': self._calculate_entropy(domain.encode())
                        })
            
            results['covert_channels'] = covert_channels
            
        except Exception as e:
            self.logger.error(f"Error detecting covert channels: {e}")
    
    async def _analyze_protocol_anomalies(self, packets: List, results: Dict[str, Any]):
        """Analyze for protocol-level anomalies."""
        try:
            anomalies = []
            
            # Protocol distribution analysis
            protocol_counts = defaultdict(int)
            for pkt in packets:
                if pkt.haslayer(IP):
                    protocol_counts[pkt[IP].proto] += 1
            
            total_packets = len(packets)
            for proto, count in protocol_counts.items():
                percentage = (count / total_packets) * 100
                
                # Flag unusual protocol distributions
                if proto not in [6, 17, 1] and percentage > 5:  # Not TCP, UDP, or ICMP
                    anomalies.append({
                        'type': 'unusual_protocol_distribution',
                        'protocol': proto,
                        'percentage': percentage,
                        'description': f'Unusual amount of protocol {proto} traffic: {percentage:.1f}%'
                    })
            
            results['protocol_anomalies'] = anomalies
            
        except Exception as e:
            self.logger.error(f"Error analyzing protocol anomalies: {e}")
    
    async def _detect_application_protocol(self, payload: bytes, port: int) -> str:
        """Detect application protocol from payload and port."""
        try:
            if not payload:
                return 'unknown'
            
            # HTTP detection
            if payload.startswith(b'GET ') or payload.startswith(b'POST ') or payload.startswith(b'HTTP/'):
                return 'HTTP'
            
            # HTTPS/TLS detection
            if payload.startswith(b'\x16\x03') or port == 443:
                return 'HTTPS/TLS'
            
            # FTP detection
            if b'220 ' in payload[:20] or port in [20, 21]:
                return 'FTP'
            
            # SMTP detection
            if b'220 ' in payload[:20] and port == 25:
                return 'SMTP'
            
            # SSH detection
            if payload.startswith(b'SSH-') or port == 22:
                return 'SSH'
            
            # DNS detection
            if port == 53:
                return 'DNS'
            
            # Common ports
            port_protocols = {
                80: 'HTTP',
                443: 'HTTPS',
                21: 'FTP',
                22: 'SSH',
                23: 'Telnet',
                25: 'SMTP',
                53: 'DNS',
                110: 'POP3',
                143: 'IMAP',
                993: 'IMAPS',
                995: 'POP3S'
            }
            
            return port_protocols.get(port, 'unknown')
            
        except Exception as e:
            self.logger.error(f"Error detecting application protocol: {e}")
            return 'unknown'
    
    async def _analyze_stream_security(self, payload: bytes, protocol: str) -> List[Dict[str, Any]]:
        """Analyze stream payload for security issues."""
        issues = []
        
        try:
            if not payload:
                return issues
            
            payload_str = payload.decode('utf-8', errors='ignore')
            
            # Check for SQL injection patterns
            for pattern in self.config['sql_injection_patterns']:
                if re.search(pattern, payload_str, re.IGNORECASE):
                    issues.append({
                        'type': 'sql_injection',
                        'pattern': pattern,
                        'severity': 'high'
                    })
            
            # Check for XSS patterns
            for pattern in self.config['xss_patterns']:
                if re.search(pattern, payload_str, re.IGNORECASE):
                    issues.append({
                        'type': 'xss',
                        'pattern': pattern,
                        'severity': 'medium'
                    })
            
            # Check for potential credentials
            if re.search(r'password\s*[:=]\s*["\']?[^\s"\']+', payload_str, re.IGNORECASE):
                issues.append({
                    'type': 'potential_credentials',
                    'description': 'Potential password transmission detected',
                    'severity': 'high'
                })
            
        except Exception as e:
            self.logger.error(f"Error analyzing stream security: {e}")
        
        return issues
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data."""
        if not data:
            return 0.0
        
        # Count byte frequencies
        byte_counts = defaultdict(int)
        for byte in data:
            byte_counts[byte] += 1
        
        # Calculate entropy
        entropy = 0.0
        data_len = len(data)
        
        for count in byte_counts.values():
            if count > 0:
                probability = count / data_len
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy
    
    def _is_suspicious_domain(self, domain: str) -> bool:
        """Check if domain has suspicious characteristics."""
        # Check for excessive length
        if len(domain) > 100:
            return True
        
        # Check for high entropy (random-looking strings)
        if self._calculate_entropy(domain.encode()) > 4.0:
            return True
        
        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf']
        if any(domain.endswith(tld) for tld in suspicious_tlds):
            return True
        
        return False
    
    def _get_suspicious_patterns(self, domain: str) -> List[str]:
        """Get list of suspicious patterns found in domain."""
        patterns = []
        
        if len(domain) > 100:
            patterns.append('excessive_length')
        
        if self._calculate_entropy(domain.encode()) > 4.0:
            patterns.append('high_entropy')
        
        if re.search(r'[0-9]{4,}', domain):
            patterns.append('excessive_numbers')
        
        return patterns
    
    def _check_http_security_patterns(self, payload: str) -> List[Dict[str, Any]]:
        """Check HTTP payload for security patterns."""
        issues = []
        
        # SQL injection
        for pattern in self.config['sql_injection_patterns']:
            if re.search(pattern, payload, re.IGNORECASE):
                issues.append({
                    'type': 'sql_injection',
                    'pattern': pattern,
                    'severity': 'high',
                    'description': f'SQL injection pattern detected: {pattern}'
                })
        
        # XSS
        for pattern in self.config['xss_patterns']:
            if re.search(pattern, payload, re.IGNORECASE):
                issues.append({
                    'type': 'xss',
                    'pattern': pattern,
                    'severity': 'medium',
                    'description': f'XSS pattern detected: {pattern}'
                })
        
        return issues


# Global instance
advanced_protocol_analyzer = AdvancedProtocolAnalyzer()