"""
Analysis endpoints for PCAP file upload and analysis submission.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Dict, Any
import os
import hashlib
import logging
from datetime import datetime

from core.config import Settings, get_settings
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob
from tasks.analysis_tasks import analyze_pcap

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_pcap_file(file: UploadFile, settings: Settings) -> None:
    """
    Validate uploaded PCAP file.
    """
    # Check file extension
    if not any(file.filename.lower().endswith(ext) for ext in settings.UPLOAD_ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed extensions: {', '.join(settings.UPLOAD_ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (this is a basic check, actual size validation happens during upload)
    if hasattr(file, 'size') and file.size > settings.UPLOAD_MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.UPLOAD_MAX_SIZE} bytes"
        )


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file.
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


@router.post("/upload")
async def upload_pcap_file(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Upload a PCAP file and start analysis.
    This endpoint implements the start_pcap_analysis MCP tool functionality.
    """
    try:
        # Validate file
        validate_pcap_file(file, settings)
        
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_PATH, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            file_size = len(content)
        
        # Calculate file hash
        file_hash = calculate_file_hash(file_path)
        
        # Create report record
        report = Report(
            filename=filename,
            original_filename=file.filename,
            file_size=file_size,
            file_hash=file_hash,
            upload_path=file_path,
            status=ReportStatus.PENDING,
        )
        await report.insert()
        
        # Submit analysis task to Celery
        task = analyze_pcap.delay(str(report.id), file_path)
        
        # Update report with job ID
        report.job_id = task.id
        await report.save()
        
        # Create analysis job record
        analysis_job = AnalysisJob(
            job_id=task.id,
            report_id=report.id,
        )
        await analysis_job.insert()
        
        logger.info(f"PCAP analysis started for file: {file.filename}, job_id: {task.id}")
        
        return {
            "message": "PCAP file uploaded and analysis started",
            "job_id": task.id,
            "report_id": str(report.id),
            "filename": file.filename,
            "file_size": file_size,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Error uploading PCAP file: {e}")
        # Clean up file if it was created
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        if isinstance(e, HTTPException):
            raise
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload and process PCAP file: {str(e)}"
        )


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
        task = analyze_pcap.AsyncResult(job_id)
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
        task = analyze_pcap.AsyncResult(job_id)
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