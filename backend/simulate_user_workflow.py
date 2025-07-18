#!/usr/bin/env python3
"""
SIMULATE USER WORKFLOW
Simulate the exact workflow the user follows to identify where the fallback occurs.
This will help identify why the user gets text instead of proper PDFs.
"""

import sys
import os
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
import hashlib
import uuid

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class UserWorkflowSimulator:
    """Simulate the complete user workflow to identify fallback triggers."""
    
    def __init__(self, pcap_path: str):
        self.pcap_path = pcap_path
        self.test_results = []
        self.job_id = None
        self.report_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] {status} {test_name}")
        if details:
            print(f"    Details: {details}")
        
        self.test_results.append({
            "name": test_name,
            "success": success,
            "details": details
        })
    
    async def step1_upload_pcap(self) -> bool:
        """Simulate PCAP file upload and analysis."""
        try:
            print("\n🔄 Step 1: Simulating PCAP upload and analysis...")
            
            # Generate job ID like the real system
            self.job_id = str(uuid.uuid4())
            
            # Calculate file hash
            with open(self.pcap_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Simulate analysis
            from services.pcap_analysis_service import PcapAnalysisService
            analysis_service = PcapAnalysisService()
            analysis_results = await analysis_service.analyze_pcap(self.pcap_path)
            
            self.log_test("PCAP Upload Simulation", True, 
                         f"Job ID: {self.job_id}, Hash: {file_hash[:16]}...")
            
            # Create realistic report document (MongoDB format)
            self.report_document = {
                "_id": str(uuid.uuid4()),
                "job_id": self.job_id,
                "original_filename": os.path.basename(self.pcap_path),
                "status": "completed",
                "file_size": os.path.getsize(self.pcap_path),
                "file_hash": file_hash,
                "created_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "processing_time": 0.8,
                "analysis_results": analysis_results.model_dump() if hasattr(analysis_results, 'model_dump') else analysis_results.dict()
            }
            
            self.log_test("Report Document Creation", True, 
                         f"Created MongoDB-style document")
            
            return True
            
        except Exception as e:
            self.log_test("PCAP Upload Simulation", False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step2_test_reports_endpoint(self) -> bool:
        """Test the reports endpoint workflow."""
        try:
            print("\n🔄 Step 2: Testing Reports Endpoint workflow...")
            
            # Simulate the reports endpoint workflow
            from api.v1.endpoints.reports import _convert_report_for_pdf
            from services.pdf_export import PDFExportService
            
            # Convert report data
            pdf_data = _convert_report_for_pdf(self.report_document)
            
            # Try to generate PDF
            pdf_service = PDFExportService()
            pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
            
            if pdf_bytes and pdf_bytes.startswith(b'%PDF-'):
                self.log_test("Reports Endpoint Test", True, 
                             f"Generated valid PDF: {len(pdf_bytes)} bytes")
                
                # Save the PDF
                reports_pdf_path = "/tmp/user_simulation_reports.pdf"
                with open(reports_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                return True
            else:
                self.log_test("Reports Endpoint Test", False, 
                             "Invalid PDF generated")
                return False
                
        except Exception as e:
            self.log_test("Reports Endpoint Test", False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step3_test_export_endpoint(self) -> bool:
        """Test the export endpoint workflow."""
        try:
            print("\n🔄 Step 3: Testing Export Endpoint workflow...")
            
            # Simulate the export endpoint workflow (this might be where the fallback occurs)
            from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
            from services.pdf_export import PDFExportService
            
            # Convert MongoDB report to PDF format
            pdf_data = _convert_mongodb_report_to_pdf_format(self.report_document)
            
            # Try to generate PDF (this is where the fallback might happen)
            pdf_service = PDFExportService()
            pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
            
            if pdf_bytes and pdf_bytes.startswith(b'%PDF-'):
                self.log_test("Export Endpoint Test", True, 
                             f"Generated valid PDF: {len(pdf_bytes)} bytes")
                
                # Save the PDF
                export_pdf_path = "/tmp/user_simulation_export.pdf"
                with open(export_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                return True
            else:
                self.log_test("Export Endpoint Test", False, 
                             "PDF generation failed or invalid")
                return False
                
        except Exception as e:
            self.log_test("Export Endpoint Test", False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step4_test_fallback_scenario(self) -> bool:
        """Test what happens when PDF generation fails."""
        try:
            print("\n🔄 Step 4: Testing Fallback Scenario...")
            
            # Simulate what happens when PDF generation fails
            from services.simple_pdf_export import SimplePDFExportService
            from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
            
            # Convert data
            pdf_data = _convert_mongodb_report_to_pdf_format(self.report_document)
            
            # Use the simple fallback service
            simple_service = SimplePDFExportService()
            text_bytes = simple_service.generate_pdf_report(pdf_data)
            
            self.log_test("Fallback Scenario Test", True, 
                         f"Generated text: {len(text_bytes)} bytes")
            
            # Save the text output
            fallback_path = "/tmp/user_simulation_fallback.txt"
            with open(fallback_path, 'wb') as f:
                f.write(text_bytes)
            
            # Compare with user's corrupted file
            try:
                with open("/mnt/d/tmp/analysis_report_analysis_report.pdf", 'rb') as f:
                    user_content = f.read()
                
                # Compare content
                if len(text_bytes) == len(user_content):
                    # Check first 100 bytes for similarity
                    similarity = sum(1 for a, b in zip(text_bytes[:100], user_content[:100]) if a == b)
                    if similarity > 80:  # 80% similarity
                        self.log_test("Fallback Content Match", True, 
                                     f"High similarity with user's file: {similarity}/100 bytes match")
                    else:
                        self.log_test("Fallback Content Match", False, 
                                     f"Low similarity: {similarity}/100 bytes match")
                else:
                    self.log_test("Fallback Content Match", False, 
                                 f"Size mismatch: {len(text_bytes)} vs {len(user_content)}")
                    
            except Exception as e:
                self.log_test("Fallback Content Match", False, f"Could not compare: {e}")
            
            return True
            
        except Exception as e:
            self.log_test("Fallback Scenario Test", False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step5_identify_issue(self) -> bool:
        """Try to identify what's causing the fallback."""
        try:
            print("\n🔄 Step 5: Identifying the Issue...")
            
            # Test specific scenarios that might cause PDF generation to fail
            from services.pdf_export import PDFExportService
            from api.v1.endpoints.export import _convert_mongodb_report_to_pdf_format
            
            # Test 1: Check if the conversion creates problematic data
            pdf_data = _convert_mongodb_report_to_pdf_format(self.report_document)
            
            # Test 2: Check if certain fields cause issues
            problematic_fields = []
            
            # Check for None values
            for key, value in pdf_data.items():
                if value is None:
                    problematic_fields.append(f"{key}: None")
            
            if problematic_fields:
                self.log_test("Problematic Fields Check", False, 
                             f"Found None values: {', '.join(problematic_fields)}")
            else:
                self.log_test("Problematic Fields Check", True, 
                             "No None values found")
            
            # Test 3: Try to generate PDF with detailed error reporting
            try:
                pdf_service = PDFExportService()
                html_content = pdf_service.generate_html_template(pdf_data)
                
                self.log_test("HTML Generation Test", True, 
                             f"Generated HTML: {len(html_content)} chars")
                
                # Try PDF conversion
                pdf_bytes = pdf_service.convert_html_to_pdf(html_content)
                
                if pdf_bytes and pdf_bytes.startswith(b'%PDF-'):
                    self.log_test("PDF Conversion Test", True, 
                                 f"Generated PDF: {len(pdf_bytes)} bytes")
                else:
                    self.log_test("PDF Conversion Test", False, 
                                 "PDF conversion failed")
                    
            except Exception as e:
                self.log_test("PDF Generation Debug", False, f"Error: {e}")
                import traceback
                traceback.print_exc()
            
            return True
            
        except Exception as e:
            self.log_test("Issue Identification", False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def step6_create_working_pdf(self) -> bool:
        """Create a working PDF for the user."""
        try:
            print("\n🔄 Step 6: Creating Working PDF...")
            
            # Use the working method to create a proper PDF
            from services.pdf_export import PDFExportService
            from api.v1.endpoints.reports import _convert_report_for_pdf
            
            # Convert using the working reports method
            pdf_data = _convert_report_for_pdf(self.report_document)
            
            # Generate PDF
            pdf_service = PDFExportService()
            pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
            
            if pdf_bytes and pdf_bytes.startswith(b'%PDF-'):
                # Save the working PDF
                working_pdf_path = "/tmp/user_working_pdf.pdf"
                with open(working_pdf_path, 'wb') as f:
                    f.write(pdf_bytes)
                
                self.log_test("Working PDF Creation", True, 
                             f"Created working PDF: {len(pdf_bytes)} bytes -> {working_pdf_path}")
                
                return True
            else:
                self.log_test("Working PDF Creation", False, 
                             "Failed to create working PDF")
                return False
                
        except Exception as e:
            self.log_test("Working PDF Creation", False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_simulation(self) -> bool:
        """Run the complete user workflow simulation."""
        print("🔬 USER WORKFLOW SIMULATION")
        print("=" * 80)
        print(f"Simulating user workflow with: {os.path.basename(self.pcap_path)}")
        
        # Run all steps
        steps = [
            self.step1_upload_pcap,
            self.step2_test_reports_endpoint,
            self.step3_test_export_endpoint,
            self.step4_test_fallback_scenario,
            self.step5_identify_issue,
            self.step6_create_working_pdf
        ]
        
        for step in steps:
            success = await step()
            if not success:
                print(f"\n❌ Step failed: {step.__name__}")
        
        # Generate summary
        print("\n" + "=" * 80)
        print("📊 SIMULATION SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['name']}")
            if result['details']:
                print(f"       {result['details']}")
        
        return failed_tests == 0

async def main():
    """Main function to run the simulation."""
    pcap_path = "/mnt/d/tmp/pcap/200722_win_scale_examples_anon.pcapng"
    
    simulator = UserWorkflowSimulator(pcap_path)
    
    try:
        success = await simulator.run_simulation()
        
        if success:
            print("\n🎉 USER WORKFLOW SIMULATION COMPLETED!")
            print("✅ All tests passed")
        else:
            print("\n⚠️  USER WORKFLOW SIMULATION FOUND ISSUES!")
            print("❌ Some tests failed")
        
        print("\n📄 Generated Files:")
        for file_path in ["/tmp/user_simulation_reports.pdf", "/tmp/user_simulation_export.pdf", 
                         "/tmp/user_simulation_fallback.txt", "/tmp/user_working_pdf.pdf"]:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   • {file_path} ({size} bytes)")
        
        return success
        
    except Exception as e:
        print(f"\n💥 SIMULATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)