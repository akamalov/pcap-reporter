"""
Test suite for PDF export functionality.
Testing PDF generation, HTML rendering, and export endpoint.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO

from main import app
from services.pdf_export import PDFExportService


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_report_data():
    """Sample report data for testing PDF generation."""
    return {
        "job_id": "test-job-123",
        "filename": "test_sample.pcap",
        "status": "completed",
        "file_size": 1024000,
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:35:00Z",
        "file_hash": "abc123def456",
        "total_packets": 1500,
        "duration": 300,
        "unique_ips": 25,
        "unique_ports": 45,
        "processing_time": 15.5,
        "protocols": {
            "TCP": 800,
            "UDP": 400,
            "HTTP": 200,
            "DNS": 100
        },
        "packet_sizes": {
            "min": 64,
            "max": 1500,
            "avg": 256,
            "total_bytes": 384000
        },
        "protocol_analysis": {
            "tcp": {
                "total_connections": 150,
                "established_connections": 140,
                "failed_connections": 10,
                "average_connection_duration": 45.2,
                "top_conversations": [
                    {
                        "src_ip": "192.168.1.100",
                        "dst_ip": "192.168.1.200",
                        "src_port": 443,
                        "dst_port": 80,
                        "packets": 50,
                        "bytes": 12800
                    }
                ]
            },
            "http": {
                "total_requests": 75,
                "status_codes": {"200": 60, "404": 10, "500": 5},
                "methods": {"GET": 50, "POST": 20, "PUT": 5},
                "top_domains": [
                    {"domain": "example.com", "requests": 30}
                ]
            }
        },
        "security_analysis": {
            "suspicious_ips": [
                {
                    "ip": "10.0.0.1",
                    "reason": "High port scan activity",
                    "severity": "high",
                    "count": 25
                }
            ],
            "port_scans": [
                {
                    "scanner_ip": "10.0.0.1",
                    "target_ip": "192.168.1.100",
                    "ports_scanned": 100,
                    "scan_type": "TCP SYN scan"
                }
            ],
            "anomalies": []
        },
        "performance_metrics": {
            "top_talkers": [
                {
                    "ip": "192.168.1.100",
                    "bytes_sent": 50000,
                    "bytes_received": 25000,
                    "total_bytes": 75000
                }
            ]
        },
        "analysis_results": {
            "network_diagrams": {
                "network_topology": "graph TD\n    A[192.168.1.100] --> B[192.168.1.200]",
                "protocol_flow": "sequenceDiagram\n    participant A as Client\n    participant B as Server\n    A->>B: HTTP Request",
                "security_incidents": "graph TD\n    A[Scanner: 10.0.0.1] -.-> B[Target: 192.168.1.100]",
                "performance_analysis": "graph TD\n    A[High Traffic: 192.168.1.100]",
                "_metadata": {
                    "generated_at": "2024-01-15T10:34:00Z",
                    "diagram_count": 4,
                    "generator_version": "1.0.0"
                }
            }
        }
    }


class TestPDFExportService:
    """Test the PDF export service functionality."""

    def test_init_service(self):
        """Test PDF service initialization."""
        service = PDFExportService()
        assert service is not None

    def test_generate_html_template_basic(self, sample_report_data):
        """Test HTML template generation with basic report data."""
        service = PDFExportService()
        html_content = service.generate_html_template(sample_report_data)
        
        # Check that HTML contains expected content
        assert "<!DOCTYPE html>" in html_content
        assert sample_report_data["filename"] in html_content
        assert "test_sample.pcap" in html_content
        assert "1500" in html_content  # total_packets
        assert "25" in html_content    # unique_ips

    def test_generate_html_template_protocols(self, sample_report_data):
        """Test HTML template includes protocol analysis."""
        service = PDFExportService()
        html_content = service.generate_html_template(sample_report_data)
        
        # Check protocol data is included
        assert "TCP" in html_content
        assert "800" in html_content  # TCP packet count
        assert "HTTP" in html_content

    def test_generate_html_template_security(self, sample_report_data):
        """Test HTML template includes security analysis."""
        service = PDFExportService()
        html_content = service.generate_html_template(sample_report_data)
        
        # Check security data is included
        assert "10.0.0.1" in html_content
        assert "High port scan activity" in html_content
        assert "high" in html_content

    def test_generate_html_template_diagrams(self, sample_report_data):
        """Test HTML template includes network diagrams."""
        service = PDFExportService()
        html_content = service.generate_html_template(sample_report_data)
        
        # Check diagrams are referenced
        assert "Network Topology" in html_content
        assert "Protocol Flow" in html_content
        assert "Security Incidents" in html_content

    def test_generate_html_empty_data(self):
        """Test HTML generation with minimal data."""
        service = PDFExportService()
        minimal_data = {
            "job_id": "minimal-test",
            "filename": "minimal.pcap",
            "status": "completed",
            "total_packets": 0,
            "unique_ips": 0,
            "protocols": {}
        }
        
        html_content = service.generate_html_template(minimal_data)
        assert "<!DOCTYPE html>" in html_content
        assert "minimal.pcap" in html_content

    @patch('weasyprint.HTML')
    def test_convert_html_to_pdf_success(self, mock_html_class, sample_report_data):
        """Test successful HTML to PDF conversion."""
        # Mock WeasyPrint HTML class
        mock_html_instance = Mock()
        mock_html_class.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"PDF content"

        service = PDFExportService()
        html_content = service.generate_html_template(sample_report_data)
        
        pdf_bytes = service.convert_html_to_pdf(html_content)
        
        # Verify WeasyPrint was called correctly
        mock_html_class.assert_called_once_with(string=html_content)
        mock_html_instance.write_pdf.assert_called_once()
        assert pdf_bytes == b"PDF content"

    @patch('weasyprint.HTML')
    def test_convert_html_to_pdf_error(self, mock_html_class):
        """Test PDF conversion handles errors gracefully."""
        # Mock WeasyPrint to raise exception
        mock_html_class.side_effect = Exception("WeasyPrint error")

        service = PDFExportService()
        
        with pytest.raises(Exception) as exc_info:
            service.convert_html_to_pdf("<html></html>")
        
        assert "WeasyPrint error" in str(exc_info.value)

    @patch.object(PDFExportService, 'convert_html_to_pdf')
    @patch.object(PDFExportService, 'generate_html_template')
    def test_generate_pdf_report_success(self, mock_generate_html, mock_convert_pdf, sample_report_data):
        """Test complete PDF generation process."""
        # Mock the template and conversion
        mock_generate_html.return_value = "<html>Report</html>"
        mock_convert_pdf.return_value = b"PDF content"

        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(sample_report_data)

        # Verify the methods were called correctly
        mock_generate_html.assert_called_once_with(sample_report_data)
        mock_convert_pdf.assert_called_once_with("<html>Report</html>")
        assert pdf_bytes == b"PDF content"

    def test_get_css_styles(self):
        """Test CSS styles are properly defined."""
        service = PDFExportService()
        css_styles = service.get_css_styles()
        
        # Check CSS contains expected styling elements
        assert "body" in css_styles
        assert "font-family" in css_styles
        assert ".header" in css_styles
        assert ".summary" in css_styles


class TestPDFExportEndpoint:
    """Test the PDF export API endpoint."""

    @patch('api.v1.endpoints.export.PDFExportService')
    @patch('api.v1.endpoints.export.get_database')
    def test_export_pdf_success(self, mock_get_db, mock_pdf_service_class, test_client, sample_report_data):
        """Test successful PDF export via API endpoint."""
        # Mock database query
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = sample_report_data

        # Mock PDF service
        mock_pdf_service = Mock()
        mock_pdf_service_class.return_value = mock_pdf_service
        mock_pdf_service.generate_pdf_report.return_value = b"PDF content"

        # Make request
        response = test_client.get("/api/v1/export/pdf/test-job-123")

        # Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment; filename=" in response.headers["content-disposition"]
        assert response.content == b"PDF content"

        # Verify database was queried
        mock_collection.find_one.assert_called_once_with({"job_id": "test-job-123"})

    @patch('api.v1.endpoints.export.get_database')
    def test_export_pdf_report_not_found(self, mock_get_db, test_client):
        """Test PDF export with non-existent job ID."""
        # Mock database query returning None
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = None

        # Make request
        response = test_client.get("/api/v1/export/pdf/nonexistent-job")

        # Verify 404 response
        assert response.status_code == 404
        assert "Report not found" in response.json()["detail"]

    @patch('api.v1.endpoints.export.PDFExportService')
    @patch('api.v1.endpoints.export.get_database')
    def test_export_pdf_incomplete_report(self, mock_get_db, mock_pdf_service_class, test_client):
        """Test PDF export with incomplete/processing report."""
        # Mock database query returning incomplete report
        incomplete_report = {
            "job_id": "processing-job",
            "status": "processing",
            "filename": "test.pcap"
        }
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = incomplete_report

        # Make request
        response = test_client.get("/api/v1/export/pdf/processing-job")

        # Verify 400 response
        assert response.status_code == 400
        assert "Report is not completed" in response.json()["detail"]

    @patch('api.v1.endpoints.export.PDFExportService')
    @patch('api.v1.endpoints.export.get_database')
    def test_export_pdf_generation_error(self, mock_get_db, mock_pdf_service_class, test_client, sample_report_data):
        """Test PDF export with generation error."""
        # Mock database query
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_collection = Mock()
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = sample_report_data

        # Mock PDF service to raise exception
        mock_pdf_service = Mock()
        mock_pdf_service_class.return_value = mock_pdf_service
        mock_pdf_service.generate_pdf_report.side_effect = Exception("PDF generation failed")

        # Make request
        response = test_client.get("/api/v1/export/pdf/test-job-123")

        # Verify 500 response
        assert response.status_code == 500
        assert "Failed to generate PDF" in response.json()["detail"]

    def test_export_pdf_invalid_job_id_format(self, test_client):
        """Test PDF export with invalid job ID format."""
        # Test with various invalid formats
        invalid_ids = ["", "   ", "invalid/id", "id with spaces"]
        
        for invalid_id in invalid_ids:
            response = test_client.get(f"/api/v1/export/pdf/{invalid_id}")
            # Should handle gracefully and return 404 or 400
            assert response.status_code in [400, 404]


class TestPDFIntegration:
    """Integration tests for PDF export functionality."""

    @patch('weasyprint.HTML')
    def test_end_to_end_pdf_generation(self, mock_html_class, sample_report_data):
        """Test complete end-to-end PDF generation process."""
        # Mock WeasyPrint
        mock_html_instance = Mock()
        mock_html_class.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"Complete PDF content"

        # Create service and generate PDF
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(sample_report_data)

        # Verify complete process
        assert pdf_bytes == b"Complete PDF content"
        mock_html_class.assert_called_once()
        mock_html_instance.write_pdf.assert_called_once()

    def test_pdf_filename_generation(self, sample_report_data):
        """Test PDF filename generation logic."""
        service = PDFExportService()
        
        # Test various filename formats
        test_cases = [
            ("test.pcap", "test_analysis_report.pdf"),
            ("sample_file.pcap", "sample_file_analysis_report.pdf"),
            ("complex-name.pcap", "complex-name_analysis_report.pdf"),
            ("no_extension", "no_extension_analysis_report.pdf")
        ]
        
        for input_filename, expected_output in test_cases:
            result = service.generate_pdf_filename(input_filename)
            assert result == expected_output

    def test_html_template_structure(self, sample_report_data):
        """Test that HTML template has proper structure for PDF generation."""
        service = PDFExportService()
        html_content = service.generate_html_template(sample_report_data)
        
        # Check HTML structure elements required for PDF
        assert "<!DOCTYPE html>" in html_content
        assert "<html>" in html_content and "</html>" in html_content
        assert "<head>" in html_content and "</head>" in html_content
        assert "<body>" in html_content and "</body>" in html_content
        assert "<style>" in html_content and "</style>" in html_content
        
        # Check content sections
        assert "Analysis Report" in html_content
        assert "Summary" in html_content or "Overview" in html_content
        assert "Protocol Analysis" in html_content or "Protocols" in html_content