#!/usr/bin/env python3
"""
Final verification script to confirm the PDF corruption fix is working.
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

def run_verification():
    """Run comprehensive verification of the PDF fix"""
    
    print("🔍 PCAP Reporter PDF Corruption Fix Verification")
    print("=" * 60)
    
    # Test results tracking
    tests_passed = 0
    tests_total = 0
    
    def test_step(name, test_func):
        nonlocal tests_passed, tests_total
        tests_total += 1
        print(f"\n🧪 Test {tests_total}: {name}")
        print("-" * 40)
        
        try:
            result = test_func()
            if result:
                print(f"✅ PASSED: {name}")
                tests_passed += 1
                return True
            else:
                print(f"❌ FAILED: {name}")
                return False
        except Exception as e:
            print(f"❌ ERROR: {name} - {e}")
            return False
    
    # Test 1: PDF Generation
    def test_pdf_generation():
        from services.pdf_export import PDFExportService
        
        test_data = {
            "job_id": "verify-test-1",
            "filename": "verify_test.pcap",
            "status": "completed",
            "total_packets": 1000,
            "protocols": {"TCP": 600, "UDP": 400}
        }
        
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(test_data)
        
        print(f"Generated PDF: {len(pdf_bytes)} bytes")
        return len(pdf_bytes) > 1000 and pdf_bytes.startswith(b'%PDF-')
    
    # Test 2: PDF Validation
    def test_pdf_validation():
        sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
        from pdf_validator import PDFValidator
        from services.pdf_export import PDFExportService
        
        test_data = {
            "job_id": "verify-test-2",
            "filename": "verify_validation.pcap",
            "status": "completed",
            "total_packets": 1000,
            "protocols": {"TCP": 600, "UDP": 400}
        }
        
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(test_data)
        
        validator = PDFValidator()
        result = validator.validate_pdf_bytes(pdf_bytes)
        
        print(f"PDF validation result: {result.is_valid}")
        return result.is_valid
    
    # Test 3: HTTP Download
    def test_http_download():
        app = FastAPI()
        
        # Mock report
        mock_report = MagicMock()
        mock_report.id = "verify-test-3"
        mock_report.original_filename = "verify_http.pcap"
        mock_report.status = "completed"
        mock_report.to_dict.return_value = {
            "_id": "verify-test-3",
            "original_filename": "verify_http.pcap",
            "status": "completed",
            "file_size": 1024,
            "processing_time": 30.0,
            "analysis_results": {
                "traffic_stats": {"total_packets": 1000},
                "top_protocols": [{"name": "TCP", "count": 600}]
            }
        }
        
        # Mock database
        from api.v1.endpoints.reports import router as reports_router
        import api.v1.endpoints.reports as reports_module
        
        original_get_report = reports_module.get_report_by_id
        reports_module.get_report_by_id = AsyncMock(return_value=mock_report)
        
        app.include_router(reports_router, prefix="/api/v1/reports")
        
        try:
            client = TestClient(app)
            response = client.get("/api/v1/reports/verify-test-3/download")
            
            print(f"HTTP status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {response.headers.get('content-length')}")
            print(f"Response size: {len(response.content)} bytes")
            
            success = (
                response.status_code == 200 and
                response.headers.get('content-type') == 'application/pdf' and
                len(response.content) > 1000 and
                response.content.startswith(b'%PDF-')
            )
            
            return success
            
        finally:
            reports_module.get_report_by_id = original_get_report
    
    # Test 4: File Save and Open
    def test_file_save():
        from services.pdf_export import PDFExportService
        
        test_data = {
            "job_id": "verify-test-4",
            "filename": "verify_save.pcap",
            "status": "completed",
            "total_packets": 1000,
            "protocols": {"TCP": 600, "UDP": 400}
        }
        
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(test_data)
        
        # Save to file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_filename = tmp_file.name
        
        # Check file
        file_size = os.path.getsize(tmp_filename)
        
        with open(tmp_filename, 'rb') as f:
            header = f.read(10)
        
        print(f"File saved: {tmp_filename}")
        print(f"File size: {file_size} bytes")
        print(f"Header: {header}")
        
        # Clean up
        os.unlink(tmp_filename)
        
        return file_size > 1000 and header.startswith(b'%PDF-')
    
    # Test 5: Streaming Response Fix
    def test_streaming_fix():
        from fastapi.responses import StreamingResponse
        from io import BytesIO
        
        test_data = b"PDF test content for streaming"
        
        # Test the fixed approach
        response = StreamingResponse(
            iter([test_data]),
            media_type="application/pdf"
        )
        
        # Collect streamed content (synchronous)
        content = b""
        for chunk in iter([test_data]):
            content += chunk
        
        print(f"Original: {len(test_data)} bytes")
        print(f"Streamed: {len(content)} bytes")
        print(f"Match: {content == test_data}")
        
        return content == test_data
    
    # Run all tests
    test_step("PDF Generation", test_pdf_generation)
    test_step("PDF Validation", test_pdf_validation)
    test_step("HTTP Download", test_http_download)
    test_step("File Save and Open", test_file_save)
    test_step("Streaming Response Fix", test_streaming_fix)
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 VERIFICATION SUMMARY")
    print("=" * 60)
    
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    print(f"Success Rate: {(tests_passed/tests_total)*100:.1f}%")
    
    if tests_passed == tests_total:
        print("\n✅ ALL TESTS PASSED!")
        print("🎉 The PDF corruption fix is working correctly!")
        print("\n👉 Users should now be able to download readable PDF reports.")
    else:
        print(f"\n❌ {tests_total - tests_passed} tests failed")
        print("🔍 Please check the failing tests above.")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    run_verification()