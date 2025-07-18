#!/usr/bin/env python3
"""
FOCUSED PDF CORRUPTION TEST
Tests the actual PDF generation without database dependency
to identify the exact corruption source.
"""

import os
import sys
import tempfile
import hashlib
import subprocess
import struct
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class FocusedPDFCorruptionTest:
    """Focused test to identify PDF corruption without database dependency."""
    
    def __init__(self):
        """Initialize the test."""
        self.test_results = []
        self.generated_files = []
        self.corruption_points = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", files: List[str] = None):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] {status} {test_name}")
        if details:
            print(f"    Details: {details}")
        if files:
            for file_path in files:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    print(f"    File: {file_path} ({size} bytes)")
        
        self.test_results.append({
            "name": test_name,
            "success": success,
            "details": details,
            "files": files or [],
            "timestamp": timestamp
        })
    
    def create_realistic_analysis_results(self) -> Dict[str, Any]:
        """Create realistic analysis results that would come from a real PCAP."""
        return {
            "file_path": "/tmp/real_network_traffic.pcap",
            "file_size": 8724,
            "analysis_timestamp": datetime.now().isoformat(),
            "traffic_stats": {
                "total_packets": 1000,
                "total_bytes": 1048576,
                "duration": 300.5,
                "packets_per_second": 3.33,
                "bytes_per_second": 3495.17
            },
            "protocol_stats": {
                "tcp_packets": 600,
                "udp_packets": 300,
                "icmp_packets": 50,
                "http_sessions": 25,
                "https_sessions": 15,
                "dns_queries": 10
            },
            "issues": [
                {
                    "type": "high_latency",
                    "severity": "medium",
                    "description": "High latency detected on connection 192.168.1.1:80",
                    "affected_hosts": ["192.168.1.1", "192.168.1.100"],
                    "count": 5
                },
                {
                    "type": "tcp_errors",
                    "severity": "low",
                    "description": "TCP retransmissions detected",
                    "affected_hosts": ["192.168.1.50"],
                    "count": 3
                }
            ],
            "top_conversations": [
                {
                    "src_ip": "192.168.1.100",
                    "dst_ip": "192.168.1.1",
                    "src_port": 12345,
                    "dst_port": 80,
                    "protocol": "TCP",
                    "packets_sent": 150,
                    "packets_received": 140,
                    "bytes_sent": 102400,
                    "bytes_received": 204800,
                    "duration": 45.2
                },
                {
                    "src_ip": "192.168.1.100",
                    "dst_ip": "8.8.8.8",
                    "src_port": 54321,
                    "dst_port": 53,
                    "protocol": "UDP",
                    "packets_sent": 10,
                    "packets_received": 10,
                    "bytes_sent": 800,
                    "bytes_received": 1200,
                    "duration": 0.5
                }
            ],
            "start_time": "2024-01-01T12:00:00Z",
            "end_time": "2024-01-01T12:05:00Z",
            "processing_time": 15.7
        }
    
    def create_realistic_report_data(self) -> Dict[str, Any]:
        """Create realistic report data structure."""
        analysis_results = self.create_realistic_analysis_results()
        
        return {
            "_id": "focused-test-report-123",
            "original_filename": "real_network_traffic.pcap",
            "status": "completed",
            "file_size": 8724,
            "file_hash": "abc123def456789",
            "created_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:05:15Z",
            "processing_time": 15.7,
            "analysis_results": analysis_results
        }
    
    def test_data_conversion(self, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Test the data conversion step."""
        try:
            from api.v1.endpoints.reports import _convert_report_for_pdf
            
            pdf_data = _convert_report_for_pdf(report_data)
            
            # Save converted data for inspection
            converted_file = "/tmp/focused_converted_data.json"
            with open(converted_file, 'w') as f:
                json.dump(pdf_data, f, indent=2, default=str)
            self.generated_files.append(converted_file)
            
            # Validate conversion
            required_fields = ['job_id', 'filename', 'total_packets', 'protocols']
            missing_fields = [field for field in required_fields if field not in pdf_data]
            
            if missing_fields:
                self.log_test("Data Conversion", False, f"Missing fields: {missing_fields}")
                return None
            
            self.log_test("Data Conversion", True, 
                         f"Converted {len(str(report_data))} → {len(str(pdf_data))} chars", 
                         [converted_file])
            
            return pdf_data
            
        except Exception as e:
            self.log_test("Data Conversion", False, f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_html_generation(self, pdf_data: Dict[str, Any]) -> Optional[str]:
        """Test HTML template generation."""
        try:
            from services.pdf_export import PDFExportService
            
            service = PDFExportService()
            html_content = service.generate_html_template(pdf_data)
            
            # Save HTML for inspection
            html_file = "/tmp/focused_html_template.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.generated_files.append(html_file)
            
            # Validate HTML structure
            validations = [
                ("DOCTYPE", "<!DOCTYPE" in html_content),
                ("HTML tags", "<html" in html_content and "</html>" in html_content),
                ("CSS styles", "<style>" in html_content),
                ("Report title", "PCAP Analysis Report" in html_content),
                ("Filename", pdf_data.get('filename', '') in html_content),
                ("Protocol data", "protocol" in html_content.lower()),
                ("Traffic stats", str(pdf_data.get('total_packets', 0)) in html_content)
            ]
            
            passed = sum(1 for _, check in validations if check)
            all_passed = passed == len(validations)
            
            self.log_test("HTML Generation", all_passed, 
                         f"Generated {len(html_content)} chars, validations: {passed}/{len(validations)}", 
                         [html_file])
            
            if not all_passed:
                failed = [name for name, check in validations if not check]
                self.log_test("HTML Validation Failures", False, f"Failed: {', '.join(failed)}")
            
            return html_content if all_passed else None
            
        except Exception as e:
            self.log_test("HTML Generation", False, f"HTML generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_pdf_generation_methods(self, html_content: str) -> Dict[str, bytes]:
        """Test different PDF generation methods."""
        pdf_results = {}
        
        # Method 1: ReportLab (current implementation)
        print(f"\n🔍 Testing ReportLab method...")
        try:
            from services.pdf_export import PDFExportService
            
            service = PDFExportService()
            pdf_bytes = service._fallback_pdf_generation(html_content)
            
            # Save PDF
            reportlab_file = "/tmp/focused_reportlab.pdf"
            with open(reportlab_file, 'wb') as f:
                f.write(pdf_bytes)
            self.generated_files.append(reportlab_file)
            
            # Validate PDF
            valid_structure = (
                pdf_bytes.startswith(b'%PDF-') and 
                b'%%EOF' in pdf_bytes and
                len(pdf_bytes) > 1000
            )
            
            if valid_structure:
                self.log_test("ReportLab PDF", True, 
                             f"Generated {len(pdf_bytes)} bytes", [reportlab_file])
                pdf_results['reportlab'] = pdf_bytes
            else:
                self.log_test("ReportLab PDF", False, "Invalid PDF structure")
                self.corruption_points.append("ReportLab PDF Generation")
                
        except Exception as e:
            self.log_test("ReportLab PDF", False, f"ReportLab failed: {e}")
            self.corruption_points.append("ReportLab PDF Generation")
        
        # Method 2: WeasyPrint
        print(f"\n🔍 Testing WeasyPrint method...")
        try:
            import weasyprint
            
            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
            
            # Save PDF
            weasyprint_file = "/tmp/focused_weasyprint.pdf"
            with open(weasyprint_file, 'wb') as f:
                f.write(pdf_bytes)
            self.generated_files.append(weasyprint_file)
            
            # Validate PDF
            valid_structure = (
                pdf_bytes.startswith(b'%PDF-') and 
                b'%%EOF' in pdf_bytes and
                len(pdf_bytes) > 1000
            )
            
            if valid_structure:
                self.log_test("WeasyPrint PDF", True, 
                             f"Generated {len(pdf_bytes)} bytes", [weasyprint_file])
                pdf_results['weasyprint'] = pdf_bytes
            else:
                self.log_test("WeasyPrint PDF", False, "Invalid PDF structure")
                
        except Exception as e:
            self.log_test("WeasyPrint PDF", False, f"WeasyPrint failed: {e}")
        
        # Method 3: xhtml2pdf
        print(f"\n🔍 Testing xhtml2pdf method...")
        try:
            from xhtml2pdf import pisa
            from io import BytesIO
            
            output = BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=output)
            
            if not pisa_status.err:
                pdf_bytes = output.getvalue()
                
                # Save PDF
                pisa_file = "/tmp/focused_pisa.pdf"
                with open(pisa_file, 'wb') as f:
                    f.write(pdf_bytes)
                self.generated_files.append(pisa_file)
                
                # Validate PDF
                valid_structure = (
                    pdf_bytes.startswith(b'%PDF-') and 
                    b'%%EOF' in pdf_bytes and
                    len(pdf_bytes) > 1000
                )
                
                if valid_structure:
                    self.log_test("xhtml2pdf PDF", True, 
                                 f"Generated {len(pdf_bytes)} bytes", [pisa_file])
                    pdf_results['pisa'] = pdf_bytes
                else:
                    self.log_test("xhtml2pdf PDF", False, "Invalid PDF structure")
            else:
                self.log_test("xhtml2pdf PDF", False, f"pisa errors: {pisa_status.err}")
                
        except Exception as e:
            self.log_test("xhtml2pdf PDF", False, f"xhtml2pdf failed: {e}")
        
        return pdf_results
    
    def test_streaming_response(self, pdf_bytes: bytes) -> bytes:
        """Test streaming response behavior."""
        try:
            from fastapi.responses import StreamingResponse
            
            # Test the current implementation
            response = StreamingResponse(
                iter([pdf_bytes]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=focused_test.pdf",
                    "Content-Length": str(len(pdf_bytes))
                }
            )
            
            # Simulate streaming
            streamed_content = b""
            for chunk in iter([pdf_bytes]):
                streamed_content += chunk
            
            # Save streamed content
            streamed_file = "/tmp/focused_streamed.pdf"
            with open(streamed_file, 'wb') as f:
                f.write(streamed_content)
            self.generated_files.append(streamed_file)
            
            # Compare byte-by-byte
            if streamed_content == pdf_bytes:
                self.log_test("Streaming Response", True, 
                             f"Streamed {len(streamed_content)} bytes", [streamed_file])
            else:
                self.log_test("Streaming Response", False, 
                             f"Content mismatch: {len(pdf_bytes)} → {len(streamed_content)}")
                self.corruption_points.append("Streaming Response")
                
                # Find first difference
                for i, (orig, streamed) in enumerate(zip(pdf_bytes, streamed_content)):
                    if orig != streamed:
                        self.log_test("Streaming Corruption Point", False, 
                                     f"First difference at byte {i}: {orig} → {streamed}")
                        break
            
            return streamed_content
            
        except Exception as e:
            self.log_test("Streaming Response", False, f"Streaming failed: {e}")
            return pdf_bytes
    
    def test_http_response_simulation(self, pdf_bytes: bytes) -> bytes:
        """Simulate HTTP response creation."""
        try:
            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from fastapi.responses import StreamingResponse
            
            app = FastAPI()
            
            @app.get("/test-pdf")
            async def test_pdf():
                return StreamingResponse(
                    iter([pdf_bytes]),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": "attachment; filename=focused_test.pdf",
                        "Content-Length": str(len(pdf_bytes))
                    }
                )
            
            client = TestClient(app)
            response = client.get("/test-pdf")
            
            if response.status_code == 200:
                http_content = response.content
                
                # Save HTTP response
                http_file = "/tmp/focused_http_response.pdf"
                with open(http_file, 'wb') as f:
                    f.write(http_content)
                self.generated_files.append(http_file)
                
                # Validate response
                content_type = response.headers.get('content-type', '')
                content_length = response.headers.get('content-length', '')
                
                if http_content == pdf_bytes:
                    self.log_test("HTTP Response", True, 
                                 f"HTTP response {len(http_content)} bytes, type: {content_type}", 
                                 [http_file])
                else:
                    self.log_test("HTTP Response", False, 
                                 f"HTTP content mismatch: {len(pdf_bytes)} → {len(http_content)}")
                    self.corruption_points.append("HTTP Response")
                
                return http_content
                
            else:
                self.log_test("HTTP Response", False, f"HTTP error: {response.status_code}")
                return pdf_bytes
                
        except Exception as e:
            self.log_test("HTTP Response", False, f"HTTP simulation failed: {e}")
            return pdf_bytes
    
    def test_binary_integrity(self, pdf_files: Dict[str, str]) -> None:
        """Test binary integrity of generated PDFs."""
        try:
            file_info = {}
            
            for method, file_path in pdf_files.items():
                if not os.path.exists(file_path):
                    continue
                
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Calculate hash
                file_hash = hashlib.md5(content).hexdigest()
                
                # Check structure
                structure_tests = [
                    ("PDF Header", content.startswith(b'%PDF-')),
                    ("PDF Trailer", b'%%EOF' in content),
                    ("PDF Objects", b'obj' in content and b'endobj' in content),
                    ("PDF Catalog", b'/Catalog' in content),
                    ("PDF Pages", b'/Pages' in content),
                    ("Minimum Size", len(content) > 1000)
                ]
                
                passed = sum(1 for _, test in structure_tests if test)
                all_passed = passed == len(structure_tests)
                
                file_info[method] = {
                    'hash': file_hash,
                    'size': len(content),
                    'valid': all_passed
                }
                
                self.log_test(f"Binary Integrity ({method})", all_passed, 
                             f"Hash: {file_hash[:8]}..., Size: {len(content)}, Tests: {passed}/{len(structure_tests)}")
                
                if not all_passed:
                    failed = [name for name, test in structure_tests if not test]
                    self.log_test(f"Structure Failures ({method})", False, f"Failed: {', '.join(failed)}")
                    self.corruption_points.append(f"Binary Integrity ({method})")
            
            # Compare hashes
            hashes = [info['hash'] for info in file_info.values()]
            unique_hashes = set(hashes)
            
            if len(unique_hashes) == 1:
                self.log_test("Hash Consistency", True, "All files have identical hashes")
            else:
                self.log_test("Hash Consistency", False, "Files have different hashes")
                for method, info in file_info.items():
                    self.log_test(f"Hash ({method})", True, f"{info['hash']}")
                    
        except Exception as e:
            self.log_test("Binary Integrity", False, f"Binary test failed: {e}")
    
    def test_external_validation(self, pdf_files: Dict[str, str]) -> None:
        """Test PDFs with external validation tools."""
        try:
            for method, file_path in pdf_files.items():
                if not os.path.exists(file_path):
                    continue
                
                # Test with system file command
                try:
                    result = subprocess.run(['file', file_path], capture_output=True, text=True)
                    if "PDF" in result.stdout:
                        self.log_test(f"File Command ({method})", True, result.stdout.strip())
                    else:
                        self.log_test(f"File Command ({method})", False, result.stdout.strip())
                except:
                    self.log_test(f"File Command ({method})", False, "file command not available")
                
                # Test with pdfinfo if available
                try:
                    result = subprocess.run(['pdfinfo', file_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        # Extract key info
                        info = {}
                        for line in result.stdout.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                info[key.strip()] = value.strip()
                        
                        pages = info.get('Pages', 'unknown')
                        self.log_test(f"pdfinfo ({method})", True, f"Pages: {pages}")
                    else:
                        self.log_test(f"pdfinfo ({method})", False, result.stderr.strip())
                        self.corruption_points.append(f"pdfinfo validation ({method})")
                except:
                    self.log_test(f"pdfinfo ({method})", False, "pdfinfo not available")
                    
        except Exception as e:
            self.log_test("External Validation", False, f"External validation failed: {e}")
    
    def generate_report(self) -> None:
        """Generate comprehensive test report."""
        print("\n" + "="*80)
        print("🔍 FOCUSED PDF CORRUPTION TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 TEST STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} [{result['timestamp']}] {result['name']}")
            if result['details']:
                print(f"       {result['details']}")
        
        print(f"\n🚨 CORRUPTION POINTS:")
        if self.corruption_points:
            for i, point in enumerate(self.corruption_points, 1):
                print(f"   {i}. {point}")
        else:
            print("   ✅ No corruption points detected")
        
        print(f"\n📄 GENERATED FILES:")
        for file_path in self.generated_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   • {file_path} ({size} bytes)")
        
        print(f"\n🎯 ANALYSIS:")
        if failed_tests == 0:
            print("   ✅ All tests passed - PDF generation pipeline is working")
        else:
            print("   ❌ Issues found in PDF generation pipeline")
            
        if self.corruption_points:
            print(f"\n💡 FOCUS AREAS:")
            print("   The following areas need immediate attention:")
            for point in self.corruption_points:
                print(f"   • {point}")
        else:
            print(f"\n💡 CONCLUSION:")
            print("   The PDF generation pipeline appears to be working correctly.")
            print("   If users report corruption, investigate client-side factors.")
    
    def run_focused_test(self) -> bool:
        """Run the focused PDF corruption test."""
        print("🔍 FOCUSED PDF CORRUPTION TEST")
        print("="*80)
        print("Testing PDF generation pipeline with realistic data...")
        
        # Step 1: Create realistic report data
        print("\n📊 Step 1: Creating realistic report data...")
        report_data = self.create_realistic_report_data()
        self.log_test("Report Data Creation", True, f"Created data with {len(str(report_data))} characters")
        
        # Step 2: Test data conversion
        print("\n🔄 Step 2: Testing data conversion...")
        pdf_data = self.test_data_conversion(report_data)
        if not pdf_data:
            return False
        
        # Step 3: Test HTML generation
        print("\n📄 Step 3: Testing HTML generation...")
        html_content = self.test_html_generation(pdf_data)
        if not html_content:
            return False
        
        # Step 4: Test PDF generation methods
        print("\n🖨️  Step 4: Testing PDF generation methods...")
        pdf_results = self.test_pdf_generation_methods(html_content)
        if not pdf_results:
            return False
        
        # Step 5: Test streaming response
        print("\n📡 Step 5: Testing streaming response...")
        if 'reportlab' in pdf_results:
            streamed_content = self.test_streaming_response(pdf_results['reportlab'])
        
        # Step 6: Test HTTP response
        print("\n🌐 Step 6: Testing HTTP response...")
        if 'reportlab' in pdf_results:
            http_content = self.test_http_response_simulation(pdf_results['reportlab'])
        
        # Step 7: Test binary integrity
        print("\n🔢 Step 7: Testing binary integrity...")
        pdf_files = {
            'reportlab': '/tmp/focused_reportlab.pdf',
            'weasyprint': '/tmp/focused_weasyprint.pdf',
            'pisa': '/tmp/focused_pisa.pdf',
            'streamed': '/tmp/focused_streamed.pdf',
            'http': '/tmp/focused_http_response.pdf'
        }
        self.test_binary_integrity(pdf_files)
        
        # Step 8: External validation
        print("\n🔍 Step 8: External validation...")
        self.test_external_validation(pdf_files)
        
        # Step 9: Generate report
        print("\n📊 Step 9: Generating report...")
        self.generate_report()
        
        return len(self.corruption_points) == 0

def main():
    """Main function."""
    tester = FocusedPDFCorruptionTest()
    
    try:
        success = tester.run_focused_test()
        
        if success:
            print("\n🎉 FOCUSED TEST COMPLETED - NO CORRUPTION FOUND!")
        else:
            print("\n🚨 FOCUSED TEST FOUND CORRUPTION ISSUES!")
            
        return success
        
    except Exception as e:
        print(f"\n💥 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)