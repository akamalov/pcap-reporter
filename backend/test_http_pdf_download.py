#!/usr/bin/env python3
"""
Test PDF download using HTTP client to simulate real browser behavior.
"""

import asyncio
import os
import tempfile
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
import sys

sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

def test_http_pdf_download():
    """Test PDF download using HTTP client like a real browser"""
    
    print("🧪 Testing PDF Download via HTTP Client")
    print("=" * 50)
    
    # Create FastAPI app
    app = FastAPI()
    
    # Mock report data
    mock_report = MagicMock()
    mock_report.id = "test-http-download-id"
    mock_report.original_filename = "test_http_download.pcap"
    mock_report.status = "completed"
    mock_report.file_size = 2048000
    mock_report.file_hash = "test123hash456"
    mock_report.created_at = datetime(2024, 1, 1, 12, 0, 0)
    mock_report.completed_at = datetime(2024, 1, 1, 12, 30, 0)
    mock_report.to_dict.return_value = {
        "_id": "test-http-download-id",
        "original_filename": "test_http_download.pcap",
        "status": "completed",
        "file_size": 2048000,
        "file_hash": "test123hash456",
        "created_at": "2024-01-01T12:00:00Z",
        "completed_at": "2024-01-01T12:30:00Z",
        "processing_time": 1800.0,
        "analysis_results": {
            "traffic_stats": {
                "total_packets": 10000,
                "total_bytes": 2048000,
                "duration": 600.0,
                "unique_ips": 150,
                "unique_ports": 200
            },
            "top_protocols": [
                {"name": "TCP", "count": 6000},
                {"name": "UDP", "count": 3000},
                {"name": "ICMP", "count": 800},
                {"name": "HTTP", "count": 200}
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
            "http_analysis": {
                "total_requests": 500,
                "status_codes": {"200": 400, "404": 50, "500": 30},
                "methods": {"GET": 450, "POST": 40, "PUT": 10}
            },
            "network_issues": [
                {
                    "type": "suspicious_activity",
                    "description": "Multiple failed connections",
                    "severity": "high",
                    "details": {"ip": "10.0.0.1"},
                    "timestamp": "2024-01-01T12:15:00Z"
                }
            ],
            "top_talkers": [
                {
                    "ip": "192.168.1.100",
                    "bytes_sent": 2048000,
                    "bytes_received": 1024000
                }
            ]
        }
    }
    
    # Mock the database function
    from api.v1.endpoints.reports import router as reports_router
    import api.v1.endpoints.reports as reports_module
    
    original_get_report = reports_module.get_report_by_id
    reports_module.get_report_by_id = AsyncMock(return_value=mock_report)
    
    # Add router to app
    app.include_router(reports_router, prefix="/api/v1/reports")
    
    try:
        # Create test client
        client = TestClient(app)
        
        print("🔍 Step 1: Make HTTP request to download endpoint...")
        
        # Make request to download endpoint
        response = client.get("/api/v1/reports/test-http-download-id/download")
        
        print(f"✅ HTTP Response received")
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        # Check response details
        if response.status_code == 200:
            print("✅ HTTP status is 200 OK")
            
            # Check content-type
            content_type = response.headers.get("content-type", "")
            print(f"📄 Content-Type: {content_type}")
            
            if content_type == "application/pdf":
                print("✅ Content-Type is correct (application/pdf)")
            else:
                print("❌ Content-Type is incorrect")
            
            # Check Content-Disposition
            content_disposition = response.headers.get("content-disposition", "")
            print(f"📄 Content-Disposition: {content_disposition}")
            
            if "attachment" in content_disposition and "filename=" in content_disposition:
                print("✅ Content-Disposition is correct")
            else:
                print("❌ Content-Disposition is incorrect")
            
            # Check Content-Length
            content_length = response.headers.get("content-length", "")
            print(f"📄 Content-Length: {content_length}")
            
            # Get response content
            pdf_content = response.content
            print(f"📊 Response content size: {len(pdf_content)} bytes")
            
            if content_length and len(pdf_content) == int(content_length):
                print("✅ Content-Length matches actual content size")
            else:
                print("❌ Content-Length mismatch")
            
            print("\n🔍 Step 2: Save and validate PDF...")
            
            # Save to file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_filename = tmp_file.name
            
            print(f"✅ PDF saved to: {tmp_filename}")
            
            # Validate PDF
            sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
            from pdf_validator import PDFValidator
            
            pdf_validator = PDFValidator()
            validation_result = pdf_validator.validate_pdf_file(tmp_filename)
            
            print(f"📄 PDF validation: {validation_result.is_valid}")
            
            if validation_result.is_valid:
                print("✅ PDF is valid!")
                
                # Check PDF signature
                with open(tmp_filename, 'rb') as f:
                    header = f.read(10)
                    print(f"📄 PDF header: {header}")
                    
                    if header.startswith(b'%PDF-'):
                        print("✅ PDF signature is correct")
                    else:
                        print("❌ PDF signature is incorrect")
                
                print(f"\n✅ SUCCESS! PDF download works correctly!")
                print(f"📄 Test file: {tmp_filename}")
                print("👉 You can open this file to verify it's readable")
                
                return tmp_filename
                
            else:
                print("❌ PDF validation failed:")
                for issue in validation_result.issues:
                    print(f"   - {issue}")
                
                # Show first few bytes for debugging
                with open(tmp_filename, 'rb') as f:
                    first_bytes = f.read(100)
                    print(f"📄 First 100 bytes: {first_bytes}")
                
        else:
            print(f"❌ HTTP request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Restore original function
        reports_module.get_report_by_id = original_get_report
    
    return None

if __name__ == "__main__":
    test_http_pdf_download()