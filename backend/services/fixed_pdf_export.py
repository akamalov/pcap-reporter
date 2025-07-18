
"""
FIXED PDF Export Service
Properly handles CSS and generates detailed PCAP analysis reports.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO

logger = logging.getLogger(__name__)

class FixedPDFExportService:
    """Fixed PDF export service with proper formatting and detailed content."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_pdf_filename(self, original_filename: str) -> str:
        """
        Generate a PDF filename from the original PCAP filename.
        
        Args:
            original_filename: Original PCAP filename
            
        Returns:
            PDF filename
        """
        from pathlib import Path
        
        # Remove extension and add .pdf
        base_name = Path(original_filename).stem
        return f"analysis_report_{base_name}.pdf"

    def generate_pdf_report(self, report_data: Dict[str, Any]) -> bytes:
        """Generate a properly formatted PDF report with detailed packet analysis."""
        try:
            self.logger.info(f"Generating fixed PDF report for {report_data.get('filename', 'unknown')}")
            
            # Create PDF buffer
            buffer = BytesIO()
            
            # Create document with proper page setup
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=inch * 0.75,
                leftMargin=inch * 0.75,
                topMargin=inch,
                bottomMargin=inch
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=20,
                textColor=colors.darkblue
            )
            
            # Special sections that need 8% lower positioning
            section_heading_style = ParagraphStyle(
                'SectionHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=int(0.08 * A4[1]),  # 8% of page height (about 67 points)
                textColor=colors.darkblue
            )
            
            # Build story
            story = []
            
            # Title
            story.append(Paragraph("PCAP Analysis Report", title_style))
            story.append(Spacer(1, 20))
            
            # File Information
            story.append(Paragraph("File Information", heading_style))
            
            file_info_data = [
                ['Filename:', report_data.get('filename', 'Unknown')],
                ['File Size:', f"{report_data.get('file_size', 0):,} bytes"],
                ['Analysis Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Total Packets:', str(report_data.get('total_packets', 0))],
                ['Duration:', f"{report_data.get('duration', 0):.2f} seconds"]
            ]
            
            file_table = Table(file_info_data, colWidths=[2*inch, 4*inch])
            file_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(file_table)
            story.append(Spacer(1, 20))
            
            # OVERVIEW SECTION - 8% lower positioning
            story.append(Paragraph("Overview", section_heading_style))
            story.append(Paragraph("This report provides a comprehensive analysis of the PCAP file including traffic patterns, protocol distribution, and security findings.", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Protocol Summary
            protocols = report_data.get('protocols', {})
            if protocols:
                story.append(Paragraph("Protocol Distribution", heading_style))
                
                protocol_data = [['Protocol', 'Packet Count', 'Percentage']]
                total_packets = report_data.get('total_packets', 1)
                
                for protocol, count in protocols.items():
                    percentage = (count / total_packets * 100) if total_packets > 0 else 0
                    protocol_data.append([protocol, str(count), f"{percentage:.1f}%"])
                
                protocol_table = Table(protocol_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
                protocol_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(protocol_table)
                story.append(Spacer(1, 20))
            
            # Detailed Packet Analysis
            packets = report_data.get('detailed_packets', [])
            if packets:
                story.append(Paragraph("Detailed Packet Analysis", heading_style))
                story.append(Paragraph(f"Showing first {len(packets)} packets:", styles['Normal']))
                story.append(Spacer(1, 10))
                
                # Create packet table
                packet_headers = ['No.', 'Time', 'Source IP', 'Dest IP', 'Protocol', 'Length', 'Src Port', 'Dst Port', 'Info']
                packet_data = [packet_headers]
                
                for packet in packets[:30]:  # Limit to 30 packets for readability
                    row = [
                        str(packet.get('no', '')),
                        str(packet.get('time', ''))[:8],  # Truncate time
                        str(packet.get('source', ''))[:15],  # Truncate IPs
                        str(packet.get('destination', ''))[:15],
                        str(packet.get('protocol', ''))[:6],
                        str(packet.get('length', '')),
                        str(packet.get('src_port', '')),
                        str(packet.get('dst_port', '')),
                        str(packet.get('info', ''))[:20]  # Truncate info
                    ]
                    packet_data.append(row)
                
                packet_table = Table(packet_data, colWidths=[0.4*inch, 0.8*inch, 1.2*inch, 1.2*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 1.6*inch])
                packet_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                ]))
                
                story.append(packet_table)
                story.append(Spacer(1, 20))
            
            # PROTOCOL ANALYSIS SECTION - 8% lower positioning  
            story.append(Paragraph("Protocol Analysis", section_heading_style))
            story.append(Paragraph("Detailed analysis of network protocols and communication patterns observed in the traffic capture.", styles['Normal']))
            story.append(Spacer(1, 15))
            
            # Traffic Flow Analysis
            story.append(Paragraph("Traffic Flow Analysis", heading_style))
            
            # Top conversations
            conversations = report_data.get('protocol_analysis', {}).get('tcp', {}).get('top_conversations', [])
            if conversations:
                story.append(Paragraph("Top TCP Conversations:", styles['Normal']))
                story.append(Spacer(1, 10))
                
                conv_data = [['Source', 'Destination', 'Packets', 'Bytes']]
                for conv in conversations[:10]:
                    conv_data.append([
                        f"{conv.get('src_ip', '')}:{conv.get('src_port', '')}",
                        f"{conv.get('dst_ip', '')}:{conv.get('dst_port', '')}",
                        str(conv.get('packets', 0)),
                        f"{conv.get('bytes', 0):,}"
                    ])
                
                conv_table = Table(conv_data, colWidths=[2.5*inch, 2.5*inch, 1*inch, 1*inch])
                conv_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(conv_table)
            
            # Security Analysis
            security_analysis = report_data.get('security_analysis', {})
            if security_analysis and any(security_analysis.values()):
                story.append(PageBreak())
                story.append(Paragraph("Security Analysis", heading_style))
                
                # Suspicious IPs
                suspicious_ips = security_analysis.get('suspicious_ips', [])
                if suspicious_ips:
                    story.append(Paragraph("Suspicious IP Addresses:", styles['Normal']))
                    story.append(Spacer(1, 10))
                    
                    sus_data = [['IP Address', 'Reason', 'Severity', 'Count']]
                    for ip_info in suspicious_ips:
                        sus_data.append([
                            ip_info.get('ip', ''),
                            ip_info.get('reason', ''),
                            ip_info.get('severity', ''),
                            str(ip_info.get('count', 0))
                        ])
                    
                    sus_table = Table(sus_data, colWidths=[2*inch, 3*inch, 1*inch, 1*inch])
                    sus_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.pink),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    story.append(sus_table)
            else:
                story.append(Paragraph("Security Analysis", heading_style))
                story.append(Paragraph("✓ No security issues detected", styles['Normal']))
            
            # NETWORK DIAGRAMS SECTION - 8% lower positioning
            story.append(Paragraph("Network Diagrams", section_heading_style))
            network_diagrams = report_data.get('analysis_results', {}).get('network_diagrams')
            if network_diagrams:
                story.append(Paragraph("Network topology and flow diagrams have been generated showing communication patterns and network structure. These visual representations help understand traffic flow and identify potential bottlenecks.", styles['Normal']))
                story.append(Paragraph(f"Generated diagrams: {network_diagrams.get('_metadata', {}).get('diagram_count', 'Multiple')}", styles['Normal']))
            else:
                story.append(Paragraph("Network diagrams provide visual representation of traffic flows and network topology. This feature enhances understanding of communication patterns within the analyzed network traffic.", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Footer
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                 ParagraphStyle('Footer', parent=styles['Normal'], 
                                              fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            buffer.seek(0)
            pdf_bytes = buffer.read()
            buffer.close()
            
            self.logger.info(f"Successfully generated PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF: {e}")
            raise Exception(f"PDF generation failed: {e}")
