#!/usr/bin/env python3
"""
Test script to verify the Celery fix works properly
"""
import asyncio
import os
import sys
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, '/home/akamalov/projects/pcap-reporter/backend')

from core.database import init_db
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from tasks.analysis_tasks import analyze_pcap_file

async def test_celery_task_fix():
    """Test that the Celery task can run successfully"""
    print("🔍 Testing Celery task fix...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Find a test file
    uploads_dir = "/app/uploads"
    pcap_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pcap')]
    
    if not pcap_files:
        print("❌ No PCAP files found for testing")
        return False
    
    test_file = os.path.join(uploads_dir, pcap_files[0])
    print(f"📁 Testing with file: {test_file}")
    
    # Create a test report
    report = Report(
        job_id="celery-test-789",
        original_filename=pcap_files[0],
        file_size=os.path.getsize(test_file),
        file_hash="celery-test-hash",
        file_path=test_file,
        status=ReportStatus.PENDING
    )
    await report.insert()
    print(f"✅ Created test report: {report.id}")
    
    # Create analysis job
    job = AnalysisJob(
        job_id="celery-test-789",
        report_id=report.id,
        status=JobStatus.PENDING,
        options={"analysis_type": "comprehensive"}
    )
    await job.insert()
    print(f"✅ Created analysis job: {job.id}")
    
    # Test direct task execution
    try:
        print("🔍 Running Celery task directly...")
        result = analyze_pcap_file(str(report.id), test_file)
        print(f"✅ Task completed successfully: {result}")
        
        # Check if report was updated
        updated_report = await Report.get(report.id)
        print(f"📊 Report status: {updated_report.status.value}")
        
        if updated_report.status == ReportStatus.COMPLETED:
            print("✅ Report generated successfully!")
            return True
        else:
            print(f"❌ Report not completed: {updated_report.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Task failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_celery_task_fix())
    sys.exit(0 if success else 1)