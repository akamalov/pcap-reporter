#!/usr/bin/env python3
"""
Comprehensive Test Suite for PCAP File Upload API

This test suite will systematically test the PCAP upload functionality
to identify and fix the current upload errors.
"""

import requests
import os
import sys
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

# Test configuration
API_BASE_URL = "http://localhost:9090"
UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/v1/analysis/submit"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

# Test file locations
TEST_PCAP_FILE = "/mnt/d/tmp/pcap/200722_win_scale_examples_anon.pcapng"
BACKUP_TEST_FILE = "/tmp/test_files"

class Colors:
    """ANSI color codes for output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class PCAPUploadTester:
    """Comprehensive PCAP Upload Testing Suite"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with color coding"""
        color = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.GREEN,
            "ERROR": Colors.RED,
            "WARNING": Colors.YELLOW,
            "DEBUG": Colors.BLUE
        }.get(level, Colors.WHITE)
        
        print(f"{color}[{level}]{Colors.END} {message}")
        
    def test_result(self, test_name: str, passed: bool, message: str = "", details: Dict = None):
        """Record test result"""
        status = "PASS" if passed else "FAIL"
        color = Colors.GREEN if passed else Colors.RED
        
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {}
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            
        print(f"  {color}[{status}]{Colors.END} {test_name}: {message}")
        
        if details and not passed:
            print(f"    {Colors.YELLOW}Details:{Colors.END} {json.dumps(details, indent=4)}")
    
    def test_api_health(self) -> bool:
        """Test API health endpoint"""
        self.log("Testing API health endpoint...")
        
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                self.test_result("API Health Check", True, f"API is healthy: {health_data.get('status', 'unknown')}")
                return True
            else:
                self.test_result("API Health Check", False, f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.test_result("API Health Check", False, f"Health check error: {str(e)}")
            return False
    
    def create_test_files(self):
        """Create test files for various scenarios"""
        self.log("Creating test files...")
        
        os.makedirs(BACKUP_TEST_FILE, exist_ok=True)
        
        # Create minimal valid PCAP file
        pcap_header = b'\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00'
        with open(f"{BACKUP_TEST_FILE}/minimal.pcap", "wb") as f:
            f.write(pcap_header)
        
        # Create too small file
        with open(f"{BACKUP_TEST_FILE}/too_small.pcap", "wb") as f:
            f.write(b"small")
        
        # Create invalid file
        with open(f"{BACKUP_TEST_FILE}/invalid.txt", "w") as f:
            f.write("This is not a PCAP file")
        
        # Create empty file
        with open(f"{BACKUP_TEST_FILE}/empty.pcap", "wb") as f:
            pass
        
        self.log("Test files created successfully")
    
    def test_file_upload(self, file_path: str, expected_status: int, test_name: str) -> Dict[str, Any]:
        """Test file upload with specific file"""
        self.log(f"Testing file upload: {test_name}")
        
        if not os.path.exists(file_path):
            self.test_result(test_name, False, f"Test file not found: {file_path}")
            return {"error": "File not found"}
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                data = {
                    'analysis_type': 'comprehensive',
                    'priority': 'normal'
                }
                
                self.log(f"Uploading file: {file_path} (size: {os.path.getsize(file_path)} bytes)")
                
                response = requests.post(
                    UPLOAD_ENDPOINT,
                    files=files,
                    data=data,
                    timeout=30
                )
                
                response_data = {}
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": response.text}
                
                success = response.status_code == expected_status
                
                self.test_result(
                    test_name, 
                    success,
                    f"Status: {response.status_code}, Expected: {expected_status}",
                    {
                        "status_code": response.status_code,
                        "response": response_data,
                        "file_size": os.path.getsize(file_path)
                    }
                )
                
                return {
                    "status_code": response.status_code,
                    "response": response_data,
                    "success": success
                }
                
        except Exception as e:
            self.test_result(test_name, False, f"Upload error: {str(e)}")
            return {"error": str(e)}
    
    def test_main_pcap_file(self):
        """Test the main PCAP file that's causing issues"""
        self.log(f"Testing main PCAP file: {TEST_PCAP_FILE}")
        
        if not os.path.exists(TEST_PCAP_FILE):
            self.test_result("Main PCAP File Test", False, f"Main test file not found: {TEST_PCAP_FILE}")
            return
        
        # Get file info
        file_size = os.path.getsize(TEST_PCAP_FILE)
        self.log(f"File size: {file_size} bytes")
        
        # Test with the actual file
        result = self.test_file_upload(TEST_PCAP_FILE, 200, "Main PCAP File Upload")
        
        if result.get("status_code") == 500:
            self.log("500 error detected - analyzing response...")
            self.analyze_500_error(result.get("response", {}))
    
    def analyze_500_error(self, response_data: Dict):
        """Analyze 500 error details"""
        self.log("Analyzing 500 Internal Server Error...", "ERROR")
        
        detail = response_data.get("detail", "")
        if "'error'" in detail:
            self.log("KeyError detected in response - this is the bug we need to fix!", "ERROR")
            
            # Log the exact error
            print(f"    {Colors.RED}Error Detail:{Colors.END} {detail}")
            
            # Suggest fixes
            self.log("Suggested fixes:", "WARNING")
            print("    1. Check all dictionary access in validation methods")
            print("    2. Look for 'error' key access without .get() method")
            print("    3. Verify validation service return structures")
    
    def test_various_scenarios(self):
        """Test various upload scenarios"""
        self.log("Testing various upload scenarios...")
        
        # Test scenarios with expected outcomes
        scenarios = [
            (f"{BACKUP_TEST_FILE}/too_small.pcap", 400, "Too Small File"),
            (f"{BACKUP_TEST_FILE}/empty.pcap", 400, "Empty File"),
            (f"{BACKUP_TEST_FILE}/invalid.txt", 400, "Invalid File Extension"),
            (f"{BACKUP_TEST_FILE}/minimal.pcap", 200, "Minimal Valid PCAP"),
        ]
        
        for file_path, expected_status, test_name in scenarios:
            self.test_file_upload(file_path, expected_status, test_name)
    
    def test_api_direct_validation(self):
        """Test API validation methods directly"""
        self.log("Testing API validation methods...")
        
        # Test file extension validation
        try:
            test_extensions = [
                ("test.pcap", True),
                ("test.pcapng", True),
                ("test.cap", True),
                ("test.txt", False),
                ("test.exe", False),
            ]
            
            for filename, expected in test_extensions:
                # This would need to be tested via the API or direct import
                # For now, we'll test via the upload endpoint
                pass
                
        except Exception as e:
            self.log(f"Direct validation test error: {e}", "ERROR")
    
    def debug_current_error(self):
        """Debug the current 500 error systematically"""
        self.log("Debugging current 500 error systematically...", "DEBUG")
        
        # Test with minimal data to isolate the issue
        test_data = {
            'analysis_type': 'comprehensive',
            'priority': 'normal'
        }
        
        # Test with different file types
        test_files = [
            (f"{BACKUP_TEST_FILE}/minimal.pcap", "Minimal PCAP"),
            (TEST_PCAP_FILE, "Main PCAP File") if os.path.exists(TEST_PCAP_FILE) else None
        ]
        
        for file_path, desc in filter(None, test_files):
            self.log(f"Debug test with {desc}")
            result = self.test_file_upload(file_path, 200, f"Debug - {desc}")
            
            if result.get("status_code") == 500:
                self.log(f"500 error confirmed with {desc}", "ERROR")
                return result
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        self.log("Starting Comprehensive PCAP Upload Test Suite", "INFO")
        print("=" * 60)
        
        # Test 1: API Health
        if not self.test_api_health():
            self.log("API is not healthy - stopping tests", "ERROR")
            return False
        
        # Test 2: Create test files
        self.create_test_files()
        
        # Test 3: Test various scenarios
        self.test_various_scenarios()
        
        # Test 4: Test main PCAP file
        self.test_main_pcap_file()
        
        # Test 5: Debug current error
        self.debug_current_error()
        
        # Test 6: API validation
        self.test_api_direct_validation()
        
        # Summary
        self.print_summary()
        
        return self.failed == 0
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        self.log("Test Summary", "INFO")
        print("=" * 60)
        
        total_tests = self.passed + self.failed
        
        print(f"Total Tests: {total_tests}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        
        if self.failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "=" * 60)
        
        if self.failed == 0:
            self.log("All tests passed!", "SUCCESS")
        else:
            self.log(f"{self.failed} tests failed - see details above", "ERROR")

def main():
    """Main test runner"""
    tester = PCAPUploadTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test suite error: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()