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
        
        # Create analysis results
        results = AnalysisResults(
            file_path=file_path,
            file_size=Path(file_path).stat().st_size,
            traffic_stats=traffic_stats,
            performance_metrics=performance_metrics,
            protocol_stats=protocol_stats,
            issues=network_issues,
            protocol_analysis=advanced_protocol_analysis,
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
            # Build tshark command for basic statistics
            cmd = [
                'tshark',
                '-r', file_path,
                '-q',  # Quiet mode
                '-z', 'io,stat,0',  # IO statistics
                '-T', 'fields',
                '-e', 'frame.number',
                '-e', 'frame.len',
                '-e', 'frame.time_relative',
                '-e', 'frame.time',
                '-c', '1'  # Just get first packet for timing info
            ]
            
            # For now, return mock data that matches expected format
            # TODO: Replace with actual tshark execution
            return {
                'total_packets': 1000,
                'total_bytes': 1024000,
                'duration': 60.0,
                'start_time': '2025-01-15 10:00:00.000000',
                'end_time': '2025-01-15 10:01:00.000000'
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
        # Mock implementation for now
        # TODO: Replace with actual tshark protocol analysis
        return {
            'tcp': '800',
            'udp': '150',
            'icmp': '50',
            'http': '25',
            'https': '30',
            'dns': '75',
            'dhcp': '5',
            'arp': '10'
        }
    
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
        # Mock implementation for now
        # TODO: Replace with actual TCP analysis using tshark/pyshark
        return {
            'avg_handshake_time': 0.05,
            'max_handshake_time': 0.25,
            'retransmissions': 15,
            'total_packets': 1000,
            'retransmission_rate': 0.015,
            'failed_connections': 2
        }
    
    async def _analyze_dns_performance(self, file_path: str) -> Dict[str, float]:
        """Analyze DNS performance metrics."""
        # Mock implementation for now  
        # TODO: Replace with actual DNS analysis using tshark/pyshark
        return {
            'avg_response_time': 0.025,
            'max_response_time': 0.15,
            'failed_queries': 5,
            'total_queries': 100,
            'failure_rate': 0.05,
            'timeout_queries': 2
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