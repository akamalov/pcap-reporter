#!/usr/bin/env python3
"""
Specific test for the race condition issue where upload succeeds
but immediate redirect to report page fails with 404.
"""

import requests
import time
import tempfile
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

BASE_URL = "http://localhost:9090"
API_BASE = f"{BASE_URL}/api/v1"
UPLOAD_ENDPOINT = f"{API_BASE}/analysis/upload"
REPORTS_ENDPOINT = f"{API_BASE}/reports"

def create_minimal_pcap():
    """Create a realistic minimal PCAP file."""
    from create_test_pcap import create_realistic_pcap_file
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pcap', delete=False) as f:
        temp_file = f.name
    
    return create_realistic_pcap_file(temp_file, 5)  # 5 packets

def test_single_upload_immediate_access():
    """Test single upload with immediate access attempt."""
    print("🔍 Testing single upload with immediate access...")
    
    pcap_file = create_minimal_pcap()
    
    try:
        # Upload file
        print("  📤 Uploading file...")
        start_time = time.time()
        
        with open(pcap_file, 'rb') as f:
            files = {'file': ('test.pcap', f, 'application/octet-stream')}
            upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
        
        upload_time = time.time() - start_time
        
        if upload_response.status_code not in [200, 201]:
            print(f"  ❌ Upload failed: {upload_response.status_code}")
            return False
        
        job_id = upload_response.json().get('job_id')
        print(f"  ✅ Upload successful in {upload_time:.3f}s: {job_id}")
        
        # Immediate access attempt
        print("  🔍 Attempting immediate access...")
        immediate_start = time.time()
        immediate_response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
        immediate_time = time.time() - immediate_start
        
        if immediate_response.status_code == 200:
            print(f"  ✅ Immediate access successful in {immediate_time:.3f}s")
            return True
        elif immediate_response.status_code == 404:
            print(f"  ❌ Immediate access failed with 404 in {immediate_time:.3f}s")
            
            # Wait and retry
            print("  ⏳ Waiting for report to become available...")
            for delay in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
                time.sleep(delay)
                retry_response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
                total_delay = sum([0.1, 0.5, 1.0, 2.0, 5.0, 10.0][:([0.1, 0.5, 1.0, 2.0, 5.0, 10.0].index(delay) + 1)])
                
                if retry_response.status_code == 200:
                    print(f"  ✅ Report became available after {total_delay:.1f}s total wait")
                    return False  # Race condition detected
            
            print(f"  ❌ Report never became available after 18.6s")
            return False
        else:
            print(f"  ❌ Unexpected response: {immediate_response.status_code}")
            return False
    
    finally:
        os.unlink(pcap_file)

def test_concurrent_uploads_race_condition():
    """Test multiple concurrent uploads to amplify race condition."""
    print("\n🔍 Testing concurrent uploads for race condition...")
    
    num_concurrent = 5
    results = []
    
    def upload_and_access(thread_id):
        """Upload a file and immediately try to access it."""
        pcap_file = create_minimal_pcap()
        
        try:
            print(f"  🧵 Thread {thread_id}: Starting upload...")
            
            with open(pcap_file, 'rb') as f:
                files = {'file': (f'test_{thread_id}.pcap', f, 'application/octet-stream')}
                upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
            
            if upload_response.status_code not in [200, 201]:
                return {"thread": thread_id, "upload_success": False, "immediate_access": False}
            
            job_id = upload_response.json().get('job_id')
            print(f"  🧵 Thread {thread_id}: Upload successful, job_id: {job_id}")
            
            # Immediate access
            immediate_response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
            immediate_success = immediate_response.status_code == 200
            
            print(f"  🧵 Thread {thread_id}: Immediate access {'✅ successful' if immediate_success else '❌ failed (404)'}")
            
            return {
                "thread": thread_id,
                "upload_success": True,
                "immediate_access": immediate_success,
                "job_id": job_id
            }
        
        except Exception as e:
            print(f"  🧵 Thread {thread_id}: Exception: {e}")
            return {"thread": thread_id, "upload_success": False, "immediate_access": False}
        
        finally:
            os.unlink(pcap_file)
    
    # Run concurrent uploads
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(upload_and_access, i) for i in range(num_concurrent)]
        
        for future in as_completed(futures):
            results.append(future.result())
    
    # Analyze results
    successful_uploads = sum(1 for r in results if r["upload_success"])
    immediate_access_success = sum(1 for r in results if r["immediate_access"])
    race_conditions = successful_uploads - immediate_access_success
    
    print(f"\n📊 Concurrent test results:")
    print(f"  Successful uploads: {successful_uploads}/{num_concurrent}")
    print(f"  Immediate access success: {immediate_access_success}/{successful_uploads}")
    print(f"  Race conditions detected: {race_conditions}")
    
    if race_conditions > 0:
        print(f"  ❌ Race condition rate: {race_conditions/successful_uploads*100:.1f}%")
        return False
    else:
        print(f"  ✅ No race conditions detected")
        return True

def test_timing_analysis():
    """Analyze timing of upload vs. report availability."""
    print("\n🔍 Performing timing analysis...")
    
    pcap_file = create_minimal_pcap()
    
    try:
        # Upload and track timing
        print("  📤 Uploading and tracking timing...")
        
        upload_start = time.time()
        with open(pcap_file, 'rb') as f:
            files = {'file': ('timing_test.pcap', f, 'application/octet-stream')}
            upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
        upload_end = time.time()
        
        if upload_response.status_code not in [200, 201]:
            print(f"  ❌ Upload failed: {upload_response.status_code}")
            return
        
        job_id = upload_response.json().get('job_id')
        upload_duration = upload_end - upload_start
        
        print(f"  ✅ Upload completed in {upload_duration:.3f}s")
        
        # Check availability every 50ms for detailed timing
        check_interval = 0.05  # 50ms
        max_checks = 600  # 30 seconds maximum
        
        print("  ⏳ Checking report availability every 50ms...")
        
        for check in range(max_checks):
            check_start = time.time()
            response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
            check_end = time.time()
            
            elapsed = (check_start - upload_end)
            check_duration = check_end - check_start
            
            if response.status_code == 200:
                print(f"  ✅ Report became available after {elapsed:.3f}s (check took {check_duration:.3f}s)")
                return elapsed
            elif response.status_code == 404:
                if check % 20 == 0:  # Print every second
                    print(f"    ⏳ Still waiting... {elapsed:.1f}s elapsed")
            else:
                print(f"  ❌ Unexpected status: {response.status_code}")
                return None
            
            time.sleep(check_interval)
        
        print(f"  ❌ Report never became available after 30s")
        return None
    
    finally:
        os.unlink(pcap_file)

def test_database_write_timing():
    """Test if the issue is database write timing."""
    print("\n🔍 Testing database write timing...")
    
    pcap_file = create_minimal_pcap()
    
    try:
        # Upload file
        with open(pcap_file, 'rb') as f:
            files = {'file': ('db_timing_test.pcap', f, 'application/octet-stream')}
            upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
        
        if upload_response.status_code not in [200, 201]:
            print(f"  ❌ Upload failed: {upload_response.status_code}")
            return
        
        job_id = upload_response.json().get('job_id')
        print(f"  ✅ Upload successful: {job_id}")
        
        # Check all reports endpoint vs. specific job endpoint
        print("  🔍 Comparing all reports vs. specific job endpoints...")
        
        for delay in [0, 0.1, 0.5, 1.0]:
            if delay > 0:
                time.sleep(delay)
            
            # Check all reports
            all_reports_response = requests.get(REPORTS_ENDPOINT)
            if all_reports_response.status_code == 200:
                all_reports = all_reports_response.json().get('reports', [])
                job_in_all = any(r.get('job_id') == job_id for r in all_reports)
            else:
                job_in_all = False
            
            # Check specific job
            specific_response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
            specific_available = specific_response.status_code == 200
            
            print(f"    After {delay}s: All reports: {'✅' if job_in_all else '❌'}, Specific: {'✅' if specific_available else '❌'}")
            
            if job_in_all and specific_available:
                print(f"  ✅ Both endpoints working after {delay}s")
                break
        else:
            print(f"  ❌ Issues persist after all delays")
    
    finally:
        os.unlink(pcap_file)

def main():
    """Run the race condition specific tests."""
    print("🚨 PCAP REPORTER - RACE CONDITION SPECIFIC TESTS")
    print("=" * 60)
    
    # Test 1: Single upload immediate access
    single_success = test_single_upload_immediate_access()
    
    # Test 2: Concurrent uploads
    concurrent_success = test_concurrent_uploads_race_condition()
    
    # Test 3: Timing analysis
    availability_delay = test_timing_analysis()
    
    # Test 4: Database timing
    test_database_write_timing()
    
    # Summary
    print(f"\n{'='*60}")
    print("🔍 RACE CONDITION TEST SUMMARY")
    print(f"{'='*60}")
    
    print(f"Single upload immediate access: {'✅ PASS' if single_success else '❌ RACE CONDITION DETECTED'}")
    print(f"Concurrent uploads: {'✅ PASS' if concurrent_success else '❌ RACE CONDITION DETECTED'}")
    
    if availability_delay is not None:
        print(f"Report availability delay: {availability_delay:.3f}s")
        if availability_delay > 0.1:
            print("⚠️  Significant delay detected - may cause user experience issues")
    
    race_condition_detected = not (single_success and concurrent_success)
    
    if race_condition_detected:
        print(f"\n🚨 RACE CONDITION CONFIRMED")
        print("Recommendations:")
        print("  1. Add database consistency checks before returning job_id")
        print("  2. Implement polling mechanism in frontend")
        print("  3. Add 'processing' status before redirecting")
        print("  4. Consider transaction-based approach for job creation")
    else:
        print(f"\n✅ NO RACE CONDITION DETECTED - SYSTEM STABLE")
    
    return not race_condition_detected

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)