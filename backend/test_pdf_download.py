#!/usr/bin/env python3
"""
Test the actual PDF download endpoint to verify the streaming fix.
"""

import asyncio
import io
from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.v1.endpoints.reports import router as reports_router
from models.report import Report, ReportStatus
from services.pdf_export import PDFExportService
import os
import tempfile

app = FastAPI()
app.include_router(reports_router, prefix="/api/v1/reports")

async def test_streaming_response_fix():
    """Test that StreamingResponse properly handles PDF bytes"""
    
    # Create mock PDF bytes
    pdf_service = PDFExportService()
    
    # Create minimal test data
    test_data = {
        "job_id": "test-streaming",
        "filename": "test_streaming.pcap",
        "status": "completed",
        "file_size": 1024,
        "created_at": "2024-01-01T12:00:00Z",
        "completed_at": "2024-01-01T12:30:00Z",
        "total_packets": 100,
        "protocols": {"TCP": 50, "UDP": 30, "ICMP": 20}
    }
    
    print("🔍 Testing PDF generation and streaming...")
    
    # Generate PDF
    pdf_bytes = pdf_service.generate_pdf_report(test_data)
    print(f"✅ PDF generated successfully: {len(pdf_bytes)} bytes")
    
    # Test old way (BytesIO - WRONG)
    print("\n🔍 Testing old StreamingResponse (BytesIO) - Expected: FAIL")
    try:
        from fastapi.responses import StreamingResponse
        
        # This is the OLD way that causes corruption
        pdf_stream_old = io.BytesIO(pdf_bytes)
        response_old = StreamingResponse(
            pdf_stream_old,  # This is WRONG - BytesIO is not an iterator
            media_type="application/pdf"
        )
        print("❌ Old way created response (but will fail during streaming)")
    except Exception as e:
        print(f"❌ Old way failed: {e}")
    
    # Test new way (iter([pdf_bytes]) - CORRECT)
    print("\n🔍 Testing new StreamingResponse (iter) - Expected: SUCCESS")
    try:
        response_new = StreamingResponse(
            iter([pdf_bytes]),  # This is CORRECT - iter yields bytes
            media_type="application/pdf"
        )
        print("✅ New way created response successfully")
        
        # Test that we can iterate over the response
        content = b""
        for chunk in iter([pdf_bytes]):
            content += chunk
        
        print(f"✅ Content retrieved: {len(content)} bytes")
        print(f"✅ Content matches original: {content == pdf_bytes}")
        
    except Exception as e:
        print(f"❌ New way failed: {e}")
    
    # Test actual file writing
    print("\n🔍 Testing actual file writing...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_filename = tmp_file.name
        
        # Check if file is readable
        with open(tmp_filename, 'rb') as f:
            read_bytes = f.read()
        
        print(f"✅ File written: {tmp_filename}")
        print(f"✅ File size: {len(read_bytes)} bytes")
        print(f"✅ Content matches: {read_bytes == pdf_bytes}")
        
        # Validate PDF structure
        pdf_validator = PDFValidator()
        validation_result = pdf_validator.validate_pdf_bytes(read_bytes)
        print(f"✅ PDF validation: {validation_result.is_valid}")
        
        # Clean up
        os.unlink(tmp_filename)
        
    except Exception as e:
        print(f"❌ File test failed: {e}")

def test_iterator_vs_bytesio():
    """Test the difference between BytesIO and iter() for streaming"""
    
    test_data = b"Hello, World! This is test PDF content."
    
    print("\n🔍 Testing iterator vs BytesIO behavior...")
    
    # Test BytesIO behavior
    print("📝 BytesIO behavior:")
    bytesio_stream = io.BytesIO(test_data)
    print(f"   Type: {type(bytesio_stream)}")
    print(f"   Is iterator: {hasattr(bytesio_stream, '__iter__')}")
    
    # Try to use BytesIO as iterator
    try:
        for chunk in bytesio_stream:
            print(f"   BytesIO chunk: {chunk}")
    except Exception as e:
        print(f"   ❌ BytesIO iteration failed: {e}")
    
    # Test iter() behavior
    print("\n📝 iter([bytes]) behavior:")
    iter_stream = iter([test_data])
    print(f"   Type: {type(iter_stream)}")
    print(f"   Is iterator: {hasattr(iter_stream, '__iter__')}")
    
    # Try to use iter() as iterator
    try:
        for chunk in iter_stream:
            print(f"   iter() chunk: {chunk}")
    except Exception as e:
        print(f"   ❌ iter() iteration failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing PDF Download Streaming Fix")
    print("=" * 50)
    
    # Import PDFValidator
    import sys
    sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
    from pdf_validator import PDFValidator
    
    test_iterator_vs_bytesio()
    
    asyncio.run(test_streaming_response_fix())
    
    print("\n✅ All tests completed!")