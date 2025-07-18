#!/usr/bin/env python3
"""
Test the fixed PDF download by simulating the exact conditions.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from io import BytesIO
import sys

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

async def test_fixed_pdf_download():
    """Test the fixed PDF download implementation"""
    
    print("🧪 Testing Fixed PDF Download Implementation")
    print("=" * 50)
    
    # Import required modules
    from services.pdf_export import PDFExportService
    from api.v1.endpoints.reports import _convert_report_for_pdf
    from fastapi.responses import StreamingResponse
    
    # Create test report data (exactly as it would come from database)
    test_report_data = {
        "_id": "test-fixed-download-id",
        "original_filename": "test_fixed_download.pcap",
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
                },
                {
                    "src_ip": "10.0.0.1",
                    "dst_ip": "10.0.0.2",
                    "src_port": 22,
                    "dst_port": 12345,
                    "packet_count": 300,
                    "bytes": 150000
                }
            ],
            "http_analysis": {
                "total_requests": 500,
                "status_codes": {"200": 400, "404": 50, "500": 30, "302": 20},
                "methods": {"GET": 450, "POST": 40, "PUT": 10}
            },
            "network_issues": [
                {
                    "type": "suspicious_activity",
                    "description": "Multiple failed connections",
                    "severity": "high",
                    "details": {"ip": "10.0.0.1"},
                    "timestamp": "2024-01-01T12:15:00Z"
                },
                {
                    "type": "port_scan",
                    "description": "Port scanning detected",
                    "severity": "medium",
                    "details": {"src_ip": "192.168.1.50", "dst_ip": "192.168.1.100", "port_count": 1000},
                    "timestamp": "2024-01-01T12:20:00Z"
                }
            ],
            "top_talkers": [
                {
                    "ip": "192.168.1.100",
                    "bytes_sent": 2048000,
                    "bytes_received": 1024000
                },
                {
                    "ip": "10.0.0.1",
                    "bytes_sent": 1536000,
                    "bytes_received": 768000
                }
            ]
        }
    }
    
    print("🔍 Step 1: Convert report data for PDF...")
    
    # Convert report data exactly as the endpoint does
    pdf_data = _convert_report_for_pdf(test_report_data)
    
    print(f"✅ Report data converted")
    print(f"   Job ID: {pdf_data['job_id']}")
    print(f"   Filename: {pdf_data['filename']}")
    print(f"   Total packets: {pdf_data['total_packets']}")
    print(f"   Protocols: {pdf_data['protocols']}")
    
    print("\n🔍 Step 2: Generate PDF...")
    
    # Generate PDF exactly as the endpoint does
    pdf_service = PDFExportService()
    pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
    
    print(f"✅ PDF generated: {len(pdf_bytes)} bytes")
    
    # Generate filename exactly as the endpoint does
    pdf_filename = pdf_service.generate_pdf_filename(test_report_data["original_filename"])
    print(f"✅ PDF filename: {pdf_filename}")
    
    print("\n🔍 Step 3: Create StreamingResponse (FIXED VERSION)...")
    
    # Test the OLD way (that causes corruption)
    print("📝 Testing OLD way (BytesIO)...")
    
    pdf_stream_old = BytesIO(pdf_bytes)
    response_old = StreamingResponse(
        pdf_stream_old,  # This was the problem
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={pdf_filename}",
            "Content-Length": str(len(pdf_bytes))
        }
    )
    
    old_content = b""
    async for chunk in response_old.body_iterator:
        old_content += chunk
    
    print(f"   OLD: {len(old_content)} bytes (should be {len(pdf_bytes)})")
    print(f"   OLD matches: {old_content == pdf_bytes}")
    
    # Test the NEW way (that fixes corruption)
    print("\n📝 Testing NEW way (iter)...")
    
    response_new = StreamingResponse(
        iter([pdf_bytes]),  # This is the fix
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={pdf_filename}",
            "Content-Length": str(len(pdf_bytes))
        }
    )
    
    new_content = b""
    async for chunk in response_new.body_iterator:
        new_content += chunk
    
    print(f"   NEW: {len(new_content)} bytes (should be {len(pdf_bytes)})")
    print(f"   NEW matches: {new_content == pdf_bytes}")
    
    print("\n🔍 Step 4: Test file saving...")
    
    # Test saving both to files
    with tempfile.NamedTemporaryFile(suffix='_old.pdf', delete=False) as tmp_old:
        tmp_old.write(old_content)
        old_filename = tmp_old.name
    
    with tempfile.NamedTemporaryFile(suffix='_new.pdf', delete=False) as tmp_new:
        tmp_new.write(new_content)
        new_filename = tmp_new.name
    
    print(f"✅ OLD PDF saved: {old_filename}")
    print(f"✅ NEW PDF saved: {new_filename}")
    
    # Validate both PDFs
    sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
    from pdf_validator import PDFValidator
    
    pdf_validator = PDFValidator()
    
    print("\n🔍 Step 5: Validate PDFs...")
    
    # Validate OLD PDF
    old_validation = pdf_validator.validate_pdf_file(old_filename)
    print(f"📄 OLD PDF validation: {old_validation.is_valid}")
    if not old_validation.is_valid:
        print("   OLD PDF issues:")
        for issue in old_validation.issues:
            print(f"     - {issue}")
    
    # Validate NEW PDF
    new_validation = pdf_validator.validate_pdf_file(new_filename)
    print(f"📄 NEW PDF validation: {new_validation.is_valid}")
    if not new_validation.is_valid:
        print("   NEW PDF issues:")
        for issue in new_validation.issues:
            print(f"     - {issue}")
    
    # Check PDF signatures
    print("\n🔍 Step 6: Check PDF signatures...")
    
    with open(old_filename, 'rb') as f:
        old_header = f.read(10)
        print(f"📄 OLD PDF header: {old_header}")
    
    with open(new_filename, 'rb') as f:
        new_header = f.read(10)
        print(f"📄 NEW PDF header: {new_header}")
    
    print("\n🔍 Step 7: Summary...")
    
    print(f"📊 Original PDF: {len(pdf_bytes)} bytes")
    print(f"📊 OLD streamed: {len(old_content)} bytes ({'✅' if old_content == pdf_bytes else '❌'} match)")
    print(f"📊 NEW streamed: {len(new_content)} bytes ({'✅' if new_content == pdf_bytes else '❌'} match)")
    print(f"📊 OLD validation: {'✅' if old_validation.is_valid else '❌'}")
    print(f"📊 NEW validation: {'✅' if new_validation.is_valid else '❌'}")
    
    if new_validation.is_valid:
        print(f"\n✅ SUCCESS! The fix works!")
        print(f"📄 Fixed PDF file: {new_filename}")
        print("👉 You can open this file to verify it's readable")
    else:
        print(f"\n❌ The fix didn't work as expected")
    
    # Clean up old file (keep new one for testing)
    os.unlink(old_filename)
    
    return new_filename

if __name__ == "__main__":
    asyncio.run(test_fixed_pdf_download())