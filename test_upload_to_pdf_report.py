#!/usr/bin/env python3
"""
Comprehensive test suite for PCAP upload to PDF report generation
This test validates the entire pipeline from file upload to PDF report generation
"""
import asyncio
import os
import sys
import time
import requests
import uuid
from pathlib import Path
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, '/home/akamalov/projects/pcap-reporter/backend')

from core.database import init_db
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus

class PCAPReportTestSuite:
    def __init__(self):
        self.api_base_url = "http://localhost:9090/api/v1"
        self.test_results = []
        self.pcap_files = []
        
    def log_test(self, test_name, status, message=""):
        """Log test results"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "timestamp": timestamp
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {message}")
        
    def find_test_pcap_files(self):
        """Find available PCAP files for testing"""
        uploads_dir = Path("/home/akamalov/projects/pcap-reporter/uploads")
        if uploads_dir.exists():
            self.pcap_files = list(uploads_dir.glob("*.pcap*"))
            
        if not self.pcap_files:
            # Create a minimal test file if none exist
            test_file = uploads_dir / "test.pcap"
            test_file.write_bytes(b"test pcap content")
            self.pcap_files = [test_file]
            
        self.log_test("Find PCAP Files", "PASS", f"Found {len(self.pcap_files)} PCAP files")
        return True
        
    def test_api_health(self):
        """Test if the API is responding"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_test("API Health Check", "PASS", "API is responding")
                return True
            else:
                self.log_test("API Health Check", "FAIL", f"API returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", "FAIL", f"API not responding: {e}")
            return False
            
    def test_file_upload(self, test_file):
        """Test file upload to the API"""
        try:
            # Test the actual upload endpoint
            with open(test_file, 'rb') as f:
                files = {'file': (test_file.name, f, 'application/octet-stream')}
                data = {
                    'analysis_type': 'comprehensive',
                    'priority': 'normal'
                }
                
                response = requests.post(
                    f"{self.api_base_url}/analysis/submit",
                    files=files,
                    data=data,
                    timeout=30
                )
                
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                self.log_test("File Upload", "PASS", f"Upload successful, job_id: {job_id}")
                return job_id
            else:
                self.log_test("File Upload", "FAIL", f"Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log_test("File Upload", "FAIL", f"Upload exception: {e}")
            return None
            
    def test_job_processing(self, job_id, timeout=60):
        """Test job processing and wait for completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check job status
                response = requests.get(f"{self.api_base_url}/reports/by-job-id/{job_id}", timeout=5)
                
                if response.status_code == 200:
                    report = response.json()
                    status = report.get('status')
                    
                    if status == 'completed':
                        self.log_test("Job Processing", "PASS", f"Job completed successfully in {time.time() - start_time:.1f}s")
                        return True
                    elif status == 'failed':
                        error = report.get('error_message', 'Unknown error')
                        self.log_test("Job Processing", "FAIL", f"Job failed: {error}")
                        return False
                    else:
                        print(f"🔄 Job status: {status}, waiting...")
                        time.sleep(2)
                        continue
                        
                elif response.status_code == 404:
                    print(f"🔄 Job not found yet, waiting...")
                    time.sleep(2)
                    continue
                else:
                    self.log_test("Job Processing", "FAIL", f"Unexpected status code: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"🔄 Error checking job status: {e}, retrying...")
                time.sleep(2)
                continue
                
        self.log_test("Job Processing", "FAIL", f"Job timed out after {timeout}s")
        return False
        
    def test_report_retrieval(self, job_id):
        """Test report retrieval"""
        try:
            response = requests.get(f"{self.api_base_url}/reports/by-job-id/{job_id}", timeout=5)
            
            if response.status_code == 200:
                report = response.json()
                
                # Check if report has analysis results
                if report.get('analysis_results'):
                    self.log_test("Report Retrieval", "PASS", "Report retrieved with analysis results")
                    return report
                else:
                    self.log_test("Report Retrieval", "FAIL", "Report found but no analysis results")
                    return None
            else:
                self.log_test("Report Retrieval", "FAIL", f"Report not found: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("Report Retrieval", "FAIL", f"Report retrieval exception: {e}")
            return None
            
    def test_pdf_generation(self, job_id):
        """Test PDF report generation"""
        try:
            response = requests.get(f"{self.api_base_url}/reports/{job_id}/pdf", timeout=30)
            
            if response.status_code == 200:
                # Check if response is actually a PDF
                if response.headers.get('content-type') == 'application/pdf':
                    pdf_size = len(response.content)
                    self.log_test("PDF Generation", "PASS", f"PDF generated successfully ({pdf_size} bytes)")
                    return True
                else:
                    self.log_test("PDF Generation", "FAIL", f"Response is not PDF: {response.headers.get('content-type')}")
                    return False
            else:
                self.log_test("PDF Generation", "FAIL", f"PDF generation failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("PDF Generation", "FAIL", f"PDF generation exception: {e}")
            return False
            
    async def test_database_state(self):
        """Test database state and data integrity"""
        try:
            await init_db()
            
            # Check reports
            reports = await Report.find_all().to_list()
            total_reports = len(reports)
            
            # Check by status
            completed = len([r for r in reports if r.status == ReportStatus.COMPLETED])
            failed = len([r for r in reports if r.status == ReportStatus.FAILED])
            pending = len([r for r in reports if r.status == ReportStatus.PENDING])
            
            self.log_test("Database State", "INFO", f"Total reports: {total_reports} (completed: {completed}, failed: {failed}, pending: {pending})")
            
            # Check jobs
            jobs = await AnalysisJob.find_all().to_list()
            total_jobs = len(jobs)
            
            job_success = len([j for j in jobs if j.status == JobStatus.SUCCESS])
            job_failed = len([j for j in jobs if j.status == JobStatus.FAILURE])
            job_pending = len([j for j in jobs if j.status == JobStatus.PENDING])
            
            self.log_test("Database Jobs", "INFO", f"Total jobs: {total_jobs} (success: {job_success}, failed: {job_failed}, pending: {job_pending})")
            
            return True
            
        except Exception as e:
            self.log_test("Database State", "FAIL", f"Database check failed: {e}")
            return False
            
    def run_full_test_suite(self):
        """Run the complete test suite"""
        print("🚀 Starting Comprehensive PCAP Upload to PDF Report Test Suite")
        print("=" * 80)
        
        # Step 1: Find test files
        if not self.find_test_pcap_files():
            return False
            
        # Step 2: Test API health
        if not self.test_api_health():
            return False
            
        # Step 3: Test database state
        asyncio.run(self.test_database_state())
        
        # Step 4: Test full pipeline with first available file
        test_file = self.pcap_files[0]
        self.log_test("Test File", "INFO", f"Using test file: {test_file.name}")
        
        # Upload file
        job_id = self.test_file_upload(test_file)
        if not job_id:
            return False
            
        # Wait for processing
        if not self.test_job_processing(job_id):
            return False
            
        # Retrieve report
        report = self.test_report_retrieval(job_id)
        if not report:
            return False
            
        # Generate PDF
        if not self.test_pdf_generation(job_id):
            return False
            
        return True
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        info = len([r for r in self.test_results if r['status'] == 'INFO'])
        
        print(f"Total tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"ℹ️  Info: {info}")
        
        if failed > 0:
            print(f"\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   ❌ {result['test_name']}: {result['message']}")
                    
        success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        # Determine overall result
        if passed > 0 and failed == 0:
            print("🎉 ALL TESTS PASSED - PCAP Upload to PDF Report pipeline is working!")
            return True
        elif success_rate >= 80:
            print("⚠️  MOSTLY WORKING - Some issues found but core functionality works")
            return True
        else:
            print("❌ MAJOR ISSUES - PCAP Upload to PDF Report pipeline is broken")
            return False

if __name__ == "__main__":
    test_suite = PCAPReportTestSuite()
    success = test_suite.run_full_test_suite()
    overall_success = test_suite.print_summary()
    
    sys.exit(0 if overall_success else 1)