"""
FIXED Analysis endpoints for PCAP file upload and analysis submission.
This is a complete rewrite to fix the persistent KeyError issue.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from typing import Dict, Any, Optional
import os
import hashlib
import logging
import uuid
from datetime import datetime, timedelta

# Direct imports to avoid dependency injection issues
from core.config import get_settings
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from tasks.analysis_tasks import analyze_pcap_file
from services.validation_service import ValidationService

logger = logging.getLogger(__name__)

router = APIRouter()


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request headers with proxy support."""
    # Check for forwarded headers (load balancer/proxy)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    # Fall back to direct connection IP
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"


@router.post("/submit")
async def submit_analysis_job_fixed(
    request: Request,
    file: UploadFile = File(...),
    analysis_type: Optional[str] = Form("comprehensive"),
    priority: Optional[str] = Form("normal")
) -> Dict[str, Any]:
    """
    Fixed submit a PCAP file for analysis with options.
    This version directly instantiates dependencies to avoid injection issues.
    """
    print(f"🔥🔥🔥 FIXED SUBMIT ANALYSIS JOB CALLED - ENTRY POINT 🔥🔥🔥")
    print(f"🔥 File: {file.filename if file else 'None'}")
    print(f"🔥 Analysis type: {analysis_type}")
    print(f"🔥 Priority: {priority}")
    
    file_path = None
    
    try:
        # Directly instantiate services to avoid dependency injection issues
        print("🔥 Instantiating settings...")
        settings = get_settings()
        print("🔥 Settings instantiated successfully")
        
        print("🔥 Instantiating validation service...")
        validation_service = ValidationService()
        print("🔥 Validation service instantiated successfully")
        
        # Extract client IP for security logging and audit trail
        print("🔥 Extracting client IP...")
        client_ip = get_client_ip(request)
        print(f"🔥 Client IP: {client_ip}")
        
        # Validate no file provided
        print("🔥 Validating file provided...")
        if not file or not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided. A PCAP file must be uploaded."
            )
        print("🔥 File validation passed")
        
        # Validate file extension
        print("🔥 Validating file extension...")
        extension_valid = validation_service.validate_file_extension(file.filename)
        if not extension_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "detail": f"Only {', '.join(settings.UPLOAD_ALLOWED_EXTENSIONS)} files are supported",
                    "supported_types": list(settings.UPLOAD_ALLOWED_EXTENSIONS)
                }
            )
        print("🔥 File extension validation passed")
        
        # Read file content to get size and validate
        print("🔥 Reading file content...")
        content = await file.read()
        file_size = len(content)
        print(f"🔥 File size: {file_size}")
        
        # Validate file size
        print("🔥 Validating file size...")
        size_validation = validation_service.validate_file_size(file_size)
        if not size_validation.get("valid", False):
            error_msg = size_validation.get("error", "File size validation failed")
            status_code = 413 if "exceeds" in error_msg else 400
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": "File size validation failed",
                    "detail": error_msg,
                    "max_size": settings.UPLOAD_MAX_SIZE,
                    "received_size": file_size
                }
            )
        print("🔥 File size validation passed")
        
        # Comprehensive file validation
        print("🔥 Running comprehensive file validation...")
        await file.seek(0)
        comprehensive_validation = await validation_service.comprehensive_file_validation(file, client_ip=client_ip)
        print(f"🔥 Comprehensive validation result: {comprehensive_validation}")
        
        if not comprehensive_validation.get("valid", False):
            # Determine appropriate status code based on security or format issues
            status_code = 403 if comprehensive_validation.get("security_threat") else 400
            error_detail = {
                "error": "Comprehensive validation failed",
                "detail": comprehensive_validation.get("message", "Validation failed"),
                "validation_id": comprehensive_validation.get("validation_id")
            }
            
            # Add security context if available
            if comprehensive_validation.get("security_threat"):
                error_detail["security_issues"] = comprehensive_validation.get("security_issues", [])
                error_detail["threat_severity"] = comprehensive_validation.get("severity", "unknown")
            
            raise HTTPException(status_code=status_code, detail=error_detail)
        print("🔥 Comprehensive validation passed")
        
        # Validate analysis options
        print("🔥 Validating analysis options...")
        options_dict = {
            "analysis_type": analysis_type,
            "priority": priority
        }
        options_validation = validation_service.validate_analysis_options(options_dict)
        
        if not options_validation.get("valid", False):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid analysis options",
                    "errors": options_validation.get("errors", [])
                }
            )
        
        validated_options = options_validation.get("options", {})
        print("🔥 Analysis options validation passed")
        
        # Create upload directory if it doesn't exist
        print("🔥 Creating upload directory...")
        os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
        
        # Generate unique filename with UUID to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{unique_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_PATH, filename)
        
        # Save file
        print("🔥 Saving file...")
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Calculate file hash
        print("🔥 Calculating file hash...")
        file_hash = calculate_file_hash(file_path)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Estimate completion time
        print("🔥 Estimating completion time...")
        estimated_time = validation_service.estimate_completion_time(
            file_size,
            validated_options.get("priority", "normal"),
            validated_options.get("analysis_type", "comprehensive")
        )
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_time)
        
        # Create report record
        print("🔥 Creating report record...")
        report_data = {
            'job_id': job_id,
            'original_filename': file.filename,
            'file_size': file_size,
            'file_hash': file_hash,
            'file_path': file_path,
            'status': ReportStatus.PENDING
        }
        
        report = Report(**report_data)
        await report.insert()
        print(f"🔥 Report created with ID: {report.id}")
        
        # Create analysis job record
        print("🔥 Creating analysis job record...")
        analysis_job = AnalysisJob(
            job_id=job_id,
            report_id=report.id,
            status=JobStatus.PENDING,
            options=validated_options,
            estimated_completion=estimated_completion
        )
        await analysis_job.insert()
        print("🔥 Analysis job created")
        
        # Submit analysis task to Celery
        print("🔥 Submitting to Celery...")
        task = analyze_pcap_file.delay(
            str(report.id),
            file_path
        )
        
        # Update records with Celery task ID
        analysis_job.celery_task_id = task.id
        await analysis_job.save()
        
        report.job_id = task.id
        await report.save()
        
        print("🔥 Analysis job submitted successfully!")
        
        # Build response
        response = {
            "job_id": job_id,
            "status": "pending",
            "filename": file.filename,
            "file_size": file_size,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "estimated_completion": estimated_completion.isoformat() + "Z",
            "analysis_type": validated_options.get("analysis_type", "comprehensive"),
            "priority": validated_options.get("priority", "normal"),
            "validation": {
                "validation_id": comprehensive_validation.get("validation_id"),
                "security_score": comprehensive_validation.get("security_score", "unknown"),
                "file_type": comprehensive_validation.get("file_type", "pcap"),
                "validation_time": comprehensive_validation.get("validation_time", 0)
            }
        }
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"🔥🔥🔥 FIXED ENDPOINT EXCEPTION: {e} 🔥🔥🔥")
        import traceback
        traceback.print_exc()
        
        # Clean up file if it was created
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up file {file_path}: {cleanup_error}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit analysis job: {str(e)}"
        )