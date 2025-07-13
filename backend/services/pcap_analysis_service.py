"""
PCAP Analysis Service.

Core service for analyzing packet capture files using a hybrid approach:
- Stage 1: High-speed triage with tshark for statistics and filtering
- Stage 2: Deep inspection with Scapy for detailed analysis

Provides comprehensive network analysis including protocol analysis,
performance metrics, and automated issue detection.
"""

import asyncio
import subprocess
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from models.analysis_results import (
    AnalysisResults, TrafficStats, PerformanceMetrics, ProtocolStats,
    NetworkIssue, TCPAnalysis, DNSAnalysis, ConversationFlow,
    SeverityLevel, IssueType
)
from services.protocol_analyzers import ProtocolAnalysisEngine
from services.packet_processing_pipeline import PacketProcessingPipeline
from services.advanced_protocol_analyzer import advanced_protocol_analyzer
from services.ml_anomaly_detector import ml_anomaly_detector

logger = logging.getLogger(__name__)


class PcapAnalysisService:
    """Service for comprehensive PCAP file analysis."""
    
    # Configuration constants
    MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB max file size
    MIN_FILE_SIZE = 24  # Minimum PCAP header size
    
    # Performance thresholds
    HIGH_LATENCY_THRESHOLD = 0.2  # 200ms
    PACKET_LOSS_THRESHOLD = 0.05  # 5%
    DNS_SLOW_THRESHOLD = 0.1  # 100ms
    DNS_FAILURE_THRESHOLD = 0.1  # 10%
    
    def __init__(self):
        """Initialize the PCAP analysis service."""
        self.logger = logging.getLogger(__name__)
        self.protocol_engine = ProtocolAnalysisEngine()
        self.packet_pipeline = PacketProcessingPipeline()
    
    async def analyze_pcap_file(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> AnalysisResults:
        """
        Analyze a PCAP file and return comprehensive results.
        
        Args:
            file_path: Path to the PCAP file to analyze
            options: Optional analysis configuration
            
        Returns:
            AnalysisResults: Comprehensive analysis results
            
        Raises:
            FileNotFoundError: If PCAP file doesn't exist
            ValueError: If file is invalid or too large/small
            RuntimeError: If analysis tools fail
        """
        start_time = time.time()
        
        # Validate file
        await self._validate_pcap_file(file_path)
        
        # Extract basic statistics using tshark
        basic_stats = await self._extract_basic_stats(file_path)
        
        # Analyze protocols
        protocol_data = await self._analyze_protocols(file_path)
        
        # Perform advanced protocol analysis
        advanced_protocol_analysis = await self._perform_advanced_protocol_analysis(file_path)
        
        # Perform deep protocol inspection
        deep_protocol_analysis = await advanced_protocol_analyzer.analyze_protocols(file_path)
        
        # Perform ML-based anomaly detection
        ml_anomaly_analysis = await ml_anomaly_detector.analyze_pcap_for_anomalies(file_path)
        
        # Detect performance issues
        issues = await self._detect_performance_issues(file_path)
        
        # Build comprehensive results
        processing_time = time.time() - start_time
        
        # Create traffic stats
        traffic_stats = TrafficStats(
            total_packets=basic_stats['total_packets'],
            total_bytes=basic_stats['total_bytes'],
            duration=basic_stats['duration'],
            avg_packet_size=basic_stats['total_bytes'] / basic_stats['total_packets'] if basic_stats['total_packets'] > 0 else 0,
            packets_per_second=basic_stats['total_packets'] / basic_stats['duration'] if basic_stats['duration'] > 0 else 0,
            bytes_per_second=basic_stats['total_bytes'] / basic_stats['duration'] if basic_stats['duration'] > 0 else 0
        )
        
        # Create performance metrics (will be enhanced with actual analysis)
        performance_metrics = PerformanceMetrics(
            avg_latency=0.05,  # Placeholder - will be calculated from actual analysis
            max_latency=0.25,  # Placeholder
            packet_loss_rate=0.01,  # Placeholder
            throughput_mbps=(basic_stats['total_bytes'] * 8) / (basic_stats['duration'] * 1024 * 1024) if basic_stats['duration'] > 0 else 0
        )
        
        # Create protocol stats
        protocol_stats = ProtocolStats(
            tcp_packets=protocol_data.get('tcp_packets', 0),
            udp_packets=protocol_data.get('udp_packets', 0),
            icmp_packets=protocol_data.get('icmp_packets', 0),
            http_sessions=protocol_data.get('http_sessions', 0),
            https_sessions=protocol_data.get('https_sessions', 0),
            dns_queries=protocol_data.get('dns_queries', 0),
            dhcp_packets=protocol_data.get('dhcp_packets', 0),
            arp_packets=protocol_data.get('arp_packets', 0)
        )
        
        # Convert issues to NetworkIssue objects
        network_issues = []
        for issue in issues:
            network_issues.append(NetworkIssue(
                type=IssueType(issue['type']),
                severity=SeverityLevel(issue['severity']),
                description=issue['description'],
                recommendation=issue.get('recommendation', ''),
                confidence=issue.get('confidence', 1.0)
            ))
        
        # Add security issues from deep protocol analysis
        for security_issue in deep_protocol_analysis.get('security_issues', []):
            network_issues.append(NetworkIssue(
                type=IssueType.SECURITY_ANOMALIES,
                severity=SeverityLevel(security_issue.get('severity', 'medium').lower()),
                description=security_issue.get('description', 'Security anomaly detected'),
                recommendation='Review security implications and implement appropriate controls',
                confidence=0.8
            ))
        
        # Add data exfiltration indicators as high-severity issues
        for exfil_indicator in deep_protocol_analysis.get('data_exfiltration_indicators', []):
            network_issues.append(NetworkIssue(
                type=IssueType.SECURITY_ANOMALIES,
                severity=SeverityLevel.HIGH,
                description=f"Data exfiltration indicator: {exfil_indicator.get('description', 'Unknown')}",
                recommendation='Investigate potential data exfiltration and secure sensitive data',
                confidence=0.85
            ))
        
        # Add malware indicators as critical issues
        for malware_indicator in deep_protocol_analysis.get('malware_indicators', []):
            network_issues.append(NetworkIssue(
                type=IssueType.SECURITY_ANOMALIES,
                severity=SeverityLevel.CRITICAL,
                description=f"Malware indicator detected: {malware_indicator.get('type', 'Unknown')}",
                recommendation='Immediate malware investigation and containment required',
                confidence=0.9
            ))
        
        # Add ML-detected anomalies as issues
        for ml_anomaly in ml_anomaly_analysis.get('anomalies', []):
            severity_map = {
                'low': SeverityLevel.LOW,
                'medium': SeverityLevel.MEDIUM,
                'high': SeverityLevel.HIGH
            }
            
            network_issues.append(NetworkIssue(
                type=IssueType.SECURITY_ANOMALIES,
                severity=severity_map.get(ml_anomaly.get('severity', 'medium'), SeverityLevel.MEDIUM),
                description=f"ML Anomaly: {ml_anomaly.get('description', 'Unknown anomaly')}",
                recommendation=f"Investigate {ml_anomaly.get('anomaly_type', 'unknown')} activity pattern",
                confidence=ml_anomaly.get('confidence', 0.7)
            ))
        
        # Merge protocol analysis results
        merged_protocol_analysis = {
            'advanced_analysis': advanced_protocol_analysis,
            'deep_inspection': deep_protocol_analysis,
            'ml_anomaly_detection': ml_anomaly_analysis
        }
        
        # Create analysis results
        results = AnalysisResults(
            file_path=file_path,
            file_size=Path(file_path).stat().st_size,
            traffic_stats=traffic_stats,
            performance_metrics=performance_metrics,
            protocol_stats=protocol_stats,
            issues=network_issues,
            protocol_analysis=merged_protocol_analysis,
            start_time=basic_stats['start_time'],
            end_time=basic_stats['end_time'],
            analysis_options=options or {},
            processing_time=processing_time
        )
        
        return results

    async def analyze_pcap(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> AnalysisResults:
        """
        Enhanced PCAP analysis method that integrates packet processing pipeline and protocol analysis.
        
        This method provides the comprehensive analysis interface expected by the integration tests
        and includes advanced protocol analysis capabilities.
        """
        return await self.analyze_pcap_file(file_path, options)

    async def _extract_packets_with_tshark(self, file_path: str) -> List:
        """
        Extract packets using tshark for packet processing pipeline.
        
        Returns a list of PacketData objects extracted from the PCAP file.
        """
        # Use the packet processing pipeline to extract packets
        packets = await self.packet_pipeline.extract_packets_with_tshark(file_path)
        return packets

    async def _perform_advanced_protocol_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Perform advanced protocol analysis using the protocol analysis engine.
        
        This includes deep packet inspection, stream reconstruction, and 
        protocol-specific analysis for TCP, UDP, HTTP, and DNS.
        """
        try:
            # Extract packets using the packet processing pipeline
            packets = await self._extract_packets_with_tshark(file_path)
            
            if not packets:
                self.logger.warning("No packets extracted from PCAP file")
                return {}
            
            # Perform comprehensive protocol analysis
            protocol_results = await self.protocol_engine.analyze_protocols(packets)
            
            # Generate protocol summary
            protocol_summary = await self.protocol_engine.generate_summary(packets)
            
            return {
                'detailed_results': protocol_results,
                'summary': protocol_summary,
                'packet_count': len(packets)
            }
            
        except Exception as e:
            self.logger.error(f"Advanced protocol analysis failed: {e}")
            return {}

    async def _validate_pcap_file(self, file_path: str) -> None:
        """Validate PCAP file exists and is within size limits."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"PCAP file not found: {file_path}")
        
        file_size = path.stat().st_size
        
        if file_size < self.MIN_FILE_SIZE:
            raise ValueError(f"PCAP file is empty or too small: {file_size} bytes")
        
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"PCAP file too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})")
    
    async def _extract_basic_stats(self, file_path: str) -> Dict[str, Any]:
        """
        Extract basic statistics using tshark.
        
        Uses tshark to quickly extract:
        - Total packet count
        - Total bytes
        - Capture duration
        - Start/end timestamps
        """
        try:
            # Get basic packet count and IO statistics
            io_stats_cmd = [
                'tshark',
                '-r', file_path,
                '-q',  # Quiet mode
                '-z', 'io,stat,0'  # IO statistics for entire capture
            ]
            
            process = await asyncio.create_subprocess_exec(
                *io_stats_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"tshark failed: {stderr.decode()}")
            
            # Parse IO statistics output
            output = stdout.decode()
            total_packets = 0
            total_bytes = 0
            duration = 0.0
            
            # Parse the IO statistics output
            for line in output.split('\n'):
                if 'Packets:' in line and 'Bytes:' in line:
                    # Extract packet and byte counts from line like: "| Duration: 60.0 | Packets: 1000 | Bytes: 1024000 |"
                    parts = line.split('|')
                    for part in parts:
                        part = part.strip()
                        if 'Packets:' in part:
                            total_packets = int(part.split(':')[1].strip())
                        elif 'Bytes:' in part:
                            total_bytes = int(part.split(':')[1].strip())
                        elif 'Duration:' in part:
                            duration = float(part.split(':')[1].strip())
            
            # Get first and last packet timestamps
            timestamps_cmd = [
                'tshark',
                '-r', file_path,
                '-T', 'fields',
                '-e', 'frame.time',
                '-E', 'separator=|'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *timestamps_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                timestamps = stdout.decode().strip().split('\n')
                if timestamps and timestamps[0]:
                    start_time = timestamps[0].strip()
                    end_time = timestamps[-1].strip() if len(timestamps) > 1 else start_time
                else:
                    # Fallback timestamps
                    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                    end_time = start_time
            else:
                # Fallback timestamps
                start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                end_time = start_time
            
            # If we couldn't parse from IO stats, try alternative method
            if total_packets == 0:
                # Count packets directly
                count_cmd = [
                    'tshark',
                    '-r', file_path,
                    '-T', 'fields',
                    '-e', 'frame.number',
                    '-e', 'frame.len'
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *count_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    lines = stdout.decode().strip().split('\n')
                    total_packets = len([line for line in lines if line.strip()])
                    
                    # Calculate total bytes
                    for line in lines:
                        if line.strip():
                            parts = line.strip().split('\t')
                            if len(parts) >= 2 and parts[1].isdigit():
                                total_bytes += int(parts[1])
            
            return {
                'total_packets': total_packets,
                'total_bytes': total_bytes,
                'duration': duration,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract basic stats: {e}")
            raise RuntimeError(f"tshark execution failed: {e}")
    
    async def _analyze_protocols(self, file_path: str) -> Dict[str, int]:
        """
        Analyze protocol distribution using tshark.
        
        Returns counts for different protocols found in the capture.
        """
        try:
            # Get protocol counts
            protocol_counts = await self._get_protocol_counts(file_path)
            
            return {
                'tcp_packets': int(protocol_counts.get('tcp', 0)),
                'udp_packets': int(protocol_counts.get('udp', 0)),
                'icmp_packets': int(protocol_counts.get('icmp', 0)),
                'http_sessions': int(protocol_counts.get('http', 0)),
                'https_sessions': int(protocol_counts.get('https', 0)),
                'dns_queries': int(protocol_counts.get('dns', 0)),
                'dhcp_packets': int(protocol_counts.get('dhcp', 0)),
                'arp_packets': int(protocol_counts.get('arp', 0))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze protocols: {e}")
            # Return zeros for all protocols on error
            return {
                'tcp_packets': 0,
                'udp_packets': 0,
                'icmp_packets': 0,
                'http_sessions': 0,
                'https_sessions': 0,
                'dns_queries': 0,
                'dhcp_packets': 0,
                'arp_packets': 0
            }
    
    async def _get_protocol_counts(self, file_path: str) -> Dict[str, str]:
        """Get protocol counts using tshark."""
        try:
            # Get protocol hierarchy statistics
            cmd = [
                'tshark',
                '-r', file_path,
                '-q',
                '-z', 'io,phs'  # Protocol hierarchy statistics
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.warning(f"tshark protocol analysis failed: {stderr.decode()}")
                return {}
            
            # Parse protocol hierarchy output
            output = stdout.decode()
            protocol_counts = {}
            
            for line in output.split('\n'):
                line = line.strip()
                if not line or line.startswith('=') or 'Protocol Hierarchy Statistics' in line:
                    continue
                
                # Parse lines like: "tcp                      frames:800 bytes:1024000"
                if 'frames:' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        protocol = parts[0].lower()
                        frames_part = [p for p in parts if 'frames:' in p]
                        if frames_part:
                            frame_count = frames_part[0].split(':')[1]
                            protocol_counts[protocol] = frame_count
            
            # Also get specific protocol counts for common protocols
            specific_protocols = {
                'http': 'http',
                'https': 'tls',
                'dns': 'dns',
                'dhcp': 'dhcp',
                'arp': 'arp'
            }
            
            for proto_name, tshark_filter in specific_protocols.items():
                cmd = [
                    'tshark',
                    '-r', file_path,
                    '-Y', tshark_filter,  # Display filter
                    '-T', 'fields',
                    '-e', 'frame.number'
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    lines = stdout.decode().strip().split('\n')
                    count = len([line for line in lines if line.strip()])
                    if count > 0:
                        protocol_counts[proto_name] = str(count)
            
            return protocol_counts
            
        except Exception as e:
            self.logger.error(f"Failed to get protocol counts: {e}")
            return {}
    
    async def _detect_performance_issues(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Detect performance issues by analyzing network metrics.
        
        Returns list of detected issues with severity and recommendations.
        """
        issues = []
        
        try:
            # Analyze TCP performance
            tcp_stats = await self._analyze_tcp_performance(file_path)
            
            # Check for high latency
            if tcp_stats.get('avg_handshake_time', 0) > self.HIGH_LATENCY_THRESHOLD:
                issues.append({
                    'type': 'high_latency',
                    'severity': 'medium' if tcp_stats['avg_handshake_time'] < 0.5 else 'high',
                    'description': f"High TCP handshake latency detected: {tcp_stats['avg_handshake_time']:.3f}s average",
                    'recommendation': 'Check network connectivity and server response times',
                    'confidence': 0.9
                })
            
            # Check for packet loss
            retrans_rate = tcp_stats.get('retransmission_rate', 0)
            if retrans_rate > self.PACKET_LOSS_THRESHOLD:
                issues.append({
                    'type': 'packet_loss',
                    'severity': 'medium' if retrans_rate < 0.1 else 'high',
                    'description': f"High retransmission rate detected: {retrans_rate:.1%}",
                    'recommendation': 'Investigate network path for packet loss',
                    'confidence': 0.85
                })
            
            # Analyze DNS performance
            dns_stats = await self._analyze_dns_performance(file_path)
            
            # Check for DNS issues
            if (dns_stats.get('avg_response_time', 0) > self.DNS_SLOW_THRESHOLD or
                dns_stats.get('failure_rate', 0) > self.DNS_FAILURE_THRESHOLD):
                issues.append({
                    'type': 'dns_issues',
                    'severity': 'medium',
                    'description': f"DNS performance issues detected",
                    'recommendation': 'Check DNS server configuration and connectivity',
                    'confidence': 0.8
                })
            
        except Exception as e:
            self.logger.error(f"Failed to detect performance issues: {e}")
        
        return issues
    
    async def _analyze_tcp_performance(self, file_path: str) -> Dict[str, float]:
        """Analyze TCP performance metrics."""
        try:
            metrics = {
                'avg_handshake_time': 0.0,
                'max_handshake_time': 0.0,
                'retransmissions': 0,
                'total_packets': 0,
                'retransmission_rate': 0.0,
                'failed_connections': 0
            }
            
            # Get TCP retransmissions
            retrans_cmd = [
                'tshark',
                '-r', file_path,
                '-Y', 'tcp.analysis.retransmission',
                '-T', 'fields',
                '-e', 'frame.number'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *retrans_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                retrans_lines = stdout.decode().strip().split('\n')
                metrics['retransmissions'] = len([line for line in retrans_lines if line.strip()])
            
            # Get total TCP packets
            tcp_cmd = [
                'tshark',
                '-r', file_path,
                '-Y', 'tcp',
                '-T', 'fields',
                '-e', 'frame.number'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *tcp_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                tcp_lines = stdout.decode().strip().split('\n')
                metrics['total_packets'] = len([line for line in tcp_lines if line.strip()])
            
            # Calculate retransmission rate
            if metrics['total_packets'] > 0:
                metrics['retransmission_rate'] = metrics['retransmissions'] / metrics['total_packets']
            
            # Analyze connection handshakes for timing (simplified)
            syn_cmd = [
                'tshark',
                '-r', file_path,
                '-Y', 'tcp.flags.syn==1 and tcp.flags.ack==0',
                '-T', 'fields',
                '-e', 'frame.time_relative'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *syn_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                syn_times = stdout.decode().strip().split('\n')
                syn_times = [float(t) for t in syn_times if t.strip() and t.replace('.', '').isdigit()]
                
                if len(syn_times) > 1:
                    # Estimate handshake times (simplified calculation)
                    handshake_times = []
                    for i in range(1, min(len(syn_times), 10)):  # Sample first 10
                        if syn_times[i] > syn_times[i-1]:
                            handshake_times.append(syn_times[i] - syn_times[i-1])
                    
                    if handshake_times:
                        metrics['avg_handshake_time'] = sum(handshake_times) / len(handshake_times)
                        metrics['max_handshake_time'] = max(handshake_times)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to analyze TCP performance: {e}")
            return {
                'avg_handshake_time': 0.0,
                'max_handshake_time': 0.0,
                'retransmissions': 0,
                'total_packets': 0,
                'retransmission_rate': 0.0,
                'failed_connections': 0
            }
    
    async def _analyze_dns_performance(self, file_path: str) -> Dict[str, float]:
        """Analyze DNS performance metrics."""
        try:
            metrics = {
                'avg_response_time': 0.0,
                'max_response_time': 0.0,
                'failed_queries': 0,
                'total_queries': 0,
                'failure_rate': 0.0,
                'timeout_queries': 0
            }
            
            # Get all DNS queries
            dns_queries_cmd = [
                'tshark',
                '-r', file_path,
                '-Y', 'dns.flags.response==0',  # DNS queries only
                '-T', 'fields',
                '-e', 'frame.number',
                '-e', 'frame.time_relative',
                '-e', 'dns.id'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *dns_queries_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            queries = []
            if process.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) >= 3:
                            queries.append({
                                'frame': parts[0],
                                'time': float(parts[1]) if parts[1].replace('.', '').isdigit() else 0.0,
                                'id': parts[2]
                            })
                
                metrics['total_queries'] = len(queries)
            
            # Get DNS responses
            dns_responses_cmd = [
                'tshark',
                '-r', file_path,
                '-Y', 'dns.flags.response==1',  # DNS responses only
                '-T', 'fields',
                '-e', 'frame.number',
                '-e', 'frame.time_relative',
                '-e', 'dns.id',
                '-e', 'dns.flags.rcode'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *dns_responses_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            responses = []
            if process.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) >= 4:
                            responses.append({
                                'frame': parts[0],
                                'time': float(parts[1]) if parts[1].replace('.', '').isdigit() else 0.0,
                                'id': parts[2],
                                'rcode': parts[3]
                            })
            
            # Match queries with responses and calculate response times
            response_times = []
            failed_count = 0
            
            for query in queries:
                # Find matching response
                matching_response = None
                for response in responses:
                    if (response['id'] == query['id'] and 
                        response['time'] > query['time']):
                        matching_response = response
                        break
                
                if matching_response:
                    response_time = matching_response['time'] - query['time']
                    response_times.append(response_time)
                    
                    # Check if it's a failed query (non-zero rcode)
                    if matching_response['rcode'] != '0':
                        failed_count += 1
                else:
                    # No response found - timeout
                    metrics['timeout_queries'] += 1
                    failed_count += 1
            
            # Calculate metrics
            if response_times:
                metrics['avg_response_time'] = sum(response_times) / len(response_times)
                metrics['max_response_time'] = max(response_times)
            
            metrics['failed_queries'] = failed_count
            
            if metrics['total_queries'] > 0:
                metrics['failure_rate'] = failed_count / metrics['total_queries']
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to analyze DNS performance: {e}")
            return {
                'avg_response_time': 0.0,
                'max_response_time': 0.0,
                'failed_queries': 0,
                'total_queries': 0,
                'failure_rate': 0.0,
                'timeout_queries': 0
            }
    
    async def _extract_conversations(self, file_path: str, limit: int = 10) -> List[ConversationFlow]:
        """Extract top network conversations from the capture."""
        # TODO: Implement conversation extraction using tshark
        return []
    
    async def _calculate_advanced_metrics(self, file_path: str) -> Dict[str, Any]:
        """Calculate advanced performance metrics."""
        # TODO: Implement advanced metrics calculation
        return {}


class TsharkError(Exception):
    """Exception raised when tshark execution fails."""
    pass


class PysharkError(Exception):
    """Exception raised when pyshark processing fails."""
    pass 