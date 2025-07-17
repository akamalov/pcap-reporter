"""
Simple PDF Export Service using basic text generation
This provides a fallback when complex PDF libraries fail.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from io import StringIO


logger = logging.getLogger(__name__)


class SimplePDFExportService:
    """Simple PDF export service using plain text."""

    def __init__(self):
        """Initialize the simple PDF export service."""
        self.logger = logging.getLogger(__name__)

    def generate_pdf_report(self, report_data: Dict[str, Any]) -> bytes:
        """
        Generate a simple text-based 'PDF' (actually formatted plain text).
        
        Args:
            report_data: Complete analysis results dictionary
            
        Returns:
            bytes: Text content as bytes (formatted as PDF-like structure)
        """
        try:
            self.logger.info(f"Generating simple text report for job {report_data.get('job_id', 'unknown')}")
            
            # Generate formatted text content
            text_content = self.generate_text_report(report_data)
            
            # Convert to bytes
            return text_content.encode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to generate simple report: {str(e)}")
            raise Exception(f"Simple PDF generation failed: {str(e)}")

    def generate_text_report(self, report_data: Dict[str, Any]) -> str:
        """
        Generate formatted text report content.
        
        Args:
            report_data: Analysis results dictionary
            
        Returns:
            str: Formatted text content
        """
        buffer = StringIO()
        
        # Header
        buffer.write("=" * 80 + "\n")
        buffer.write("PCAP ANALYSIS REPORT\n")
        buffer.write("=" * 80 + "\n\n")
        
        # Basic info
        buffer.write(f"Filename: {report_data.get('filename', 'Unknown')}\n")
        buffer.write(f"Job ID: {report_data.get('job_id', 'Unknown')}\n")
        buffer.write(f"Status: {report_data.get('status', 'Unknown')}\n")
        buffer.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # File information
        buffer.write("-" * 50 + "\n")
        buffer.write("FILE INFORMATION\n")
        buffer.write("-" * 50 + "\n")
        
        file_size = report_data.get('file_size', 0)
        if file_size > 0:
            file_size_mb = file_size / (1024 * 1024)
            buffer.write(f"File Size: {file_size_mb:.2f} MB ({file_size:,} bytes)\n")
        else:
            buffer.write("File Size: Unknown\n")
        
        buffer.write(f"File Hash: {report_data.get('file_hash', 'Not available')}\n")
        
        if 'created_at' in report_data:
            buffer.write(f"Analysis Started: {report_data['created_at']}\n")
        if 'completed_at' in report_data:
            buffer.write(f"Analysis Completed: {report_data['completed_at']}\n")
        if 'processing_time' in report_data:
            buffer.write(f"Processing Time: {report_data['processing_time']:.2f} seconds\n")
        
        buffer.write("\n")
        
        # Traffic summary
        buffer.write("-" * 50 + "\n")
        buffer.write("TRAFFIC SUMMARY\n")
        buffer.write("-" * 50 + "\n")
        
        total_packets = report_data.get('total_packets', 0)
        buffer.write(f"Total Packets: {total_packets:,}\n")
        buffer.write(f"Unique IPs: {report_data.get('unique_ips', 0)}\n")
        buffer.write(f"Unique Ports: {report_data.get('unique_ports', 0)}\n")
        buffer.write(f"Duration: {report_data.get('duration', 0)} seconds\n\n")
        
        # Protocol distribution
        protocols = report_data.get('protocols', {})
        if protocols:
            buffer.write("-" * 50 + "\n")
            buffer.write("PROTOCOL DISTRIBUTION\n")
            buffer.write("-" * 50 + "\n")
            
            for protocol, count in protocols.items():
                percentage = (count / total_packets * 100) if total_packets > 0 else 0
                buffer.write(f"{protocol:<10}: {count:>8,} packets ({percentage:>5.1f}%)\n")
            buffer.write("\n")
        
        # Protocol analysis
        protocol_analysis = report_data.get('protocol_analysis', {})
        if protocol_analysis:
            buffer.write("-" * 50 + "\n")
            buffer.write("PROTOCOL ANALYSIS\n")
            buffer.write("-" * 50 + "\n")
            
            # TCP analysis
            tcp_data = protocol_analysis.get('tcp', {})
            if tcp_data:
                buffer.write("TCP Connections:\n")
                buffer.write(f"  Total: {tcp_data.get('total_connections', 0)}\n")
                buffer.write(f"  Established: {tcp_data.get('established_connections', 0)}\n")
                buffer.write(f"  Failed: {tcp_data.get('failed_connections', 0)}\n")
                buffer.write(f"  Avg Duration: {tcp_data.get('average_connection_duration', 0):.1f}s\n\n")
                
                # Top conversations
                top_convs = tcp_data.get('top_conversations', [])
                if top_convs:
                    buffer.write("Top TCP Conversations:\n")
                    for i, conv in enumerate(top_convs[:5], 1):
                        buffer.write(f"  {i}. {conv.get('src_ip')}:{conv.get('src_port')} -> ")
                        buffer.write(f"{conv.get('dst_ip')}:{conv.get('dst_port')} ")
                        buffer.write(f"({conv.get('packets', 0)} packets, {conv.get('bytes', 0)} bytes)\n")
                    buffer.write("\n")
            
            # HTTP analysis
            http_data = protocol_analysis.get('http', {})
            if http_data:
                buffer.write("HTTP Analysis:\n")
                buffer.write(f"  Total Requests: {http_data.get('total_requests', 0)}\n")
                
                status_codes = http_data.get('status_codes', {})
                if status_codes:
                    buffer.write("  Status Codes:\n")
                    for code, count in status_codes.items():
                        buffer.write(f"    {code}: {count}\n")
                
                methods = http_data.get('methods', {})
                if methods:
                    buffer.write("  Methods:\n")
                    for method, count in methods.items():
                        buffer.write(f"    {method}: {count}\n")
                buffer.write("\n")
        
        # Security analysis
        security_analysis = report_data.get('security_analysis', {})
        if security_analysis and any(security_analysis.values()):
            buffer.write("-" * 50 + "\n")
            buffer.write("SECURITY ANALYSIS\n")
            buffer.write("-" * 50 + "\n")
            
            suspicious_ips = security_analysis.get('suspicious_ips', [])
            if suspicious_ips:
                buffer.write("Suspicious IP Addresses:\n")
                for ip_data in suspicious_ips:
                    buffer.write(f"  {ip_data.get('ip', 'Unknown')}: {ip_data.get('reason', 'Unknown reason')}\n")
                    buffer.write(f"    Severity: {ip_data.get('severity', 'Unknown')}\n")
                    buffer.write(f"    Count: {ip_data.get('count', 0)}\n")
                buffer.write("\n")
            
            port_scans = security_analysis.get('port_scans', [])
            if port_scans:
                buffer.write("Port Scans Detected:\n")
                for scan in port_scans:
                    buffer.write(f"  {scan.get('scanner_ip', 'Unknown')} -> {scan.get('target_ip', 'Unknown')}\n")
                    buffer.write(f"    Ports scanned: {scan.get('ports_scanned', 0)}\n")
                    buffer.write(f"    Scan type: {scan.get('scan_type', 'Unknown')}\n")
                buffer.write("\n")
            
            anomalies = security_analysis.get('anomalies', [])
            if anomalies:
                buffer.write("Network Anomalies:\n")
                for anomaly in anomalies:
                    buffer.write(f"  {anomaly.get('type', 'Unknown')}: {anomaly.get('description', 'No description')}\n")
                    buffer.write(f"    Severity: {anomaly.get('severity', 'Unknown')}\n")
                buffer.write("\n")
        
        # Performance metrics
        performance_metrics = report_data.get('performance_metrics', {})
        if performance_metrics:
            buffer.write("-" * 50 + "\n")
            buffer.write("PERFORMANCE METRICS\n")
            buffer.write("-" * 50 + "\n")
            
            top_talkers = performance_metrics.get('top_talkers', [])
            if top_talkers:
                buffer.write("Top Network Talkers:\n")
                for i, talker in enumerate(top_talkers[:5], 1):
                    total_bytes = talker.get('total_bytes', 0)
                    total_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0
                    buffer.write(f"  {i}. {talker.get('ip', 'Unknown')}: {total_mb:.2f} MB\n")
                    buffer.write(f"     Sent: {talker.get('bytes_sent', 0):,} bytes\n")
                    buffer.write(f"     Received: {talker.get('bytes_received', 0):,} bytes\n")
                buffer.write("\n")
        
        # Footer
        buffer.write("-" * 50 + "\n")
        buffer.write("END OF REPORT\n")
        buffer.write("-" * 50 + "\n")
        buffer.write(f"Generated by PCAP Reporter - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        content = buffer.getvalue()
        buffer.close()
        return content

    def generate_pdf_filename(self, original_filename: str) -> str:
        """
        Generate appropriate filename for PDF export.
        
        Args:
            original_filename: Original PCAP filename
            
        Returns:
            str: Text report filename
        """
        from pathlib import Path
        base_name = Path(original_filename).stem
        return f"{base_name}_analysis_report.txt"