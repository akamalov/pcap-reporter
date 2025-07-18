#!/usr/bin/env python3
"""
TEST EXPORT ENDPOINT FIX
Test that the export endpoint now generates proper PDFs instead of text files.
"""

import sys
import os
import traceback

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

def test_export_endpoint_data_conversion():
    """Test the export endpoint's data conversion with problematic data."""
    
    print("🔍 TESTING EXPORT ENDPOINT DATA CONVERSION")
    print("=" * 60)
    
    try:
        # Import the conversion function from export endpoint
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Create MongoDB report with null values that previously caused crashes
        mongo_report = {
            "job_id": "test-export-123",
            "original_filename": "test_export.pcap",
            "status": "completed",
            "file_size": 1024000,
            "file_hash": "test123hash",
            "created_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:05:00Z",
            "processing_time": 30.5,
            "analysis_results": {
                "traffic_stats": {
                    "total_packets": 1000,
                    "total_bytes": 2048000,
                    "duration": 120.0,
                    "unique_ips": 50,
                    "unique_ports": 100
                },
                "top_protocols": [
                    {"name": "TCP", "count": 600},
                    {"name": "UDP", "count": 300},
                    {"name": "ICMP", "count": 100}
                ],
                "top_tcp_conversations": [
                    {
                        "src_ip": "192.168.1.1",
                        "dst_ip": "192.168.1.2", 
                        "src_port": 80,
                        "dst_port": 443,
                        "packet_count": 50,
                        "bytes": 10240
                    }
                ],
                # These null values previously caused crashes
                "dns_analysis": None,
                "http_analysis": None,
                "network_issues": []
            }
        }
        
        print("📊 Step 1: Testing data conversion with null values...")
        
        # This should work now without crashing
        pdf_data = _convert_mongodb_report_to_pdf_format(mongo_report)
        
        print("✅ Data conversion successful!")
        print(f"   - Job ID: {pdf_data.get('job_id')}")
        print(f"   - Filename: {pdf_data.get('filename')}")
        print(f"   - Total packets: {pdf_data.get('total_packets')}")
        print(f"   - Protocols: {pdf_data.get('protocols')}")
        print(f"   - Has DNS analysis: {'dns' in pdf_data.get('protocol_analysis', {})}")
        print(f"   - Has HTTP analysis: {'http' in pdf_data.get('protocol_analysis', {})}")
        
        return pdf_data
        
    except Exception as e:
        print(f"❌ Data conversion failed: {e}")
        traceback.print_exc()
        return None

def test_pdf_generation_with_export_data(pdf_data):
    """Test PDF generation with the export endpoint's converted data."""
    
    print("\n🔍 TESTING PDF GENERATION WITH EXPORT DATA")
    print("=" * 60)
    
    try:
        from services.pdf_export import PDFExportService
        
        print("📊 Step 2: Testing PDF generation with converted data...")
        
        # Generate PDF with the converted data
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        print(f"✅ PDF generation successful: {len(pdf_bytes)} bytes")
        
        # Validate PDF structure
        if pdf_bytes.startswith(b'%PDF-') and b'%%EOF' in pdf_bytes:
            print("✅ PDF structure valid")
        else:
            print("❌ PDF structure invalid")
            return False
        
        # Save the PDF
        with open("/tmp/export_endpoint_test.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("💾 PDF saved to /tmp/export_endpoint_test.pdf")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        traceback.print_exc()
        return False

def test_export_endpoint_simulation():
    """Simulate the complete export endpoint flow."""
    
    print("\n🔍 TESTING COMPLETE EXPORT ENDPOINT SIMULATION")
    print("=" * 60)
    
    try:
        # This simulates what happens in the export endpoint
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        from services.pdf_export import PDFExportService
        
        # Mock MongoDB report (similar to what would be in the database)
        mongo_report = {
            "job_id": "export-simulation-456",
            "original_filename": "simulation.pcap",
            "status": "completed",
            "file_size": 2048000,
            "analysis_results": {
                "traffic_stats": {
                    "total_packets": 2000,
                    "total_bytes": 4096000,
                    "duration": 300.0
                },
                "top_protocols": [
                    {"name": "TCP", "count": 1200},
                    {"name": "UDP", "count": 600},
                    {"name": "ICMP", "count": 200}
                ],
                # Mix of null and valid data
                "dns_analysis": {
                    "total_queries": 100,
                    "query_types": {"A": 70, "AAAA": 30},
                    "top_domains": {"example.com": 50, "google.com": 30}
                },
                "http_analysis": None,  # This should be handled gracefully
                "network_issues": [
                    {
                        "type": "security_issue",
                        "severity": "medium",
                        "description": "Suspicious traffic detected"
                    }
                ]
            }
        }
        
        print("📊 Step 3: Simulating complete export endpoint flow...")
        
        # Step 1: Convert MongoDB data to PDF format
        pdf_data = _convert_mongodb_report_to_pdf_format(mongo_report)
        print("✅ MongoDB data converted to PDF format")
        
        # Step 2: Generate PDF (this would previously fail and trigger fallback)
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        print(f"✅ PDF generated: {len(pdf_bytes)} bytes")
        
        # Step 3: Validate PDF
        if pdf_bytes.startswith(b'%PDF-') and b'%%EOF' in pdf_bytes:
            print("✅ PDF structure valid")
        else:
            print("❌ PDF structure invalid")
            return False
        
        # Step 4: Save and verify
        with open("/tmp/export_simulation_test.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("💾 Simulation PDF saved to /tmp/export_simulation_test.pdf")
        
        return True
        
    except Exception as e:
        print(f"❌ Export endpoint simulation failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 EXPORT ENDPOINT FIX TEST")
    print("=" * 60)
    
    # Test 1: Data conversion with null values
    pdf_data = test_export_endpoint_data_conversion()
    if not pdf_data:
        print("\n❌ Data conversion test failed!")
        sys.exit(1)
    
    # Test 2: PDF generation with converted data
    pdf_success = test_pdf_generation_with_export_data(pdf_data)
    if not pdf_success:
        print("\n❌ PDF generation test failed!")
        sys.exit(1)
    
    # Test 3: Complete export endpoint simulation
    simulation_success = test_export_endpoint_simulation()
    if not simulation_success:
        print("\n❌ Export endpoint simulation failed!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("✅ Export endpoint data conversion handles null values")
    print("✅ PDF generation works with export endpoint data")
    print("✅ Complete export endpoint flow generates valid PDFs")
    print("✅ No fallback to text generation triggered")
    
    print("\n📄 Generated test files:")
    print("   - /tmp/export_endpoint_test.pdf")
    print("   - /tmp/export_simulation_test.pdf")
    
    print("\n🎯 CONCLUSION:")
    print("The export endpoint should now generate proper PDFs instead of text files!")
    
    sys.exit(0)