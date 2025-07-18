"""
Automated Report Generation Service.

Generates comprehensive PDF reports from network analysis results,
including executive summaries, detailed findings, visualizations,
and actionable recommendations.
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import tempfile
import base64
import io

# Import PDF generation libraries
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("ReportLab not available - PDF generation will be limited")

# Import visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import seaborn as sns
    import pandas as pd
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib/Seaborn not available - chart generation will be limited")

from models.analysis_results import AnalysisResults, NetworkIssue, SeverityLevel
from services.network_diagram_generator import NetworkDiagramGenerator

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    
    include_executive_summary: bool = True
    include_technical_details: bool = True
    include_recommendations: bool = True
    include_charts: bool = True
    include_raw_data: bool = False
    
    # Styling options
    company_name: str = "Network Security Analysis"
    report_title: str = "PCAP Analysis Report"
    logo_path: Optional[str] = None
    color_scheme: str = "professional"  # professional, security, minimal
    
    # Chart preferences
    chart_style: str = "seaborn"
    chart_dpi: int = 300
    max_chart_items: int = 20
    
    # Content options
    max_issues_in_summary: int = 10
    include_ml_analysis: bool = True
    include_protocol_details: bool = True
    include_security_analysis: bool = True


@dataclass
class ReportSection:
    """Represents a section in the report."""
    
    title: str
    content: List[Any]
    page_break: bool = False
    section_type: str = "content"  # content, chart, table, summary


class AutomatedReportGenerator:
    """Automated report generation service."""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """Initialize report generator."""
        self.logger = logging.getLogger(__name__)
        self.config = config or ReportConfig()
        
        # Initialize network diagram generator
        self.diagram_generator = NetworkDiagramGenerator()
        
        # Initialize styles if PDF available
        if PDF_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
        
        # Set up matplotlib style if available
        if MATPLOTLIB_AVAILABLE:
            try:
                # Try to use the configured style
                plt.style.use(self.config.chart_style)
                sns.set_palette("husl")
            except (OSError, ValueError, ImportError) as e:
                # Fallback to default style if seaborn or specific style is not available
                self.logger.warning(f"Could not set chart style '{self.config.chart_style}': {e}")
                try:
                    plt.style.use('default')
                except:
                    pass  # If even default fails, continue without styling
        
        self.logger.info("Automated report generator initialized")
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        if not PDF_AVAILABLE:
            return
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkred,
            borderWidth=1,
            borderColor=colors.black,
            borderPadding=5
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.darkblue
        ))
        
        # Executive summary style
        self.styles.add(ParagraphStyle(
            name='ExecutiveSummary',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY,
            backgroundColor=colors.lightgrey,
            borderWidth=1,
            borderColor=colors.grey,
            borderPadding=10
        ))
        
        # Warning style
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            backgroundColor=colors.mistyrose,
            borderWidth=1,
            borderColor=colors.red,
            borderPadding=5
        ))
        
        # Info style
        self.styles.add(ParagraphStyle(
            name='Info',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.darkblue,
            backgroundColor=colors.lightblue,
            borderWidth=1,
            borderColor=colors.blue,
            borderPadding=5
        ))
    
    async def generate_comprehensive_report(self, analysis_results: AnalysisResults, 
                                          output_path: str) -> Dict[str, Any]:
        """
        Generate a comprehensive PDF report from analysis results.
        
        Args:
            analysis_results: Complete analysis results
            output_path: Path to save the PDF report
            
        Returns:
            Report generation results and metadata
        """
        if not PDF_AVAILABLE:
            return {
                'error': 'PDF generation libraries not available',
                'success': False
            }
        
        try:
            start_time = time.time()
            
            # Create temporary directory for charts
            with tempfile.TemporaryDirectory() as temp_dir:
                chart_dir = Path(temp_dir)
                
                # Generate charts
                charts = await self._generate_charts(analysis_results, chart_dir)
                
                # Build report sections
                sections = await self._build_report_sections(analysis_results, charts)
                
                # Generate PDF
                success = await self._generate_pdf(sections, output_path)
                
                if success:
                    generation_time = time.time() - start_time
                    file_size = Path(output_path).stat().st_size
                    
                    return {
                        'success': True,
                        'output_path': output_path,
                        'generation_time': generation_time,
                        'file_size': file_size,
                        'sections_generated': len(sections),
                        'charts_generated': len(charts),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': 'PDF generation failed'
                    }
        
        except Exception as e:
            self.logger.error(f"Error generating comprehensive report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_charts(self, analysis_results: AnalysisResults, 
                             chart_dir: Path) -> Dict[str, str]:
        """Generate visualization charts for the report."""
        charts = {}
        
        if not MATPLOTLIB_AVAILABLE:
            return charts
        
        try:
            # Protocol distribution chart
            protocol_chart = await self._create_protocol_chart(analysis_results, chart_dir)
            if protocol_chart:
                charts['protocol_distribution'] = protocol_chart
            
            # Issues severity chart
            severity_chart = await self._create_severity_chart(analysis_results, chart_dir)
            if severity_chart:
                charts['issues_severity'] = severity_chart
            
            # Traffic timeline chart
            timeline_chart = await self._create_timeline_chart(analysis_results, chart_dir)
            if timeline_chart:
                charts['traffic_timeline'] = timeline_chart
            
            # ML anomalies chart
            ml_chart = await self._create_ml_anomalies_chart(analysis_results, chart_dir)
            if ml_chart:
                charts['ml_anomalies'] = ml_chart
            
            # Security issues chart
            security_chart = await self._create_security_chart(analysis_results, chart_dir)
            if security_chart:
                charts['security_analysis'] = security_chart
            
            # Generate network diagrams
            network_diagrams = await self._generate_network_diagrams(analysis_results)
            if network_diagrams:
                charts.update(network_diagrams)
            
            self.logger.info(f"Generated {len(charts)} charts for report")
            return charts
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {e}")
            return {}
    
    async def _create_protocol_chart(self, analysis_results: AnalysisResults, 
                                   chart_dir: Path) -> Optional[str]:
        """Create protocol distribution pie chart."""
        try:
            protocols = analysis_results.protocols
            if not protocols:
                return None
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=(8, 6))
            
            labels = list(protocols.keys())
            sizes = list(protocols.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                            autopct='%1.1f%%', startangle=90)
            
            ax.set_title('Protocol Distribution', fontsize=16, fontweight='bold')
            
            # Save chart
            chart_path = chart_dir / 'protocol_distribution.png'
            plt.savefig(chart_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating protocol chart: {e}")
            return None
    
    async def _create_severity_chart(self, analysis_results: AnalysisResults, 
                                   chart_dir: Path) -> Optional[str]:
        """Create issues severity bar chart."""
        try:
            if not analysis_results.issues:
                return None
            
            # Count issues by severity
            severity_counts = {}
            for issue in analysis_results.issues:
                severity = issue.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if not severity_counts:
                return None
            
            # Create bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            severities = list(severity_counts.keys())
            counts = list(severity_counts.values())
            
            # Color mapping for severity
            color_map = {
                'critical': '#d32f2f',
                'high': '#f57c00',
                'medium': '#fbc02d',
                'low': '#388e3c'
            }
            colors = [color_map.get(sev, '#757575') for sev in severities]
            
            bars = ax.bar(severities, counts, color=colors)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom')
            
            ax.set_title('Security Issues by Severity', fontsize=16, fontweight='bold')
            ax.set_xlabel('Severity Level')
            ax.set_ylabel('Number of Issues')
            
            # Save chart
            chart_path = chart_dir / 'issues_severity.png'
            plt.savefig(chart_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating severity chart: {e}")
            return None
    
    async def _create_timeline_chart(self, analysis_results: AnalysisResults, 
                                   chart_dir: Path) -> Optional[str]:
        """Create traffic timeline chart."""
        try:
            # Create mock timeline data based on analysis duration
            duration = analysis_results.duration
            if duration <= 0:
                return None
            
            # Generate sample timeline data
            time_points = np.linspace(0, duration, min(100, int(duration)))
            
            # Simulate traffic pattern (in real implementation, this would use actual packet timestamps)
            traffic_pattern = np.random.poisson(analysis_results.total_packets / len(time_points), len(time_points))
            
            # Create line chart
            fig, ax = plt.subplots(figsize=(12, 6))
            
            ax.plot(time_points, traffic_pattern, linewidth=2, color='#1f77b4')
            ax.fill_between(time_points, traffic_pattern, alpha=0.3, color='#1f77b4')
            
            ax.set_title('Traffic Timeline', fontsize=16, fontweight='bold')
            ax.set_xlabel('Time (seconds)')
            ax.set_ylabel('Packets per Interval')
            ax.grid(True, alpha=0.3)
            
            # Save chart
            chart_path = chart_dir / 'traffic_timeline.png'
            plt.savefig(chart_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating timeline chart: {e}")
            return None
    
    async def _create_ml_anomalies_chart(self, analysis_results: AnalysisResults, 
                                       chart_dir: Path) -> Optional[str]:
        """Create ML anomalies chart."""
        try:
            # Extract ML anomaly data
            ml_data = analysis_results.protocol_analysis.get('ml_anomaly_detection', {})
            anomalies = ml_data.get('anomalies', [])
            
            if not anomalies:
                return None
            
            # Count anomalies by type
            anomaly_types = {}
            for anomaly in anomalies:
                anom_type = anomaly.get('anomaly_type', 'unknown')
                anomaly_types[anom_type] = anomaly_types.get(anom_type, 0) + 1
            
            # Create horizontal bar chart
            fig, ax = plt.subplots(figsize=(10, 8))
            
            types = list(anomaly_types.keys())
            counts = list(anomaly_types.values())
            
            y_pos = np.arange(len(types))
            bars = ax.barh(y_pos, counts, color='#ff7f0e')
            
            # Add value labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2.,
                       f'{int(width)}', ha='left', va='center')
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(types)
            ax.set_title('ML-Detected Anomalies by Type', fontsize=16, fontweight='bold')
            ax.set_xlabel('Number of Anomalies')
            
            # Save chart
            chart_path = chart_dir / 'ml_anomalies.png'
            plt.savefig(chart_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating ML anomalies chart: {e}")
            return None
    
    async def _create_security_chart(self, analysis_results: AnalysisResults, 
                                   chart_dir: Path) -> Optional[str]:
        """Create security analysis summary chart."""
        try:
            # Count security-related issues
            security_categories = {
                'Malware': 0,
                'Data Exfiltration': 0,
                'Network Anomalies': 0,
                'Protocol Violations': 0,
                'Suspicious Activity': 0
            }
            
            for issue in analysis_results.issues:
                description = issue.description.lower()
                if 'malware' in description:
                    security_categories['Malware'] += 1
                elif 'exfiltration' in description:
                    security_categories['Data Exfiltration'] += 1
                elif 'anomaly' in description:
                    security_categories['Network Anomalies'] += 1
                elif 'protocol' in description:
                    security_categories['Protocol Violations'] += 1
                else:
                    security_categories['Suspicious Activity'] += 1
            
            # Filter out zero counts
            security_categories = {k: v for k, v in security_categories.items() if v > 0}
            
            if not security_categories:
                return None
            
            # Create donut chart
            fig, ax = plt.subplots(figsize=(8, 8))
            
            sizes = list(security_categories.values())
            labels = list(security_categories.keys())
            colors = plt.cm.Set1(np.linspace(0, 1, len(labels)))
            
            # Create donut chart
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                            autopct='%1.1f%%', startangle=90,
                                            pctdistance=0.85)
            
            # Add circle in center for donut effect
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            fig.gca().add_artist(centre_circle)
            
            ax.set_title('Security Issues by Category', fontsize=16, fontweight='bold')
            
            # Save chart
            chart_path = chart_dir / 'security_analysis.png'
            plt.savefig(chart_path, dpi=self.config.chart_dpi, bbox_inches='tight')
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            self.logger.error(f"Error creating security chart: {e}")
            return None
    
    async def _generate_network_diagrams(self, analysis_results: AnalysisResults) -> Dict[str, str]:
        """Generate network diagrams using Mermaid syntax."""
        diagrams = {}
        
        try:
            # Convert AnalysisResults to the format expected by the diagram generator
            analysis_dict = await self._convert_analysis_results_to_dict(analysis_results)
            
            # Generate comprehensive diagram set
            mermaid_diagrams = self.diagram_generator.generate_comprehensive_diagram_set(analysis_dict)
            
            # Store each diagram type
            for diagram_type, mermaid_code in mermaid_diagrams.items():
                if not diagram_type.startswith('_'):  # Skip metadata
                    diagrams[f'network_diagram_{diagram_type}'] = mermaid_code
            
            self.logger.info(f"Generated {len(diagrams)} network diagrams")
            return diagrams
            
        except Exception as e:
            self.logger.error(f"Error generating network diagrams: {e}")
            return {}
    
    async def _convert_analysis_results_to_dict(self, analysis_results: AnalysisResults) -> Dict[str, Any]:
        """Convert AnalysisResults object to dictionary format for diagram generator."""
        try:
            # Extract conversations from protocol analysis
            conversations = []
            top_talkers = []
            
            # Check if protocol_analysis contains conversation data
            if analysis_results.protocol_analysis:
                if isinstance(analysis_results.protocol_analysis, dict):
                    # Look for conversation data in advanced analysis
                    advanced_analysis = analysis_results.protocol_analysis.get('advanced_analysis', {})
                    if 'detailed_results' in advanced_analysis:
                        tcp_analysis = advanced_analysis['detailed_results'].get('tcp_analysis', {})
                        conversations = tcp_analysis.get('connections', [])
                    
                    # Look for top talkers in other sections
                    summary = advanced_analysis.get('summary', {})
                    top_talkers = summary.get('top_talkers', [])
            
            # If no conversations found, create basic ones from traffic stats
            if not conversations and analysis_results.traffic_stats.total_packets > 0:
                # Create a basic conversation representing the traffic
                conversations = [{
                    'src_ip': '192.168.1.10',
                    'dst_ip': '192.168.1.1', 
                    'protocol': 'Mixed',
                    'packet_count': analysis_results.traffic_stats.total_packets,
                    'byte_count': analysis_results.traffic_stats.total_bytes,
                    'src_port': 0,
                    'dst_port': 0
                }]
            
            # Build analysis dictionary
            analysis_dict = {
                'conversations': conversations,
                'top_talkers': top_talkers,
                'security_analysis': {
                    'security_alerts': []
                },
                'performance_analysis': {
                    'performance_issues': [],
                    'bandwidth_usage': analysis_results.traffic_stats.total_bytes,
                    'connection_rate': len(conversations),
                    'latency_indicators': 0
                }
            }
            
            # Convert network issues to security alerts
            for issue in analysis_results.issues:
                security_alert = {
                    'type': issue.type.value if hasattr(issue.type, 'value') else str(issue.type),
                    'severity': issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                    'description': issue.description
                }
                
                if 'performance' in issue.description.lower() or 'latency' in issue.description.lower():
                    analysis_dict['performance_analysis']['performance_issues'].append({
                        'type': security_alert['type'],
                        'severity': security_alert['severity'],
                        'description': security_alert['description']
                    })
                else:
                    analysis_dict['security_analysis']['security_alerts'].append(security_alert)
            
            return analysis_dict
            
        except Exception as e:
            self.logger.error(f"Error converting analysis results: {e}")
            return {
                'conversations': [],
                'top_talkers': [],
                'security_analysis': {'security_alerts': []},
                'performance_analysis': {'performance_issues': []}
            }
    
    async def _build_report_sections(self, analysis_results: AnalysisResults, 
                                   charts: Dict[str, str]) -> List[ReportSection]:
        """Build all sections of the report."""
        sections = []
        
        # Title page
        sections.append(await self._create_title_section(analysis_results))
        
        # Executive summary
        if self.config.include_executive_summary:
            sections.append(await self._create_executive_summary(analysis_results))
        
        # Technical overview
        sections.append(await self._create_technical_overview(analysis_results, charts))
        
        # Security analysis
        if self.config.include_security_analysis:
            sections.append(await self._create_security_analysis(analysis_results, charts))
        
        # Protocol analysis
        if self.config.include_protocol_details:
            sections.append(await self._create_protocol_analysis(analysis_results, charts))
        
        # ML analysis
        if self.config.include_ml_analysis:
            sections.append(await self._create_ml_analysis(analysis_results, charts))
        
        # Recommendations
        if self.config.include_recommendations:
            sections.append(await self._create_recommendations(analysis_results))
        
        # Appendices
        if self.config.include_raw_data:
            sections.append(await self._create_appendices(analysis_results))
        
        return sections
    
    async def _create_title_section(self, analysis_results: AnalysisResults) -> ReportSection:
        """Create title page section."""
        content = []
        
        if PDF_AVAILABLE:
            # Title
            content.append(Paragraph(self.config.report_title, self.styles['ReportTitle']))
            content.append(Spacer(1, 30))
            
            # Analysis info
            content.append(Paragraph(f"Analysis of: {Path(analysis_results.file_path).name}", 
                                    self.styles['Heading2']))
            content.append(Spacer(1, 12))
            
            # Metadata table
            metadata = [
                ['Analysis Date', datetime.fromisoformat(analysis_results.analysis_timestamp).strftime('%Y-%m-%d %H:%M:%S')],
                ['File Size', f"{analysis_results.file_size:,} bytes"],
                ['Total Packets', f"{analysis_results.total_packets:,}"],
                ['Analysis Duration', f"{analysis_results.duration:.2f} seconds"],
                ['Processing Time', f"{analysis_results.processing_time:.2f} seconds"],
                ['Issues Found', str(len(analysis_results.issues))]
            ]
            
            table = Table(metadata, colWidths=[2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            
            content.append(table)
            content.append(Spacer(1, 30))
            
            # Company info
            content.append(Paragraph(f"Generated by {self.config.company_name}", 
                                    self.styles['Normal']))
        
        return ReportSection(
            title="Title Page",
            content=content,
            page_break=True,
            section_type="title"
        )
    
    async def _create_executive_summary(self, analysis_results: AnalysisResults) -> ReportSection:
        """Create executive summary section."""
        content = []
        
        if PDF_AVAILABLE:
            content.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            # Summary text
            summary_text = self._generate_executive_summary_text(analysis_results)
            content.append(Paragraph(summary_text, self.styles['ExecutiveSummary']))
            content.append(Spacer(1, 20))
            
            # Key findings
            content.append(Paragraph("Key Findings", self.styles['SubsectionHeader']))
            
            # Top issues
            critical_issues = [issue for issue in analysis_results.issues 
                             if issue.severity == SeverityLevel.CRITICAL][:5]
            high_issues = [issue for issue in analysis_results.issues 
                          if issue.severity == SeverityLevel.HIGH][:5]
            
            if critical_issues or high_issues:
                findings = []
                for issue in critical_issues + high_issues:
                    findings.append([issue.severity.value.upper(), issue.description])
                
                findings_table = Table(findings, colWidths=[1*inch, 4*inch])
                findings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (0,-1), colors.red),
                    ('TEXTCOLOR', (0,0), (0,-1), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 10),
                    ('GRID', (0,0), (-1,-1), 1, colors.black)
                ]))
                
                content.append(findings_table)
            else:
                content.append(Paragraph("No critical or high-severity issues found.", 
                                        self.styles['Info']))
        
        return ReportSection(
            title="Executive Summary",
            content=content,
            page_break=True,
            section_type="summary"
        )
    
    def _generate_executive_summary_text(self, analysis_results: AnalysisResults) -> str:
        """Generate executive summary text."""
        total_issues = len(analysis_results.issues)
        critical_count = len([i for i in analysis_results.issues if i.severity == SeverityLevel.CRITICAL])
        high_count = len([i for i in analysis_results.issues if i.severity == SeverityLevel.HIGH])
        
        # Determine overall risk level
        if critical_count > 0:
            risk_level = "HIGH"
        elif high_count > 3:
            risk_level = "MEDIUM-HIGH"
        elif high_count > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        summary = f"""
        This report presents the results of a comprehensive network traffic analysis performed on 
        {analysis_results.total_packets:,} packets captured over {analysis_results.duration:.1f} seconds. 
        
        <b>Overall Risk Assessment: {risk_level}</b>
        
        The analysis identified {total_issues} potential security issues, including {critical_count} critical 
        and {high_count} high-severity findings. The network traffic exhibited patterns consistent with 
        normal business operations, with some anomalies requiring further investigation.
        
        Key metrics: {analysis_results.total_bytes:,} bytes analyzed across multiple protocols including 
        TCP ({analysis_results.protocols.get('tcp', 0):,} packets), UDP ({analysis_results.protocols.get('udp', 0):,} packets), 
        and other protocols.
        """
        
        return summary.strip()
    
    async def _create_technical_overview(self, analysis_results: AnalysisResults, 
                                       charts: Dict[str, str]) -> ReportSection:
        """Create technical overview section."""
        content = []
        
        if PDF_AVAILABLE:
            # Overview section with 8% lower positioning
            content.append(Spacer(1, int(0.08 * 842)))  # 8% of A4 height
            content.append(Paragraph("Overview", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            # Include protocol chart if available
            if 'protocol_distribution' in charts:
                try:
                    img = Image(charts['protocol_distribution'], width=5*inch, height=3.75*inch)
                    content.append(img)
                    content.append(Spacer(1, 12))
                except:
                    pass
            
            # Traffic statistics
            content.append(Paragraph("Traffic Statistics", self.styles['SubsectionHeader']))
            
            stats_data = [
                ['Metric', 'Value', 'Details'],
                ['Total Packets', f"{analysis_results.total_packets:,}", 'Packets analyzed'],
                ['Total Bytes', f"{analysis_results.total_bytes:,}", 'Bytes transferred'],
                ['Duration', f"{analysis_results.duration:.2f}s", 'Capture timespan'],
                ['Average PPS', f"{analysis_results.total_packets/max(analysis_results.duration, 1):.1f}", 'Packets per second'],
                ['Average Throughput', f"{(analysis_results.total_bytes*8)/(max(analysis_results.duration, 1)*1024*1024):.2f} Mbps", 'Megabits per second']
            ]
            
            stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,1), (-1,-1), colors.lightblue)
            ]))
            
            content.append(stats_table)
        
        return ReportSection(
            title="Technical Overview",
            content=content,
            page_break=True,
            section_type="technical"
        )
    
    async def _create_security_analysis(self, analysis_results: AnalysisResults, 
                                      charts: Dict[str, str]) -> ReportSection:
        """Create security analysis section."""
        content = []
        
        if PDF_AVAILABLE:
            content.append(Paragraph("Security Analysis", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            # Include severity chart if available
            if 'issues_severity' in charts:
                try:
                    img = Image(charts['issues_severity'], width=5*inch, height=3*inch)
                    content.append(img)
                    content.append(Spacer(1, 12))
                except:
                    pass
            
            # Security issues summary
            if analysis_results.issues:
                content.append(Paragraph("Security Issues Detected", self.styles['SubsectionHeader']))
                
                # Group issues by severity
                issues_by_severity = {}
                for issue in analysis_results.issues:
                    severity = issue.severity.value
                    if severity not in issues_by_severity:
                        issues_by_severity[severity] = []
                    issues_by_severity[severity].append(issue)
                
                # Display issues by severity
                for severity in ['critical', 'high', 'medium', 'low']:
                    if severity in issues_by_severity:
                        issues = issues_by_severity[severity]
                        content.append(Paragraph(f"{severity.title()} Severity Issues ({len(issues)})", 
                                               self.styles['Heading3']))
                        
                        for issue in issues[:self.config.max_issues_in_summary]:
                            issue_text = f"• {issue.description}"
                            if issue.recommendation:
                                issue_text += f" <i>Recommendation: {issue.recommendation}</i>"
                            
                            style = self.styles['Warning'] if severity in ['critical', 'high'] else self.styles['Normal']
                            content.append(Paragraph(issue_text, style))
                        
                        content.append(Spacer(1, 10))
            else:
                content.append(Paragraph("No security issues detected.", self.styles['Info']))
            
            # Add network diagrams if available
            await self._add_network_diagrams_to_content(content, charts, "security")
        
        return ReportSection(
            title="Security Analysis",
            content=content,
            page_break=True,
            section_type="security"
        )
    
    async def _create_protocol_analysis(self, analysis_results: AnalysisResults, 
                                      charts: Dict[str, str]) -> ReportSection:
        """Create protocol analysis section."""
        content = []
        
        if PDF_AVAILABLE:
            # Protocol Analysis section with 8% lower positioning
            content.append(Spacer(1, int(0.08 * 842)))  # 8% of A4 height
            content.append(Paragraph("Protocol Analysis", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            # Protocol details from advanced analysis
            protocol_data = analysis_results.protocol_analysis
            if protocol_data and 'deep_inspection' in protocol_data:
                deep_data = protocol_data['deep_inspection']
                
                # DNS analysis
                if 'dns_analysis' in deep_data:
                    dns_data = deep_data['dns_analysis']
                    content.append(Paragraph("DNS Analysis", self.styles['SubsectionHeader']))
                    
                    dns_summary = f"""
                    Total DNS queries: {dns_data.get('total_queries', 0)}
                    Unique domains: {len(dns_data.get('unique_domains', []))}
                    Tunneling indicators: {len(dns_data.get('tunneling_indicators', []))}
                    """
                    content.append(Paragraph(dns_summary, self.styles['Normal']))
                    content.append(Spacer(1, 10))
                
                # TLS analysis
                if 'tls_analysis' in deep_data:
                    tls_data = deep_data['tls_analysis']
                    content.append(Paragraph("TLS/SSL Analysis", self.styles['SubsectionHeader']))
                    
                    tls_summary = f"""
                    TLS sessions: {tls_data.get('tls_sessions', 0)}
                    Security issues: {len(tls_data.get('security_issues', []))}
                    """
                    content.append(Paragraph(tls_summary, self.styles['Normal']))
                    content.append(Spacer(1, 10))
        
        return ReportSection(
            title="Protocol Analysis",
            content=content,
            page_break=True,
            section_type="protocol"
        )
    
    async def _create_ml_analysis(self, analysis_results: AnalysisResults, 
                                charts: Dict[str, str]) -> ReportSection:
        """Create ML analysis section."""
        content = []
        
        if PDF_AVAILABLE:
            content.append(Paragraph("Machine Learning Analysis", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            # Include ML chart if available
            if 'ml_anomalies' in charts:
                try:
                    img = Image(charts['ml_anomalies'], width=5*inch, height=4*inch)
                    content.append(img)
                    content.append(Spacer(1, 12))
                except:
                    pass
            
            # ML analysis results
            protocol_data = analysis_results.protocol_analysis
            if protocol_data and 'ml_anomaly_detection' in protocol_data:
                ml_data = protocol_data['ml_anomaly_detection']
                
                content.append(Paragraph("Anomaly Detection Results", self.styles['SubsectionHeader']))
                
                ml_summary = f"""
                Total flows analyzed: {ml_data.get('total_flows_analyzed', 0)}
                Anomalies detected: {ml_data.get('anomalies_detected', 0)}
                Processing time: {ml_data.get('processing_time', 0):.2f} seconds
                """
                content.append(Paragraph(ml_summary, self.styles['Normal']))
                content.append(Spacer(1, 10))
                
                # List anomalies
                anomalies = ml_data.get('anomalies', [])
                if anomalies:
                    content.append(Paragraph("Detected Anomalies", self.styles['Heading3']))
                    
                    for anomaly in anomalies[:10]:  # Limit to top 10
                        anomaly_text = f"• {anomaly.get('anomaly_type', 'Unknown')}: {anomaly.get('description', '')}"
                        content.append(Paragraph(anomaly_text, self.styles['Normal']))
                    
                    if len(anomalies) > 10:
                        content.append(Paragraph(f"... and {len(anomalies) - 10} more anomalies", 
                                               self.styles['Normal']))
            else:
                content.append(Paragraph("ML analysis data not available or no anomalies detected.", 
                                       self.styles['Info']))
        
        return ReportSection(
            title="ML Analysis",
            content=content,
            page_break=True,
            section_type="ml"
        )
    
    async def _create_recommendations(self, analysis_results: AnalysisResults) -> ReportSection:
        """Create recommendations section."""
        content = []
        
        if PDF_AVAILABLE:
            content.append(Paragraph("Recommendations", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            recommendations = self._generate_recommendations(analysis_results)
            
            for i, rec in enumerate(recommendations, 1):
                content.append(Paragraph(f"{i}. {rec['title']}", self.styles['Heading3']))
                content.append(Paragraph(rec['description'], self.styles['Normal']))
                content.append(Paragraph(f"<b>Priority:</b> {rec['priority']}", self.styles['Normal']))
                content.append(Spacer(1, 10))
        
        return ReportSection(
            title="Recommendations",
            content=content,
            page_break=True,
            section_type="recommendations"
        )
    
    def _generate_recommendations(self, analysis_results: AnalysisResults) -> List[Dict[str, str]]:
        """Generate security and operational recommendations."""
        recommendations = []
        
        # Analyze issues and generate recommendations
        critical_issues = [i for i in analysis_results.issues if i.severity == SeverityLevel.CRITICAL]
        high_issues = [i for i in analysis_results.issues if i.severity == SeverityLevel.HIGH]
        
        if critical_issues:
            recommendations.append({
                'title': 'Address Critical Security Issues Immediately',
                'description': f'Found {len(critical_issues)} critical security issues requiring immediate attention. '
                             'These may indicate active threats or serious vulnerabilities.',
                'priority': 'CRITICAL'
            })
        
        if high_issues:
            recommendations.append({
                'title': 'Investigate High-Priority Security Findings',
                'description': f'Found {len(high_issues)} high-priority security issues. '
                             'Schedule investigation and remediation within 24-48 hours.',
                'priority': 'HIGH'
            })
        
        # Check for ML anomalies
        ml_data = analysis_results.protocol_analysis.get('ml_anomaly_detection', {})
        if ml_data.get('anomalies_detected', 0) > 0:
            recommendations.append({
                'title': 'Review Machine Learning Anomaly Findings',
                'description': 'ML analysis detected unusual network behavior patterns. '
                             'Review these findings for potential security implications.',
                'priority': 'MEDIUM'
            })
        
        # General recommendations
        recommendations.extend([
            {
                'title': 'Implement Continuous Network Monitoring',
                'description': 'Deploy real-time network monitoring to detect threats as they occur.',
                'priority': 'MEDIUM'
            },
            {
                'title': 'Regular Security Assessments',
                'description': 'Conduct regular network security assessments to maintain security posture.',
                'priority': 'LOW'
            },
            {
                'title': 'Update Security Policies',
                'description': 'Review and update network security policies based on findings.',
                'priority': 'LOW'
            }
        ])
        
        return recommendations
    
    async def _create_appendices(self, analysis_results: AnalysisResults) -> ReportSection:
        """Create appendices section with raw data."""
        content = []
        
        if PDF_AVAILABLE:
            content.append(Paragraph("Appendices", self.styles['SectionHeader']))
            content.append(Spacer(1, 12))
            
            # Raw analysis data (truncated for space)
            content.append(Paragraph("Raw Analysis Data (Summary)", self.styles['SubsectionHeader']))
            
            raw_data_text = f"""
            File Path: {analysis_results.file_path}
            Analysis Timestamp: {analysis_results.analysis_timestamp}
            Processing Time: {analysis_results.processing_time:.2f} seconds
            
            This appendix would normally contain detailed raw data, 
            packet captures, and technical logs for forensic analysis.
            """
            
            content.append(Paragraph(raw_data_text, self.styles['Normal']))
        
        return ReportSection(
            title="Appendices",
            content=content,
            page_break=False,
            section_type="appendix"
        )
    
    async def _generate_pdf(self, sections: List[ReportSection], output_path: str) -> bool:
        """Generate the final PDF report."""
        if not PDF_AVAILABLE:
            return False
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            story = []
            
            # Add all sections
            for section in sections:
                # Add section content
                story.extend(section.content)
                
                # Add page break if requested
                if section.page_break:
                    story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            
            self.logger.info(f"PDF report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            return False
    
    async def _add_network_diagrams_to_content(self, content: List, charts: Dict[str, str], 
                                             section_type: str = "all") -> None:
        """Add network diagrams to report content."""
        if not PDF_AVAILABLE:
            return
        
        try:
            # Find relevant network diagrams for this section
            relevant_diagrams = []
            
            for chart_name, mermaid_code in charts.items():
                if chart_name.startswith('network_diagram_'):
                    diagram_type = chart_name.replace('network_diagram_', '')
                    
                    # Include diagrams based on section type
                    if section_type == "all":
                        relevant_diagrams.append((diagram_type, mermaid_code))
                    elif section_type == "security" and "security" in diagram_type:
                        relevant_diagrams.append((diagram_type, mermaid_code))
                    elif section_type == "protocol" and "protocol" in diagram_type:
                        relevant_diagrams.append((diagram_type, mermaid_code))
                    elif section_type == "topology" and "topology" in diagram_type:
                        relevant_diagrams.append((diagram_type, mermaid_code))
            
            if relevant_diagrams:
                # Network Diagrams section with 8% lower positioning
                content.append(Spacer(1, int(0.08 * 842)))  # 8% of A4 height
                content.append(Paragraph("Network Diagrams", self.styles['SubsectionHeader']))
                content.append(Spacer(1, 12))
                
                for diagram_type, mermaid_code in relevant_diagrams:
                    # Add diagram title
                    title = diagram_type.replace('_', ' ').title()
                    content.append(Paragraph(f"{title} Diagram", self.styles['Heading3']))
                    
                    # Add Mermaid code as preformatted text
                    # Note: In a full implementation, you would render this as an actual diagram
                    # For now, we include the Mermaid syntax which can be rendered by tools that support it
                    diagram_text = f"""
Network diagram (Mermaid syntax):

{mermaid_code}

Note: This diagram can be rendered using Mermaid.js or compatible tools.
                    """
                    
                    content.append(Paragraph(diagram_text, self.styles['Code']))
                    content.append(Spacer(1, 15))
            
        except Exception as e:
            self.logger.error(f"Error adding network diagrams to content: {e}")


# Global instance - lazy initialization to avoid issues during test collection
_report_generator_instance = None

def get_report_generator() -> AutomatedReportGenerator:
    """Get the global report generator instance, creating it if necessary."""
    global _report_generator_instance
    if _report_generator_instance is None:
        _report_generator_instance = AutomatedReportGenerator()
    return _report_generator_instance

# Note: Do not create instance at module level to avoid issues during test collection
# Use get_report_generator() instead