#!/usr/bin/env python3
"""
Remove duplicate job_ids from the database via API.
"""

import requests
import json
from collections import Counter

def remove_duplicates():
    """Remove duplicate job_ids, keeping only the latest entry."""
    
    # Get all reports
    response = requests.get("http://localhost:9090/api/v1/reports/")
    if response.status_code != 200:
        print(f"❌ Failed to get reports: {response.status_code}")
        return
    
    reports = response.json().get("reports", [])
    print(f"📋 Found {len(reports)} reports")
    
    # Find duplicates by job_id
    job_ids = [r.get("job_id") for r in reports]
    job_id_counts = Counter(job_ids)
    duplicates = {job_id: count for job_id, count in job_id_counts.items() if count > 1}
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
    
    print(f"🔄 Found duplicates: {duplicates}")
    
    # Group reports by job_id
    reports_by_job_id = {}
    for report in reports:
        job_id = report.get("job_id")
        if job_id not in reports_by_job_id:
            reports_by_job_id[job_id] = []
        reports_by_job_id[job_id].append(report)
    
    removed_count = 0
    
    for job_id, count in duplicates.items():
        print(f"\n🔧 Processing job_id: {job_id} ({count} duplicates)")
        
        # Get all reports for this job_id
        job_reports = reports_by_job_id[job_id]
        
        # Sort by created_at to keep the latest one
        job_reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Remove all but the latest
        for report in job_reports[1:]:  # Skip the first (latest) one
            report_id = report.get("id")
            if report_id:
                print(f"  ❌ Removing duplicate: {report_id}")
                delete_response = requests.delete(f"http://localhost:9090/api/v1/reports/{report_id}")
                if delete_response.status_code == 200:
                    removed_count += 1
                    print(f"    ✅ Removed successfully")
                else:
                    print(f"    ❌ Failed to remove: {delete_response.status_code}")
    
    print(f"\n🎉 Cleanup complete! Removed {removed_count} duplicate entries.")
    
    # Verify cleanup
    print("\n🔍 Verifying cleanup...")
    response = requests.get("http://localhost:9090/api/v1/reports/")
    if response.status_code == 200:
        reports = response.json().get("reports", [])
        job_ids = [r.get("job_id") for r in reports]
        job_id_counts = Counter(job_ids)
        remaining_duplicates = {job_id: count for job_id, count in job_id_counts.items() if count > 1}
        
        if remaining_duplicates:
            print(f"⚠️  Still have duplicates: {remaining_duplicates}")
        else:
            print("✅ No duplicates remaining!")
            print(f"📊 Total reports: {len(reports)}")
    else:
        print(f"❌ Failed to verify: {response.status_code}")

if __name__ == "__main__":
    remove_duplicates()