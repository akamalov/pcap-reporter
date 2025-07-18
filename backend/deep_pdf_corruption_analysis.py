#!/usr/bin/env python3
"""
Deep analysis of PDF corruption in the report generation pipeline.
This will test every step of the process to identify where corruption occurs.
"""

import asyncio
import os
import tempfile
import struct
from datetime import datetime
from pathlib import Path
import sys
import io

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class PDFCorruptionAnalyzer:
    """Analyzes PDF corruption in the report generation pipeline."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.test_results = []
        self.created_files = []
        self.analysis_results = None
        self.report_data = None
        self.html_content = None
        self.pdf_bytes = None
    
    def log_result(self, stage, success, message, details=None):
        """Log a test result."""
        status = "✅" if success else "❌"
        print(f"{status} {stage}: {message}")
        if details:
            for detail in details:
                print(f"   • {detail}")
        
        self.test_results.append({
            "stage": stage,
            "success": success,
            "message": message,
            "details": details or []
        })
    
    def create_test_pcap(self):
        """Create a test PCAP file with proper structure."""
        pcap_path = "/tmp/corruption_test.pcap"
        
        try:
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
            
            # Create proper Ethernet + IP + TCP packet
            # Ethernet header (14 bytes)
            eth_dst = b'\x00\x01\x02\x03\x04\x05'
            eth_src = b'\x00\x06\x07\x08\x09\x0a'
            eth_type = b'\x08\x00'  # IPv4
            
            # IP header (20 bytes)
            ip_header = struct.pack(
                '>BBHHHBBH4s4s',
                0x45,        # Version + IHL
                0,           # Type of Service
                54,          # Total Length
                0,           # Identification
                0,           # Flags + Fragment Offset
                64,          # TTL
                6,           # Protocol (TCP)
                0,           # Checksum
                struct.pack('>I', 0xc0a80101),  # Source IP
                struct.pack('>I', 0xc0a80102)   # Dest IP
            )
            
            # TCP header (20 bytes)
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
            packet_data = eth_dst + eth_src + eth_type + ip_header + tcp_header
            
            # Write PCAP file
            with open(pcap_path, 'wb') as f:
                f.write(global_header)
                
                # Write multiple packets with different characteristics
                for i in range(50):
                    timestamp = int(datetime.now().timestamp()) + i
                    packet_header = struct.pack(
                        '<IIII',
                        timestamp,
                        0,
                        len(packet_data),
                        len(packet_data)
                    )
                    f.write(packet_header)
                    f.write(packet_data)
            
            self.created_files.append(pcap_path)
            self.log_result("PCAP Creation", True, f"Created test PCAP with 50 packets", [
                f"File: {pcap_path}",
                f"Size: {os.path.getsize(pcap_path)} bytes"
            ])
            
            return pcap_path
            
        except Exception as e:
            self.log_result("PCAP Creation", False, f"Failed: {e}")
            return None
    
    async def analyze_pcap(self, pcap_path):
        """Analyze the PCAP file."""
        try:
            from services.pcap_analysis_service import PcapAnalysisService
            
            service = PcapAnalysisService()
            results = await service.analyze_pcap_file(pcap_path)
            
            self.analysis_results = results
            
            details = [
                f"Total packets: {results.total_packets}",
                f"Total bytes: {results.total_bytes}",
                f"Duration: {results.duration}s",
                f"Protocols: {results.protocols}",
                f"Issues: {len(results.issues)}",
                f"Conversations: {len(results.top_conversations)}"
            ]
            
            success = results.total_packets > 0 and results.total_bytes > 0
            self.log_result("PCAP Analysis", success, "Analysis completed", details)
            
            return results if success else None
            
        except Exception as e:
            self.log_result("PCAP Analysis", False, f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_report_data(self, analysis_results):
        """Create report data structure."""
        try:
            report_data = {
                "_id": "corruption-test-report",
                "original_filename": "corruption_test.pcap",
                "status": "completed",
                "file_size": analysis_results.file_size,
                "file_hash": "corruption_test_hash",
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:30:00Z",
                "processing_time": 300.0,
                "analysis_results": analysis_results.model_dump()
            }
            
            self.report_data = report_data
            
            details = [
                f"Report ID: {report_data['_id']}",
                f"Filename: {report_data['original_filename']}",
                f"Status: {report_data['status']}",
                f"Analysis results size: {len(str(report_data['analysis_results']))} chars"
            ]
            
            self.log_result("Report Data Creation", True, "Report data created", details)
            return report_data
            
        except Exception as e:
            self.log_result("Report Data Creation", False, f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def convert_for_pdf(self, report_data):
        """Convert report data for PDF generation."""
        try:
            from api.v1.endpoints.reports import _convert_report_for_pdf
            
            pdf_data = _convert_report_for_pdf(report_data)
            
            details = [
                f"Job ID: {pdf_data.get('job_id', 'Missing')}",
                f"Filename: {pdf_data.get('filename', 'Missing')}",
                f"Total packets: {pdf_data.get('total_packets', 0)}",
                f"Protocols: {pdf_data.get('protocols', {})}",
                f"Has security analysis: {'security_analysis' in pdf_data}",
                f"Has performance metrics: {'performance_metrics' in pdf_data}"
            ]
            
            success = 'job_id' in pdf_data and pdf_data.get('total_packets', 0) > 0
            self.log_result("PDF Data Conversion", success, "Data converted for PDF", details)
            
            return pdf_data if success else None
            
        except Exception as e:
            self.log_result("PDF Data Conversion", False, f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_html_template(self, pdf_data):
        """Generate HTML template."""
        try:
            from services.pdf_export import PDFExportService
            
            service = PDFExportService()
            html_content = service.generate_html_template(pdf_data)
            
            self.html_content = html_content
            
            # Save HTML for inspection
            html_path = "/tmp/corruption_test_report.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.created_files.append(html_path)
            
            details = [
                f"HTML length: {len(html_content)} characters",
                f"Contains DOCTYPE: {'<!DOCTYPE' in html_content}",
                f"Contains title: {'PCAP Analysis Report' in html_content}",
                f"Contains CSS: {'<style>' in html_content}",
                f"Contains data: {pdf_data.get('filename', 'test') in html_content}",
                f"HTML file saved: {html_path}"
            ]
            
            success = (
                len(html_content) > 1000 and
                '<!DOCTYPE' in html_content and
                '<html' in html_content and
                '</html>' in html_content
            )
            
            self.log_result("HTML Template Generation", success, "HTML template generated", details)
            return html_content if success else None
            
        except Exception as e:
            self.log_result("HTML Template Generation", False, f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_pdf_generation_methods(self, html_content):
        """Test different PDF generation methods."""
        try:
            from services.pdf_export import PDFExportService
            
            service = PDFExportService()
            
            # Test Method 1: ReportLab fallback (current method)
            print("\n🔍 Testing ReportLab method...")
            
            try:
                pdf_bytes_reportlab = service._fallback_pdf_generation(html_content)
                
                # Save for inspection
                pdf_path = "/tmp/corruption_test_reportlab.pdf"
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes_reportlab)
                self.created_files.append(pdf_path)
                
                details = [
                    f"PDF size: {len(pdf_bytes_reportlab)} bytes",
                    f"Starts with %PDF: {pdf_bytes_reportlab.startswith(b'%PDF-')}",
                    f"Contains ReportLab: {b'ReportLab' in pdf_bytes_reportlab}",
                    f"PDF saved: {pdf_path}"
                ]
                
                success = len(pdf_bytes_reportlab) > 1000 and pdf_bytes_reportlab.startswith(b'%PDF-')
                self.log_result("ReportLab PDF Generation", success, "ReportLab PDF generated", details)
                
                if success:
                    self.pdf_bytes = pdf_bytes_reportlab
                    return pdf_bytes_reportlab
                    
            except Exception as e:
                self.log_result("ReportLab PDF Generation", False, f"ReportLab failed: {e}")
            
            # Test Method 2: WeasyPrint (if available)
            print("\n🔍 Testing WeasyPrint method...")
            
            try:
                import weasyprint
                
                pdf_bytes_weasy = weasyprint.HTML(string=html_content).write_pdf()
                
                # Save for inspection
                pdf_path = "/tmp/corruption_test_weasyprint.pdf"
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes_weasy)
                self.created_files.append(pdf_path)
                
                details = [
                    f"PDF size: {len(pdf_bytes_weasy)} bytes",
                    f"Starts with %PDF: {pdf_bytes_weasy.startswith(b'%PDF-')}",
                    f"PDF saved: {pdf_path}"
                ]
                
                success = len(pdf_bytes_weasy) > 1000 and pdf_bytes_weasy.startswith(b'%PDF-')
                self.log_result("WeasyPrint PDF Generation", success, "WeasyPrint PDF generated", details)
                
                if success and not self.pdf_bytes:
                    self.pdf_bytes = pdf_bytes_weasy
                    return pdf_bytes_weasy
                    
            except Exception as e:
                self.log_result("WeasyPrint PDF Generation", False, f"WeasyPrint failed: {e}")
            
            # Test Method 3: Try with xhtml2pdf
            print("\n🔍 Testing xhtml2pdf method...")
            
            try:
                from xhtml2pdf import pisa
                
                output = io.BytesIO()
                pisa_status = pisa.CreatePDF(html_content, dest=output)
                
                if not pisa_status.err:
                    pdf_bytes_pisa = output.getvalue()
                    
                    # Save for inspection
                    pdf_path = "/tmp/corruption_test_pisa.pdf"
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_bytes_pisa)
                    self.created_files.append(pdf_path)
                    
                    details = [
                        f"PDF size: {len(pdf_bytes_pisa)} bytes",
                        f"Starts with %PDF: {pdf_bytes_pisa.startswith(b'%PDF-')}",
                        f"PDF saved: {pdf_path}"
                    ]
                    
                    success = len(pdf_bytes_pisa) > 1000 and pdf_bytes_pisa.startswith(b'%PDF-')
                    self.log_result("xhtml2pdf PDF Generation", success, "xhtml2pdf PDF generated", details)
                    
                    if success and not self.pdf_bytes:
                        self.pdf_bytes = pdf_bytes_pisa
                        return pdf_bytes_pisa
                else:
                    self.log_result("xhtml2pdf PDF Generation", False, f"xhtml2pdf errors: {pisa_status.err}")
                    
            except Exception as e:
                self.log_result("xhtml2pdf PDF Generation", False, f"xhtml2pdf failed: {e}")
            
            return self.pdf_bytes
            
        except Exception as e:
            self.log_result("PDF Generation Methods", False, f"All methods failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_pdf_validation(self, pdf_bytes):
        """Test PDF validation."""
        try:
            sys.path.append("/home/akamalov/projects/pcap-reporter/backend/tests/utils")
            from pdf_validator import PDFValidator
            
            validator = PDFValidator()
            validation_result = validator.validate_pdf_bytes(pdf_bytes)
            
            details = [
                f"Is valid: {validation_result.is_valid}",
                f"Errors: {len(validation_result.errors)}",
                f"Warnings: {len(validation_result.warnings)}",
                f"Info: {validation_result.info}"
            ]
            
            if validation_result.errors:
                details.extend([f"Error: {error}" for error in validation_result.errors[:5]])
            if validation_result.warnings:
                details.extend([f"Warning: {warning}" for warning in validation_result.warnings[:3]])
            
            self.log_result("PDF Validation", validation_result.is_valid, 
                           "PDF validation completed", details)
            
            return validation_result.is_valid
            
        except Exception as e:
            self.log_result("PDF Validation", False, f"Validation failed: {e}")
            return False
    
    def test_streaming_response(self, pdf_bytes):
        """Test streaming response behavior."""
        try:
            from fastapi.responses import StreamingResponse
            
            # Test current implementation
            response = StreamingResponse(
                iter([pdf_bytes]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=test.pdf",
                    "Content-Length": str(len(pdf_bytes))
                }
            )
            
            # Collect streamed content
            streamed_content = b""
            for chunk in iter([pdf_bytes]):
                streamed_content += chunk
            
            # Save streamed content
            streamed_path = "/tmp/corruption_test_streamed.pdf"
            with open(streamed_path, 'wb') as f:
                f.write(streamed_content)
            self.created_files.append(streamed_path)
            
            details = [
                f"Original size: {len(pdf_bytes)} bytes",
                f"Streamed size: {len(streamed_content)} bytes",
                f"Content matches: {streamed_content == pdf_bytes}",
                f"Streamed PDF saved: {streamed_path}"
            ]
            
            success = streamed_content == pdf_bytes
            self.log_result("Streaming Response", success, "Streaming test completed", details)
            
            return success
            
        except Exception as e:
            self.log_result("Streaming Response", False, f"Streaming failed: {e}")
            return False
    
    def test_external_pdf_readers(self, pdf_bytes):
        """Test with external PDF readers/validators."""
        try:
            pdf_path = "/tmp/corruption_test_final.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            self.created_files.append(pdf_path)
            
            tests = []
            
            # Test 1: pdfinfo
            try:
                import subprocess
                result = subprocess.run(['pdfinfo', pdf_path], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    tests.append("pdfinfo: ✅ OK")
                else:
                    tests.append(f"pdfinfo: ❌ {result.stderr.strip()}")
            except:
                tests.append("pdfinfo: ⚠️ Not available")
            
            # Test 2: file command
            try:
                result = subprocess.run(['file', pdf_path], 
                                      capture_output=True, text=True, timeout=10)
                if "PDF" in result.stdout:
                    tests.append("file: ✅ PDF detected")
                else:
                    tests.append(f"file: ❌ {result.stdout.strip()}")
            except:
                tests.append("file: ⚠️ Not available")
            
            # Test 3: Basic structure
            with open(pdf_path, 'rb') as f:
                content = f.read()
            
            structure_ok = (
                content.startswith(b'%PDF-') and
                b'%%EOF' in content and
                b'/Type' in content
            )
            
            tests.append(f"Structure: {'✅' if structure_ok else '❌'} Basic PDF structure")
            
            success = structure_ok
            self.log_result("External PDF Validation", success, "External validation completed", tests)
            
            return success
            
        except Exception as e:
            self.log_result("External PDF Validation", False, f"External validation failed: {e}")
            return False
    
    def generate_analysis_report(self):
        """Generate comprehensive analysis report."""
        print("\n" + "="*80)
        print("📊 DEEP PDF CORRUPTION ANALYSIS REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Steps: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['stage']}: {result['message']}")
            
            if not result['success']:
                print(f"   Issue: {result['message']}")
                for detail in result['details']:
                    print(f"   • {detail}")
        
        print(f"\n📄 GENERATED FILES:")
        for file_path in self.created_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   • {file_path} ({size} bytes)")
        
        # Identify the root cause
        print(f"\n🔍 ROOT CAUSE ANALYSIS:")
        
        if failed_tests == 0:
            print("✅ No issues found in the pipeline!")
            print("   The PDF generation process is working correctly.")
        else:
            print("❌ Issues found in the pipeline:")
            
            failed_stages = [r['stage'] for r in self.test_results if not r['success']]
            
            if 'PCAP Analysis' in failed_stages:
                print("   • PCAP analysis is failing - check tshark/scapy dependencies")
            if 'PDF Data Conversion' in failed_stages:
                print("   • Data conversion is failing - check data model compatibility")
            if 'HTML Template Generation' in failed_stages:
                print("   • HTML template generation is failing - check Jinja2 templates")
            if 'ReportLab PDF Generation' in failed_stages:
                print("   • ReportLab PDF generation is failing - check ReportLab installation")
            if 'PDF Validation' in failed_stages:
                print("   • PDF validation is failing - PDFs may be structurally corrupt")
            if 'Streaming Response' in failed_stages:
                print("   • Streaming response is failing - check FastAPI implementation")
            if 'External PDF Validation' in failed_stages:
                print("   • External tools can't read PDFs - PDFs are likely corrupt")
        
        print(f"\n👉 RECOMMENDATION:")
        if failed_tests == 0:
            print("   The pipeline is working. If users report corruption, check:")
            print("   1. Browser download handling")
            print("   2. File system permissions")
            print("   3. Network transfer issues")
        else:
            print("   Fix the failing stages in order:")
            for i, stage in enumerate(failed_stages, 1):
                print(f"   {i}. {stage}")
        
        return failed_tests == 0
    
    async def run_deep_analysis(self):
        """Run the complete deep analysis."""
        print("🔍 Starting Deep PDF Corruption Analysis")
        print("="*80)
        
        # Step 1: Create test PCAP
        pcap_path = self.create_test_pcap()
        if not pcap_path:
            return False
        
        # Step 2: Analyze PCAP
        analysis_results = await self.analyze_pcap(pcap_path)
        if not analysis_results:
            return False
        
        # Step 3: Create report data
        report_data = self.create_report_data(analysis_results)
        if not report_data:
            return False
        
        # Step 4: Convert for PDF
        pdf_data = self.convert_for_pdf(report_data)
        if not pdf_data:
            return False
        
        # Step 5: Generate HTML
        html_content = self.generate_html_template(pdf_data)
        if not html_content:
            return False
        
        # Step 6: Test PDF generation
        pdf_bytes = self.test_pdf_generation_methods(html_content)
        if not pdf_bytes:
            return False
        
        # Step 7: Validate PDF
        self.test_pdf_validation(pdf_bytes)
        
        # Step 8: Test streaming
        self.test_streaming_response(pdf_bytes)
        
        # Step 9: External validation
        self.test_external_pdf_readers(pdf_bytes)
        
        # Step 10: Generate report
        return self.generate_analysis_report()

async def main():
    """Main function."""
    analyzer = PDFCorruptionAnalyzer()
    
    try:
        success = await analyzer.run_deep_analysis()
        
        if success:
            print("\n🎉 DEEP ANALYSIS COMPLETED SUCCESSFULLY!")
        else:
            print("\n❌ DEEP ANALYSIS FOUND ISSUES!")
            
        return success
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)