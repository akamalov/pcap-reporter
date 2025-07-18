#!/usr/bin/env python3
"""
Real-world test of PDF download by creating a test report and downloading it.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from bson import ObjectId
import sys

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

async def create_test_report():
    """Create a test report in the database"""
    
    from models.report import Report, ReportStatus
    from beanie import init_beanie
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Initialize database connection
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    try:
        await init_beanie(
            database=client.pcap_reporter,
            document_models=[Report]
        )
        
        print("✅ Database connection established")
        
        # Create test report
        test_report = Report(
            job_id="test-real-pdf-download",
            original_filename="test_real_download.pcap",
            status=ReportStatus.COMPLETED,
            file_size=2048,
            file_hash="test123hash",
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            analysis_results={
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
        )
        
        # Save the report
        await test_report.save()
        print(f"✅ Test report created: {test_report.id}")
        
        return str(test_report.id)
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None
        
    finally:
        client.close()

async def test_pdf_download(report_id):
    """Test downloading the PDF using the actual endpoint"""
    
    from api.v1.endpoints.reports import download_report_pdf
    
    print(f"🔍 Testing PDF download for report: {report_id}")
    
    try:
        # Call the actual endpoint
        response = await download_report_pdf(report_id)
        
        print(f"✅ Response created successfully")
        print(f"   Media type: {response.media_type}")
        print(f"   Headers: {dict(response.headers)}")
        
        # Stream the response
        content = b""
        async for chunk in response.body_iterator:
            content += chunk
        
        print(f"✅ Response streamed: {len(content)} bytes")
        
        # Save to file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_filename = tmp_file.name
        
        print(f"✅ PDF saved to: {tmp_filename}")
        
        # Validate the PDF
        sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
        from pdf_validator import PDFValidator
        
        pdf_validator = PDFValidator()
        
        # Validate from file
        validation_result = pdf_validator.validate_pdf_file(tmp_filename)
        print(f"✅ PDF validation: {validation_result.is_valid}")
        
        if validation_result.is_valid:
            print("✅ PDF is valid and should be readable!")
            print(f"📄 File location: {tmp_filename}")
            print("👉 Try opening this file in a PDF reader to verify it works")
        else:
            print("❌ PDF validation failed:")
            for issue in validation_result.issues:
                print(f"   - {issue}")
        
        # Check file size
        file_size = os.path.getsize(tmp_filename)
        print(f"📊 File size: {file_size} bytes")
        
        # Check PDF header
        with open(tmp_filename, 'rb') as f:
            header = f.read(10)
            print(f"📄 PDF header: {header}")
            
            # Check if it starts with PDF signature
            if header.startswith(b'%PDF-'):
                print("✅ PDF signature is correct")
            else:
                print("❌ PDF signature is incorrect")
        
        return tmp_filename
        
    except Exception as e:
        print(f"❌ PDF download failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main test function"""
    
    print("🧪 Real-World PDF Download Test")
    print("=" * 50)
    
    # Create test report
    report_id = await create_test_report()
    
    if not report_id:
        print("❌ Failed to create test report")
        return
    
    # Test PDF download
    pdf_file = await test_pdf_download(report_id)
    
    if pdf_file:
        print(f"\n✅ Test completed successfully!")
        print(f"📄 PDF file: {pdf_file}")
        print("👉 You can now try to open this file to verify it's readable")
    else:
        print("\n❌ Test failed")

if __name__ == "__main__":
    asyncio.run(main())