"""
Reports endpoints for retrieving PCAP analysis reports and results.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """
    Get a specific report by ID.
    This endpoint implements the get_analysis_report MCP tool functionality.
    """
    try:
        report = await Report.get(report_id)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        return report.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report {report_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get report: {str(e)}"
        )


@router.get("/{report_id}/results")
async def get_report_results(report_id: str) -> Dict[str, Any]:
    """
    Get the analysis results for a specific report.
    """
    try:
        report = await Report.get(report_id)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        if report.status != ReportStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Report is not completed. Current status: {report.status.value}"
            )
        
        if not report.analysis_results:
            raise HTTPException(
                status_code=404,
                detail="Analysis results not found"
            )
        
        return {
            "report_id": str(report.id),
            "filename": report.original_filename,
            "status": report.status.value,
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            "processing_time": report.get_processing_time(),
            "results": report.analysis_results.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report results {report_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get report results: {str(e)}"
        )


@router.get("/")
async def list_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
) -> Dict[str, Any]:
    """
    List reports with optional filtering and pagination.
    """
    try:
        # Build query filters
        filters = {}
        if status:
            try:
                status_enum = ReportStatus(status)
                filters["status"] = status_enum
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid statuses: {[s.value for s in ReportStatus]}"
                )
        
        # Get reports with pagination
        reports = await Report.find(filters).sort("-created_at").skip(offset).limit(limit).to_list()
        
        # Get total count
        total_count = await Report.find(filters).count()
        
        return {
            "reports": [report.to_dict() for report in reports],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": total_count > offset + limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.delete("/{report_id}")
async def delete_report(report_id: str) -> Dict[str, Any]:
    """
    Delete a report and its associated data.
    """
    try:
        report = await Report.get(report_id)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        # Delete associated analysis job
        if report.job_id:
            analysis_job = await AnalysisJob.find_one({"job_id": report.job_id})
            if analysis_job:
                await analysis_job.delete()
        
        # Delete the report
        await report.delete()
        
        # TODO: Clean up uploaded file from filesystem
        # This should be implemented when we add file cleanup functionality
        
        logger.info(f"Report deleted: {report_id}")
        
        return {
            "message": "Report deleted successfully",
            "report_id": report_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete report: {str(e)}"
        )


@router.get("/{report_id}/summary")
async def get_report_summary(report_id: str) -> Dict[str, Any]:
    """
    Get a summary of the report without full analysis results.
    """
    try:
        report = await Report.get(report_id)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        summary = {
            "report_id": str(report.id),
            "filename": report.original_filename,
            "file_size": report.file_size,
            "status": report.status.value,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
            "processing_time": report.get_processing_time(),
        }
        
        # Add basic analysis summary if available
        if report.analysis_results:
            summary["analysis_summary"] = {
                "executive_summary": report.analysis_results.executive_summary,
                "total_packets": report.analysis_results.traffic_stats.get("total_packets", 0),
                "total_bytes": report.analysis_results.traffic_stats.get("total_bytes", 0),
                "duration": report.analysis_results.traffic_stats.get("duration", 0),
                "top_protocols": report.analysis_results.top_protocols[:5] if report.analysis_results.top_protocols else [],
                "issues_found": len(report.analysis_results.network_issues),
            }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report summary {report_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get report summary: {str(e)}"
        ) 