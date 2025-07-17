#!/usr/bin/env python3
"""
Comprehensive test suite for PCAP report generation pipeline
This test will trace through the entire pipeline to identify failure points
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, '/home/akamalov/projects/pcap-reporter/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from core.config import get_settings
from services.pcap_analysis_service import PcapAnalysisService
from services.validation_service import ValidationService

async def test_database_connection():
    """Test database connection and initialization"""
    print("🔍 Testing database connection...")
    try:
        settings = get_settings()
        client = AsyncIOMotorClient(settings.DATABASE_URL)
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Database connection successful")
        
        # Test database initialization
        # Extract database name from URL
        database_name = settings.DATABASE_URL.split('/')[-1]
        database = client[database_name]
        await init_beanie(
            database=database,
            document_models=[Report, AnalysisJob]
        )
        print("✅ Database initialization successful")
        
        return client, database
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None, None

async def test_report_creation():
    """Test creating a report in the database"""
    print("\n🔍 Testing report creation...")
    try:
        # Create a test report
        report = Report(
            job_id="test-job-123",
            original_filename="test.pcap",
            file_size=1024,
            file_hash="test-hash",
            file_path="/tmp/test.pcap",
            status=ReportStatus.PENDING
        )
        
        await report.insert()
        print(f"✅ Report created successfully: {report.id}")
        
        # Test retrieval
        retrieved = await Report.get(report.id)
        if retrieved:
            print(f"✅ Report retrieved successfully: {retrieved.job_id}")
        else:
            print("❌ Failed to retrieve report")
            
        return report
        
    except Exception as e:
        print(f"❌ Report creation failed: {e}")
        return None

async def test_analysis_job_creation():
    """Test creating an analysis job"""
    print("\n🔍 Testing analysis job creation...")
    try:
        job = AnalysisJob(
            job_id="test-job-123",
            report_id="test-report-id",
            status=JobStatus.PENDING,
            options={"analysis_type": "comprehensive"}
        )
        
        await job.insert()
        print(f"✅ Analysis job created successfully: {job.id}")
        
        return job
        
    except Exception as e:
        print(f"❌ Analysis job creation failed: {e}")
        return None

async def test_pcap_file_validation():
    """Test PCAP file validation"""
    print("\n🔍 Testing PCAP file validation...")
    
    # Find a real PCAP file to test with
    pcap_files = list(Path("/home/akamalov/projects/pcap-reporter/uploads").glob("*.pcap"))
    if not pcap_files:
        print("❌ No PCAP files found for testing")
        return None
    
    test_file = pcap_files[0]
    print(f"📁 Testing with file: {test_file}")
    
    try:
        validation_service = ValidationService()
        
        # Test file extension validation
        ext_valid = validation_service.validate_file_extension(test_file.name)
        print(f"✅ Extension validation: {ext_valid}")
        
        # Test file size validation
        file_size = test_file.stat().st_size
        size_valid = validation_service.validate_file_size(file_size)
        print(f"✅ Size validation: {size_valid}")
        
        return str(test_file)
        
    except Exception as e:
        print(f"❌ PCAP validation failed: {e}")
        return None

async def test_pcap_analysis_service():
    """Test the PCAP analysis service directly"""
    print("\n🔍 Testing PCAP analysis service...")
    
    # Find a real PCAP file to test with
    pcap_files = list(Path("/home/akamalov/projects/pcap-reporter/uploads").glob("*.pcap"))
    if not pcap_files:
        print("❌ No PCAP files found for testing")
        return False
    
    test_file = pcap_files[0]
    print(f"📁 Testing analysis with file: {test_file}")
    
    try:
        analysis_service = PcapAnalysisService()
        
        # Test basic file validation
        await analysis_service._validate_pcap_file(str(test_file))
        print("✅ PCAP file validation passed")
        
        # Test actual analysis (this might fail due to event loop issues)
        print("🔍 Starting PCAP analysis...")
        results = await analysis_service.analyze_pcap_file(str(test_file))
        print(f"✅ PCAP analysis completed: {len(results.issues)} issues found")
        
        return True
        
    except Exception as e:
        print(f"❌ PCAP analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_pipeline():
    """Test the complete pipeline from upload to report generation"""
    print("\n🔍 Testing full pipeline...")
    
    # Find a real PCAP file to test with
    pcap_files = list(Path("/home/akamalov/projects/pcap-reporter/uploads").glob("*.pcap"))
    if not pcap_files:
        print("❌ No PCAP files found for testing")
        return False
    
    test_file = pcap_files[0]
    print(f"📁 Testing full pipeline with file: {test_file}")
    
    try:
        # Step 1: Create report
        report = Report(
            job_id="pipeline-test-456",
            original_filename=test_file.name,
            file_size=test_file.stat().st_size,
            file_hash="pipeline-test-hash",
            file_path=str(test_file),
            status=ReportStatus.PENDING
        )
        await report.insert()
        print(f"✅ Step 1: Report created - {report.id}")
        
        # Step 2: Create analysis job
        job = AnalysisJob(
            job_id="pipeline-test-456",
            report_id=report.id,
            status=JobStatus.PENDING,
            options={"analysis_type": "comprehensive"}
        )
        await job.insert()
        print(f"✅ Step 2: Analysis job created - {job.id}")
        
        # Step 3: Simulate what the Celery task would do
        print("🔍 Step 3: Simulating Celery task execution...")
        
        # Update report status
        report.status = ReportStatus.PROCESSING
        report.started_at = datetime.utcnow()
        await report.save()
        print("✅ Step 3a: Report status updated to PROCESSING")
        
        # Update job status
        job.status = JobStatus.STARTED
        job.current_step = "Starting analysis..."
        await job.save()
        print("✅ Step 3b: Job status updated to STARTED")
        
        # Try to run analysis
        try:
            analysis_service = PcapAnalysisService()
            results = await analysis_service.analyze_pcap_file(str(test_file))
            print("✅ Step 3c: Analysis completed successfully")
            
            # Update with results
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            report.analysis_results = {
                "file_path": str(test_file),
                "total_packets": results.traffic_stats.total_packets,
                "issues_found": len(results.issues)
            }
            await report.save()
            print("✅ Step 3d: Report updated with results")
            
            job.status = JobStatus.SUCCESS
            job.progress = 100
            job.current_step = "Analysis completed successfully"
            await job.save()
            print("✅ Step 3e: Job marked as successful")
            
            return True
            
        except Exception as analysis_error:
            print(f"❌ Step 3c: Analysis failed - {analysis_error}")
            
            # Update with error
            report.status = ReportStatus.FAILED
            report.error_message = str(analysis_error)
            await report.save()
            
            job.status = JobStatus.FAILURE
            job.error = str(analysis_error)
            await job.save()
            
            return False
            
    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_existing_reports():
    """Check existing reports in the database"""
    print("\n🔍 Checking existing reports...")
    
    try:
        # Check all reports
        reports = await Report.find_all().to_list()
        print(f"📊 Found {len(reports)} total reports")
        
        # Check by status
        for status in ReportStatus:
            count = await Report.find({"status": status}).count()
            print(f"   {status.value}: {count}")
        
        # Check recent reports
        print("\n📋 Recent reports:")
        recent_reports = await Report.find().sort("-created_at").limit(5).to_list()
        for report in recent_reports:
            print(f"   {report.job_id}: {report.status.value} - {report.original_filename}")
            
        # Check analysis jobs
        jobs = await AnalysisJob.find_all().to_list()
        print(f"\n📊 Found {len(jobs)} total analysis jobs")
        
        for status in JobStatus:
            count = await AnalysisJob.find({"status": status}).count()
            print(f"   {status.value}: {count}")
            
    except Exception as e:
        print(f"❌ Failed to check existing reports: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting comprehensive report generation test suite")
    print("=" * 60)
    
    # Test 1: Database connection
    client, database = await test_database_connection()
    if not client:
        print("❌ Cannot continue without database connection")
        return
    
    # Test 2: Check existing data
    await check_existing_reports()
    
    # Test 3: Test individual components
    await test_report_creation()
    await test_analysis_job_creation()
    
    # Test 4: Test file validation
    test_file = await test_pcap_file_validation()
    
    # Test 5: Test analysis service
    analysis_works = await test_pcap_analysis_service()
    
    # Test 6: Test full pipeline
    pipeline_works = await test_full_pipeline()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    print(f"Database Connection: ✅")
    print(f"File Validation: {'✅' if test_file else '❌'}")
    print(f"Analysis Service: {'✅' if analysis_works else '❌'}")
    print(f"Full Pipeline: {'✅' if pipeline_works else '❌'}")
    
    if not analysis_works:
        print("\n🔍 ANALYSIS FAILURE DETECTED:")
        print("   The PCAP analysis service is failing, likely due to:")
        print("   1. Event loop closure issues in async code")
        print("   2. Database connection problems in analysis tasks")
        print("   3. PCAP parsing library issues")
        print("   This explains why Celery tasks are failing to generate reports")
    
    # Close database connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())