#!/usr/bin/env python3
"""
DEBUG PDF SERVICE TEST
Test to find why PDFExportService fails and triggers fallback to text generation.
"""

import sys
import os
import traceback

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

def test_pdf_service():
    """Test the PDFExportService to identify failure points."""
    
    print("🔍 DEBUGGING PDFExportService FAILURE")
    print("=" * 60)
    
    try:
        # Test 1: Import PDFExportService
        print("\n📦 Step 1: Testing PDFExportService import...")
        from services.pdf_export import PDFExportService
        print("✅ PDFExportService imported successfully")
        
        # Test 2: Initialize service
        print("\n🏗️ Step 2: Testing PDFExportService initialization...")
        service = PDFExportService()
        print("✅ PDFExportService initialized successfully")
        
        # Test 3: Create realistic test data
        print("\n📊 Step 3: Creating realistic test data...")
        test_data = {
            "job_id": "debug-test-123",
            "filename": "debug_test.pcap",
            "status": "completed",
            "total_packets": 1000,
            "unique_ips": 50,
            "unique_ports": 100,
            "duration": 120.5,
            "file_size": 1024000,
            "protocols": {
                "TCP": 600,
                "UDP": 300,
                "ICMP": 100
            },
            "processing_time": 25.3,
            "created_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:05:00Z"
        }
        print("✅ Test data created")
        
        # Test 4: Generate HTML template
        print("\n📄 Step 4: Testing HTML template generation...")
        html_content = service.generate_html_template(test_data)
        print(f"✅ HTML template generated: {len(html_content)} characters")
        
        # Test 5: Test convert_html_to_pdf
        print("\n🔄 Step 5: Testing HTML to PDF conversion...")
        pdf_bytes = service.convert_html_to_pdf(html_content)
        print(f"✅ PDF generated: {len(pdf_bytes)} bytes")
        
        # Test 6: Validate PDF structure
        print("\n🔍 Step 6: Validating PDF structure...")
        if pdf_bytes.startswith(b'%PDF-') and b'%%EOF' in pdf_bytes:
            print("✅ PDF structure valid")
        else:
            print("❌ PDF structure invalid")
            print(f"   First 50 bytes: {pdf_bytes[:50]}")
            print(f"   Last 50 bytes: {pdf_bytes[-50:]}")
            return False
        
        # Test 7: Full generate_pdf_report method
        print("\n📊 Step 7: Testing full generate_pdf_report method...")
        full_pdf_bytes = service.generate_pdf_report(test_data)
        print(f"✅ Full PDF generation: {len(full_pdf_bytes)} bytes")
        
        # Test 8: Save test PDF
        print("\n💾 Step 8: Saving test PDF...")
        with open("/tmp/debug_pdf_test.pdf", "wb") as f:
            f.write(full_pdf_bytes)
        print("✅ Test PDF saved to /tmp/debug_pdf_test.pdf")
        
        # Test 9: Test specific dependencies
        print("\n🔧 Step 9: Testing specific dependencies...")
        
        # Test ReportLab
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            print("✅ ReportLab imports successful")
        except Exception as e:
            print(f"❌ ReportLab import failed: {e}")
            return False
        
        # Test WeasyPrint
        try:
            import weasyprint
            print("✅ WeasyPrint import successful")
        except Exception as e:
            print(f"⚠️ WeasyPrint import failed: {e}")
            print("   This is expected and should fallback to ReportLab")
        
        # Test Jinja2
        try:
            from jinja2 import Template
            print("✅ Jinja2 import successful")
        except Exception as e:
            print(f"❌ Jinja2 import failed: {e}")
            return False
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ PDFExportService is working correctly")
        print(f"✅ Generated PDF: {len(full_pdf_bytes)} bytes")
        return True
        
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        print("\n🔍 FULL TRACEBACK:")
        traceback.print_exc()
        return False

def test_simple_pdf_service():
    """Test the SimplePDFExportService to show the difference."""
    
    print("\n" + "=" * 60)
    print("🔍 TESTING SimplePDFExportService FOR COMPARISON")
    print("=" * 60)
    
    try:
        from services.simple_pdf_export import SimplePDFExportService
        
        service = SimplePDFExportService()
        
        test_data = {
            "job_id": "simple-test-123",
            "filename": "simple_test.pcap",
            "status": "completed",
            "total_packets": 1000,
            "unique_ips": 50,
            "unique_ports": 100,
            "duration": 120.5,
            "file_size": 1024000,
            "protocols": {
                "TCP": 600,
                "UDP": 300,
                "ICMP": 100
            }
        }
        
        # Generate "PDF" (actually text)
        text_bytes = service.generate_pdf_report(test_data)
        
        print(f"📄 SimplePDFExportService output: {len(text_bytes)} bytes")
        print("📄 Content type: TEXT (not PDF)")
        
        # Check if it's text
        try:
            text_content = text_bytes.decode('utf-8')
            print(f"✅ Content is text: {text_content[:100]}...")
        except:
            print("❌ Content is not text")
        
        # Save for comparison
        with open("/tmp/debug_simple_output.txt", "wb") as f:
            f.write(text_bytes)
        print("💾 Simple output saved to /tmp/debug_simple_output.txt")
        
        return True
        
    except Exception as e:
        print(f"💥 SimplePDFExportService test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 PDF SERVICE DEBUG TEST")
    print("=" * 60)
    
    # Test the proper PDF service
    pdf_success = test_pdf_service()
    
    # Test the simple (text) service for comparison
    simple_success = test_simple_pdf_service()
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    print("=" * 60)
    print(f"✅ PDFExportService: {'WORKING' if pdf_success else 'FAILED'}")
    print(f"✅ SimplePDFExportService: {'WORKING' if simple_success else 'FAILED'}")
    
    if pdf_success:
        print("\n🎯 CONCLUSION:")
        print("✅ PDFExportService is working correctly")
        print("✅ The fallback to SimplePDFExportService was unnecessary")
        print("✅ Users should get proper PDFs now that fallback is removed")
        print("\n📄 Check generated files:")
        print("   - /tmp/debug_pdf_test.pdf (proper PDF)")
        print("   - /tmp/debug_simple_output.txt (text output)")
    else:
        print("\n🚨 PDFExportService has issues that need to be fixed!")
    
    sys.exit(0 if pdf_success else 1)