"""
Analysis endpoints for PCAP file upload and analysis submission.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request
from typing import Dict, Any, Optional
import os
import hashlib
import logging
import uuid
from datetime import datetime, timedelta

from core.config import Settings, get_settings
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from tasks.analysis_tasks import analyze_pcap_file
from services.validation_service import get_validation_service, ValidationService

logger = logging.getLogger(__name__)

router = APIRouter()


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file.
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request headers with proxy support.
    """
    # Check for forwarded headers (load balancer/proxy)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # Take the first IP in the chain (original client)
        return x_forwarded_for.split(",")[0].strip()
    
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    # Fall back to direct connection IP
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"


@router.post("/submit")
async def submit_analysis_job(
    request: Request,
    file: UploadFile = File(...),
    analysis_type: Optional[str] = Form("comprehensive"),
    priority: Optional[str] = Form("normal"),
    settings: Settings = Depends(get_settings),
    validation_service: ValidationService = Depends(get_validation_service)
) -> Dict[str, Any]:
    """
    Submit a PCAP file for analysis with options.
    Enhanced version with comprehensive validation and analysis options.
    """
    file_path = None
    try:
        # Extract client IP for security logging and audit trail
        client_ip = get_client_ip(request)
        
        # Validate no file provided
        if not file or not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided. A PCAP file must be uploaded."
            )
        
        # Validate file extension
        if not validation_service.validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "detail": f"Only {', '.join(settings.UPLOAD_ALLOWED_EXTENSIONS)} files are supported",
                    "supported_types": list(settings.UPLOAD_ALLOWED_EXTENSIONS)
                }
            )
        
        # Read file content to get size and validate
        content = await file.read()
        file_size = len(content)
        
        # Validate file size with enhanced validation
        size_validation = validation_service.validate_file_size(file_size)
        if not size_validation["valid"]:
            status_code = 413 if "exceeds" in size_validation["error"] else 400
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": "File size validation failed",
                    "detail": size_validation["error"],
                    "max_size": settings.UPLOAD_MAX_SIZE,
                    "received_size": file_size
                }
            )
        
        # Comprehensive file validation with security, integrity, and format checks
        await file.seek(0)
        comprehensive_validation = await validation_service.comprehensive_file_validation(file, client_ip=client_ip)
        
        if not comprehensive_validation["valid"]:
            # Determine appropriate status code based on security or format issues
            status_code = 403 if comprehensive_validation.get("security_threat") else 400
            error_detail = {
                "error": "Comprehensive validation failed",
                "detail": comprehensive_validation["error"],
                "validation_id": comprehensive_validation.get("validation_id")
            }
            
            # Add security context if available
            if comprehensive_validation.get("security_threat"):
                error_detail["security_issues"] = comprehensive_validation.get("security_issues", [])
                error_detail["threat_severity"] = comprehensive_validation.get("severity", "unknown")
            
            # Add format detection context
            if "detected_format" in comprehensive_validation:
                error_detail["detected_format"] = comprehensive_validation["detected_format"]
            if "pcap_validation" in comprehensive_validation:
                pcap_info = comprehensive_validation["pcap_validation"]
                if "magic" in pcap_info:
                    error_detail["magic_number"] = pcap_info["magic"]
                if "possible_format" in pcap_info:
                    error_detail["suggested_format"] = pcap_info["possible_format"]
            
            raise HTTPException(status_code=status_code, detail=error_detail)
        
        # Validate analysis options
        options_dict = {
            "analysis_type": analysis_type,
            "priority": priority
        }
        options_validation = validation_service.validate_analysis_options(options_dict)
        
        if not options_validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid analysis options",
                    "errors": options_validation["errors"]
                }
            )
        
        validated_options = options_validation["options"]
        
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
        
        # Generate unique filename with UUID to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{unique_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_PATH, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Calculate file hash
        file_hash = calculate_file_hash(file_path)
        
        # Estimate completion time
        estimated_time = validation_service.estimate_completion_time(
            file_size, 
            validated_options["priority"], 
            validated_options["analysis_type"]
        )
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_time)
        
        # Create report record
        report = Report(
            filename=filename,
            original_filename=file.filename,
            file_size=file_size,
            file_hash=file_hash,
            upload_path=file_path,
            status=ReportStatus.PENDING,
            analysis_options=validated_options
        )
        await report.insert()
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create analysis job record first
        analysis_job = AnalysisJob(
            job_id=job_id,
            report_id=report.id,
            status=JobStatus.PENDING,
            options=validated_options,
            estimated_completion=estimated_completion
        )
        await analysis_job.insert()
        
        # Submit analysis task to Celery
        task = analyze_pcap_file.delay(
            str(report.id), 
            file_path
        )
        
        # Update records with Celery task ID
        analysis_job.celery_task_id = task.id
        await analysis_job.save()
        
        report.job_id = task.id
        await report.save()
        
        logger.info(f"PCAP analysis submitted - file: {file.filename}, job_id: {job_id}, task_id: {task.id}, "
                   f"client_ip: {client_ip}, validation_id: {comprehensive_validation.get('validation_id', 'N/A')}")
        
        # Build response with validation details
        response = {
            "job_id": job_id,
            "status": "pending",
            "filename": file.filename,
            "file_size": file_size,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "estimated_completion": estimated_completion.isoformat() + "Z",
            "analysis_type": validated_options["analysis_type"],
            "priority": validated_options["priority"],
            "validation": {
                "validation_id": comprehensive_validation.get("validation_id"),
                "security_score": comprehensive_validation.get("security_score", "unknown"),
                "file_type": comprehensive_validation.get("file_type", "pcap"),
                "validation_time": comprehensive_validation.get("validation_time", 0)
            }
        }
        
        # Add options if they differ from defaults
        if validated_options["analysis_type"] != "comprehensive":
            response["options"] = {k: v for k, v in validated_options.items() 
                                  if k not in ["analysis_type", "priority"]}
        
        return response
        
    except Exception as e:
        logger.error(f"Error submitting analysis job: {e}")
        
        # Clean up file if it was created
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up file {file_path}: {cleanup_error}")
        
        if isinstance(e, HTTPException):
            raise
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit analysis job: {str(e)}"
        )


# Keep the old upload endpoint for backward compatibility
@router.post("/upload")
async def upload_pcap_file(
    request: Request,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    validation_service: ValidationService = Depends(get_validation_service)
) -> Dict[str, Any]:
    """
    Legacy upload endpoint for backward compatibility.
    Redirects to the new submit endpoint with default options.
    """
    return await submit_analysis_job(request, file, "comprehensive", "normal", settings, validation_service)


@router.get("/status/{job_id}")
async def get_analysis_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of an analysis job.
    """
    try:
        # Find the analysis job
        analysis_job = await AnalysisJob.find_one({"job_id": job_id})
        if not analysis_job:
            raise HTTPException(
                status_code=404,
                detail="Analysis job not found"
            )
        
        # Get the associated report
        report = await Report.get(analysis_job.report_id)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Associated report not found"
            )
        
        # Get Celery task status
        task = analyze_pcap_file.AsyncResult(job_id)
        celery_status = task.status
        celery_result = task.result if task.ready() else None
        
        return {
            "job_id": job_id,
            "status": analysis_job.status.value,
            "progress": analysis_job.progress,
            "current_step": analysis_job.current_step,
            "celery_status": celery_status,
            "report": {
                "id": str(report.id),
                "filename": report.original_filename,
                "file_size": report.file_size,
                "status": report.status.value,
                "created_at": report.created_at.isoformat(),
                "updated_at": report.updated_at.isoformat(),
            },
            "result": celery_result if celery_result else None,
            "error": analysis_job.error,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis status: {str(e)}"
        )


@router.delete("/cancel/{job_id}")
async def cancel_analysis(job_id: str) -> Dict[str, Any]:
    """
    Cancel a running analysis job.
    """
    try:
        # Find the analysis job
        analysis_job = await AnalysisJob.find_one({"job_id": job_id})
        if not analysis_job:
            raise HTTPException(
                status_code=404,
                detail="Analysis job not found"
            )
        
        # Cancel the Celery task
        task = analyze_pcap_file.AsyncResult(job_id)
        task.revoke(terminate=True)
        
        # Update job status
        analysis_job.fail_job("Cancelled by user")
        await analysis_job.save()
        
        # Update report status
        report = await Report.get(analysis_job.report_id)
        if report:
            report.update_status(ReportStatus.FAILED, "Analysis cancelled by user")
            await report.save()
        
        logger.info(f"Analysis job cancelled: {job_id}")
        
        return {
            "message": "Analysis job cancelled",
            "job_id": job_id,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel analysis: {str(e)}"
        ) 