#!/usr/bin/env python3
"""
Test script to verify the duplicate job_id fix.
"""

import requests
import json
import time

def test_duplicate_fix():
    """Test the duplicate job_id fix by creating a test report."""
    
    # Test 1: Get current reports
    print("🔍 Testing reports endpoint...")
    response = requests.get("http://localhost:9090/api/v1/reports/")
    
    if response.status_code == 200:
        data = response.json()
        reports = data.get("reports", [])
        print(f"✅ Found {len(reports)} reports")
        
        # Check for duplicate job_ids
        job_ids = [r.get("job_id") for r in reports]
        unique_job_ids = set(job_ids)
        
        if len(job_ids) != len(unique_job_ids):
            print(f"❌ Found duplicates! {len(job_ids)} total, {len(unique_job_ids)} unique")
            # Find the duplicates
            from collections import Counter
            job_id_counts = Counter(job_ids)
            duplicates = {job_id: count for job_id, count in job_id_counts.items() if count > 1}
            print(f"🔄 Duplicates: {duplicates}")
        else:
            print("✅ No duplicate job_ids found")
    else:
        print(f"❌ Reports endpoint failed: {response.status_code}")
    
    # Test 2: Try to access a non-existent report
    print("\n🔍 Testing non-existent report...")
    test_job_id = "non-existent-job-id-12345"
    response = requests.get(f"http://localhost:9090/api/v1/reports/by-job-id/{test_job_id}")
    
    if response.status_code == 404:
        print("✅ Non-existent report correctly returns 404")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
    
    # Test 3: Try to access a real report if any exist
    if reports:
        print("\n🔍 Testing existing report...")
        test_job_id = reports[0].get("job_id")
        if test_job_id:
            response = requests.get(f"http://localhost:9090/api/v1/reports/by-job-id/{test_job_id}")
            if response.status_code == 200:
                print("✅ Existing report correctly returns 200")
            else:
                print(f"❌ Expected 200, got {response.status_code}")
        else:
            print("⚠️  No job_id found in report")
    
    print("\n🎉 Duplicate fix test completed!")

if __name__ == "__main__":
    test_duplicate_fix()