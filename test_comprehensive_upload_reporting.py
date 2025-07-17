#!/usr/bin/env python3
"""
Comprehensive test suite for PCAP upload and report generation.
Tests the complete workflow including race conditions and edge cases.
"""

import requests
import time
import json
import os
import tempfile
import asyncio
from pathlib import Path
import random
import string
from typing import Dict, List, Optional, Tuple

# Test configuration
BASE_URL = "http://localhost:9090"
API_BASE = f"{BASE_URL}/api/v1"
UPLOAD_ENDPOINT = f"{API_BASE}/analysis/upload"
REPORTS_ENDPOINT = f"{API_BASE}/reports"

class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class TestResults:
    """Track test results and statistics."""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []
    
    def add_result(self, test_name: str, status: str, message: str = "", timing: float = 0):
        self.total += 1
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "WARN":
            self.warnings += 1
        
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "timing": timing
        })
    
    def print_summary(self):
        print(f"\n{Colors.BOLD}{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}{Colors.END}")
        print(f"Total Tests: {self.total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        if self.warnings > 0:
            print(f"{Colors.YELLOW}Warnings: {self.warnings}{Colors.END}")
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed > 0:
            print(f"\n{Colors.RED}FAILED TESTS:{Colors.END}")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  ❌ {result['test']}: {result['message']}")

def print_test_header(title: str):
    """Print formatted test section header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{Colors.END}")

def print_test_step(step: str):
    """Print formatted test step."""
    print(f"{Colors.BLUE}🔍 {step}...{Colors.END}")

def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def create_test_pcap_file(filename: str, size_kb: int = 1) -> str:
    """Create a realistic test PCAP file for testing."""
    from create_test_pcap import create_realistic_pcap_file
    
    # Calculate number of packets based on desired size
    # Roughly 100-200 bytes per packet
    num_packets = max(5, size_kb * 5)  # At least 5 packets
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pcap', delete=False) as f:
        temp_file = f.name
    
    return create_realistic_pcap_file(temp_file, num_packets)

def create_invalid_file(filename: str) -> str:
    """Create an invalid file for testing error handling."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is not a PCAP file, just plain text.")
        return f.name

def wait_for_report_availability(job_id: str, max_wait: int = 30, check_interval: float = 0.5) -> Tuple[bool, Dict]:
    """
    Wait for a report to become available, checking at regular intervals.
    Returns (success, report_data)
    """
    print_test_step(f"Waiting for report {job_id} to become available (max {max_wait}s)")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                time.sleep(check_interval)
                continue
            else:
                print_error(f"Unexpected status code: {response.status_code}")
                return False, {}
        except Exception as e:
            print_error(f"Error checking report: {e}")
            time.sleep(check_interval)
    
    return False, {}

def test_basic_upload_and_retrieval(results: TestResults):
    """Test basic upload and immediate retrieval - this often triggers the race condition."""
    print_test_header("Basic Upload and Immediate Retrieval Test")
    
    test_start = time.time()
    
    try:
        # Create test PCAP file
        pcap_file = create_test_pcap_file("test_basic.pcap", 2)
        
        print_test_step("Uploading PCAP file")
        with open(pcap_file, 'rb') as f:
            files = {'file': ('test_basic.pcap', f, 'application/octet-stream')}
            upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
        
        if upload_response.status_code not in [200, 201]:
            results.add_result("basic_upload", "FAIL", f"Upload failed: {upload_response.status_code}")
            return
        
        upload_data = upload_response.json()
        job_id = upload_data.get('job_id')
        
        if not job_id:
            results.add_result("basic_upload", "FAIL", "No job_id in upload response")
            return
        
        print_success(f"Upload successful, job_id: {job_id}")
        
        # Immediate retrieval attempt (this often fails due to race condition)
        print_test_step("Attempting immediate report retrieval")
        immediate_response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
        
        if immediate_response.status_code == 200:
            print_success("Immediate retrieval successful - no race condition detected")
            results.add_result("immediate_retrieval", "PASS", "Report available immediately")
        elif immediate_response.status_code == 404:
            print_warning("Immediate retrieval failed with 404 - race condition detected")
            
            # Wait for report to become available
            success, report_data = wait_for_report_availability(job_id, max_wait=30)
            
            if success:
                print_success("Report became available after waiting")
                results.add_result("delayed_retrieval", "WARN", "Race condition: report not immediately available")
            else:
                results.add_result("delayed_retrieval", "FAIL", "Report never became available")
        else:
            results.add_result("immediate_retrieval", "FAIL", f"Unexpected status: {immediate_response.status_code}")
        
        # Cleanup
        os.unlink(pcap_file)
        
    except Exception as e:
        results.add_result("basic_upload", "FAIL", f"Exception: {str(e)}")
    
    test_time = time.time() - test_start
    print(f"Test completed in {test_time:.2f}s")

def test_race_condition_timing(results: TestResults):
    """Test the race condition with multiple timing scenarios."""
    print_test_header("Race Condition Timing Analysis")
    
    delays = [0, 0.1, 0.5, 1.0, 2.0, 5.0]  # Different delay times
    
    for delay in delays:
        test_start = time.time()
        test_name = f"race_condition_delay_{delay}s"
        
        try:
            print_test_step(f"Testing with {delay}s delay")
            
            # Create and upload file
            pcap_file = create_test_pcap_file(f"test_race_{delay}.pcap", 1)
            
            with open(pcap_file, 'rb') as f:
                files = {'file': (f'test_race_{delay}.pcap', f, 'application/octet-stream')}
                upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
            
            if upload_response.status_code not in [200, 201]:
                results.add_result(test_name, "FAIL", f"Upload failed: {upload_response.status_code}")
                continue
            
            job_id = upload_response.json().get('job_id')
            
            # Wait for specified delay
            if delay > 0:
                time.sleep(delay)
            
            # Try to retrieve report
            response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
            
            if response.status_code == 200:
                print_success(f"Report available after {delay}s delay")
                results.add_result(test_name, "PASS", f"Available after {delay}s")
            elif response.status_code == 404:
                print_warning(f"Report still not available after {delay}s delay")
                results.add_result(test_name, "WARN", f"Not available after {delay}s")
            else:
                results.add_result(test_name, "FAIL", f"Unexpected status: {response.status_code}")
            
            # Cleanup
            os.unlink(pcap_file)
            
        except Exception as e:
            results.add_result(test_name, "FAIL", f"Exception: {str(e)}")
        
        test_time = time.time() - test_start
        print(f"  Delay test completed in {test_time:.2f}s")

def test_multiple_concurrent_uploads(results: TestResults):
    """Test multiple concurrent uploads to stress test the system."""
    print_test_header("Concurrent Upload Stress Test")
    
    num_uploads = 5
    test_start = time.time()
    
    upload_jobs = []
    
    try:
        print_test_step(f"Creating {num_uploads} concurrent uploads")
        
        # Create multiple uploads simultaneously
        for i in range(num_uploads):
            pcap_file = create_test_pcap_file(f"test_concurrent_{i}.pcap", 1)
            
            with open(pcap_file, 'rb') as f:
                files = {'file': (f'test_concurrent_{i}.pcap', f, 'application/octet-stream')}
                upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
            
            if upload_response.status_code in [200, 201]:
                job_id = upload_response.json().get('job_id')
                upload_jobs.append((i, job_id, pcap_file))
                print_success(f"Upload {i} successful: {job_id}")
            else:
                print_error(f"Upload {i} failed: {upload_response.status_code}")
                results.add_result(f"concurrent_upload_{i}", "FAIL", f"Upload failed: {upload_response.status_code}")
        
        # Check availability of all uploads
        print_test_step("Checking availability of all concurrent uploads")
        
        available_count = 0
        for i, job_id, pcap_file in upload_jobs:
            success, _ = wait_for_report_availability(job_id, max_wait=60)
            if success:
                available_count += 1
                results.add_result(f"concurrent_retrieval_{i}", "PASS", "Report became available")
            else:
                results.add_result(f"concurrent_retrieval_{i}", "FAIL", "Report never became available")
            
            # Cleanup
            os.unlink(pcap_file)
        
        success_rate = (available_count / len(upload_jobs) * 100) if upload_jobs else 0
        print(f"Concurrent test success rate: {success_rate:.1f}% ({available_count}/{len(upload_jobs)})")
        
        if success_rate >= 80:
            results.add_result("concurrent_stress_test", "PASS", f"Success rate: {success_rate:.1f}%")
        else:
            results.add_result("concurrent_stress_test", "FAIL", f"Low success rate: {success_rate:.1f}%")
        
    except Exception as e:
        results.add_result("concurrent_stress_test", "FAIL", f"Exception: {str(e)}")
    
    test_time = time.time() - test_start
    print(f"Concurrent test completed in {test_time:.2f}s")

def test_file_format_variations(results: TestResults):
    """Test various file formats and edge cases."""
    print_test_header("File Format and Edge Case Testing")
    
    test_cases = [
        ("small_pcap", lambda: create_test_pcap_file("small.pcap", 1), True),
        ("medium_pcap", lambda: create_test_pcap_file("medium.pcap", 10), True),
        ("large_pcap", lambda: create_test_pcap_file("large.pcap", 100), True),
        ("invalid_text_file", lambda: create_invalid_file("invalid.txt"), False),
        ("empty_file", lambda: tempfile.NamedTemporaryFile(delete=False).name, False),
    ]
    
    for test_name, file_creator, should_succeed in test_cases:
        test_start = time.time()
        
        try:
            print_test_step(f"Testing {test_name}")
            
            file_path = file_creator()
            
            with open(file_path, 'rb') as f:
                files = {'file': (f'{test_name}.pcap', f, 'application/octet-stream')}
                upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
            
            if should_succeed:
                if upload_response.status_code in [200, 201]:
                    job_id = upload_response.json().get('job_id')
                    print_success(f"{test_name} upload successful: {job_id}")
                    
                    # Check if report becomes available
                    success, _ = wait_for_report_availability(job_id, max_wait=30)
                    if success:
                        results.add_result(test_name, "PASS", "Upload and processing successful")
                    else:
                        results.add_result(test_name, "WARN", "Upload successful but report not available")
                else:
                    results.add_result(test_name, "FAIL", f"Upload failed: {upload_response.status_code}")
            else:
                if upload_response.status_code >= 400:
                    print_success(f"{test_name} correctly rejected")
                    results.add_result(test_name, "PASS", "Invalid file correctly rejected")
                else:
                    results.add_result(test_name, "FAIL", "Invalid file was accepted")
            
            # Cleanup
            os.unlink(file_path)
            
        except Exception as e:
            results.add_result(test_name, "FAIL", f"Exception: {str(e)}")
        
        test_time = time.time() - test_start
        print(f"  {test_name} completed in {test_time:.2f}s")

def test_api_health_and_connectivity(results: TestResults):
    """Test API health and basic connectivity."""
    print_test_header("API Health and Connectivity Test")
    
    # Test health endpoint
    try:
        print_test_step("Checking health endpoint")
        health_response = requests.get(f"{BASE_URL}/health")
        
        if health_response.status_code == 200:
            print_success("Health endpoint responding")
            results.add_result("health_check", "PASS", "Health endpoint OK")
        else:
            print_error(f"Health endpoint failed: {health_response.status_code}")
            results.add_result("health_check", "FAIL", f"Health endpoint: {health_response.status_code}")
    except Exception as e:
        results.add_result("health_check", "FAIL", f"Health check exception: {str(e)}")
    
    # Test reports endpoint
    try:
        print_test_step("Checking reports endpoint")
        reports_response = requests.get(REPORTS_ENDPOINT)
        
        if reports_response.status_code == 200:
            reports_data = reports_response.json()
            report_count = len(reports_data.get('reports', []))
            print_success(f"Reports endpoint responding with {report_count} reports")
            results.add_result("reports_endpoint", "PASS", f"{report_count} reports available")
        else:
            print_error(f"Reports endpoint failed: {reports_response.status_code}")
            results.add_result("reports_endpoint", "FAIL", f"Reports endpoint: {reports_response.status_code}")
    except Exception as e:
        results.add_result("reports_endpoint", "FAIL", f"Reports endpoint exception: {str(e)}")

def test_error_handling_robustness(results: TestResults):
    """Test error handling for various edge cases."""
    print_test_header("Error Handling Robustness Test")
    
    # Test 1: No file upload
    try:
        print_test_step("Testing upload with no file")
        response = requests.post(UPLOAD_ENDPOINT)
        
        if response.status_code >= 400:
            print_success("No file upload correctly rejected")
            results.add_result("no_file_upload", "PASS", "Correctly rejected empty upload")
        else:
            results.add_result("no_file_upload", "FAIL", "Empty upload was accepted")
    except Exception as e:
        results.add_result("no_file_upload", "FAIL", f"Exception: {str(e)}")
    
    # Test 2: Malformed job ID retrieval
    try:
        print_test_step("Testing malformed job ID retrieval")
        malformed_ids = ["", "invalid-id", "null", "undefined", " ", "very-long-" + "x" * 100]
        
        for malformed_id in malformed_ids:
            response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{malformed_id}")
            if response.status_code == 404:
                continue  # Expected
            else:
                results.add_result("malformed_id_test", "WARN", f"Unexpected response for '{malformed_id}': {response.status_code}")
                break
        else:
            print_success("Malformed job IDs correctly return 404")
            results.add_result("malformed_id_test", "PASS", "All malformed IDs correctly handled")
    except Exception as e:
        results.add_result("malformed_id_test", "FAIL", f"Exception: {str(e)}")

def main():
    """Run the comprehensive test suite."""
    print(f"{Colors.BOLD}{Colors.PURPLE}")
    print("=" * 80)
    print("PCAP REPORTER - COMPREHENSIVE UPLOAD & REPORTING TEST SUITE")
    print("=" * 80)
    print(f"{Colors.END}")
    
    results = TestResults()
    
    # Run all test suites
    test_api_health_and_connectivity(results)
    test_basic_upload_and_retrieval(results)
    test_race_condition_timing(results)
    test_multiple_concurrent_uploads(results)
    test_file_format_variations(results)
    test_error_handling_robustness(results)
    
    # Print final results
    results.print_summary()
    
    # Additional analysis
    print(f"\n{Colors.BOLD}ANALYSIS & RECOMMENDATIONS:{Colors.END}")
    
    race_condition_detected = any(result["status"] == "WARN" and "race condition" in result["message"].lower() for result in results.results)
    
    if race_condition_detected:
        print(f"{Colors.YELLOW}🚨 RACE CONDITION DETECTED:{Colors.END}")
        print("  - Reports are created successfully but not immediately available")
        print("  - This causes 404 errors when users are redirected immediately after upload")
        print("  - Recommendation: Add polling mechanism or delay before redirect")
        print("  - Alternative: Show 'processing' status until report is confirmed available")
    
    high_failure_rate = (results.failed / results.total) > 0.2 if results.total > 0 else False
    if high_failure_rate:
        print(f"{Colors.RED}⚠️  HIGH FAILURE RATE DETECTED:{Colors.END}")
        print("  - System may be unstable or overloaded")
        print("  - Recommendation: Check backend logs and system resources")
    
    if results.failed == 0 and results.warnings == 0:
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED - SYSTEM IS STABLE{Colors.END}")
    elif results.failed == 0:
        print(f"{Colors.YELLOW}✅ NO FAILURES - MINOR ISSUES DETECTED{Colors.END}")
    else:
        print(f"{Colors.RED}🔧 ISSUES REQUIRE ATTENTION{Colors.END}")
    
    return results.failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)