"""
Integration tests for PDF export endpoint functionality.
Tests the complete PDF export workflow including MongoDB integration.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from fastapi.testclient import TestClient
from services.pdf_export import PDFExportService
from services.simple_pdf_export import SimplePDFExportService
from tests.utils.pdf_validator import PDFValidator


class TestPDFExportIntegration:
    """Integration tests for PDF export functionality."""
    
    def setup_method(self):
        """Set up test data."""
        self.mock_mongodb_report = {
            "_id": "507f1f77bcf86cd799439011",
            "job_id": "test_integration_123",
            "filename": "integration_test.pcap",
            "original_filename": "integration_test.pcap",
            "status": "completed",
            "file_size": 2048576,
            "created_at": "2024-01-01T10:00:00Z",
            "completed_at": "2024-01-01T10:45:00Z",
            "file_hash": "sha256:abcdef123456789",
            "processing_time": 2700.0,
            "analysis_results": {
                "traffic_stats": {
                    "total_packets": 15000,
                    "duration": 1800.0,
                    "unique_ips": 120,
                    "unique_ports": 250,
                    "total_bytes": 7680000,
                    "avg_packet_size": 512,
                    "packets_per_second": 8.33,
                    "bytes_per_second": 4266.67
                },
                "top_protocols": [
                    {"name": "TCP", "count": 9000},
                    {"name": "UDP", "count": 4500},
                    {"name": "ICMP", "count": 1200},
                    {"name": "HTTP", "count": 300}
                ],
                "packet_size_distribution": {
                    "min_size": 64,
                    "max_size": 1518,
                    "average_size": 512
                },
                "top_tcp_conversations": [
                    {
                        "src_ip": "192.168.1.100",
                        "dst_ip": "192.168.1.200",
                        "src_port": 443,
                        "dst_port": 54321,
                        "packet_count": 1200,
                        "bytes": 614400
                    },
                    {
                        "src_ip": "10.0.0.1",
                        "dst_ip": "10.0.0.2",
                        "src_port": 80,
                        "dst_port": 12345,
                        "packet_count": 800,
                        "bytes": 409600
                    }
                ],
                "http_analysis": {
                    "total_requests": 500,
                    "status_codes": {
                        "200": 400,
                        "404": 60,
                        "500": 25,
                        "302": 15
                    },
                    "methods": {
                        "GET": 450,
                        "POST": 35,
                        "PUT": 10,
                        "DELETE": 5
                    },
                    "top_domains": {
                        "example.com": 200,
                        "api.service.com": 150,
                        "cdn.assets.com": 100
                    }
                },
                "dns_analysis": {
                    "total_queries": 300,
                    "query_types": {
                        "A": 200,
                        "AAAA": 50,
                        "CNAME": 25,
                        "MX": 15,
                        "PTR": 10
                    },
                    "top_domains": {
                        "google.com": 80,
                        "cloudflare.com": 60,
                        "amazonaws.com": 40
                    },
                    "response_codes": {
                        "NOERROR": 250,
                        "NXDOMAIN": 30,
                        "SERVFAIL": 20
                    }
                },
                "network_issues": [
                    {
                        "type": "suspicious_activity",
                        "description": "High volume of failed connections",
                        "severity": "high",
                        "timestamp": "2024-01-01T10:15:00Z",
                        "details": {
                            "ip": "192.168.1.50",
                            "failed_connections": 50
                        }
                    },
                    {
                        "type": "port_scanning",
                        "description": "Sequential port access detected",
                        "severity": "medium",
                        "timestamp": "2024-01-01T10:25:00Z",
                        "details": {
                            "src_ip": "10.0.0.10",
                            "dst_ip": "10.0.0.20",
                            "port_count": 100
                        }
                    },
                    {
                        "type": "anomaly",
                        "description": "Unusual traffic pattern detected",
                        "severity": "low",
                        "timestamp": "2024-01-01T10:35:00Z",
                        "details": {
                            "pattern": "burst_traffic",
                            "threshold_exceeded": 1.5
                        }
                    }
                ],
                "top_talkers": [
                    {
                        "ip": "192.168.1.100",
                        "bytes_sent": 3072000,
                        "bytes_received": 1536000,
                        "packet_count": 6000
                    },
                    {
                        "ip": "10.0.0.1",
                        "bytes_sent": 2048000,
                        "bytes_received": 1024000,
                        "packet_count": 4000
                    },
                    {
                        "ip": "172.16.0.1",
                        "bytes_sent": 1024000,
                        "bytes_received": 512000,
                        "packet_count": 2000
                    }
                ],
                "network_diagrams": {
                    "_metadata": {
                        "generated_at": "2024-01-01T10:45:00Z",
                        "diagram_count": 3
                    },
                    "topology": {
                        "nodes": 25,
                        "edges": 40,
                        "clusters": 3
                    },
                    "flows": {
                        "tcp_flows": 150,
                        "udp_flows": 75,
                        "protocols": ["TCP", "UDP", "HTTP", "DNS"]
                    }
                }
            }
        }
    
    def test_mongodb_to_pdf_conversion(self):
        """Test conversion from MongoDB format to PDF format."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Convert MongoDB report to PDF format
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        
        # Validate conversion
        assert pdf_data['job_id'] == 'test_integration_123'
        assert pdf_data['filename'] == 'integration_test.pcap'
        assert pdf_data['status'] == 'completed'
        assert pdf_data['total_packets'] == 15000
        assert pdf_data['unique_ips'] == 120
        assert pdf_data['unique_ports'] == 250
        assert pdf_data['duration'] == 1800.0
        
        # Check protocols
        assert pdf_data['protocols']['TCP'] == 9000
        assert pdf_data['protocols']['UDP'] == 4500
        assert pdf_data['protocols']['ICMP'] == 1200
        
        # Check packet sizes
        assert pdf_data['packet_sizes']['min'] == 64
        assert pdf_data['packet_sizes']['max'] == 1518
        assert pdf_data['packet_sizes']['avg'] == 512
        
        # Check protocol analysis
        assert 'tcp' in pdf_data['protocol_analysis']
        assert 'http' in pdf_data['protocol_analysis']
        assert 'dns' in pdf_data['protocol_analysis']
        
        # Check TCP analysis
        tcp_analysis = pdf_data['protocol_analysis']['tcp']
        assert tcp_analysis['total_connections'] == 2
        assert tcp_analysis['established_connections'] == 2
        assert len(tcp_analysis['top_conversations']) == 2
        
        # Check HTTP analysis
        http_analysis = pdf_data['protocol_analysis']['http']
        assert http_analysis['total_requests'] == 500
        assert http_analysis['status_codes']['200'] == 400
        assert http_analysis['methods']['GET'] == 450
        
        # Check security analysis
        security_analysis = pdf_data['security_analysis']
        assert len(security_analysis['suspicious_ips']) == 1
        assert len(security_analysis['port_scans']) == 1
        assert len(security_analysis['anomalies']) == 1
        
        # Check performance metrics
        performance_metrics = pdf_data['performance_metrics']
        assert len(performance_metrics['top_talkers']) == 3
        assert performance_metrics['top_talkers'][0]['ip'] == '192.168.1.100'
    
    def test_pdf_generation_with_converted_data(self):
        """Test PDF generation with converted MongoDB data."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Convert data
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        
        # Generate PDF
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        # Validate PDF
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000  # Should be substantial
        
        # Validate PDF structure
        validator = PDFValidator()
        result = validator.validate_pdf_bytes(pdf_bytes)
        
        assert result.is_valid == True
        assert result.info['pdf_type'] == 'Standard PDF'
        assert result.info['has_catalog'] == True
        assert result.info['has_pages'] == True
        assert result.info['page_count'] > 0
        
        # Check for no corruption
        diagnosis = validator.diagnose_corruption(pdf_bytes)
        assert diagnosis['corruption_detected'] == False
    
    def test_pdf_content_validation(self):
        """Test PDF content validation."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Convert and generate PDF
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        # Convert to string for content checking
        pdf_content = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Check for ReportLab structure
        assert 'ReportLab' in pdf_content
        assert '/Producer' in pdf_content
        
        # Check for PDF version
        assert '1.4' in pdf_content  # ReportLab default version
        
        # Check for proper PDF structure
        assert 'endobj' in pdf_content
        assert 'xref' in pdf_content
        assert 'trailer' in pdf_content
        assert 'startxref' in pdf_content
        assert '%%EOF' in pdf_content
    
    def test_simple_pdf_fallback(self):
        """Test simple PDF fallback service."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Convert data
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        
        # Generate with simple service
        service = SimplePDFExportService()
        text_bytes = service.generate_pdf_report(pdf_data)
        
        # Validate text report
        assert text_bytes is not None
        assert len(text_bytes) > 500  # Should be substantial
        
        # Check content
        text_content = text_bytes.decode('utf-8')
        assert 'PCAP ANALYSIS REPORT' in text_content
        assert 'integration_test.pcap' in text_content
        assert 'test_integration_123' in text_content
        assert 'TCP' in text_content
        assert 'UDP' in text_content
        assert 'SECURITY ANALYSIS' in text_content
        assert 'PERFORMANCE METRICS' in text_content
    
    def test_pdf_size_and_performance(self):
        """Test PDF size and generation performance."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        import time
        
        # Convert data
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        
        # Time the generation
        service = PDFExportService()
        start_time = time.time()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        end_time = time.time()
        
        generation_time = end_time - start_time
        
        # Performance assertions
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 5000  # Should be substantial for complex report
        assert len(pdf_bytes) < 5 * 1024 * 1024  # Should be under 5MB
        assert generation_time < 5.0  # Should complete within 5 seconds
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        service = PDFExportService()
        
        # Test with minimal data
        minimal_data = {
            'job_id': 'minimal_test',
            'filename': 'minimal.pcap',
            'status': 'completed'
        }
        
        pdf_bytes = service.generate_pdf_report(minimal_data)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        
        # Test with empty protocols
        empty_protocols_data = {
            'job_id': 'empty_protocols',
            'filename': 'empty.pcap',
            'status': 'completed',
            'total_packets': 0,
            'protocols': {}
        }
        
        pdf_bytes = service.generate_pdf_report(empty_protocols_data)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        
        # Test with None values
        none_data = {
            'job_id': 'none_test',
            'filename': 'none.pcap',
            'status': 'completed',
            'total_packets': None,
            'protocols': None,
            'security_analysis': None
        }
        
        pdf_bytes = service.generate_pdf_report(none_data)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
    
    def test_filename_generation(self):
        """Test PDF filename generation."""
        service = PDFExportService()
        
        # Test various filename scenarios
        test_cases = [
            ('test.pcap', 'test_analysis_report.pdf'),
            ('capture.pcapng', 'capture_analysis_report.pdf'),
            ('network_trace.cap', 'network_trace_analysis_report.pdf'),
            ('file_with_spaces.pcap', 'file_with_spaces_analysis_report.pdf'),
            ('file-with-dashes.pcap', 'file-with-dashes_analysis_report.pdf'),
            ('file.with.dots.pcap', 'file.with.dots_analysis_report.pdf')
        ]
        
        for input_filename, expected_output in test_cases:
            result = service.generate_pdf_filename(input_filename)
            assert result == expected_output
    
    def test_concurrent_pdf_generation(self):
        """Test concurrent PDF generation."""
        import threading
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Convert data
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        
        results = []
        errors = []
        
        def generate_pdf():
            try:
                service = PDFExportService()
                pdf_bytes = service.generate_pdf_report(pdf_data)
                results.append(len(pdf_bytes))
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=generate_pdf)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Validate results
        assert len(errors) == 0, f"Concurrent generation failed: {errors}"
        assert len(results) == 3
        assert all(size > 1000 for size in results)
    
    def test_memory_usage_with_large_data(self):
        """Test memory usage with large datasets."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Create large dataset
        large_report = self.mock_mongodb_report.copy()
        large_report['analysis_results']['top_tcp_conversations'] = [
            {
                "src_ip": f"192.168.1.{i}",
                "dst_ip": f"192.168.2.{i}",
                "src_port": 80 + i,
                "dst_port": 443 + i,
                "packet_count": 100 + i,
                "bytes": 10000 + i * 100
            }
            for i in range(200)  # 200 conversations
        ]
        
        large_report['analysis_results']['network_issues'] = [
            {
                "type": "anomaly",
                "description": f"Anomaly {i}",
                "severity": "medium",
                "timestamp": "2024-01-01T10:00:00Z",
                "details": {"value": i}
            }
            for i in range(100)  # 100 issues
        ]
        
        # Convert and generate
        pdf_data = _convert_mongodb_report_to_pdf_format(large_report)
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        # Validate
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 10000  # Should be substantial
        assert len(pdf_bytes) < 20 * 1024 * 1024  # Should be under 20MB
    
    def test_pdf_validation_comprehensive(self):
        """Test comprehensive PDF validation."""
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Generate PDF
        pdf_data = _convert_mongodb_report_to_pdf_format(self.mock_mongodb_report)
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        # Comprehensive validation
        validator = PDFValidator()
        result = validator.validate_pdf_bytes(pdf_bytes)
        
        # Should be valid
        assert result.is_valid == True
        
        # Should have minimal errors
        assert len(result.errors) == 0
        
        # Check key info
        assert result.info['pdf_version'] in ['1.4', '1.5', '1.6', '1.7']
        assert result.info['object_count'] > 0
        assert result.info['has_catalog'] == True
        assert result.info['has_pages'] == True
        assert result.info['page_count'] > 0
        
        # Check for ReportLab
        assert result.info['generated_by'] == 'ReportLab'
        assert result.info['reportlab_producer'] == True
        
        # Check file characteristics
        assert result.info['file_size'] > 1000
        assert result.info['null_byte_percentage'] < 1.0  # Should be minimal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])