#!/usr/bin/env python3
"""
COMPREHENSIVE REAL PCAP TEST
Use the user's actual PCAP file to reproduce the issue and generate a proper PDF.
This will test the complete pipeline from PCAP analysis to PDF generation.
"""

import sys
import os
import asyncio
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class ComprehensiveRealPcapTest:
    """Test the complete pipeline with user's real PCAP file."""
    
    def __init__(self, pcap_path: str):
        self.pcap_path = pcap_path
        self.test_results = []
        self.generated_files = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", files: list = None):
        """Log test results."""
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
            "files": files or []
        })
    
    def verify_pcap_file(self) -> bool:
        """Verify the PCAP file exists and is valid."""
        try:
            if not os.path.exists(self.pcap_path):
                self.log_test("PCAP File Existence", False, f"File not found: {self.pcap_path}")
                return False
            
            file_size = os.path.getsize(self.pcap_path)
            if file_size == 0:
                self.log_test("PCAP File Size", False, "File is empty")
                return False
            
            # Check if it's a valid PCAP file by reading the header
            with open(self.pcap_path, 'rb') as f:
                header = f.read(24)
                # Check for PCAP magic numbers
                if header[:4] in [b'\xa1\xb2\xc3\xd4', b'\xd4\xc3\xb2\xa1', b'\x0a\x0d\x0d\x0a']:
                    self.log_test("PCAP File Validation", True, f"Valid PCAP file: {file_size} bytes")
                    return True
                else:
                    self.log_test("PCAP File Validation", False, f"Invalid PCAP magic: {header[:4]}")
                    return False
                    
        except Exception as e:
            self.log_test("PCAP File Validation", False, f"Error reading file: {e}")
            return False
    
    async def test_pcap_analysis(self) -> dict:
        """Test PCAP analysis with the real file."""
        try:
            from services.pcap_analysis_service import PcapAnalysisService
            
            # Create analysis service
            analysis_service = PcapAnalysisService()
            
            # Analyze the PCAP file
            self.log_test("PCAP Analysis Start", True, "Starting analysis of real PCAP file")
            analysis_results = await analysis_service.analyze_pcap(self.pcap_path)
            
            # Check if analysis was successful
            if analysis_results:
                # Convert to dict for inspection
                if hasattr(analysis_results, 'dict'):
                    results_dict = analysis_results.dict()
                elif hasattr(analysis_results, '__dict__'):
                    results_dict = analysis_results.__dict__
                else:
                    results_dict = analysis_results
                
                # Log key metrics
                total_packets = results_dict.get('traffic_stats', {}).get('total_packets', 0)
                duration = results_dict.get('traffic_stats', {}).get('duration', 0)
                
                self.log_test("PCAP Analysis Complete", True, 
                             f"Analyzed {total_packets} packets over {duration:.1f} seconds")
                
                # Save analysis results for inspection
                import json
                analysis_file = "/tmp/real_pcap_analysis.json"
                with open(analysis_file, 'w') as f:
                    json.dump(results_dict, f, indent=2, default=str)
                self.generated_files.append(analysis_file)
                
                return results_dict
            else:
                self.log_test("PCAP Analysis Complete", False, "Analysis returned no results")
                return None
                
        except Exception as e:
            self.log_test("PCAP Analysis Complete", False, f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_report_creation(self, analysis_results: dict) -> dict:
        """Test creating a report structure from analysis results."""
        try:
            # Create a realistic report structure
            report_data = {
                "job_id": "real-pcap-test",
                "original_filename": os.path.basename(self.pcap_path),
                "status": "completed",
                "file_size": os.path.getsize(self.pcap_path),
                "file_hash": "real-pcap-hash",
                "created_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "processing_time": 30.0,
                "analysis_results": analysis_results
            }
            
            self.log_test("Report Creation", True, 
                         f"Created report for {report_data['original_filename']}")
            
            return report_data
            
        except Exception as e:
            self.log_test("Report Creation", False, f"Report creation failed: {e}")
            return None
    
    def test_data_conversion_reports_endpoint(self, report_data: dict) -> dict:
        """Test data conversion using the reports endpoint method."""
        try:
            from api.v1.endpoints.reports import _convert_report_for_pdf
            
            # Convert using reports endpoint method
            pdf_data = _convert_report_for_pdf(report_data)
            
            self.log_test("Data Conversion (Reports)", True, 
                         f"Converted data: {len(str(pdf_data))} characters")
            
            # Save converted data
            import json
            converted_file = "/tmp/real_pcap_converted_reports.json"
            with open(converted_file, 'w') as f:
                json.dump(pdf_data, f, indent=2, default=str)
            self.generated_files.append(converted_file)
            
            return pdf_data
            
        except Exception as e:
            self.log_test("Data Conversion (Reports)", False, f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_data_conversion_export_endpoint(self, report_data: dict) -> dict:
        """Test data conversion using the export endpoint method."""
        try:
            from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
            
            # Convert using export endpoint method
            pdf_data = _convert_mongodb_report_to_pdf_format(report_data)
            
            self.log_test("Data Conversion (Export)", True, 
                         f"Converted data: {len(str(pdf_data))} characters")
            
            # Save converted data
            import json
            converted_file = "/tmp/real_pcap_converted_export.json"
            with open(converted_file, 'w') as f:
                json.dump(pdf_data, f, indent=2, default=str)
            self.generated_files.append(converted_file)
            
            return pdf_data
            
        except Exception as e:
            self.log_test("Data Conversion (Export)", False, f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_pdf_generation(self, pdf_data: dict, endpoint_name: str) -> bytes:
        """Test PDF generation with the converted data."""
        try:
            from services.pdf_export import PDFExportService
            
            # Generate PDF
            service = PDFExportService()
            pdf_bytes = service.generate_pdf_report(pdf_data)
            
            # Validate PDF
            if pdf_bytes.startswith(b'%PDF-') and b'%%EOF' in pdf_bytes:
                self.log_test(f"PDF Generation ({endpoint_name})", True, 
                             f"Generated valid PDF: {len(pdf_bytes)} bytes")
                
                # Save PDF
                pdf_file = f"/tmp/real_pcap_{endpoint_name.lower()}.pdf"
                with open(pdf_file, 'wb') as f:
                    f.write(pdf_bytes)
                self.generated_files.append(pdf_file)
                
                return pdf_bytes
            else:
                self.log_test(f"PDF Generation ({endpoint_name})", False, 
                             f"Invalid PDF structure: {pdf_bytes[:50]}")
                return None
                
        except Exception as e:
            self.log_test(f"PDF Generation ({endpoint_name})", False, f"PDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_simple_pdf_fallback(self, pdf_data: dict) -> bytes:
        """Test what happens with the simple PDF fallback."""
        try:
            from services.simple_pdf_export import SimplePDFExportService
            
            # Generate with simple service
            service = SimplePDFExportService()
            text_bytes = service.generate_pdf_report(pdf_data)
            
            self.log_test("Simple PDF Fallback", True, 
                         f"Generated text: {len(text_bytes)} bytes")
            
            # Save text output
            text_file = "/tmp/real_pcap_simple_fallback.txt"
            with open(text_file, 'wb') as f:
                f.write(text_bytes)
            self.generated_files.append(text_file)
            
            # Check if this matches the user's corrupted file
            try:
                with open("/mnt/d/tmp/analysis_report_analysis_report.pdf", 'rb') as f:
                    user_content = f.read()
                
                if text_bytes == user_content:
                    self.log_test("Fallback Match Check", True, 
                                 "Simple fallback matches user's corrupted file!")
                else:
                    self.log_test("Fallback Match Check", False, 
                                 f"Content differs: {len(text_bytes)} vs {len(user_content)}")
            except Exception as e:
                self.log_test("Fallback Match Check", False, f"Could not compare: {e}")
            
            return text_bytes
            
        except Exception as e:
            self.log_test("Simple PDF Fallback", False, f"Simple PDF failed: {e}")
            return None
    
    def test_http_endpoints(self, report_data: dict) -> dict:
        """Test both HTTP endpoints with the real data."""
        results = {}
        
        try:
            # Test Reports endpoint
            from api.v1.endpoints.reports import _convert_report_for_pdf
            from services.pdf_export import PDFExportService
            
            # Simulate reports endpoint
            pdf_data = _convert_report_for_pdf(report_data)
            service = PDFExportService()
            pdf_bytes = service.generate_pdf_report(pdf_data)
            
            if pdf_bytes and pdf_bytes.startswith(b'%PDF-'):
                self.log_test("Reports Endpoint Simulation", True, 
                             f"Generated valid PDF: {len(pdf_bytes)} bytes")
                
                reports_file = "/tmp/real_pcap_reports_endpoint.pdf"
                with open(reports_file, 'wb') as f:
                    f.write(pdf_bytes)
                self.generated_files.append(reports_file)
                results['reports'] = pdf_bytes
            else:
                self.log_test("Reports Endpoint Simulation", False, "Invalid PDF generated")
                
        except Exception as e:
            self.log_test("Reports Endpoint Simulation", False, f"Reports endpoint failed: {e}")
        
        try:
            # Test Export endpoint
            from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
            
            # Simulate export endpoint
            pdf_data = _convert_mongodb_report_to_pdf_format(report_data)
            service = PDFExportService()
            pdf_bytes = service.generate_pdf_report(pdf_data)
            
            if pdf_bytes and pdf_bytes.startswith(b'%PDF-'):
                self.log_test("Export Endpoint Simulation", True, 
                             f"Generated valid PDF: {len(pdf_bytes)} bytes")
                
                export_file = "/tmp/real_pcap_export_endpoint.pdf"
                with open(export_file, 'wb') as f:
                    f.write(pdf_bytes)
                self.generated_files.append(export_file)
                results['export'] = pdf_bytes
            else:
                self.log_test("Export Endpoint Simulation", False, "Invalid PDF generated")
                
        except Exception as e:
            self.log_test("Export Endpoint Simulation", False, f"Export endpoint failed: {e}")
        
        return results
    
    def generate_final_report(self) -> None:
        """Generate comprehensive test report."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE REAL PCAP TEST REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📈 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['name']}")
            if result['details']:
                print(f"       {result['details']}")
        
        print(f"\n📄 GENERATED FILES:")
        for file_path in self.generated_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   • {file_path} ({size} bytes)")
        
        print(f"\n🎯 ANALYSIS:")
        if failed_tests == 0:
            print("   ✅ All tests passed - PDF generation is working correctly")
        else:
            print("   ❌ Some tests failed - issues identified in the pipeline")
        
        print(f"\n💡 NEXT STEPS:")
        print("   1. Compare generated PDFs with user's corrupted file")
        print("   2. Identify which code path the user is hitting")
        print("   3. Fix the problematic code path")
        print("   4. Generate a proper PDF for the user")
    
    async def run_comprehensive_test(self) -> bool:
        """Run the complete comprehensive test."""
        print("🔬 COMPREHENSIVE REAL PCAP TEST")
        print("=" * 80)
        print(f"Using PCAP file: {self.pcap_path}")
        
        # Step 1: Verify PCAP file
        print("\n📁 Step 1: Verifying PCAP file...")
        if not self.verify_pcap_file():
            return False
        
        # Step 2: Analyze PCAP file
        print("\n🔬 Step 2: Analyzing PCAP file...")
        analysis_results = await self.test_pcap_analysis()
        if not analysis_results:
            return False
        
        # Step 3: Create report data
        print("\n📊 Step 3: Creating report data...")
        report_data = self.test_report_creation(analysis_results)
        if not report_data:
            return False
        
        # Step 4: Test data conversion (both endpoints)
        print("\n🔄 Step 4: Testing data conversion...")
        reports_pdf_data = self.test_data_conversion_reports_endpoint(report_data)
        export_pdf_data = self.test_data_conversion_export_endpoint(report_data)
        
        # Step 5: Test PDF generation
        print("\n📄 Step 5: Testing PDF generation...")
        if reports_pdf_data:
            self.test_pdf_generation(reports_pdf_data, "Reports")
        if export_pdf_data:
            self.test_pdf_generation(export_pdf_data, "Export")
        
        # Step 6: Test simple PDF fallback
        print("\n⚠️  Step 6: Testing simple PDF fallback...")
        if reports_pdf_data:
            self.test_simple_pdf_fallback(reports_pdf_data)
        
        # Step 7: Test HTTP endpoints
        print("\n🌐 Step 7: Testing HTTP endpoints...")
        endpoint_results = self.test_http_endpoints(report_data)
        
        # Step 8: Generate final report
        print("\n📊 Step 8: Generating final report...")
        self.generate_final_report()
        
        return len([r for r in self.test_results if not r['success']]) == 0

async def main():
    """Main function to run the comprehensive test."""
    pcap_path = "/mnt/d/tmp/pcap/200722_win_scale_examples_anon.pcapng"
    
    tester = ComprehensiveRealPcapTest(pcap_path)
    
    try:
        success = await tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 COMPREHENSIVE TEST COMPLETED SUCCESSFULLY!")
            print("✅ All tests passed - PDF generation is working")
        else:
            print("\n⚠️  COMPREHENSIVE TEST FOUND ISSUES!")
            print("❌ Some tests failed - check the detailed report above")
        
        return success
        
    except Exception as e:
        print(f"\n💥 COMPREHENSIVE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)