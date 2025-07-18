"""
Comprehensive test suite for PDF export functionality.
Tests PDF generation, validation, and corruption detection.
"""

import pytest
import os
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from services.pdf_export import PDFExportService
from services.simple_pdf_export import SimplePDFExportService


class TestPDFExportValidation:
    """Test PDF export validation and corruption detection."""
    
    def setup_method(self):
        """Set up test data."""
        self.test_report_data = {
            "job_id": "test_job_123",
            "filename": "test.pcap",
            "status": "completed",
            "file_size": 1024000,
            "created_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:30:00Z",
            "file_hash": "abc123def456",
            "analysis_type": "comprehensive",
            "total_packets": 5000,
            "unique_ips": 50,
            "unique_ports": 100,
            "duration": 300.5,
            "processing_time": 45.2,
            "protocols": {
                "TCP": 3000,
                "UDP": 1500,
                "ICMP": 500
            },
            "packet_sizes": {
                "min": 64,
                "max": 1518,
                "avg": 512,
                "total_bytes": 2560000
            },
            "protocol_analysis": {
                "tcp": {
                    "total_connections": 150,
                    "established_connections": 145,
                    "failed_connections": 5,
                    "average_connection_duration": 45.5,
                    "top_conversations": [
                        {
                            "src_ip": "192.168.1.100",
                            "dst_ip": "192.168.1.200",
                            "src_port": 80,
                            "dst_port": 443,
                            "packets": 500,
                            "bytes": 256000
                        }
                    ]
                },
                "http": {
                    "total_requests": 200,
                    "status_codes": {
                        "200": 150,
                        "404": 30,
                        "500": 20
                    },
                    "methods": {
                        "GET": 180,
                        "POST": 20
                    }
                },
                "dns": {
                    "total_queries": 100,
                    "query_types": {
                        "A": 80,
                        "AAAA": 15,
                        "MX": 5
                    },
                    "top_domains": [
                        {"domain": "example.com", "queries": 30},
                        {"domain": "google.com", "queries": 25}
                    ]
                }
            },
            "security_analysis": {
                "suspicious_ips": [
                    {
                        "ip": "10.0.0.1",
                        "reason": "Multiple failed connections",
                        "severity": "medium",
                        "count": 5
                    }
                ],
                "port_scans": [
                    {
                        "scanner_ip": "192.168.1.50",
                        "target_ip": "192.168.1.100",
                        "ports_scanned": 100,
                        "scan_type": "TCP SYN scan"
                    }
                ],
                "anomalies": [
                    {
                        "type": "Unusual traffic pattern",
                        "description": "High traffic volume from single IP",
                        "severity": "low",
                        "timestamp": "2024-01-01T12:15:00Z"
                    }
                ]
            },
            "performance_metrics": {
                "top_talkers": [
                    {
                        "ip": "192.168.1.100",
                        "bytes_sent": 1024000,
                        "bytes_received": 512000,
                        "total_bytes": 1536000
                    }
                ],
                "bandwidth_usage": [
                    {
                        "timestamp": "2024-01-01T12:00:00Z",
                        "bytes_per_second": 1024000
                    }
                ]
            }
        }
    
    def test_pdf_service_initialization(self):
        """Test PDF service initialization."""
        service = PDFExportService()
        assert service is not None
        assert service.logger is not None
    
    def test_simple_pdf_service_initialization(self):
        """Test simple PDF service initialization."""
        service = SimplePDFExportService()
        assert service is not None
        assert service.logger is not None
    
    def test_pdf_generation_with_valid_data(self):
        """Test PDF generation with valid report data."""
        service = PDFExportService()
        
        # Test PDF generation
        pdf_bytes = service.generate_pdf_report(self.test_report_data)
        
        # Validate PDF output
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        
        # Check for PDF signature (ReportLab generates proper PDF)
        # PDF files should start with %PDF-
        pdf_content = pdf_bytes.decode('latin-1', errors='ignore')
        assert '%PDF-' in pdf_content or pdf_content.startswith('1 0 obj')
    
    def test_simple_pdf_generation(self):
        """Test simple PDF generation (text-based)."""
        service = SimplePDFExportService()
        
        # Test text report generation
        text_bytes = service.generate_pdf_report(self.test_report_data)
        
        # Validate output
        assert text_bytes is not None
        assert isinstance(text_bytes, bytes)
        assert len(text_bytes) > 0
        
        # Check for text content
        text_content = text_bytes.decode('utf-8')
        assert 'PCAP ANALYSIS REPORT' in text_content
        assert 'test.pcap' in text_content
        assert 'test_job_123' in text_content
    
    def test_pdf_content_validation(self):
        """Test PDF content validation."""
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(self.test_report_data)
        
        # Validate content structure
        assert len(pdf_bytes) > 1000  # PDF should be substantial
        
        # Check for ReportLab-specific content
        pdf_content = pdf_bytes.decode('latin-1', errors='ignore')
        
        # PDF should have proper structure
        assert 'obj' in pdf_content  # PDF objects
        assert 'endobj' in pdf_content  # PDF object endings
        
        # Check for content hints (ReportLab embeds some text)
        # Note: In real PDF, text is encoded, but we can check for structure
        content_lower = pdf_content.lower()
        assert any(keyword in content_lower for keyword in ['report', 'analysis', 'pcap'])
    
    def test_html_template_generation(self):
        """Test HTML template generation."""
        service = PDFExportService()
        
        # Test HTML template generation
        html_content = service.generate_html_template(self.test_report_data)
        
        # Validate HTML structure
        assert html_content is not None
        assert '<html' in html_content
        assert '</html>' in html_content
        assert '<body>' in html_content
        assert '</body>' in html_content
        
        # Check for report content
        assert 'test.pcap' in html_content
        assert 'test_job_123' in html_content
        assert 'TCP' in html_content
        assert 'UDP' in html_content
    
    def test_template_context_preparation(self):
        """Test template context preparation."""
        service = PDFExportService()
        
        # Test context preparation
        context = service._prepare_template_context(self.test_report_data)
        
        # Validate context structure
        assert 'report' in context
        assert 'generated_at' in context
        assert 'css_styles' in context
        assert 'formatted_file_size' in context
        assert 'formatted_duration' in context
        assert 'protocol_percentages' in context
        assert 'security_summary' in context
        assert 'performance_summary' in context
        
        # Check formatted values
        assert context['formatted_file_size'] == '1000.0 KB'
        assert '5.0 minutes' in context['formatted_duration']
        
        # Check protocol percentages
        assert context['protocol_percentages']['TCP'] == 60.0
        assert context['protocol_percentages']['UDP'] == 30.0
    
    def test_file_size_formatting(self):
        """Test file size formatting."""
        service = PDFExportService()
        
        # Test various file sizes
        assert service._format_file_size(1000) == '1000.0 B'
        assert service._format_file_size(1024) == '1.0 KB'
        assert service._format_file_size(1024 * 1024) == '1.0 MB'
        assert service._format_file_size(1024 * 1024 * 1024) == '1.0 GB'
    
    def test_duration_formatting(self):
        """Test duration formatting."""
        service = PDFExportService()
        
        # Test various durations
        assert service._format_duration(30) == '30.0 seconds'
        assert service._format_duration(90) == '1.5 minutes'
        assert service._format_duration(3600) == '1.0 hours'
        assert service._format_duration(7200) == '2.0 hours'
    
    def test_protocol_percentage_calculation(self):
        """Test protocol percentage calculation."""
        service = PDFExportService()
        
        protocols = {'TCP': 300, 'UDP': 150, 'ICMP': 50}
        total_packets = 500
        
        percentages = service._calculate_protocol_percentages(protocols, total_packets)
        
        assert percentages['TCP'] == 60.0
        assert percentages['UDP'] == 30.0
        assert percentages['ICMP'] == 10.0
    
    def test_security_summary_preparation(self):
        """Test security summary preparation."""
        service = PDFExportService()
        
        security_data = self.test_report_data['security_analysis']
        summary = service._prepare_security_summary(security_data)
        
        assert summary['suspicious_ip_count'] == 1
        assert summary['port_scan_count'] == 1
        assert summary['anomaly_count'] == 1
        assert summary['total_security_issues'] == 3
        assert summary['medium_severity_count'] == 1
        assert summary['low_severity_count'] == 1
    
    def test_performance_summary_preparation(self):
        """Test performance summary preparation."""
        service = PDFExportService()
        
        performance_data = self.test_report_data['performance_metrics']
        summary = service._prepare_performance_summary(performance_data)
        
        assert summary['top_talker_count'] == 1
        assert summary['bandwidth_points'] == 1
        assert summary['total_traffic_bytes'] == 1536000
        assert '1.5 MB' in summary['formatted_total_traffic']
    
    def test_filename_generation(self):
        """Test PDF filename generation."""
        service = PDFExportService()
        
        # Test filename generation
        filename = service.generate_pdf_filename('test.pcap')
        assert filename == 'test_analysis_report.pdf'
        
        # Test with different extensions
        filename = service.generate_pdf_filename('capture.pcapng')
        assert filename == 'capture_analysis_report.pdf'
    
    def test_empty_data_handling(self):
        """Test handling of empty or minimal data."""
        service = PDFExportService()
        
        minimal_data = {
            'job_id': 'test',
            'filename': 'minimal.pcap',
            'status': 'completed'
        }
        
        # Should not crash with minimal data
        pdf_bytes = service.generate_pdf_report(minimal_data)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
    
    def test_error_handling_in_pdf_generation(self):
        """Test error handling in PDF generation."""
        service = PDFExportService()
        
        # Test with None data
        with pytest.raises(Exception):
            service.generate_pdf_report(None)
        
        # Test with invalid data types
        with pytest.raises(Exception):
            service.generate_pdf_report("invalid_data")
    
    def test_simple_pdf_text_content(self):
        """Test simple PDF text content structure."""
        service = SimplePDFExportService()
        
        text_content = service.generate_text_report(self.test_report_data)
        
        # Check for expected sections
        assert 'PCAP ANALYSIS REPORT' in text_content
        assert 'FILE INFORMATION' in text_content
        assert 'TRAFFIC SUMMARY' in text_content
        assert 'PROTOCOL DISTRIBUTION' in text_content
        assert 'PROTOCOL ANALYSIS' in text_content
        assert 'SECURITY ANALYSIS' in text_content
        assert 'PERFORMANCE METRICS' in text_content
        assert 'END OF REPORT' in text_content
        
        # Check for specific values
        assert 'test.pcap' in text_content
        assert 'test_job_123' in text_content
        assert '5,000' in text_content  # Total packets
        assert 'TCP' in text_content
        assert 'UDP' in text_content
    
    def test_css_styles_generation(self):
        """Test CSS styles generation."""
        service = PDFExportService()
        
        css_styles = service.get_css_styles()
        
        # Check for essential CSS elements
        assert '<style>' in css_styles
        assert '</style>' in css_styles
        assert '@page' in css_styles
        assert 'body' in css_styles
        assert '.header' in css_styles
        assert '.summary' in css_styles
        assert '.table' in css_styles
    
    def test_timestamp_formatting(self):
        """Test timestamp formatting."""
        service = PDFExportService()
        
        # Test ISO timestamp formatting
        timestamp = "2024-01-01T12:00:00Z"
        formatted = service._format_timestamp(timestamp)
        assert '2024-01-01' in formatted
        assert '12:00:00' in formatted
        assert 'UTC' in formatted
    
    @patch('services.pdf_export.weasyprint')
    def test_weasyprint_fallback(self, mock_weasyprint):
        """Test fallback when WeasyPrint fails."""
        # Mock WeasyPrint to raise an exception
        mock_weasyprint.HTML.side_effect = Exception("WeasyPrint failed")
        
        service = PDFExportService()
        
        # Should fallback to ReportLab
        pdf_bytes = service.generate_pdf_report(self.test_report_data)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0


class TestPDFExportIntegration:
    """Integration tests for PDF export functionality."""
    
    def test_pdf_export_endpoint_integration(self):
        """Test PDF export endpoint integration."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Mock MongoDB report
        mongo_report = {
            "job_id": "test_job_123",
            "filename": "test.pcap",
            "original_filename": "test.pcap",
            "status": "completed",
            "file_size": 1024000,
            "created_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:30:00Z",
            "file_hash": "abc123def456",
            "processing_time": 45.2,
            "analysis_results": {
                "traffic_stats": {
                    "total_packets": 5000,
                    "duration": 300.5,
                    "unique_ips": 50,
                    "unique_ports": 100,
                    "total_bytes": 2560000
                },
                "top_protocols": [
                    {"name": "TCP", "count": 3000},
                    {"name": "UDP", "count": 1500},
                    {"name": "ICMP", "count": 500}
                ],
                "top_tcp_conversations": [
                    {
                        "src_ip": "192.168.1.100",
                        "dst_ip": "192.168.1.200",
                        "src_port": 80,
                        "dst_port": 443,
                        "packet_count": 500,
                        "bytes": 256000
                    }
                ],
                "network_issues": [
                    {
                        "type": "suspicious_activity",
                        "description": "Multiple failed connections",
                        "severity": "medium",
                        "details": {"ip": "10.0.0.1"}
                    }
                ],
                "top_talkers": [
                    {
                        "ip": "192.168.1.100",
                        "bytes_sent": 1024000,
                        "bytes_received": 512000
                    }
                ]
            }
        }
        
        # Test conversion
        pdf_data = _convert_mongodb_report_to_pdf_format(mongo_report)
        
        # Validate converted data
        assert pdf_data['job_id'] == 'test_job_123'
        assert pdf_data['filename'] == 'test.pcap'
        assert pdf_data['total_packets'] == 5000
        assert pdf_data['protocols']['TCP'] == 3000
        assert pdf_data['protocols']['UDP'] == 1500
        
        # Test with PDF service
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
    
    def test_pdf_file_integrity(self):
        """Test PDF file integrity and corruption detection."""
        service = PDFExportService()
        
        # Generate PDF
        pdf_bytes = service.generate_pdf_report({
            'job_id': 'test',
            'filename': 'test.pcap',
            'status': 'completed',
            'total_packets': 1000,
            'protocols': {'TCP': 800, 'UDP': 200}
        })
        
        # Test file integrity
        assert len(pdf_bytes) > 100  # Should be substantial
        
        # Check for proper PDF structure
        pdf_content = pdf_bytes.decode('latin-1', errors='ignore')
        
        # PDF should have proper structure markers
        assert any(marker in pdf_content for marker in ['%PDF-', '1 0 obj', 'endobj'])
        
        # Save to temporary file and verify it can be read
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            # File should exist and be readable
            assert os.path.exists(tmp_file_path)
            assert os.path.getsize(tmp_file_path) > 0
            
            # Try to read the file back
            with open(tmp_file_path, 'rb') as f:
                read_bytes = f.read()
            
            assert read_bytes == pdf_bytes
            
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)


class TestPDFExportPerformance:
    """Performance tests for PDF export."""
    
    def test_pdf_generation_performance(self):
        """Test PDF generation performance."""
        import time
        
        service = PDFExportService()
        
        # Large dataset
        large_data = {
            'job_id': 'perf_test',
            'filename': 'large.pcap',
            'status': 'completed',
            'total_packets': 100000,
            'protocols': {f'Protocol_{i}': 1000 for i in range(50)},
            'protocol_analysis': {
                'tcp': {
                    'total_connections': 10000,
                    'established_connections': 9500,
                    'failed_connections': 500,
                    'average_connection_duration': 45.5,
                    'top_conversations': [
                        {
                            'src_ip': f'192.168.1.{i}',
                            'dst_ip': f'192.168.2.{i}',
                            'src_port': 80 + i,
                            'dst_port': 443 + i,
                            'packets': 100 + i,
                            'bytes': 10000 + i * 100
                        }
                        for i in range(100)
                    ]
                }
            },
            'security_analysis': {
                'suspicious_ips': [
                    {
                        'ip': f'10.0.0.{i}',
                        'reason': f'Suspicious activity {i}',
                        'severity': 'medium',
                        'count': i
                    }
                    for i in range(50)
                ]
            }
        }
        
        # Time the generation
        start_time = time.time()
        pdf_bytes = service.generate_pdf_report(large_data)
        end_time = time.time()
        
        generation_time = end_time - start_time
        
        # Performance assertions
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert generation_time < 10.0  # Should complete within 10 seconds
        
        # Size should be reasonable
        assert len(pdf_bytes) < 10 * 1024 * 1024  # Should be under 10MB
    
    def test_memory_usage_during_generation(self):
        """Test memory usage during PDF generation."""
        import tracemalloc
        
        service = PDFExportService()
        
        # Start memory tracking
        tracemalloc.start()
        
        # Generate PDF
        pdf_bytes = service.generate_pdf_report({
            'job_id': 'memory_test',
            'filename': 'memory.pcap',
            'status': 'completed',
            'total_packets': 50000,
            'protocols': {'TCP': 30000, 'UDP': 15000, 'ICMP': 5000}
        })
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory assertions
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        
        # Peak memory should be reasonable (less than 100MB)
        assert peak < 100 * 1024 * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v"])