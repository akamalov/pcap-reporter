"""
PCAP Analysis Service - Hybrid engine using tshark and Scapy for comprehensive network analysis.
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import tempfile
import os
import asyncio
from datetime import datetime, timedelta
import hashlib

try:
    from scapy.all import rdpcap, IP, TCP, UDP, DNS, ICMP, ARP, Ether
    from scapy.layers.inet import traceroute
    from scapy.sessions import DefaultSession
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available, falling back to tshark-only analysis")

from models.report import AnalysisResults, TrafficStats, NetworkIssue, TopProtocol, TopHost, SecurityAlert

logger = logging.getLogger(__name__)


class PCAPAnalyzer:
    """
    Hybrid PCAP analysis engine combining tshark and Scapy for comprehensive network analysis.
    """
    
    def __init__(self):
        self.tshark_path = self._find_tshark()
        self.scapy_available = SCAPY_AVAILABLE
        
    def _find_tshark(self) -> Optional[str]:
        """Find tshark executable in system PATH."""
        try:
            result = subprocess.run(
                ["which", "tshark"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            logger.warning("tshark not found in PATH")
            return None
    
    async def analyze_pcap(self, file_path: str, progress_callback=None) -> AnalysisResults:
        """
        Perform comprehensive PCAP analysis using hybrid tshark/Scapy approach.
        
        Args:
            file_path: Path to the PCAP file
            progress_callback: Optional callback for progress updates
            
        Returns:
            AnalysisResults object containing comprehensive analysis
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PCAP file not found: {file_path}")
        
        logger.info(f"Starting PCAP analysis for: {file_path}")
        
        # Initialize progress
        if progress_callback:
            await progress_callback(5, "Initializing analysis...")
        
        # Phase 1: Basic file validation and stats
        basic_stats = await self._get_basic_stats(file_path)
        if progress_callback:
            await progress_callback(15, "Basic file analysis complete...")
        
        # Phase 2: tshark analysis for protocol statistics
        tshark_results = await self._analyze_with_tshark(file_path)
        if progress_callback:
            await progress_callback(40, "Protocol analysis complete...")
        
        # Phase 3: Scapy analysis for deep packet inspection
        scapy_results = {}
        if self.scapy_available:
            scapy_results = await self._analyze_with_scapy(file_path)
            if progress_callback:
                await progress_callback(70, "Deep packet analysis complete...")
        
        # Phase 4: Combine results and generate insights
        combined_results = await self._combine_analysis_results(
            basic_stats, tshark_results, scapy_results
        )
        if progress_callback:
            await progress_callback(90, "Generating insights...")
        
        # Phase 5: Generate executive summary
        executive_summary = self._generate_executive_summary(combined_results)
        combined_results["executive_summary"] = executive_summary
        
        if progress_callback:
            await progress_callback(100, "Analysis complete!")
        
        logger.info(f"PCAP analysis completed for: {file_path}")
        return AnalysisResults(**combined_results)
    
    async def _get_basic_stats(self, file_path: str) -> Dict[str, Any]:
        """Get basic file statistics."""
        file_size = os.path.getsize(file_path)
        
        # Calculate file hash for integrity
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        return {
            "file_size": file_size,
            "file_hash": file_hash,
            "analysis_start_time": datetime.utcnow().isoformat()
        }
    
    async def _analyze_with_tshark(self, file_path: str) -> Dict[str, Any]:
        """Analyze PCAP using tshark for protocol statistics and basic info."""
        if not self.tshark_path:
            logger.warning("tshark not available, skipping tshark analysis")
            return {}
        
        results = {}
        
        try:
            # Get basic packet count and file info
            basic_info = await self._run_tshark_command([
                self.tshark_path, "-r", file_path, "-q", "-z", "io,stat,0"
            ])
            results["basic_info"] = basic_info
            
            # Get protocol hierarchy
            protocol_hierarchy = await self._run_tshark_command([
                self.tshark_path, "-r", file_path, "-q", "-z", "io,phs"
            ])
            results["protocol_hierarchy"] = protocol_hierarchy
            
            # Get conversation statistics
            conv_stats = await self._run_tshark_command([
                self.tshark_path, "-r", file_path, "-q", "-z", "conv,ip"
            ])
            results["conversations"] = conv_stats
            
            # Get endpoints
            endpoints = await self._run_tshark_command([
                self.tshark_path, "-r", file_path, "-q", "-z", "endpoints,ip"
            ])
            results["endpoints"] = endpoints
            
            # Get HTTP statistics if available
            try:
                http_stats = await self._run_tshark_command([
                    self.tshark_path, "-r", file_path, "-q", "-z", "http,stat"
                ])
                results["http_stats"] = http_stats
            except:
                pass  # HTTP stats not available
            
            # Get DNS statistics
            try:
                dns_stats = await self._run_tshark_command([
                    self.tshark_path, "-r", file_path, "-q", "-z", "dns,tree"
                ])
                results["dns_stats"] = dns_stats
            except:
                pass  # DNS stats not available
            
        except Exception as e:
            logger.error(f"Error in tshark analysis: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _run_tshark_command(self, command: List[str]) -> str:
        """Run tshark command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, command, stdout, stderr
                )
            
            return stdout.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.error(f"tshark command failed: {' '.join(command)}, error: {e}")
            raise
    
    async def _analyze_with_scapy(self, file_path: str) -> Dict[str, Any]:
        """Analyze PCAP using Scapy for deep packet inspection."""
        if not self.scapy_available:
            return {}
        
        results = {}
        
        try:
            # Load packets
            packets = rdpcap(file_path)
            results["total_packets"] = len(packets)
            
            # Analyze packet timing
            if packets:
                first_packet_time = packets[0].time
                last_packet_time = packets[-1].time
                duration = last_packet_time - first_packet_time
                results["duration"] = duration
                results["first_packet_time"] = datetime.fromtimestamp(first_packet_time).isoformat()
                results["last_packet_time"] = datetime.fromtimestamp(last_packet_time).isoformat()
            
            # Protocol analysis
            protocol_counts = {}
            ip_addresses = set()
            tcp_flags = {}
            dns_queries = []
            security_issues = []
            
            for packet in packets:
                # Protocol counting
                if packet.haslayer(IP):
                    ip_addresses.add(packet[IP].src)
                    ip_addresses.add(packet[IP].dst)
                    
                    if packet.haslayer(TCP):
                        protocol_counts["TCP"] = protocol_counts.get("TCP", 0) + 1
                        # TCP flag analysis
                        flags = packet[TCP].flags
                        tcp_flags[flags] = tcp_flags.get(flags, 0) + 1
                        
                        # Check for suspicious TCP behavior
                        if flags & 0x01:  # FIN flag
                            if packet[TCP].dport in [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995]:
                                security_issues.append({
                                    "type": "suspicious_fin",
                                    "description": f"FIN packet to common service port {packet[TCP].dport}",
                                    "src": packet[IP].src,
                                    "dst": packet[IP].dst,
                                    "port": packet[TCP].dport
                                })
                    
                    elif packet.haslayer(UDP):
                        protocol_counts["UDP"] = protocol_counts.get("UDP", 0) + 1
                        
                        # DNS analysis
                        if packet.haslayer(DNS):
                            dns = packet[DNS]
                            if dns.qr == 0:  # Query
                                dns_queries.append({
                                    "query": dns.qd.qname.decode('utf-8') if dns.qd else "Unknown",
                                    "type": dns.qd.qtype if dns.qd else 0,
                                    "src": packet[IP].src
                                })
                    
                    elif packet.haslayer(ICMP):
                        protocol_counts["ICMP"] = protocol_counts.get("ICMP", 0) + 1
                
                elif packet.haslayer(ARP):
                    protocol_counts["ARP"] = protocol_counts.get("ARP", 0) + 1
            
            results["protocol_counts"] = protocol_counts
            results["unique_ip_addresses"] = len(ip_addresses)
            results["ip_addresses"] = list(ip_addresses)
            results["tcp_flags"] = tcp_flags
            results["dns_queries"] = dns_queries
            results["security_issues"] = security_issues
            
        except Exception as e:
            logger.error(f"Error in Scapy analysis: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _combine_analysis_results(
        self, 
        basic_stats: Dict[str, Any], 
        tshark_results: Dict[str, Any], 
        scapy_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine results from all analysis phases."""
        
        # Extract traffic statistics
        traffic_stats = {
            "total_packets": scapy_results.get("total_packets", 0),
            "total_bytes": basic_stats.get("file_size", 0),
            "duration": scapy_results.get("duration", 0),
            "first_packet_time": scapy_results.get("first_packet_time"),
            "last_packet_time": scapy_results.get("last_packet_time"),
            "unique_ip_addresses": scapy_results.get("unique_ip_addresses", 0),
            "file_hash": basic_stats.get("file_hash")
        }
        
        # Extract top protocols
        protocol_counts = scapy_results.get("protocol_counts", {})
        top_protocols = [
            TopProtocol(protocol=proto, packet_count=count, percentage=0.0)
            for proto, count in sorted(protocol_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Calculate percentages
        total_packets = traffic_stats["total_packets"]
        if total_packets > 0:
            for proto in top_protocols:
                proto.percentage = (proto.packet_count / total_packets) * 100
        
        # Extract top hosts (from IP addresses)
        ip_addresses = scapy_results.get("ip_addresses", [])
        top_hosts = [
            TopHost(ip_address=ip, packet_count=0, bytes_sent=0, bytes_received=0)
            for ip in ip_addresses[:10]  # Top 10 hosts
        ]
        
        # Network issues from security analysis
        network_issues = []
        for issue in scapy_results.get("security_issues", []):
            network_issues.append(
                NetworkIssue(
                    issue_type=issue["type"],
                    severity="medium",
                    description=issue["description"],
                    affected_hosts=[issue["src"], issue["dst"]],
                    recommendation=f"Investigate {issue['type']} behavior"
                )
            )
        
        # Security alerts
        security_alerts = []
        dns_queries = scapy_results.get("dns_queries", [])
        suspicious_domains = ["malware.com", "phishing.net", "suspicious.org"]  # Example
        
        for query in dns_queries:
            if any(domain in query["query"] for domain in suspicious_domains):
                security_alerts.append(
                    SecurityAlert(
                        alert_type="suspicious_dns",
                        severity="high",
                        description=f"Suspicious DNS query: {query['query']}",
                        source_ip=query["src"],
                        timestamp=datetime.utcnow().isoformat()
                    )
                )
        
        return {
            "traffic_stats": traffic_stats,
            "top_protocols": top_protocols,
            "top_hosts": top_hosts,
            "network_issues": network_issues,
            "security_alerts": security_alerts,
            "dns_analysis": {
                "total_queries": len(dns_queries),
                "unique_domains": len(set(q["query"] for q in dns_queries)),
                "top_queried_domains": list(set(q["query"] for q in dns_queries))[:10]
            },
            "tcp_analysis": {
                "flag_distribution": scapy_results.get("tcp_flags", {}),
                "connection_attempts": protocol_counts.get("TCP", 0)
            }
        }
    
    def _generate_executive_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Generate executive summary of the analysis."""
        stats = analysis_results.get("traffic_stats", {})
        protocols = analysis_results.get("top_protocols", [])
        issues = analysis_results.get("network_issues", [])
        alerts = analysis_results.get("security_alerts", [])
        
        summary_parts = []
        
        # Basic statistics
        total_packets = stats.get("total_packets", 0)
        duration = stats.get("duration", 0)
        unique_ips = stats.get("unique_ip_addresses", 0)
        
        summary_parts.append(
            f"Analyzed {total_packets:,} packets over {duration:.2f} seconds "
            f"involving {unique_ips} unique IP addresses."
        )
        
        # Protocol distribution
        if protocols:
            top_proto = protocols[0]
            summary_parts.append(
                f"Primary protocol: {top_proto.protocol} ({top_proto.percentage:.1f}% of traffic)."
            )
        
        # Security assessment
        if alerts:
            summary_parts.append(
                f"Security analysis identified {len(alerts)} security alerts requiring attention."
            )
        
        if issues:
            summary_parts.append(
                f"Network analysis detected {len(issues)} potential issues."
            )
        else:
            summary_parts.append("No significant network issues detected.")
        
        # DNS analysis
        dns_stats = analysis_results.get("dns_analysis", {})
        if dns_stats.get("total_queries", 0) > 0:
            summary_parts.append(
                f"DNS activity: {dns_stats['total_queries']} queries to "
                f"{dns_stats['unique_domains']} unique domains."
            )
        
        return " ".join(summary_parts)


# Global analyzer instance
analyzer = PCAPAnalyzer() 