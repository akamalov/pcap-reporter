#!/usr/bin/env python3
"""
Comprehensive PCAP to PDF testing framework.
This will test the entire pipeline from PCAP file analysis to PDF generation.
"""

import asyncio
import os
import tempfile
import struct
from datetime import datetime
from pathlib import Path
import sys

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class ComprehensivePcapPdfTester:
    """Comprehensive testing framework for PCAP to PDF generation."""
    
    def __init__(self):
        """Initialize the tester."""
        self.test_results = []
        self.created_files = []
        
    def log_test(self, test_name, success, message="", details=None):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        if details:
            for detail in details:
                print(f"   • {detail}")
        
        self.test_results.append({
            "name": test_name,
            "success": success,
            "message": message,
            "details": details or []
        })
    
    def create_sample_pcap(self, filename="test_sample.pcap"):
        """Create a minimal valid PCAP file for testing."""
        pcap_path = f"/tmp/{filename}"
        
        try:
            # PCAP Global Header (24 bytes)
            global_header = struct.pack(
                '<IHHIIII',
                0xa1b2c3d4,  # Magic number
                2,           # Version major
                4,           # Version minor
                0,           # Thiszone (GMT)
                0,           # Sigfigs
                65535,       # Snaplen
                1            # Network (Ethernet)
            )
            
            # Create a simple Ethernet frame
            # Ethernet header (14 bytes) + IP header (20 bytes) + TCP header (20 bytes)
            ethernet_dst = b'\x00\x01\x02\x03\x04\x05'  # Destination MAC
            ethernet_src = b'\x00\x06\x07\x08\x09\x0a'  # Source MAC
            ethernet_type = struct.pack('>H', 0x0800)    # IP type
            
            # IP header (simplified)
            ip_header = struct.pack(
                '>BBHHHBBH4s4s',
                0x45,        # Version + IHL
                0,           # Type of Service
                40,          # Total Length
                0,           # Identification
                0,           # Flags + Fragment Offset
                64,          # TTL
                6,           # Protocol (TCP)
                0,           # Checksum (0 for now)
                struct.pack('>I', 0xc0a80101),  # Source IP (192.168.1.1)
                struct.pack('>I', 0xc0a80102)   # Dest IP (192.168.1.2)
            )
            
            # TCP header (simplified)
            tcp_header = struct.pack(
                '>HHLLBBHHH',
                80,          # Source Port
                8080,        # Destination Port
                0,           # Sequence Number
                0,           # Acknowledgment Number
                0x50,        # Data Offset + Reserved
                0x02,        # Flags (SYN)
                8192,        # Window Size
                0,           # Checksum
                0            # Urgent Pointer
            )
            
            # Complete packet
            packet_data = ethernet_dst + ethernet_src + ethernet_type + ip_header + tcp_header
            
            # Packet record header
            timestamp = int(datetime.now().timestamp())
            packet_header = struct.pack(
                '<IIII',
                timestamp,              # Timestamp seconds
                0,                      # Timestamp microseconds
                len(packet_data),       # Captured packet length
                len(packet_data)        # Original packet length
            )
            
            # Write PCAP file
            with open(pcap_path, 'wb') as f:
                f.write(global_header)
                # Write multiple packets for better testing
                for i in range(100):
                    f.write(packet_header)
                    f.write(packet_data)
            
            self.created_files.append(pcap_path)
            return pcap_path
            
        except Exception as e:
            self.log_test("Create Sample PCAP", False, f"Failed to create PCAP: {e}")
            return None
    
    async def test_pcap_analysis_service(self, pcap_path):
        """Test the PCAP analysis service."""
        print("\n🔍 Testing PCAP Analysis Service...")
        
        try:
            from services.pcap_analysis_service import PcapAnalysisService
            
            service = PcapAnalysisService()
            results = await service.analyze_pcap_file(pcap_path)
            
            details = [
                f"Total packets: {results.traffic_stats.total_packets}",
                f"Total bytes: {results.traffic_stats.total_bytes}",
                f"Duration: {results.traffic_stats.duration}s",
                f"Top protocols: {len(results.top_protocols)}",
                f"Network issues: {len(results.network_issues)}",
                f"TCP conversations: {len(results.top_tcp_conversations)}"
            ]
            
            success = (
                results.traffic_stats.total_packets > 0 and
                results.traffic_stats.total_bytes > 0 and
                len(results.top_protocols) > 0
            )
            
            self.log_test("PCAP Analysis Service", success, "Analysis completed", details)
            return results if success else None
            
        except Exception as e:
            self.log_test("PCAP Analysis Service", False, f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def test_report_data_conversion(self, analysis_results):
        """Test converting analysis results to report data format."""
        print("\n🔍 Testing Report Data Conversion...")
        
        try:
            from api.v1.endpoints.reports import _convert_report_for_pdf
            
            # Create mock report data structure
            report_data = {
                "_id": "test-comprehensive-analysis",
                "original_filename": "test_sample.pcap",
                "status": "completed",
                "file_size": 2048,
                "file_hash": "test123hash",
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:30:00Z",
                "processing_time": 300.0,
                "analysis_results": analysis_results.dict()
            }
            
            # Convert to PDF format
            pdf_data = _convert_report_for_pdf(report_data)
            
            details = [
                f"Job ID: {pdf_data.get('job_id', 'Missing')}",
                f"Filename: {pdf_data.get('filename', 'Missing')}",
                f"Total packets: {pdf_data.get('total_packets', 0)}",
                f"Protocols: {len(pdf_data.get('protocols', {}))}",
                f"Has protocol analysis: {'protocol_analysis' in pdf_data}",
                f"Has security analysis: {'security_analysis' in pdf_data}",
                f"Has performance metrics: {'performance_metrics' in pdf_data}"
            ]
            
            success = (
                'job_id' in pdf_data and
                'filename' in pdf_data and
                'total_packets' in pdf_data and
                pdf_data['total_packets'] > 0
            )
            
            self.log_test("Report Data Conversion", success, "Conversion completed", details)
            return pdf_data if success else None
            
        except Exception as e:
            self.log_test("Report Data Conversion", False, f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_html_template_generation(self, pdf_data):
        """Test HTML template generation."""
        print("\n🔍 Testing HTML Template Generation...")
        
        try:
            from services.pdf_export import PDFExportService
            
            service = PDFExportService()
            html_content = service.generate_html_template(pdf_data)
            
            details = [
                f"HTML length: {len(html_content)} characters",
                f"Contains CSS: {'<style>' in html_content}",
                f"Contains header: {'PCAP Analysis Report' in html_content}",
                f"Contains filename: {pdf_data.get('filename', 'unknown') in html_content}",
                f"Contains protocol data: {'protocol' in html_content.lower()}",
                f"Contains security section: {'security' in html_content.lower()}"
            ]
            
            success = (
                len(html_content) > 1000 and
                '<html' in html_content and
                '</html>' in html_content and
                'PCAP Analysis Report' in html_content
            )
            
            self.log_test("HTML Template Generation", success, "Template generated", details)
            
            # Save HTML for inspection
            html_path = "/tmp/test_comprehensive_report.html"
            with open(html_path, 'w') as f:
                f.write(html_content)
            self.created_files.append(html_path)
            
            return html_content if success else None
            
        except Exception as e:
            self.log_test("HTML Template Generation", False, f"Template generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_pdf_generation_methods(self, html_content):
        """Test different PDF generation methods."""
        print("\n🔍 Testing PDF Generation Methods...")
        
        from services.pdf_export import PDFExportService
        
        service = PDFExportService()
        
        # Test 1: ReportLab fallback method (current implementation)
        try:
            pdf_bytes_reportlab = service._fallback_pdf_generation(html_content)
            
            details = [
                f"PDF size: {len(pdf_bytes_reportlab)} bytes",
                f"PDF signature: {pdf_bytes_reportlab[:10]}",
                f"Starts with %PDF: {pdf_bytes_reportlab.startswith(b'%PDF-')}",
                f"Contains ReportLab: {b'ReportLab' in pdf_bytes_reportlab}"
            ]
            
            success = (
                len(pdf_bytes_reportlab) > 1000 and
                pdf_bytes_reportlab.startswith(b'%PDF-')
            )
            
            self.log_test("ReportLab PDF Generation", success, "ReportLab method", details)
            
            if success:
                # Save PDF for inspection
                pdf_path = "/tmp/test_comprehensive_reportlab.pdf"
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes_reportlab)
                self.created_files.append(pdf_path)
                
                return pdf_bytes_reportlab
            
        except Exception as e:
            self.log_test("ReportLab PDF Generation", False, f"ReportLab failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Try WeasyPrint method
        try:
            import weasyprint
            
            pdf_bytes_weasyprint = weasyprint.HTML(string=html_content).write_pdf()
            
            details = [
                f"PDF size: {len(pdf_bytes_weasyprint)} bytes",
                f"PDF signature: {pdf_bytes_weasyprint[:10]}",
                f"Starts with %PDF: {pdf_bytes_weasyprint.startswith(b'%PDF-')}"
            ]
            
            success = (
                len(pdf_bytes_weasyprint) > 1000 and
                pdf_bytes_weasyprint.startswith(b'%PDF-')
            )
            
            self.log_test("WeasyPrint PDF Generation", success, "WeasyPrint method", details)
            
            if success:
                # Save PDF for inspection
                pdf_path = "/tmp/test_comprehensive_weasyprint.pdf"
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes_weasyprint)
                self.created_files.append(pdf_path)
                
                return pdf_bytes_weasyprint
            
        except Exception as e:
            self.log_test("WeasyPrint PDF Generation", False, f"WeasyPrint failed: {e}")
        
        return None
    
    def test_pdf_validation(self, pdf_bytes, method_name):
        """Test PDF validation using our validator."""
        print(f"\n🔍 Testing PDF Validation ({method_name})...")
        
        try:
            sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
            from pdf_validator import PDFValidator
            
            validator = PDFValidator()
            validation_result = validator.validate_pdf_bytes(pdf_bytes)
            
            details = [
                f"Is valid: {validation_result.is_valid}",
                f"PDF version: {validation_result.pdf_version}",
                f"Page count: {validation_result.page_count}",
                f"File size: {validation_result.file_size} bytes",
                f"Issues found: {len(validation_result.issues)}"
            ]
            
            if validation_result.issues:
                details.extend([f"Issue: {issue}" for issue in validation_result.issues[:3]])
            
            self.log_test(f"PDF Validation ({method_name})", validation_result.is_valid, 
                         "PDF validation completed", details)
            
            return validation_result.is_valid
            
        except Exception as e:
            self.log_test(f"PDF Validation ({method_name})", False, f"Validation failed: {e}")
            return False
    
    def test_pdf_external_tools(self, pdf_bytes, method_name):
        """Test PDF with external tools."""
        print(f"\n🔍 Testing PDF with External Tools ({method_name})...")
        
        try:
            # Save PDF to temporary file
            pdf_path = f"/tmp/test_external_{method_name.lower()}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            self.created_files.append(pdf_path)
            
            tests_passed = []
            
            # Test 1: Check with pdfinfo (if available)
            try:
                import subprocess
                result = subprocess.run(['pdfinfo', pdf_path], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    tests_passed.append("pdfinfo: OK")
                else:
                    tests_passed.append(f"pdfinfo: Failed ({result.stderr.strip()})")
            except:
                tests_passed.append("pdfinfo: Not available")
            
            # Test 2: Check with file command
            try:
                result = subprocess.run(['file', pdf_path], 
                                      capture_output=True, text=True, timeout=10)
                if "PDF" in result.stdout:
                    tests_passed.append("file command: PDF detected")
                else:
                    tests_passed.append(f"file command: {result.stdout.strip()}")
            except:
                tests_passed.append("file command: Not available")
            
            # Test 3: Check basic PDF structure
            with open(pdf_path, 'rb') as f:
                content = f.read()
                
            structure_tests = [
                f"Size: {len(content)} bytes",
                f"Starts with %PDF: {content.startswith(b'%PDF-')}",
                f"Contains %%EOF: {b'%%EOF' in content}",
                f"Contains /Type: {b'/Type' in content}",
                f"Contains xref: {b'xref' in content or b'/XRef' in content}",
                f"Contains trailer: {b'trailer' in content or b'/Root' in content}"
            ]
            
            success = (
                content.startswith(b'%PDF-') and
                b'%%EOF' in content and
                len(content) > 1000
            )
            
            self.log_test(f"PDF External Tools ({method_name})", success, 
                         "External tool tests", tests_passed + structure_tests)
            
            return success
            
        except Exception as e:
            self.log_test(f"PDF External Tools ({method_name})", False, f"External tests failed: {e}")
            return False
    
    def test_streaming_response_simulation(self, pdf_bytes):
        """Test streaming response simulation."""
        print("\n🔍 Testing Streaming Response Simulation...")
        
        try:
            from fastapi.responses import StreamingResponse
            from io import BytesIO
            
            # Test current implementation
            response = StreamingResponse(
                iter([pdf_bytes]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=test.pdf",
                    "Content-Length": str(len(pdf_bytes))
                }
            )
            
            # Simulate streaming
            streamed_content = b""
            for chunk in iter([pdf_bytes]):
                streamed_content += chunk
            
            details = [
                f"Original size: {len(pdf_bytes)} bytes",
                f"Streamed size: {len(streamed_content)} bytes",
                f"Content matches: {streamed_content == pdf_bytes}",
                f"Content-Type: {response.media_type}",
                f"Headers: {dict(response.headers)}"
            ]
            
            success = (
                streamed_content == pdf_bytes and
                response.media_type == "application/pdf" and
                len(streamed_content) > 1000
            )
            
            self.log_test("Streaming Response Simulation", success, "Streaming test", details)
            
            return success
            
        except Exception as e:
            self.log_test("Streaming Response Simulation", False, f"Streaming test failed: {e}")
            return False
    
    def generate_test_report(self):
        """Generate a comprehensive test report."""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({'✅' if passed_tests == total_tests else '⚠️'})")
        print(f"Failed: {failed_tests} ({'✅' if failed_tests == 0 else '❌'})")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['name']}: {result['message']}")
        
        print(f"\n📄 Created Files for Manual Inspection:")
        for file_path in self.created_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  • {file_path} ({size} bytes)")
        
        return passed_tests == total_tests
    
    async def run_comprehensive_test(self):
        """Run the complete comprehensive test suite."""
        print("🧪 Starting Comprehensive PCAP to PDF Test Suite")
        print("="*80)
        
        # Step 1: Create sample PCAP file
        print("\n🔍 Step 1: Creating Sample PCAP File...")
        pcap_path = self.create_sample_pcap()
        if not pcap_path:
            return False
        
        # Step 2: Test PCAP analysis
        print("\n🔍 Step 2: Testing PCAP Analysis...")
        analysis_results = await self.test_pcap_analysis_service(pcap_path)
        if not analysis_results:
            return False
        
        # Step 3: Test report data conversion
        print("\n🔍 Step 3: Testing Report Data Conversion...")
        pdf_data = await self.test_report_data_conversion(analysis_results)
        if not pdf_data:
            return False
        
        # Step 4: Test HTML template generation
        print("\n🔍 Step 4: Testing HTML Template Generation...")
        html_content = self.test_html_template_generation(pdf_data)
        if not html_content:
            return False
        
        # Step 5: Test PDF generation methods
        print("\n🔍 Step 5: Testing PDF Generation Methods...")
        pdf_bytes = self.test_pdf_generation_methods(html_content)
        if not pdf_bytes:
            return False
        
        # Step 6: Test PDF validation
        print("\n🔍 Step 6: Testing PDF Validation...")
        self.test_pdf_validation(pdf_bytes, "ReportLab")
        
        # Step 7: Test PDF with external tools
        print("\n🔍 Step 7: Testing PDF with External Tools...")
        self.test_pdf_external_tools(pdf_bytes, "ReportLab")
        
        # Step 8: Test streaming response
        print("\n🔍 Step 8: Testing Streaming Response...")
        self.test_streaming_response_simulation(pdf_bytes)
        
        # Generate final report
        return self.generate_test_report()

async def main():
    """Main test function."""
    tester = ComprehensivePcapPdfTester()
    
    try:
        success = await tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            print("👉 Check the generated files for manual verification")
        else:
            print("\n❌ SOME TESTS FAILED!")
            print("👉 Check the test report above for details")
            
        return success
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)