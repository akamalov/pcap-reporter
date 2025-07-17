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
    print(f"🔥🔥🔥 SUBMIT ANALYSIS JOB CALLED - ENTRY POINT 🔥🔥🔥")
    print(f"🔥 File: {file.filename if file else 'None'}")
    print(f"🔥 Analysis type: {analysis_type}")
    print(f"🔥 Priority: {priority}")
    print(f"🔥 Settings type: {type(settings)}")
    print(f"🔥 Validation service type: {type(validation_service)}")
    
    # CRITICAL DEBUG: Add try-catch around the ENTIRE function body
    try:
        print(f"🔥 About to call logger.info")
        try:
            logger.info(f"=== SUBMIT ANALYSIS JOB CALLED ===")
            logger.info(f"File: {file.filename if file else 'None'}")
            logger.info(f"Analysis type: {analysis_type}")
            logger.info(f"Priority: {priority}")
            print(f"🔥 Logger calls completed")
        except Exception as e:
            print(f"🔥 Logger error: {e}")
        
        print(f"🔥 About to set file_path = None")
        file_path = None
        print(f"🔥 About to enter main try block")
        
        # MAIN FUNCTION LOGIC STARTS HERE
        try:
        # Extract client IP for security logging and audit trail
        print(f"🔥 About to extract client IP...")
        try:
            client_ip = get_client_ip(request)
            print(f"🔥 Client IP extracted: {client_ip}")
        except Exception as e:
            print(f"🔥 Error extracting client IP: {e}")
            client_ip = "unknown"
        print(f"🔥 Client IP final: {client_ip}")
        
        # Validate no file provided
        print(f"🔥 About to validate file provided...")
        if not file or not file.filename:
            print(f"🔥 No file provided error")
            raise HTTPException(
                status_code=400,
                detail="No file provided. A PCAP file must be uploaded."
            )
        print(f"🔥 File provided: {file.filename}")
        
        # Validate file extension
        print(f"🔥 About to validate file extension...")
        extension_valid = validation_service.validate_file_extension(file.filename)
        print(f"🔥 Extension validation result: {extension_valid} for file: {file.filename}")
        if not extension_valid:
            print(f"🔥 Extension validation failed")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "detail": f"Only {', '.join(settings.UPLOAD_ALLOWED_EXTENSIONS)} files are supported",
                    "supported_types": list(settings.UPLOAD_ALLOWED_EXTENSIONS)
                }
            )
        print(f"🔥 Extension validation passed")
        
        # Read file content to get size and validate
        print(f"🔥 About to read file content...")
        content = await file.read()
        file_size = len(content)
        print(f"🔥 Read file content, size: {file_size}")
        
        # Validate file size with enhanced validation
        print(f"🔥 About to validate file size...")
        size_validation = validation_service.validate_file_size(file_size)
        print(f"🔥 size_validation result: {size_validation}")
        print(f"🔥 size_validation keys: {list(size_validation.keys())}")
        print(f"🔥 size_validation valid: {size_validation.get('valid', 'KEY_NOT_FOUND')}")
        
        if not size_validation.get("valid", False):
            print(f"🔥 Size validation failed!")
            error_msg = size_validation.get("error", "File size validation failed")
            status_code = 413 if "exceeds" in error_msg else 400
            print(f"🔥 About to raise HTTPException for size validation")
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": "File size validation failed",
                    "detail": error_msg,
                    "max_size": settings.UPLOAD_MAX_SIZE,
                    "received_size": file_size
                }
            )
        print(f"🔥 Size validation passed")
        
        # Comprehensive file validation with security, integrity, and format checks
        await file.seek(0)
        comprehensive_validation = await validation_service.comprehensive_file_validation(file, client_ip=client_ip)
        print(f"🔥 comprehensive_validation result: {comprehensive_validation}")
        print(f"🔥 comprehensive_validation keys: {list(comprehensive_validation.keys())}")
        print(f"🔥 comprehensive_validation valid: {comprehensive_validation.get('valid', 'KEY_NOT_FOUND')}")
        
        if not comprehensive_validation.get("valid", False):
            print(f"🔥 COMPREHENSIVE VALIDATION FAILED!")
            print(f"🔥 Available keys: {list(comprehensive_validation.keys())}")
            print(f"🔥 message key: {comprehensive_validation.get('message', 'NO_MESSAGE_KEY')}")
            
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
            
            # Add format detection context
            if "detected_format" in comprehensive_validation:
                error_detail["detected_format"] = comprehensive_validation.get("detected_format")
            if "pcap_validation" in comprehensive_validation:
                pcap_info = comprehensive_validation.get("pcap_validation", {})
                if "magic" in pcap_info:
                    error_detail["magic_number"] = pcap_info.get("magic")
                if "possible_format" in pcap_info:
                    error_detail["suggested_format"] = pcap_info.get("possible_format")
            
            print(f"🔥 About to raise HTTPException with status_code={status_code}")
            raise HTTPException(status_code=status_code, detail=error_detail)
        
        # Validate analysis options
        options_dict = {
            "analysis_type": analysis_type,
            "priority": priority
        }
        print(f"🔥 About to validate options: {options_dict}")
        options_validation = validation_service.validate_analysis_options(options_dict)
        print(f"🔥 options_validation result: {options_validation}")
        print(f"🔥 options_validation keys: {list(options_validation.keys())}")
        print(f"🔥 options_validation valid: {options_validation.get('valid', 'KEY_NOT_FOUND')}")
        
        if not options_validation.get("valid", False):
            print(f"🔥 OPTIONS VALIDATION FAILED!")
            print(f"🔥 Available keys: {list(options_validation.keys())}")
            print(f"🔥 errors key: {options_validation.get('errors', 'NO_ERRORS_KEY')}")
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid analysis options",
                    "errors": options_validation.get("errors", [])
                }
            )
        
        print(f"🔥 OPTIONS VALIDATION PASSED!")
        
        print(f"🔥 About to extract validated_options...")
        print(f"🔥 options_validation keys: {list(options_validation.keys())}")
        print(f"🔥 options key exists: {'options' in options_validation}")
        
        validated_options = options_validation.get("options", {})
        print(f"🔥 validated_options extracted: {validated_options}")
        
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
        
        # Generate job ID first
        job_id = str(uuid.uuid4())
        
        # Estimate completion time
        estimated_time = validation_service.estimate_completion_time(
            file_size, 
            validated_options.get("priority", "normal"), 
            validated_options.get("analysis_type", "comprehensive")
        )
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_time)
        
        # Create report record
        print(f"🔥 DEBUGGING: About to create report with:")
        print(f"🔥   job_id={job_id}")
        print(f"🔥   file_path={file_path}")
        print(f"🔥   original_filename={file.filename}")
        print(f"🔥   file_size={file_size}")
        print(f"🔥   file_hash={file_hash}")
        print(f"🔥   validated_options={validated_options}")
        logger.info(f"Creating report with job_id={job_id}, file_path={file_path}, original_filename={file.filename}")
        
        try:
            # Make sure we're using the right variables
            report_data = {
                'job_id': job_id,
                'original_filename': file.filename,
                'file_size': file_size,
                'file_hash': file_hash,
                'file_path': file_path,
                'status': ReportStatus.PENDING
            }
            print(f"🔥 Report data: {report_data}")
            
            report = Report(**report_data)
            print(f"🔥 Report created successfully!")
        except Exception as e:
            print(f"🔥 ERROR creating report: {e}")
            import traceback
            traceback.print_exc()
            raise
        print(f"🔥 Report created successfully, inserting into database")
        logger.info(f"Report created successfully, inserting into database")
        await report.insert()
        print(f"🔥 Report inserted with id: {report.id}")
        logger.info(f"Report inserted with id: {report.id}")
        
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
            "analysis_type": validated_options.get("analysis_type", "comprehensive"),
            "priority": validated_options.get("priority", "normal"),
            "validation": {
                "validation_id": comprehensive_validation.get("validation_id"),
                "security_score": comprehensive_validation.get("security_score", "unknown"),
                "file_type": comprehensive_validation.get("file_type", "pcap"),
                "validation_time": comprehensive_validation.get("validation_time", 0)
            }
        }
        
        # Add options if they differ from defaults
        if validated_options.get("analysis_type", "comprehensive") != "comprehensive":
            response["options"] = {k: v for k, v in validated_options.items() 
                                  if k not in ["analysis_type", "priority"]}
        
        return response
        
    except Exception as e:
        logger.error(f"Error submitting analysis job: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Full traceback: {error_traceback}")
        print(f"🔥 FULL TRACEBACK: {error_traceback}")
        
        # CRITICAL DEBUG: Check if this is the KeyError we're looking for
        if "KeyError" in str(e) and "'error'" in str(e):
            print(f"🔥🔥🔥 FOUND THE KEYERROR! 🔥🔥🔥")
            print(f"🔥 Exception type: {type(e)}")
            print(f"🔥 Exception message: {str(e)}")
            print(f"🔥 Exception args: {e.args}")
            
            # Try to get more details about the KeyError
            try:
                # Extract the problematic line from traceback
                tb_lines = error_traceback.split('\n')
                for i, line in enumerate(tb_lines):
                    if "KeyError" in line or "'error'" in line:
                        print(f"🔥 KeyError context line {i}: {line}")
                        if i > 0:
                            print(f"🔥 Previous line: {tb_lines[i-1]}")
                        if i < len(tb_lines) - 1:
                            print(f"🔥 Next line: {tb_lines[i+1]}")
            except Exception as debug_error:
                print(f"🔥 Debug error: {debug_error}")
        
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
    
    except Exception as outer_e:
        # CRITICAL DEBUG: This catches KeyErrors happening at the function level
        print(f"🔥🔥🔥 OUTER EXCEPTION CAUGHT! 🔥🔥🔥")
        print(f"🔥 Exception type: {type(outer_e)}")
        print(f"🔥 Exception message: {str(outer_e)}")
        print(f"🔥 Exception args: {outer_e.args}")
        
        import traceback
        outer_traceback = traceback.format_exc()
        print(f"🔥 OUTER TRACEBACK: {outer_traceback}")
        
        # Check if this is the KeyError we're looking for
        if "KeyError" in str(outer_e) and "'error'" in str(outer_e):
            print(f"🔥🔥🔥 FOUND THE KEYERROR IN OUTER HANDLER! 🔥🔥🔥")
            
            # Extract the problematic line from traceback
            try:
                tb_lines = outer_traceback.split('\n')
                for i, line in enumerate(tb_lines):
                    if "KeyError" in line or "'error'" in line:
                        print(f"🔥 KeyError context line {i}: {line}")
                        if i > 0:
                            print(f"🔥 Previous line: {tb_lines[i-1]}")
                        if i < len(tb_lines) - 1:
                            print(f"🔥 Next line: {tb_lines[i+1]}")
            except Exception as debug_error:
                print(f"🔥 Debug error: {debug_error}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit analysis job: {str(outer_e)}"
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