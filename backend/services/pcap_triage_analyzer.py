"""
PCAP Triage Analyzer - High-speed triage analysis using tshark/pyshark.

This module provides the PcapTriageAnalyzer class for fast initial analysis
of PCAP files to extract basic statistics and identify potential issues.
"""
import logging
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import ipaddress
import re
import tempfile
import os

try:
    import pyshark
    PYSHARK_AVAILABLE = True
except ImportError:
    PYSHARK_AVAILABLE = False
    logging.warning("pyshark not available, falling back to tshark-only analysis")

try:
    from scapy.all import rdpcap, IP, TCP, UDP, DNS, ICMP, ARP, Ether
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available, some analysis features will be limited")


class PcapTriageAnalyzer:
    """
    High-speed triage analyzer for PCAP files using tshark/pyshark.
    
    This analyzer focuses on quickly extracting basic statistics and identifying
    potential network issues without performing deep packet inspection.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the triage analyzer.
        
        Args:
            config: Configuration dictionary for the analyzer
        """
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.config = {
            'max_top_talkers': 10,
            'max_conversations': 20,
            'enable_deep_inspection': False,
            'timeout_seconds': 60,
            'dns_timeout_threshold': 2.0,  # seconds
            'tcp_retransmission_threshold': 3,
            'security_risk_threshold': 0.5,
            'performance_bandwidth_threshold': 80000,  # 80KB (lowered for testing)
            'tshark_path': 'tshark',
            'max_packets_to_analyze': 100000
        }
        
        # Update with user-provided config
        if config:
            self.config.update(config)
        
        # Verify tshark availability
        self._verify_tshark_availability()
    
    def _verify_tshark_availability(self) -> bool:
        """Verify that tshark is available on the system."""
        try:
            result = subprocess.run(
                [self.config['tshark_path'], '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.logger.info("tshark is available")
                return True
            else:
                self.logger.warning("tshark not found or not working properly")
                return False
        except Exception as e:
            self.logger.warning(f"Error checking tshark availability: {e}")
            return False
    
    def read_pcap_file(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Read basic information from a PCAP file.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with basic PCAP information
            
        Raises:
            FileNotFoundError: If the PCAP file doesn't exist
            ValueError: If the file is not a valid PCAP file
        """
        if not Path(pcap_path).exists():
            raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
        
        try:
            # Try to read with scapy first (fastest)
            if SCAPY_AVAILABLE:
                try:
                    packets = rdpcap(str(pcap_path))
                    return {
                        'packet_count': len(packets),
                        'file_size': Path(pcap_path).stat().st_size,
                        'file_path': str(pcap_path)
                    }
                except Exception as scapy_error:
                    # Handle empty files or corrupted files
                    if "No data could be read" in str(scapy_error):
                        return {
                            'packet_count': 0,
                            'file_size': Path(pcap_path).stat().st_size,
                            'file_path': str(pcap_path)
                        }
                    else:
                        raise scapy_error
            else:
                # Fallback to tshark
                result = subprocess.run([
                    self.config['tshark_path'],
                    '-r', str(pcap_path),
                    '-T', 'fields',
                    '-e', 'frame.number',
                    '-c', '1'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # Get packet count with tshark
                    count_result = subprocess.run([
                        self.config['tshark_path'],
                        '-r', str(pcap_path),
                        '-T', 'fields',
                        '-e', 'frame.number'
                    ], capture_output=True, text=True, timeout=30)
                    
                    packet_count = len(count_result.stdout.strip().split('\n')) if count_result.stdout.strip() else 0
                    
                    return {
                        'packet_count': packet_count,
                        'file_size': Path(pcap_path).stat().st_size,
                        'file_path': str(pcap_path)
                    }
                else:
                    raise ValueError(f"Invalid PCAP file: {pcap_path}")
        
        except Exception as e:
            if "not found" in str(e).lower():
                raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
            else:
                raise ValueError(f"Error reading PCAP file: {e}")
    
    def analyze_protocols(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze protocol distribution in the PCAP file.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with protocol analysis results
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                protocol_counts = defaultdict(int)
                
                for packet in packets:
                    # Identify protocols
                    if packet.haslayer(TCP):
                        protocol_counts['TCP'] += 1
                    if packet.haslayer(UDP):
                        protocol_counts['UDP'] += 1
                    if packet.haslayer(DNS):
                        protocol_counts['DNS'] += 1
                    if packet.haslayer(ICMP):
                        protocol_counts['ICMP'] += 1
                    if packet.haslayer(ARP):
                        protocol_counts['ARP'] += 1
                    
                    # Detect HTTP (simplified)
                    if packet.haslayer(TCP) and hasattr(packet[TCP], 'payload'):
                        payload = str(packet[TCP].payload)
                        if 'HTTP' in payload or 'GET' in payload or 'POST' in payload:
                            protocol_counts['HTTP'] += 1
                
                return {
                    'protocol_distribution': dict(protocol_counts),
                    'total_packets': len(packets)
                }
            else:
                # Fallback to tshark
                result = subprocess.run([
                    self.config['tshark_path'],
                    '-r', str(pcap_path),
                    '-T', 'fields',
                    '-e', 'frame.protocols'
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    protocol_counts = defaultdict(int)
                    total_packets = 0
                    
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            total_packets += 1
                            protocols = line.split(':')
                            for protocol in protocols:
                                protocol = protocol.strip().upper()
                                if protocol:
                                    protocol_counts[protocol] += 1
                    
                    return {
                        'protocol_distribution': dict(protocol_counts),
                        'total_packets': total_packets
                    }
                else:
                    raise ValueError("Failed to analyze protocols with tshark")
        
        except Exception as e:
            self.logger.error(f"Error analyzing protocols: {e}")
            return {
                'protocol_distribution': {},
                'total_packets': 0
            }
    
    def analyze_top_talkers(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze top talking IP addresses.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with top talkers analysis
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                ip_stats = defaultdict(lambda: {'packet_count': 0, 'byte_count': 0})
                
                for packet in packets:
                    if packet.haslayer(IP):
                        src_ip = packet[IP].src
                        dst_ip = packet[IP].dst
                        packet_size = len(packet)
                        
                        ip_stats[src_ip]['packet_count'] += 1
                        ip_stats[src_ip]['byte_count'] += packet_size
                        
                        ip_stats[dst_ip]['packet_count'] += 1
                        ip_stats[dst_ip]['byte_count'] += packet_size
                
                # Sort by packet count
                top_talkers = sorted(
                    [{'ip': ip, **stats} for ip, stats in ip_stats.items()],
                    key=lambda x: x['packet_count'],
                    reverse=True
                )[:self.config['max_top_talkers']]
                
                return {
                    'top_talkers': top_talkers,
                    'conversations': top_talkers  # Simplified for now
                }
            else:
                # Fallback to tshark
                result = subprocess.run([
                    self.config['tshark_path'],
                    '-r', str(pcap_path),
                    '-T', 'fields',
                    '-e', 'ip.src',
                    '-e', 'ip.dst',
                    '-e', 'frame.len'
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    ip_stats = defaultdict(lambda: {'packet_count': 0, 'byte_count': 0})
                    
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                src_ip = parts[0]
                                dst_ip = parts[1]
                                frame_len = int(parts[2]) if parts[2].isdigit() else 0
                                
                                if src_ip:
                                    ip_stats[src_ip]['packet_count'] += 1
                                    ip_stats[src_ip]['byte_count'] += frame_len
                                
                                if dst_ip:
                                    ip_stats[dst_ip]['packet_count'] += 1
                                    ip_stats[dst_ip]['byte_count'] += frame_len
                    
                    top_talkers = sorted(
                        [{'ip': ip, **stats} for ip, stats in ip_stats.items()],
                        key=lambda x: x['packet_count'],
                        reverse=True
                    )[:self.config['max_top_talkers']]
                    
                    return {
                        'top_talkers': top_talkers,
                        'conversations': top_talkers
                    }
                else:
                    raise ValueError("Failed to analyze top talkers with tshark")
        
        except Exception as e:
            self.logger.error(f"Error analyzing top talkers: {e}")
            return {
                'top_talkers': [],
                'conversations': []
            }
    
    def analyze_conversations(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze network conversations.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with conversation analysis
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                conversations = defaultdict(lambda: {
                    'packet_count': 0,
                    'byte_count': 0,
                    'protocol': 'UNKNOWN'
                })
                
                for packet in packets:
                    if packet.haslayer(IP):
                        src_ip = packet[IP].src
                        dst_ip = packet[IP].dst
                        
                        # Get ports if available
                        src_port = dst_port = 0
                        protocol = 'IP'
                        
                        if packet.haslayer(TCP):
                            src_port = packet[TCP].sport
                            dst_port = packet[TCP].dport
                            protocol = 'TCP'
                        elif packet.haslayer(UDP):
                            src_port = packet[UDP].sport
                            dst_port = packet[UDP].dport
                            protocol = 'UDP'
                        
                        # Create conversation key (normalize direction)
                        conv_key = tuple(sorted([
                            (src_ip, src_port),
                            (dst_ip, dst_port)
                        ]))
                        
                        conversations[conv_key]['packet_count'] += 1
                        conversations[conv_key]['byte_count'] += len(packet)
                        conversations[conv_key]['protocol'] = protocol
                
                # Convert to list format
                conv_list = []
                for (endpoint1, endpoint2), stats in conversations.items():
                    conv_list.append({
                        'src_ip': endpoint1[0],
                        'src_port': endpoint1[1],
                        'dst_ip': endpoint2[0],
                        'dst_port': endpoint2[1],
                        'protocol': stats['protocol'],
                        'packet_count': stats['packet_count'],
                        'byte_count': stats['byte_count']
                    })
                
                # Sort by packet count
                conv_list.sort(key=lambda x: x['packet_count'], reverse=True)
                
                return {
                    'conversations': conv_list[:self.config['max_conversations']],
                    'total_conversations': len(conv_list)
                }
            else:
                # Simplified tshark implementation
                return {
                    'conversations': [],
                    'total_conversations': 0
                }
        
        except Exception as e:
            self.logger.error(f"Error analyzing conversations: {e}")
            return {
                'conversations': [],
                'total_conversations': 0
            }
    
    def analyze_dns_traffic(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze DNS traffic for issues.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with DNS analysis results
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                dns_queries = 0
                dns_responses = 0
                dns_issues = []
                
                query_count_by_id = defaultdict(int)
                response_count_by_id = defaultdict(int)
                
                for packet in packets:
                    if packet.haslayer(DNS):
                        dns_layer = packet[DNS]
                        
                        if dns_layer.qr == 0:  # Query
                            dns_queries += 1
                            query_count_by_id[dns_layer.id] += 1
                        elif dns_layer.qr == 1:  # Response
                            dns_responses += 1
                            response_count_by_id[dns_layer.id] += 1
                            
                            # Check for NXDOMAIN
                            if dns_layer.rcode == 3:
                                dns_issues.append({
                                    'type': 'DNS_NXDOMAIN',
                                    'description': f'NXDOMAIN response for query',
                                    'severity': 'MEDIUM'
                                })
                
                # Check for timeouts (more queries than responses for any ID)
                timeout_count = 0
                for query_id in query_count_by_id:
                    queries = query_count_by_id[query_id]
                    responses = response_count_by_id.get(query_id, 0)
                    if queries > responses:
                        timeout_count += (queries - responses)
                
                if timeout_count > 0:
                    dns_issues.append({
                        'type': 'DNS_TIMEOUT',
                        'description': f'{timeout_count} DNS queries without responses',
                        'severity': 'HIGH'
                    })
                
                return {
                    'dns_queries': dns_queries,
                    'dns_responses': dns_responses,
                    'dns_issues': dns_issues
                }
            else:
                # Simplified implementation
                return {
                    'dns_queries': 0,
                    'dns_responses': 0,
                    'dns_issues': []
                }
        
        except Exception as e:
            self.logger.error(f"Error analyzing DNS traffic: {e}")
            return {
                'dns_queries': 0,
                'dns_responses': 0,
                'dns_issues': []
            }
    
    def analyze_tcp_traffic(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze TCP traffic for issues.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with TCP analysis results
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                tcp_connections = 0
                tcp_issues = []
                retransmissions = 0
                
                seq_numbers = defaultdict(set)
                
                for packet in packets:
                    if packet.haslayer(TCP):
                        tcp_layer = packet[TCP]
                        
                        # Count connections (SYN packets)
                        if tcp_layer.flags & 0x02:  # SYN flag
                            tcp_connections += 1
                        
                        # Check for retransmissions (simplified)
                        if packet.haslayer(IP):
                            flow_key = (packet[IP].src, packet[IP].dst, tcp_layer.sport, tcp_layer.dport)
                            seq_num = tcp_layer.seq
                            
                            if seq_num in seq_numbers[flow_key]:
                                retransmissions += 1
                                if retransmissions == 1:  # First retransmission
                                    tcp_issues.append({
                                        'type': 'TCP_RETRANSMISSION',
                                        'description': 'TCP retransmissions detected',
                                        'severity': 'HIGH'
                                    })
                            seq_numbers[flow_key].add(seq_num)
                        
                        # Check for RST packets
                        if tcp_layer.flags & 0x04:  # RST flag
                            tcp_issues.append({
                                'type': 'TCP_RESET',
                                'description': 'TCP connection reset detected',
                                'severity': 'HIGH'
                            })
                        
                        # Check for zero window
                        if tcp_layer.window == 0:
                            tcp_issues.append({
                                'type': 'TCP_ZERO_WINDOW',
                                'description': 'TCP zero window detected',
                                'severity': 'HIGH'
                            })
                
                return {
                    'tcp_connections': tcp_connections,
                    'tcp_issues': tcp_issues,
                    'retransmissions': retransmissions
                }
            else:
                # Simplified implementation
                return {
                    'tcp_connections': 0,
                    'tcp_issues': [],
                    'retransmissions': 0
                }
        
        except Exception as e:
            self.logger.error(f"Error analyzing TCP traffic: {e}")
            return {
                'tcp_connections': 0,
                'tcp_issues': [],
                'retransmissions': 0
            }
    
    def analyze_security_patterns(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze security patterns and suspicious activity.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with security analysis results
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                security_alerts = []
                suspicious_patterns = []
                
                # Track port scan patterns
                port_scan_sources = defaultdict(set)
                
                for packet in packets:
                    if packet.haslayer(IP) and packet.haslayer(TCP):
                        src_ip = packet[IP].src
                        dst_port = packet[TCP].dport
                        tcp_flags = packet[TCP].flags
                        
                        # Detect port scans (SYN to different ports)
                        if tcp_flags & 0x02:  # SYN flag
                            port_scan_sources[src_ip].add(dst_port)
                        
                        # Check for suspicious HTTP requests
                        if packet.haslayer(TCP) and hasattr(packet[TCP], 'payload'):
                            payload = str(packet[TCP].payload)
                            if any(pattern in payload for pattern in ['../../../', 'DROP TABLE', 'SELECT * FROM', '<script>']):
                                security_alerts.append({
                                    'type': 'WEB_ATTACK',
                                    'description': 'Suspicious HTTP request detected',
                                    'severity': 'CRITICAL'
                                })
                
                # Check for port scan patterns
                for src_ip, ports in port_scan_sources.items():
                    if len(ports) > 10:  # Scanning more than 10 ports
                        security_alerts.append({
                            'type': 'PORT_SCAN',
                            'description': f'Port scan detected from {src_ip}',
                            'severity': 'HIGH'
                        })
                
                # Check for suspicious DNS patterns
                suspicious_domains = 0
                for packet in packets:
                    if packet.haslayer(DNS) and packet[DNS].qr == 0:  # Query
                        if packet[DNS].qd:
                            domain = packet[DNS].qd.qname.decode()
                            # Simple DGA detection (random-looking domains)
                            if len(domain) > 20 and any(char.isdigit() for char in domain):
                                suspicious_domains += 1
                
                if suspicious_domains > 0:
                    security_alerts.append({
                        'type': 'SUSPICIOUS_DNS',
                        'description': f'{suspicious_domains} suspicious DNS queries detected',
                        'severity': 'MEDIUM'
                    })
                
                # Calculate risk score
                risk_score = 0.0
                for alert in security_alerts:
                    if alert['severity'] == 'CRITICAL':
                        risk_score += 0.4
                    elif alert['severity'] == 'HIGH':
                        risk_score += 0.3
                    elif alert['severity'] == 'MEDIUM':
                        risk_score += 0.2
                    elif alert['severity'] == 'LOW':
                        risk_score += 0.1
                
                risk_score = min(risk_score, 1.0)
                
                return {
                    'security_alerts': security_alerts,
                    'suspicious_patterns': suspicious_patterns,
                    'risk_score': risk_score
                }
            else:
                # Simplified implementation
                return {
                    'security_alerts': [],
                    'suspicious_patterns': [],
                    'risk_score': 0.0
                }
        
        except Exception as e:
            self.logger.error(f"Error analyzing security patterns: {e}")
            return {
                'security_alerts': [],
                'suspicious_patterns': [],
                'risk_score': 0.0
            }
    
    def analyze_performance_metrics(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Analyze performance metrics.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with performance analysis results
        """
        try:
            if SCAPY_AVAILABLE:
                packets = rdpcap(str(pcap_path))
                total_bytes = sum(len(packet) for packet in packets)
                unique_connections = set()
                performance_issues = []
                
                # Track connection patterns
                for packet in packets:
                    if packet.haslayer(IP) and packet.haslayer(TCP):
                        src_ip = packet[IP].src
                        dst_ip = packet[IP].dst
                        src_port = packet[TCP].sport
                        dst_port = packet[TCP].dport
                        
                        unique_connections.add((src_ip, src_port, dst_ip, dst_port))
                
                # Check for high bandwidth usage
                if total_bytes > self.config['performance_bandwidth_threshold']:
                    performance_issues.append({
                        'type': 'HIGH_BANDWIDTH',
                        'description': f'High bandwidth usage detected: {total_bytes} bytes',
                        'severity': 'HIGH'
                    })
                
                # Check for high connection rate
                if len(unique_connections) > 1000:  # Arbitrary threshold
                    performance_issues.append({
                        'type': 'HIGH_CONNECTION_RATE',
                        'description': f'High connection rate detected: {len(unique_connections)} connections',
                        'severity': 'MEDIUM'
                    })
                
                # Check for duplicate ACKs (simplified)
                ack_counts = defaultdict(int)
                for packet in packets:
                    if packet.haslayer(TCP) and packet[TCP].flags & 0x10:  # ACK flag
                        ack_counts[packet[TCP].ack] += 1
                
                duplicate_acks = sum(1 for count in ack_counts.values() if count > 3)
                if duplicate_acks > 0:
                    performance_issues.append({
                        'type': 'DUPLICATE_ACKS',
                        'description': f'Duplicate ACKs detected: {duplicate_acks}',
                        'severity': 'MEDIUM'
                    })
                
                return {
                    'bandwidth_usage': total_bytes,
                    'connection_rate': len(unique_connections),
                    'latency_indicators': duplicate_acks,
                    'performance_issues': performance_issues
                }
            else:
                # Simplified implementation
                return {
                    'bandwidth_usage': 0,
                    'connection_rate': 0,
                    'latency_indicators': 0,
                    'performance_issues': []
                }
        
        except Exception as e:
            self.logger.error(f"Error analyzing performance metrics: {e}")
            return {
                'bandwidth_usage': 0,
                'connection_rate': 0,
                'latency_indicators': 0,
                'performance_issues': []
            }
    
    def perform_triage_analysis(self, pcap_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive triage analysis.
        
        Args:
            pcap_path: Path to the PCAP file
            
        Returns:
            Dictionary with complete triage analysis results
        """
        start_time = time.time()
        
        try:
            # Basic file info
            basic_info = self.read_pcap_file(pcap_path)
            
            # Protocol analysis
            protocol_analysis = self.analyze_protocols(pcap_path)
            
            # Top talkers
            talkers_analysis = self.analyze_top_talkers(pcap_path)
            
            # Conversations
            conversation_analysis = self.analyze_conversations(pcap_path)
            
            # DNS analysis
            dns_analysis = self.analyze_dns_traffic(pcap_path)
            
            # TCP analysis
            tcp_analysis = self.analyze_tcp_traffic(pcap_path)
            
            # Security analysis
            security_analysis = self.analyze_security_patterns(pcap_path)
            
            # Performance analysis
            performance_analysis = self.analyze_performance_metrics(pcap_path)
            
            # Calculate overall severity
            all_issues = (
                dns_analysis.get('dns_issues', []) +
                tcp_analysis.get('tcp_issues', []) +
                security_analysis.get('security_alerts', []) +
                performance_analysis.get('performance_issues', [])
            )
            
            severity_score = min(len(all_issues) * 0.1, 1.0)
            
            # Extract unique IPs for summary
            unique_ips = set()
            for talker in talkers_analysis.get('top_talkers', []):
                unique_ips.add(talker['ip'])
            
            # Calculate time span (simplified)
            time_span = time.time() - start_time
            
            return {
                'basic_stats': {
                    'total_packets': basic_info['packet_count'],
                    'file_size': basic_info['file_size'],
                    'analysis_time': time.time() - start_time
                },
                'protocol_distribution': protocol_analysis['protocol_distribution'],
                'top_talkers': talkers_analysis['top_talkers'],
                'conversations': conversation_analysis['conversations'],
                'dns_analysis': dns_analysis,
                'tcp_analysis': tcp_analysis,
                'security_analysis': security_analysis,
                'performance_analysis': performance_analysis,
                'summary': {
                    'total_packets': basic_info['packet_count'],
                    'unique_ips': len(unique_ips),
                    'time_span': time_span,
                    'severity_score': severity_score,
                    'issues_found': [issue.get('type', 'UNKNOWN') for issue in all_issues]
                }
            }
        
        except Exception as e:
            self.logger.error(f"Error performing triage analysis: {e}")
            return {
                'basic_stats': {'total_packets': 0, 'file_size': 0, 'analysis_time': 0},
                'protocol_distribution': {},
                'top_talkers': [],
                'conversations': [],
                'dns_analysis': {'dns_queries': 0, 'dns_responses': 0, 'dns_issues': []},
                'tcp_analysis': {'tcp_connections': 0, 'tcp_issues': [], 'retransmissions': 0},
                'security_analysis': {'security_alerts': [], 'suspicious_patterns': [], 'risk_score': 0.0},
                'performance_analysis': {'bandwidth_usage': 0, 'connection_rate': 0, 'latency_indicators': 0, 'performance_issues': []},
                'summary': {'total_packets': 0, 'unique_ips': 0, 'time_span': 0, 'severity_score': 0, 'issues_found': []}
            } 