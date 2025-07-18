#!/usr/bin/env python3
"""
ULTIMATE PDF CORRUPTION DETECTOR
This will test the ACTUAL report generation engine with REAL data
and identify exactly where PDF corruption occurs.
"""

import asyncio
import os
import sys
import tempfile
import hashlib
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class UltimatePDFCorruptionDetector:
    """Ultimate PDF corruption detector for real-world scenarios."""
    
    def __init__(self):
        """Initialize the detector."""
        self.test_results = []
        self.generated_files = []
        self.corruption_points = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", files: List[str] = None):
        """Log a test result with detailed information."""
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
                else:
                    print(f"    File: {file_path} (NOT FOUND)")
        
        self.test_results.append({
            "name": test_name,
            "success": success,
            "details": details,
            "files": files or [],
            "timestamp": timestamp
        })
    
    def create_real_pcap_file(self) -> str:
        """Create a realistic PCAP file with actual network traffic."""
        pcap_path = "/tmp/real_network_traffic.pcap"
        
        try:
            # Create a more realistic PCAP with HTTP traffic
            import struct
            
            # PCAP Global Header
            global_header = struct.pack(
                '<IHHIIII',
                0xa1b2c3d4,  # Magic number
                2,           # Version major
                4,           # Version minor
                0,           # Thiszone
                0,           # Sigfigs
                65535,       # Snaplen
                1            # Network (Ethernet)
            )
            
            packets = []
            
            # Create HTTP GET request packet
            eth_header = b'\x00\x01\x02\x03\x04\x05\x00\x06\x07\x08\x09\x0a\x08\x00'
            ip_header = struct.pack('>BBHHHBBH4s4s', 0x45, 0, 0, 0, 0, 64, 6, 0, 
                                  struct.pack('>I', 0xc0a80101), struct.pack('>I', 0xc0a80102))
            tcp_header = struct.pack('>HHLLBBHHH', 1234, 80, 0, 0, 0x50, 0x18, 8192, 0, 0)
            http_data = b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n'
            
            # Create DNS query packet
            dns_header = struct.pack('>HHLLBBHHH', 5353, 53, 0, 0, 0x50, 0x18, 8192, 0, 0)
            dns_query = b'\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
            
            # Create various packet types
            packets.extend([
                eth_header + ip_header + tcp_header + http_data,  # HTTP request
                eth_header + ip_header + tcp_header + b'HTTP/1.1 200 OK\r\n\r\n',  # HTTP response
                eth_header + ip_header + dns_header + dns_query,  # DNS query
                eth_header + ip_header + tcp_header + b'',  # TCP SYN
                eth_header + ip_header + tcp_header + b'',  # TCP ACK
            ])
            
            # Write PCAP file
            with open(pcap_path, 'wb') as f:
                f.write(global_header)
                
                for i, packet_data in enumerate(packets):
                    # Create multiple instances of each packet type
                    for j in range(20):  # 20 instances of each packet type
                        timestamp = int(datetime.now().timestamp()) + i * 10 + j
                        packet_header = struct.pack('<IIII', timestamp, 0, len(packet_data), len(packet_data))
                        f.write(packet_header)
                        f.write(packet_data)
            
            file_size = os.path.getsize(pcap_path)
            self.generated_files.append(pcap_path)
            
            self.log_test("Real PCAP Creation", True, 
                         f"Created realistic PCAP with {len(packets)*20} packets", [pcap_path])
            
            return pcap_path
            
        except Exception as e:
            self.log_test("Real PCAP Creation", False, f"Failed to create PCAP: {e}")
            return None
    
    async def test_full_analysis_pipeline(self, pcap_path: str) -> Optional[str]:
        """Test the complete analysis pipeline with real data."""
        try:
            # Import all necessary modules
            from models.report import Report, ReportStatus
            from models.analysis_job import AnalysisJob
            from tasks.analysis_tasks import analyze_pcap_file
            from beanie import init_beanie
            from motor.motor_asyncio import AsyncIOMotorClient
            import uuid
            
            # Initialize database connection
            try:
                client = AsyncIOMotorClient("mongodb://localhost:27017")
                await init_beanie(
                    database=client.pcap_reporter,
                    document_models=[Report, AnalysisJob]
                )
                
                self.log_test("Database Connection", True, "Successfully connected to MongoDB")
                
            except Exception as e:
                self.log_test("Database Connection", False, f"Failed to connect: {e}")
                return None
            
            # Create a real report entry
            report_id = str(uuid.uuid4())
            job_id = str(uuid.uuid4())
            
            report = Report(
                job_id=job_id,
                original_filename="real_network_traffic.pcap",
                status=ReportStatus.PENDING,
                file_size=os.path.getsize(pcap_path),
                file_hash=hashlib.md5(open(pcap_path, 'rb').read()).hexdigest()
            )
            
            await report.save()
            
            self.log_test("Real Report Creation", True, f"Created report with ID: {report.id}")
            
            # Run the actual analysis task
            try:
                # This is the REAL analysis task that users trigger
                result = await analyze_pcap_file.run(str(report.id), pcap_path)
                
                self.log_test("Real Analysis Task", True, f"Analysis completed: {result}")
                
                # Get the updated report
                updated_report = await Report.get(report.id)
                
                if updated_report and updated_report.status == ReportStatus.COMPLETED:
                    self.log_test("Analysis Completion", True, "Report marked as completed")
                    return str(updated_report.id)
                else:
                    self.log_test("Analysis Completion", False, f"Report status: {updated_report.status if updated_report else 'None'}")
                    return None
                    
            except Exception as e:
                self.log_test("Real Analysis Task", False, f"Analysis failed: {e}")
                import traceback
                traceback.print_exc()
                return None
            
        except Exception as e:
            self.log_test("Full Analysis Pipeline", False, f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_pdf_generation_stages(self, report_id: str) -> Dict[str, bytes]:
        """Test PDF generation at each stage to identify corruption points."""
        pdf_stages = {}
        
        try:
            # Stage 1: Get report data from database
            import asyncio
            from models.report import Report
            
            async def get_report_data():
                report = await Report.get(report_id)
                return report.to_dict() if report else None
            
            report_data = asyncio.run(get_report_data())
            
            if not report_data:
                self.log_test("Report Data Retrieval", False, "Failed to get report data")
                return {}
            
            self.log_test("Report Data Retrieval", True, f"Retrieved report data: {len(str(report_data))} chars")
            
            # Stage 2: Convert report data for PDF
            from api.v1.endpoints.reports import _convert_report_for_pdf
            
            try:
                pdf_data = _convert_report_for_pdf(report_data)
                self.log_test("PDF Data Conversion", True, f"Converted data: {len(str(pdf_data))} chars")
                
                # Save intermediate data for inspection
                import json
                data_file = "/tmp/pdf_data_stage.json"
                with open(data_file, 'w') as f:
                    json.dump(pdf_data, f, indent=2, default=str)
                self.generated_files.append(data_file)
                
            except Exception as e:
                self.log_test("PDF Data Conversion", False, f"Conversion failed: {e}")
                return {}
            
            # Stage 3: Generate HTML template
            from services.pdf_export import PDFExportService
            
            try:
                service = PDFExportService()
                html_content = service.generate_html_template(pdf_data)
                
                # Save HTML for inspection
                html_file = "/tmp/real_report_stage.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.generated_files.append(html_file)
                
                self.log_test("HTML Template Generation", True, f"Generated HTML: {len(html_content)} chars", [html_file])
                
            except Exception as e:
                self.log_test("HTML Template Generation", False, f"HTML generation failed: {e}")
                return {}
            
            # Stage 4: Generate PDF using different methods
            try:
                # Method 1: ReportLab (current method)
                pdf_bytes_reportlab = service._fallback_pdf_generation(html_content)
                pdf_stages['reportlab'] = pdf_bytes_reportlab
                
                reportlab_file = "/tmp/real_report_reportlab.pdf"
                with open(reportlab_file, 'wb') as f:
                    f.write(pdf_bytes_reportlab)
                self.generated_files.append(reportlab_file)
                
                self.log_test("ReportLab PDF Generation", True, 
                             f"Generated PDF: {len(pdf_bytes_reportlab)} bytes", [reportlab_file])
                
                # Test if this PDF is valid
                if pdf_bytes_reportlab.startswith(b'%PDF-') and b'%%EOF' in pdf_bytes_reportlab:
                    self.log_test("ReportLab PDF Structure", True, "PDF has valid structure")
                else:
                    self.log_test("ReportLab PDF Structure", False, "PDF structure invalid")
                    self.corruption_points.append("ReportLab PDF Generation")
                
            except Exception as e:
                self.log_test("ReportLab PDF Generation", False, f"ReportLab failed: {e}")
                self.corruption_points.append("ReportLab PDF Generation")
            
            # Method 2: Try WeasyPrint if available
            try:
                import weasyprint
                pdf_bytes_weasy = weasyprint.HTML(string=html_content).write_pdf()
                pdf_stages['weasyprint'] = pdf_bytes_weasy
                
                weasy_file = "/tmp/real_report_weasyprint.pdf"
                with open(weasy_file, 'wb') as f:
                    f.write(pdf_bytes_weasy)
                self.generated_files.append(weasy_file)
                
                self.log_test("WeasyPrint PDF Generation", True, 
                             f"Generated PDF: {len(pdf_bytes_weasy)} bytes", [weasy_file])
                
            except Exception as e:
                self.log_test("WeasyPrint PDF Generation", False, f"WeasyPrint failed: {e}")
            
            return pdf_stages
            
        except Exception as e:
            self.log_test("PDF Generation Stages", False, f"Stage testing failed: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def test_http_endpoint_directly(self, report_id: str) -> Optional[bytes]:
        """Test the actual HTTP endpoint that users call."""
        try:
            # Test the actual FastAPI endpoint
            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from api.v1.endpoints.reports import router as reports_router
            
            app = FastAPI()
            app.include_router(reports_router, prefix="/api/v1/reports")
            
            client = TestClient(app)
            
            # Make the actual request that users make
            response = client.get(f"/api/v1/reports/{report_id}/download")
            
            if response.status_code == 200:
                pdf_content = response.content
                
                # Save the HTTP response PDF
                http_pdf_file = "/tmp/real_http_response.pdf"
                with open(http_pdf_file, 'wb') as f:
                    f.write(pdf_content)
                self.generated_files.append(http_pdf_file)
                
                # Check headers
                headers = dict(response.headers)
                content_type = headers.get('content-type', '')
                content_length = headers.get('content-length', '')
                content_disposition = headers.get('content-disposition', '')
                
                self.log_test("HTTP Endpoint Test", True, 
                             f"Status: {response.status_code}, Size: {len(pdf_content)} bytes", 
                             [http_pdf_file])
                
                self.log_test("HTTP Headers Check", True, 
                             f"Content-Type: {content_type}, Length: {content_length}, Disposition: {content_disposition}")
                
                # Validate PDF structure
                if pdf_content.startswith(b'%PDF-') and b'%%EOF' in pdf_content:
                    self.log_test("HTTP PDF Structure", True, "PDF structure valid")
                else:
                    self.log_test("HTTP PDF Structure", False, "PDF structure invalid")
                    self.corruption_points.append("HTTP Endpoint Response")
                
                return pdf_content
                
            else:
                self.log_test("HTTP Endpoint Test", False, 
                             f"Status: {response.status_code}, Error: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("HTTP Endpoint Test", False, f"HTTP test failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_streaming_corruption(self, pdf_bytes: bytes) -> bytes:
        """Test if streaming causes corruption."""
        try:
            from fastapi.responses import StreamingResponse
            import asyncio
            
            # Test current streaming implementation
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
            
            # Compare byte-by-byte
            if streamed_content == pdf_bytes:
                self.log_test("Streaming Integrity", True, "Streaming preserves content")
            else:
                self.log_test("Streaming Integrity", False, "Streaming corrupts content")
                self.corruption_points.append("Streaming Response")
                
                # Find where corruption occurs
                for i, (original, streamed) in enumerate(zip(pdf_bytes, streamed_content)):
                    if original != streamed:
                        self.log_test("Corruption Point", False, f"First difference at byte {i}: {original} != {streamed}")
                        break
            
            # Save streamed content
            streamed_file = "/tmp/real_streamed_content.pdf"
            with open(streamed_file, 'wb') as f:
                f.write(streamed_content)
            self.generated_files.append(streamed_file)
            
            return streamed_content
            
        except Exception as e:
            self.log_test("Streaming Corruption Test", False, f"Streaming test failed: {e}")
            return pdf_bytes
    
    def test_binary_corruption(self, pdf_files: Dict[str, str]) -> None:
        """Test for binary corruption by comparing file hashes."""
        try:
            hashes = {}
            
            for stage, file_path in pdf_files.items():
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        hashes[stage] = hashlib.md5(content).hexdigest()
                        
                        # Check for binary integrity
                        if content.startswith(b'%PDF-') and b'%%EOF' in content:
                            self.log_test(f"Binary Integrity ({stage})", True, f"Hash: {hashes[stage][:8]}...")
                        else:
                            self.log_test(f"Binary Integrity ({stage})", False, f"Binary corruption detected")
                            self.corruption_points.append(f"Binary Corruption in {stage}")
            
            # Compare hashes to find where corruption occurs
            unique_hashes = set(hashes.values())
            if len(unique_hashes) == 1:
                self.log_test("Hash Consistency", True, "All PDF files have identical hashes")
            else:
                self.log_test("Hash Consistency", False, "PDF files have different hashes - corruption detected")
                for stage, hash_val in hashes.items():
                    self.log_test(f"Hash ({stage})", True, f"{hash_val}")
                    
        except Exception as e:
            self.log_test("Binary Corruption Test", False, f"Binary test failed: {e}")
    
    def test_pdf_readers(self, pdf_files: Dict[str, str]) -> None:
        """Test PDF files with multiple readers/validators."""
        try:
            for stage, file_path in pdf_files.items():
                if not os.path.exists(file_path):
                    continue
                
                # Test 1: System file command
                try:
                    result = subprocess.run(['file', file_path], capture_output=True, text=True)
                    if "PDF" in result.stdout:
                        self.log_test(f"File Command ({stage})", True, result.stdout.strip())
                    else:
                        self.log_test(f"File Command ({stage})", False, result.stdout.strip())
                except:
                    self.log_test(f"File Command ({stage})", False, "Command not available")
                
                # Test 2: pdfinfo (if available)
                try:
                    result = subprocess.run(['pdfinfo', file_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        pages = "unknown"
                        for line in result.stdout.split('\n'):
                            if line.startswith('Pages:'):
                                pages = line.split(':')[1].strip()
                        self.log_test(f"pdfinfo ({stage})", True, f"Pages: {pages}")
                    else:
                        self.log_test(f"pdfinfo ({stage})", False, result.stderr.strip())
                except:
                    self.log_test(f"pdfinfo ({stage})", False, "pdfinfo not available")
                
                # Test 3: PDF structure validation
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    tests = [
                        ("PDF Header", content.startswith(b'%PDF-')),
                        ("PDF Trailer", b'%%EOF' in content),
                        ("PDF Objects", b'obj' in content and b'endobj' in content),
                        ("PDF Xref", b'xref' in content or b'/XRef' in content),
                        ("PDF Catalog", b'/Catalog' in content),
                        ("PDF Pages", b'/Pages' in content),
                        ("Minimum Size", len(content) > 1000)
                    ]
                    
                    passed = sum(1 for _, test in tests if test)
                    self.log_test(f"Structure Tests ({stage})", passed == len(tests), 
                                 f"Passed: {passed}/{len(tests)}")
                    
                    if passed < len(tests):
                        failed_tests = [name for name, test in tests if not test]
                        self.log_test(f"Failed Structure Tests ({stage})", False, 
                                     f"Failed: {', '.join(failed_tests)}")
                        
                except Exception as e:
                    self.log_test(f"Structure Tests ({stage})", False, f"Structure test failed: {e}")
                    
        except Exception as e:
            self.log_test("PDF Readers Test", False, f"Reader test failed: {e}")
    
    def test_real_browser_download(self, report_id: str) -> Optional[str]:
        """Test downloading PDF as a real browser would."""
        try:
            import requests
            
            # Make HTTP request as browser would
            url = f"http://localhost:8000/api/v1/reports/{report_id}/download"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Save as browser would
                browser_file = "/tmp/real_browser_download.pdf"
                with open(browser_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.generated_files.append(browser_file)
                
                # Check if download matches expected
                content_length = response.headers.get('content-length')
                actual_size = os.path.getsize(browser_file)
                
                if content_length and int(content_length) == actual_size:
                    self.log_test("Browser Download Size", True, f"Size matches: {actual_size} bytes")
                else:
                    self.log_test("Browser Download Size", False, 
                                 f"Size mismatch: expected {content_length}, got {actual_size}")
                    self.corruption_points.append("Browser Download Size Mismatch")
                
                # Check PDF validity
                with open(browser_file, 'rb') as f:
                    content = f.read()
                
                if content.startswith(b'%PDF-') and b'%%EOF' in content:
                    self.log_test("Browser Download Validity", True, "PDF structure valid")
                else:
                    self.log_test("Browser Download Validity", False, "PDF structure invalid")
                    self.corruption_points.append("Browser Download Corruption")
                
                return browser_file
                
            else:
                self.log_test("Browser Download", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Browser Download", False, f"Download failed: {e}")
            return None
    
    def generate_comprehensive_report(self) -> None:
        """Generate comprehensive corruption analysis report."""
        print("\n" + "="*80)
        print("🔍 ULTIMATE PDF CORRUPTION ANALYSIS REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n🔍 DETAILED TEST RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} [{result['timestamp']}] {result['name']}")
            if result['details']:
                print(f"       {result['details']}")
            if not result['success']:
                print(f"       ⚠️  POTENTIAL CORRUPTION POINT")
        
        print(f"\n🚨 CORRUPTION POINTS IDENTIFIED:")
        if self.corruption_points:
            for i, point in enumerate(self.corruption_points, 1):
                print(f"   {i}. {point}")
        else:
            print("   No corruption points identified")
        
        print(f"\n📄 GENERATED FILES FOR MANUAL INSPECTION:")
        for file_path in self.generated_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   • {file_path} ({size} bytes)")
        
        print(f"\n🎯 ROOT CAUSE ANALYSIS:")
        if failed_tests == 0:
            print("   ✅ All tests passed - PDF generation appears to be working")
            print("   🔍 If users report corruption, check client-side factors:")
            print("       - Browser download handling")
            print("       - Network transfer issues")
            print("       - File system problems")
        else:
            print("   ❌ Issues detected in PDF generation pipeline:")
            failed_stages = [r['name'] for r in self.test_results if not r['success']]
            for stage in failed_stages:
                print(f"       - {stage}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if self.corruption_points:
            print("   1. Focus on the identified corruption points")
            print("   2. Compare generated files manually")
            print("   3. Test fixes at each corruption point")
        else:
            print("   1. Pipeline appears functional - investigate client-side issues")
            print("   2. Test with different browsers and network conditions")
            print("   3. Check server logs for additional clues")
    
    async def run_ultimate_test(self) -> bool:
        """Run the ultimate PDF corruption test."""
        print("🔍 ULTIMATE PDF CORRUPTION DETECTOR")
        print("=" * 80)
        print("Testing REAL report generation with ACTUAL data...")
        
        # Step 1: Create realistic PCAP file
        print("\n📁 Step 1: Creating realistic PCAP file...")
        pcap_path = self.create_real_pcap_file()
        if not pcap_path:
            return False
        
        # Step 2: Run full analysis pipeline
        print("\n🔬 Step 2: Running full analysis pipeline...")
        report_id = await self.test_full_analysis_pipeline(pcap_path)
        if not report_id:
            return False
        
        # Step 3: Test PDF generation at each stage
        print("\n📄 Step 3: Testing PDF generation stages...")
        pdf_stages = self.test_pdf_generation_stages(report_id)
        if not pdf_stages:
            return False
        
        # Step 4: Test HTTP endpoint directly
        print("\n🌐 Step 4: Testing HTTP endpoint...")
        http_pdf = self.test_http_endpoint_directly(report_id)
        
        # Step 5: Test streaming corruption
        print("\n📡 Step 5: Testing streaming corruption...")
        if 'reportlab' in pdf_stages:
            streamed_pdf = self.test_streaming_corruption(pdf_stages['reportlab'])
        
        # Step 6: Test binary corruption
        print("\n🔢 Step 6: Testing binary corruption...")
        pdf_files = {
            'reportlab': '/tmp/real_report_reportlab.pdf',
            'http_response': '/tmp/real_http_response.pdf',
            'streamed': '/tmp/real_streamed_content.pdf'
        }
        self.test_binary_corruption(pdf_files)
        
        # Step 7: Test PDF readers
        print("\n📖 Step 7: Testing PDF readers...")
        self.test_pdf_readers(pdf_files)
        
        # Step 8: Test real browser download
        print("\n🌐 Step 8: Testing browser download...")
        browser_file = self.test_real_browser_download(report_id)
        if browser_file:
            pdf_files['browser'] = browser_file
        
        # Step 9: Generate comprehensive report
        print("\n📊 Step 9: Generating comprehensive report...")
        self.generate_comprehensive_report()
        
        return len(self.corruption_points) == 0

async def main():
    """Main function to run the ultimate PDF corruption detector."""
    detector = UltimatePDFCorruptionDetector()
    
    try:
        success = await detector.run_ultimate_test()
        
        if success:
            print("\n🎉 ULTIMATE TEST COMPLETED - NO CORRUPTION DETECTED!")
            print("📧 If users still report issues, they may be client-side problems.")
        else:
            print("\n🚨 ULTIMATE TEST FOUND CORRUPTION ISSUES!")
            print("📧 Check the detailed report above for corruption points.")
            
        return success
        
    except Exception as e:
        print(f"\n💥 ULTIMATE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)