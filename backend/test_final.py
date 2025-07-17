#!/usr/bin/env python3
"""
Test the final fix for report generation
"""
import asyncio
import sys
from models.report import Report
from models.analysis_job import AnalysisJob, JobStatus
from models.report import ReportStatus
from tasks.analysis_tasks import analyze_pcap_file

async def test_final_fix():
    try:
        # Initialize database first
        from core.database import init_db
        await init_db()
        
        # Create a new test report 
        report = Report(
            job_id='test-final-fix-789',
            original_filename='test.pcap',
            file_size=1024,
            file_hash='test-hash',
            file_path='/app/uploads/20250716_205129_30802204_20250716_174022_2a12271e_telnet-raw.pcap',
            status=ReportStatus.PENDING
        )
        await report.insert()
        print(f'✅ Created test report: {report.id}')
        
        # Submit to Celery
        task = analyze_pcap_file.delay(str(report.id), report.file_path)
        print(f'✅ Submitted task to Celery: {task.id}')
        
        # Wait for processing
        import time
        for i in range(15):
            await asyncio.sleep(1)
            updated_report = await Report.get(report.id)
            print(f'📊 Status check {i+1}: {updated_report.status.value}')
            
            if updated_report.status != ReportStatus.PENDING:
                break
        
        # Final check
        final_report = await Report.get(report.id)
        print(f'📊 Final status: {final_report.status.value}')
        
        if final_report.status == ReportStatus.COMPLETED:
            print('✅ SUCCESS: Report generated successfully!')
            if final_report.analysis_results:
                print(f'📊 Analysis results found: {len(final_report.analysis_results)} keys')
                return True
        else:
            print(f'❌ FAILURE: {final_report.error_message}')
            return False
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_final_fix())
    sys.exit(0 if success else 1)