#!/usr/bin/env python3
"""
Comprehensive PDF corruption detection and testing script.
This script tests PDF generation and identifies corruption issues.
"""

import sys
import os
import tempfile
from pathlib import Path
import traceback
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.pdf_export import PDFExportService
from services.simple_pdf_export import SimplePDFExportService
from tests.utils.pdf_validator import PDFValidator, diagnose_pdf_corruption
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_report_data():
    """Create comprehensive test report data."""
    return {
        "job_id": "test_pdf_corruption_123",
        "filename": "test_corruption.pcap",
        "status": "completed",
        "file_size": 2048576,  # 2MB
        "created_at": "2024-01-01T12:00:00Z",
        "completed_at": "2024-01-01T12:30:00Z",
        "file_hash": "abc123def456789",
        "analysis_type": "comprehensive",
        "total_packets": 10000,
        "unique_ips": 150,
        "unique_ports": 200,
        "duration": 600.5,
        "processing_time": 90.2,
        "protocols": {
            "TCP": 6000,
            "UDP": 3000,
            "ICMP": 800,
            "HTTP": 200
        },
        "packet_sizes": {
            "min": 64,
            "max": 1518,
            "avg": 512,
            "total_bytes": 5120000
        },
        "protocol_analysis": {
            "tcp": {
                "total_connections": 300,
                "established_connections": 290,
                "failed_connections": 10,
                "average_connection_duration": 45.5,
                "top_conversations": [
                    {
                        "src_ip": "192.168.1.100",
                        "dst_ip": "192.168.1.200",
                        "src_port": 80,
                        "dst_port": 443,
                        "packets": 500,
                        "bytes": 256000
                    },
                    {
                        "src_ip": "10.0.0.1",
                        "dst_ip": "10.0.0.2",
                        "src_port": 22,
                        "dst_port": 12345,
                        "packets": 300,
                        "bytes": 150000
                    }
                ]
            },
            "http": {
                "total_requests": 500,
                "status_codes": {
                    "200": 400,
                    "404": 50,
                    "500": 30,
                    "302": 20
                },
                "methods": {
                    "GET": 450,
                    "POST": 40,
                    "PUT": 10
                }
            },
            "dns": {
                "total_queries": 200,
                "query_types": {
                    "A": 150,
                    "AAAA": 30,
                    "MX": 15,
                    "PTR": 5
                },
                "top_domains": [
                    {"domain": "example.com", "queries": 50},
                    {"domain": "google.com", "queries": 40},
                    {"domain": "github.com", "queries": 30}
                ]
            }
        },
        "security_analysis": {
            "suspicious_ips": [
                {
                    "ip": "10.0.0.1",
                    "reason": "Multiple failed connections",
                    "severity": "high",
                    "count": 10
                },
                {
                    "ip": "192.168.1.50",
                    "reason": "Port scanning detected",
                    "severity": "medium",
                    "count": 5
                }
            ],
            "port_scans": [
                {
                    "scanner_ip": "192.168.1.50",
                    "target_ip": "192.168.1.100",
                    "ports_scanned": 1000,
                    "scan_type": "TCP SYN scan"
                }
            ],
            "anomalies": [
                {
                    "type": "Unusual traffic pattern",
                    "description": "High traffic volume from single IP",
                    "severity": "low",
                    "timestamp": "2024-01-01T12:15:00Z"
                },
                {
                    "type": "Protocol anomaly",
                    "description": "Unexpected protocol usage",
                    "severity": "medium",
                    "timestamp": "2024-01-01T12:20:00Z"
                }
            ]
        },
        "performance_metrics": {
            "top_talkers": [
                {
                    "ip": "192.168.1.100",
                    "bytes_sent": 2048000,
                    "bytes_received": 1024000,
                    "total_bytes": 3072000
                },
                {
                    "ip": "10.0.0.1",
                    "bytes_sent": 1536000,
                    "bytes_received": 768000,
                    "total_bytes": 2304000
                }
            ],
            "bandwidth_usage": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "bytes_per_second": 1024000
                },
                {
                    "timestamp": "2024-01-01T12:10:00Z",
                    "bytes_per_second": 1536000
                }
            ],
            "packet_rate": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "packets_per_second": 1000
                },
                {
                    "timestamp": "2024-01-01T12:10:00Z",
                    "packets_per_second": 1500
                }
            ]
        }
    }


def test_pdf_export_service():
    """Test the PDF export service."""
    print("="*80)
    print("TESTING PDF EXPORT SERVICE")
    print("="*80)
    
    service = PDFExportService()
    test_data = create_test_report_data()
    
    try:
        print("🔍 Generating PDF with PDFExportService...")
        pdf_bytes = service.generate_pdf_report(test_data)
        
        print(f"✅ PDF generated successfully!")
        print(f"📊 PDF size: {len(pdf_bytes):,} bytes")
        
        # Validate PDF
        validator = PDFValidator()
        result = validator.validate_pdf_bytes(pdf_bytes)
        
        print(f"🔍 PDF Validation Result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
        
        if result.errors:
            print("❌ Errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if result.info:
            print("📋 Info:")
            for key, value in result.info.items():
                print(f"  - {key}: {value}")
        
        # Diagnose corruption
        diagnosis = diagnose_pdf_corruption(pdf_bytes)
        if diagnosis["corruption_detected"]:
            print(f"🚨 CORRUPTION DETECTED: {diagnosis['corruption_type']}")
            print("Details:", diagnosis["corruption_details"])
            print("Suggestions:", diagnosis["repair_suggestions"])
        else:
            print("✅ No corruption detected")
        
        # Save to file for manual inspection
        test_file = f"/tmp/test_pdf_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        with open(test_file, 'wb') as f:
            f.write(pdf_bytes)
        print(f"💾 PDF saved to: {test_file}")
        
        return True, pdf_bytes
        
    except Exception as e:
        print(f"❌ PDF generation failed: {str(e)}")
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False, None


def test_simple_pdf_service():
    """Test the simple PDF service."""
    print("\n" + "="*80)
    print("TESTING SIMPLE PDF SERVICE")
    print("="*80)
    
    service = SimplePDFExportService()
    test_data = create_test_report_data()
    
    try:
        print("🔍 Generating text report with SimplePDFExportService...")
        text_bytes = service.generate_pdf_report(test_data)
        
        print(f"✅ Text report generated successfully!")
        print(f"📊 Report size: {len(text_bytes):,} bytes")
        
        # Check content
        text_content = text_bytes.decode('utf-8')
        print(f"📝 Content preview (first 200 chars):")
        print(text_content[:200])
        
        # Validate as text
        if 'PCAP ANALYSIS REPORT' in text_content:
            print("✅ Text report contains expected header")
        else:
            print("❌ Text report missing expected header")
        
        if 'test_corruption.pcap' in text_content:
            print("✅ Text report contains filename")
        else:
            print("❌ Text report missing filename")
        
        # Save to file for manual inspection
        test_file = f"/tmp/test_simple_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(test_file, 'wb') as f:
            f.write(text_bytes)
        print(f"💾 Text report saved to: {test_file}")
        
        return True, text_bytes
        
    except Exception as e:
        print(f"❌ Text report generation failed: {str(e)}")
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False, None


def test_html_generation():
    """Test HTML generation separately."""
    print("\n" + "="*80)
    print("TESTING HTML GENERATION")
    print("="*80)
    
    service = PDFExportService()
    test_data = create_test_report_data()
    
    try:
        print("🔍 Generating HTML template...")
        html_content = service.generate_html_template(test_data)
        
        print(f"✅ HTML generated successfully!")
        print(f"📊 HTML size: {len(html_content):,} characters")
        
        # Validate HTML structure
        if '<html' in html_content and '</html>' in html_content:
            print("✅ HTML has proper html tags")
        else:
            print("❌ HTML missing proper html tags")
        
        if '<body>' in html_content and '</body>' in html_content:
            print("✅ HTML has proper body tags")
        else:
            print("❌ HTML missing proper body tags")
        
        if 'test_corruption.pcap' in html_content:
            print("✅ HTML contains filename")
        else:
            print("❌ HTML missing filename")
        
        # Save HTML for inspection
        test_file = f"/tmp/test_html_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"💾 HTML saved to: {test_file}")
        
        return True, html_content
        
    except Exception as e:
        print(f"❌ HTML generation failed: {str(e)}")
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False, None


def test_reportlab_direct():
    """Test ReportLab PDF generation directly."""
    print("\n" + "="*80)
    print("TESTING REPORTLAB DIRECT")
    print("="*80)
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO
        
        print("🔍 Testing ReportLab directly...")
        
        # Create a BytesIO buffer
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Add content
        story.append(Paragraph("PCAP Analysis Report", styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Test report generated by ReportLab", styles['Normal']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("This is a test to verify ReportLab PDF generation", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        
        print(f"✅ ReportLab PDF generated successfully!")
        print(f"📊 PDF size: {len(pdf_bytes):,} bytes")
        
        # Validate PDF
        validator = PDFValidator()
        result = validator.validate_pdf_bytes(pdf_bytes)
        
        print(f"🔍 PDF Validation Result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
        
        if result.errors:
            print("❌ Errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        # Save to file
        test_file = f"/tmp/test_reportlab_direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        with open(test_file, 'wb') as f:
            f.write(pdf_bytes)
        print(f"💾 ReportLab PDF saved to: {test_file}")
        
        return True, pdf_bytes
        
    except Exception as e:
        print(f"❌ ReportLab direct test failed: {str(e)}")
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False, None


def test_export_endpoint_conversion():
    """Test the export endpoint conversion function."""
    print("\n" + "="*80)
    print("TESTING EXPORT ENDPOINT CONVERSION")
    print("="*80)
    
    try:
        from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
        
        # Mock MongoDB report
        mongo_report = {
            "job_id": "test_mongo_123",
            "filename": "mongo_test.pcap",
            "original_filename": "mongo_test.pcap",
            "status": "completed",
            "file_size": 1024000,
            "created_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:30:00Z",
            "file_hash": "mongo123test456",
            "processing_time": 45.2,
            "analysis_results": {
                "traffic_stats": {
                    "total_packets": 5000,
                    "duration": 300.5,
                    "unique_ips": 50,
                    "unique_ports": 100,
                    "total_bytes": 2560000
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
                        "packet_count": 500,
                        "bytes": 256000
                    }
                ],
                "network_issues": [
                    {
                        "type": "suspicious_activity",
                        "description": "Multiple failed connections",
                        "severity": "medium",
                        "details": {"ip": "10.0.0.1"}
                    }
                ]
            }
        }
        
        print("🔍 Converting MongoDB report to PDF format...")
        pdf_data = _convert_mongodb_report_to_pdf_format(mongo_report)
        
        print(f"✅ Conversion successful!")
        print(f"📊 Converted data keys: {list(pdf_data.keys())}")
        
        # Validate conversion
        expected_keys = ['job_id', 'filename', 'status', 'total_packets', 'protocols']
        for key in expected_keys:
            if key in pdf_data:
                print(f"✅ {key}: {pdf_data[key]}")
            else:
                print(f"❌ Missing key: {key}")
        
        # Test with PDF service
        print("🔍 Testing converted data with PDF service...")
        service = PDFExportService()
        pdf_bytes = service.generate_pdf_report(pdf_data)
        
        print(f"✅ PDF generation with converted data successful!")
        print(f"📊 PDF size: {len(pdf_bytes):,} bytes")
        
        # Save to file
        test_file = f"/tmp/test_converted_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        with open(test_file, 'wb') as f:
            f.write(pdf_bytes)
        print(f"💾 Converted PDF saved to: {test_file}")
        
        return True, pdf_bytes
        
    except Exception as e:
        print(f"❌ Export endpoint conversion test failed: {str(e)}")
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False, None


def main():
    """Run all PDF corruption tests."""
    print("🧪 PCAP REPORTER PDF CORRUPTION DETECTION TESTS")
    print("🕒 Started at:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*80)
    
    test_results = {}
    
    # Test 1: PDF Export Service
    success, data = test_pdf_export_service()
    test_results['pdf_service'] = success
    
    # Test 2: Simple PDF Service
    success, data = test_simple_pdf_service()
    test_results['simple_service'] = success
    
    # Test 3: HTML Generation
    success, data = test_html_generation()
    test_results['html_generation'] = success
    
    # Test 4: ReportLab Direct
    success, data = test_reportlab_direct()
    test_results['reportlab_direct'] = success
    
    # Test 5: Export Endpoint Conversion
    success, data = test_export_endpoint_conversion()
    test_results['endpoint_conversion'] = success
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PDF generation is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("💡 Common issues:")
        print("   - Missing dependencies (ReportLab)")
        print("   - Incorrect content type in response")
        print("   - Template rendering issues")
        print("   - File encoding problems")
    
    print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)