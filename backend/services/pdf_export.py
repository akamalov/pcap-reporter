"""
PDF Export Service for PCAP Analysis Reports

This service handles the generation of PDF reports from analysis results.
It creates HTML templates and converts them to professional PDF documents.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import weasyprint
from jinja2 import Template
from pathlib import Path


logger = logging.getLogger(__name__)


class PDFExportService:
    """Service for generating PDF reports from analysis results."""

    def __init__(self):
        """Initialize the PDF export service."""
        self.logger = logging.getLogger(__name__)

    def generate_pdf_report(self, report_data: Dict[str, Any]) -> bytes:
        """
        Generate a complete PDF report from analysis data.
        
        Args:
            report_data: Complete analysis results dictionary
            
        Returns:
            bytes: PDF content as bytes
            
        Raises:
            Exception: If PDF generation fails
        """
        try:
            self.logger.info(f"Generating PDF report for job {report_data.get('job_id', 'unknown')}")
            
            # Generate HTML template
            html_content = self.generate_html_template(report_data)
            
            # Convert to PDF
            pdf_bytes = self.convert_html_to_pdf(html_content)
            
            self.logger.info("PDF report generated successfully")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF report: {str(e)}")
            raise Exception(f"PDF generation failed: {str(e)}")

    def generate_html_template(self, report_data: Dict[str, Any]) -> str:
        """
        Generate HTML content from report data using Jinja2 template.
        
        Args:
            report_data: Analysis results dictionary
            
        Returns:
            str: HTML content ready for PDF conversion
        """
        template_str = self._get_html_template()
        template = Template(template_str)
        
        # Prepare data for template
        context = self._prepare_template_context(report_data)
        
        # Render template
        html_content = template.render(**context)
        return html_content

    def convert_html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML content to PDF using ReportLab (WeasyPrint fallback due to compatibility issues).
        
        Args:
            html_content: HTML string to convert
            
        Returns:
            bytes: PDF content
            
        Raises:
            Exception: If conversion fails
        """
        try:
            # Use ReportLab directly due to WeasyPrint compatibility issues
            self.logger.info("Using ReportLab for PDF generation (WeasyPrint compatibility issue)")
            return self._fallback_pdf_generation(html_content)
            
        except Exception as e:
            self.logger.error(f"PDF generation failed: {str(e)}")
            raise Exception(f"HTML to PDF conversion failed: {str(e)}")

    def generate_pdf_filename(self, original_filename: str) -> str:
        """
        Generate appropriate filename for PDF export.
        
        Args:
            original_filename: Original PCAP filename
            
        Returns:
            str: PDF filename
        """
        # Remove extension and add PDF suffix
        base_name = Path(original_filename).stem
        return f"{base_name}_analysis_report.pdf"

    def _fallback_pdf_generation(self, html_content: str) -> bytes:
        """
        Fallback PDF generation using simpler method when WeasyPrint fails.
        
        Args:
            html_content: HTML content to convert
            
        Returns:
            bytes: PDF content
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO
        import re
        
        # Create a BytesIO buffer
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Simple HTML to text conversion
        text_content = re.sub('<[^<]+?>', '', html_content)  # Remove HTML tags
        text_content = text_content.replace('&nbsp;', ' ')
        text_content = text_content.replace('&amp;', '&')
        text_content = text_content.replace('&lt;', '<')
        text_content = text_content.replace('&gt;', '>')
        
        # Split into lines and create paragraphs
        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                if len(line) > 100:  # Long lines, probably content
                    story.append(Paragraph(line, styles['Normal']))
                else:  # Short lines, probably headers
                    story.append(Paragraph(line, styles['Heading2']))
                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        
        return pdf_bytes

    def _prepare_template_context(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data context for HTML template rendering.
        
        Args:
            report_data: Raw analysis results
            
        Returns:
            dict: Template context with formatted data
        """
        context = {
            'report': report_data,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'css_styles': self.get_css_styles(),
        }
        
        # Format file size
        if 'file_size' in report_data:
            context['formatted_file_size'] = self._format_file_size(report_data['file_size'])
        
        # Format duration
        if 'duration' in report_data:
            context['formatted_duration'] = self._format_duration(report_data['duration'])
        
        # Format processing time
        if 'processing_time' in report_data:
            context['formatted_processing_time'] = self._format_duration(report_data['processing_time'])
        
        # Calculate protocol percentages
        if 'protocols' in report_data and 'total_packets' in report_data:
            context['protocol_percentages'] = self._calculate_protocol_percentages(
                report_data['protocols'], report_data['total_packets']
            )
        
        # Format timestamps
        for field in ['created_at', 'completed_at']:
            if field in report_data:
                context[f'formatted_{field}'] = self._format_timestamp(report_data[field])
        
        # Security summary
        context['security_summary'] = self._prepare_security_summary(
            report_data.get('security_analysis', {})
        )
        
        # Performance summary
        context['performance_summary'] = self._prepare_performance_summary(
            report_data.get('performance_metrics', {})
        )
        
        return context

    def _format_file_size(self, bytes_size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"

    def _format_timestamp(self, timestamp_str: str) -> str:
        """Format ISO timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return timestamp_str

    def _calculate_protocol_percentages(self, protocols: Dict[str, int], total_packets: int) -> Dict[str, float]:
        """Calculate percentage distribution of protocols."""
        if total_packets == 0:
            return {}
        
        return {
            protocol: (count / total_packets) * 100
            for protocol, count in protocols.items()
        }

    def _prepare_security_summary(self, security_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare security analysis summary."""
        summary = {
            'suspicious_ip_count': len(security_data.get('suspicious_ips', [])),
            'port_scan_count': len(security_data.get('port_scans', [])),
            'anomaly_count': len(security_data.get('anomalies', [])),
            'high_severity_count': 0,
            'medium_severity_count': 0,
            'low_severity_count': 0
        }
        
        # Count severity levels
        all_incidents = (
            security_data.get('suspicious_ips', []) +
            security_data.get('anomalies', [])
        )
        
        for incident in all_incidents:
            severity = incident.get('severity', '').lower()
            if severity == 'high':
                summary['high_severity_count'] += 1
            elif severity == 'medium':
                summary['medium_severity_count'] += 1
            elif severity == 'low':
                summary['low_severity_count'] += 1
        
        summary['total_security_issues'] = (
            summary['suspicious_ip_count'] +
            summary['port_scan_count'] +
            summary['anomaly_count']
        )
        
        return summary

    def _prepare_performance_summary(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare performance metrics summary."""
        summary = {
            'top_talker_count': len(performance_data.get('top_talkers', [])),
            'bandwidth_points': len(performance_data.get('bandwidth_usage', [])),
            'packet_rate_points': len(performance_data.get('packet_rate', []))
        }
        
        # Calculate top talker totals
        top_talkers = performance_data.get('top_talkers', [])
        if top_talkers:
            summary['total_traffic_bytes'] = sum(
                talker.get('total_bytes', 0) for talker in top_talkers
            )
            summary['formatted_total_traffic'] = self._format_file_size(summary['total_traffic_bytes'])
        
        return summary

    def get_css_styles(self) -> str:
        """
        Get CSS styles for PDF formatting.
        
        Returns:
            str: CSS styles for the PDF document
        """
        return """
        <style>
            @page {
                size: A4;
                margin: 2cm;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10px;
                    color: #666;
                }
            }
            
            body {
                font-family: 'DejaVu Sans', sans-serif;
                font-size: 11px;
                line-height: 1.4;
                color: #333;
                margin: 0;
                padding: 0;
            }
            
            .header {
                background-color: #1f2937;
                color: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            
            .header h1 {
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: bold;
            }
            
            .header .subtitle {
                font-size: 14px;
                opacity: 0.9;
            }
            
            .summary {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
            }
            
            .summary h2 {
                margin: 0 0 15px 0;
                font-size: 16px;
                color: #1f2937;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 5px;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .stat-item {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                padding: 10px;
                text-align: center;
            }
            
            .stat-value {
                font-size: 18px;
                font-weight: bold;
                color: #3b82f6;
                display: block;
            }
            
            .stat-label {
                font-size: 10px;
                color: #6b7280;
                text-transform: uppercase;
                margin-top: 5px;
            }
            
            .section {
                margin-bottom: 25px;
                page-break-inside: avoid;
            }
            
            .section h3 {
                font-size: 14px;
                color: #1f2937;
                margin: 0 0 10px 0;
                padding: 8px 0;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
                font-size: 10px;
            }
            
            .table th,
            .table td {
                border: 1px solid #e2e8f0;
                padding: 6px 8px;
                text-align: left;
            }
            
            .table th {
                background-color: #f1f5f9;
                font-weight: bold;
                color: #1f2937;
            }
            
            .table tr:nth-child(even) {
                background-color: #f8fafc;
            }
            
            .protocol-list {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin-bottom: 15px;
            }
            
            .protocol-item {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 3px;
                padding: 8px;
                font-size: 10px;
            }
            
            .protocol-name {
                font-weight: bold;
                color: #1f2937;
            }
            
            .protocol-count {
                color: #6b7280;
                font-size: 9px;
            }
            
            .alert {
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 15px;
                font-size: 10px;
            }
            
            .alert-success {
                background-color: #ecfdf5;
                border: 1px solid #a7f3d0;
                color: #065f46;
            }
            
            .alert-warning {
                background-color: #fffbeb;
                border: 1px solid #fcd34d;
                color: #92400e;
            }
            
            .alert-danger {
                background-color: #fef2f2;
                border: 1px solid #fca5a5;
                color: #991b1b;
            }
            
            .security-item {
                background: #fef2f2;
                border-left: 4px solid #ef4444;
                padding: 10px;
                margin-bottom: 10px;
                font-size: 10px;
            }
            
            .security-ip {
                font-weight: bold;
                color: #991b1b;
            }
            
            .security-reason {
                color: #6b7280;
                margin-top: 3px;
            }
            
            .diagram-note {
                background-color: #f0f9ff;
                border: 1px solid #7dd3fc;
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 15px;
                font-size: 10px;
                color: #0c4a6e;
            }
            
            .footer {
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #e2e8f0;
                font-size: 9px;
                color: #6b7280;
                text-align: center;
            }
            
            .page-break {
                page-break-before: always;
            }
        </style>
        """

    def _get_html_template(self) -> str:
        """
        Get the main HTML template for PDF generation.
        
        Returns:
            str: Jinja2 HTML template
        """
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCAP Analysis Report - {{ report.filename }}</title>
    {{ css_styles|safe }}
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>PCAP Analysis Report</h1>
        <div class="subtitle">
            {{ report.filename }} • Generated on {{ generated_at }}
        </div>
    </div>

    <!-- Executive Summary -->
    <div class="summary">
        <h2>Executive Summary</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-value">{{ report.total_packets|default(0) }}</span>
                <div class="stat-label">Total Packets</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ report.unique_ips|default(0) }}</span>
                <div class="stat-label">Unique IP Addresses</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ report.unique_ports|default(0) }}</span>
                <div class="stat-label">Unique Ports</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ formatted_file_size|default('Unknown') }}</span>
                <div class="stat-label">File Size</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ formatted_duration|default('Unknown') }}</span>
                <div class="stat-label">Capture Duration</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ formatted_processing_time|default('Unknown') }}</span>
                <div class="stat-label">Processing Time</div>
            </div>
        </div>
        
        <p><strong>Analysis Status:</strong> {{ report.status|title }}</p>
        <p><strong>File Hash:</strong> {{ report.file_hash|default('Not available') }}</p>
        {% if formatted_created_at %}
        <p><strong>Analysis Started:</strong> {{ formatted_created_at }}</p>
        {% endif %}
        {% if formatted_completed_at %}
        <p><strong>Analysis Completed:</strong> {{ formatted_completed_at }}</p>
        {% endif %}
    </div>

    <!-- Protocol Analysis -->
    <div class="section">
        <h3>Protocol Distribution</h3>
        {% if report.protocols %}
        <div class="protocol-list">
            {% for protocol, count in report.protocols.items() %}
            <div class="protocol-item">
                <div class="protocol-name">{{ protocol }}</div>
                <div class="protocol-count">
                    {{ count }} packets
                    {% if protocol_percentages and protocol in protocol_percentages %}
                    ({{ "%.1f"|format(protocol_percentages[protocol]) }}%)
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p>No protocol data available.</p>
        {% endif %}
    </div>

    <!-- TCP Analysis -->
    {% if report.protocol_analysis and report.protocol_analysis.tcp %}
    <div class="section">
        <h3>TCP Analysis</h3>
        <div class="stats-grid">
            <div class="stat-item">
                <span class="stat-value">{{ report.protocol_analysis.tcp.total_connections }}</span>
                <div class="stat-label">Total Connections</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ report.protocol_analysis.tcp.established_connections }}</span>
                <div class="stat-label">Established</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ report.protocol_analysis.tcp.failed_connections }}</span>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-item">
                <span class="stat-value">{{ "%.1f"|format(report.protocol_analysis.tcp.average_connection_duration) }}s</span>
                <div class="stat-label">Avg Duration</div>
            </div>
        </div>

        {% if report.protocol_analysis.tcp.top_conversations %}
        <h4>Top TCP Conversations</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>Source IP</th>
                    <th>Source Port</th>
                    <th>Destination IP</th>
                    <th>Destination Port</th>
                    <th>Packets</th>
                    <th>Bytes</th>
                </tr>
            </thead>
            <tbody>
                {% for conv in report.protocol_analysis.tcp.top_conversations[:10] %}
                <tr>
                    <td>{{ conv.src_ip }}</td>
                    <td>{{ conv.src_port }}</td>
                    <td>{{ conv.dst_ip }}</td>
                    <td>{{ conv.dst_port }}</td>
                    <td>{{ conv.packets }}</td>
                    <td>{{ conv.bytes }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endif %}

    <!-- HTTP Analysis -->
    {% if report.protocol_analysis and report.protocol_analysis.http %}
    <div class="section">
        <h3>HTTP Analysis</h3>
        <p><strong>Total HTTP Requests:</strong> {{ report.protocol_analysis.http.total_requests }}</p>
        
        {% if report.protocol_analysis.http.status_codes %}
        <h4>HTTP Status Codes</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>Status Code</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                {% for code, count in report.protocol_analysis.http.status_codes.items() %}
                <tr>
                    <td>{{ code }}</td>
                    <td>{{ count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if report.protocol_analysis.http.methods %}
        <h4>HTTP Methods</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>Method</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                {% for method, count in report.protocol_analysis.http.methods.items() %}
                <tr>
                    <td>{{ method }}</td>
                    <td>{{ count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endif %}

    <!-- Security Analysis -->
    <div class="section page-break">
        <h3>Security Analysis</h3>
        {% if security_summary.total_security_issues > 0 %}
        <div class="alert alert-warning">
            <strong>Security Issues Detected:</strong> {{ security_summary.total_security_issues }} total issues found
            ({{ security_summary.high_severity_count }} high, {{ security_summary.medium_severity_count }} medium, {{ security_summary.low_severity_count }} low severity)
        </div>

        {% if report.security_analysis.suspicious_ips %}
        <h4>Suspicious IP Addresses</h4>
        {% for ip_data in report.security_analysis.suspicious_ips %}
        <div class="security-item">
            <div class="security-ip">{{ ip_data.ip }}</div>
            <div class="security-reason">{{ ip_data.reason }} ({{ ip_data.severity|upper }})</div>
            <div class="security-reason">Occurrences: {{ ip_data.count }}</div>
        </div>
        {% endfor %}
        {% endif %}

        {% if report.security_analysis.port_scans %}
        <h4>Port Scan Detection</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>Scanner IP</th>
                    <th>Target IP</th>
                    <th>Ports Scanned</th>
                    <th>Scan Type</th>
                </tr>
            </thead>
            <tbody>
                {% for scan in report.security_analysis.port_scans %}
                <tr>
                    <td>{{ scan.scanner_ip }}</td>
                    <td>{{ scan.target_ip }}</td>
                    <td>{{ scan.ports_scanned }}</td>
                    <td>{{ scan.scan_type }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if report.security_analysis.anomalies %}
        <h4>Network Anomalies</h4>
        {% for anomaly in report.security_analysis.anomalies %}
        <div class="security-item">
            <div class="security-ip">{{ anomaly.type }} ({{ anomaly.severity|upper }})</div>
            <div class="security-reason">{{ anomaly.description }}</div>
            {% if anomaly.timestamp %}
            <div class="security-reason">Timestamp: {{ anomaly.timestamp }}</div>
            {% endif %}
        </div>
        {% endfor %}
        {% endif %}
        {% else %}
        <div class="alert alert-success">
            <strong>No Security Issues Detected:</strong> The analysis did not identify any suspicious activities, port scans, or network anomalies.
        </div>
        {% endif %}
    </div>

    <!-- Performance Metrics -->
    {% if report.performance_metrics %}
    <div class="section">
        <h3>Performance Analysis</h3>
        
        {% if report.performance_metrics.top_talkers %}
        <h4>Top Network Talkers</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>IP Address</th>
                    <th>Bytes Sent</th>
                    <th>Bytes Received</th>
                    <th>Total Bytes</th>
                </tr>
            </thead>
            <tbody>
                {% for talker in report.performance_metrics.top_talkers[:10] %}
                <tr>
                    <td>{{ talker.ip }}</td>
                    <td>{{ talker.bytes_sent }}</td>
                    <td>{{ talker.bytes_received }}</td>
                    <td>{{ talker.total_bytes }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if performance_summary.formatted_total_traffic %}
        <p><strong>Total Traffic Analyzed:</strong> {{ performance_summary.formatted_total_traffic }}</p>
        {% endif %}
    </div>
    {% endif %}

    <!-- Network Diagrams -->
    {% if report.analysis_results and report.analysis_results.network_diagrams %}
    <div class="section">
        <h3>Network Diagrams</h3>
        <div class="diagram-note">
            <strong>Note:</strong> Network diagrams have been generated for this analysis including network topology, protocol flows, and security incidents. 
            These visual representations are available in the web interface and can be downloaded separately.
            {% if report.analysis_results.network_diagrams._metadata %}
            <br><strong>Generated:</strong> {{ report.analysis_results.network_diagrams._metadata.generated_at|default('Unknown') }}
            <br><strong>Diagram Count:</strong> {{ report.analysis_results.network_diagrams._metadata.diagram_count|default(0) }}
            {% endif %}
        </div>
    </div>
    {% endif %}

    <!-- Footer -->
    <div class="footer">
        <p>Generated by PCAP Reporter • {{ generated_at }}</p>
        <p>This report contains analysis results from: {{ report.filename }}</p>
    </div>
</body>
</html>
        """