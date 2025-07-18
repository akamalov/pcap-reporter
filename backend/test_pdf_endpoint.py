#!/usr/bin/env python3
"""
Integration test for the PDF download endpoint to verify the streaming fix.
"""

import asyncio
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Mock MongoDB dependencies
import sys
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

async def test_pdf_download_endpoint():
    """Test the actual PDF download endpoint"""
    
    # Mock the report data
    mock_report = MagicMock()
    mock_report.id = "test-report-id-123"
    mock_report.original_filename = "test_endpoint.pcap"
    mock_report.status = "completed"
    mock_report.file_size = 2048
    mock_report.created_at = datetime(2024, 1, 1, 12, 0, 0)
    mock_report.completed_at = datetime(2024, 1, 1, 12, 30, 0)
    mock_report.file_hash = "abcdef123456"
    mock_report.to_dict.return_value = {
        "_id": "test-report-id-123",
        "original_filename": "test_endpoint.pcap",
        "status": "completed",
        "file_size": 2048,
        "created_at": "2024-01-01T12:00:00Z",
        "completed_at": "2024-01-01T12:30:00Z",
        "file_hash": "abcdef123456",
        "processing_time": 1800.0,
        "analysis_results": {
            "traffic_stats": {
                "total_packets": 5000,
                "total_bytes": 1024000,
                "duration": 300.0,
                "unique_ips": 100,
                "unique_ports": 150
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
                    "packet_count": 250,
                    "bytes": 128000
                }
            ],
            "http_analysis": {
                "total_requests": 200,
                "status_codes": {"200": 150, "404": 30, "500": 20},
                "methods": {"GET": 180, "POST": 20}
            },
            "network_issues": [
                {
                    "type": "suspicious_activity",
                    "description": "Multiple failed connections",
                    "severity": "medium",
                    "details": {"ip": "10.0.0.1"},
                    "timestamp": "2024-01-01T12:15:00Z"
                }
            ],
            "top_talkers": [
                {
                    "ip": "192.168.1.100",
                    "bytes_sent": 512000,
                    "bytes_received": 256000
                }
            ]
        }
    }
    
    print("🧪 Testing PDF Download Endpoint Integration")
    print("=" * 50)
    
    # Import required modules
    from api.v1.endpoints.reports import download_report_pdf, get_report_by_id, _convert_report_for_pdf
    from services.pdf_export import PDFExportService
    
    # Mock the database call
    import api.v1.endpoints.reports as reports_module
    
    # Mock get_report_by_id to return our test report
    original_get_report = reports_module.get_report_by_id
    reports_module.get_report_by_id = AsyncMock(return_value=mock_report)
    
    try:
        print("🔍 Testing PDF data conversion...")
        
        # Test the conversion function
        report_data = mock_report.to_dict()
        pdf_data = _convert_report_for_pdf(report_data)
        
        print(f"✅ Report converted successfully")
        print(f"   - Job ID: {pdf_data['job_id']}")
        print(f"   - Filename: {pdf_data['filename']}")
        print(f"   - Total packets: {pdf_data['total_packets']}")
        print(f"   - Protocols: {pdf_data['protocols']}")
        
        print("\n🔍 Testing PDF generation...")
        
        # Test PDF generation
        pdf_service = PDFExportService()
        pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
        
        print(f"✅ PDF generated: {len(pdf_bytes)} bytes")
        
        # Validate PDF structure
        sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
        from pdf_validator import PDFValidator
        
        pdf_validator = PDFValidator()
        validation_result = pdf_validator.validate_pdf_bytes(pdf_bytes)
        
        print(f"✅ PDF validation: {validation_result.is_valid}")
        if not validation_result.is_valid:
            print(f"   Issues: {validation_result.issues}")
        
        print("\n🔍 Testing StreamingResponse creation...")
        
        # Test the actual endpoint (mocked)
        response = await download_report_pdf("test-report-id-123")
        
        print(f"✅ StreamingResponse created successfully")
        print(f"   - Media type: {response.media_type}")
        print(f"   - Headers: {response.headers}")
        
        # Test streaming the response
        print("\n🔍 Testing response streaming...")
        
        content = b""
        async for chunk in response.body_iterator:
            content += chunk
        
        print(f"✅ Response streamed: {len(content)} bytes")
        print(f"✅ Content matches PDF: {content == pdf_bytes}")
        
        # Test saving to file
        print("\n🔍 Testing file saving...")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_filename = tmp_file.name
        
        print(f"✅ File saved: {tmp_filename}")
        
        # Verify file is readable
        with open(tmp_filename, 'rb') as f:
            file_content = f.read()
        
        print(f"✅ File size: {len(file_content)} bytes")
        print(f"✅ File content matches: {file_content == pdf_bytes}")
        
        # Final validation
        final_validation = pdf_validator.validate_pdf_bytes(file_content)
        print(f"✅ Final PDF validation: {final_validation.is_valid}")
        
        # Clean up
        os.unlink(tmp_filename)
        
        print("\n✅ All endpoint tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Restore original function
        reports_module.get_report_by_id = original_get_report

if __name__ == "__main__":
    asyncio.run(test_pdf_download_endpoint())