"""
Reports endpoints for retrieving PCAP analysis reports and results.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
import logging
from io import BytesIO

from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob
from services.pdf_export import PDFExportService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_report_by_id(report_id: str) -> Optional[Report]:
    """
    Helper function to get a report by job_id (UUID string) or MongoDB _id.
    """
    try:
        print(f"🔥 Searching for report with job_id: {report_id}")
        # Try to find by job_id first (UUID string)
        report = await Report.find_one({"job_id": report_id})
        print(f"🔥 Found report by job_id: {report is not None}")
        
        # If not found by job_id, try by MongoDB _id (for backward compatibility)
        if not report:
            try:
                from bson import ObjectId
                if ObjectId.is_valid(report_id):
                    print(f"🔥 Trying to find by ObjectId: {report_id}")
                    report = await Report.get(report_id)
                    print(f"🔥 Found report by ObjectId: {report is not None}")
            except Exception as e:
                print(f"🔥 Error finding by ObjectId: {e}")
                pass
        
        return report
    except Exception as e:
        print(f"🔥 Error in get_report_by_id: {e}")
        raise



@router.get("/by-job-id/{job_id}")
async def get_report_by_job_id(job_id: str) -> Dict[str, Any]:
    """
    Get a specific report by job ID (UUID).
    This endpoint is specifically for job ID lookups to avoid path validation issues.
    """
    try:
        # Only search by job_id, not by MongoDB ObjectId
        report = await Report.find_one({"job_id": job_id})
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        return report.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report by job_id {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get report: {str(e)}"
        )


@router.get("/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """
    Get a specific report by MongoDB ObjectId.
    This endpoint implements the get_analysis_report MCP tool functionality.
    """
    print(f"🔥 get_report called with report_id: {report_id}")
    try:
        report = await get_report_by_id(report_id)
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
        report = await get_report_by_id(report_id)
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
        report = await get_report_by_id(report_id)
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
        report = await get_report_by_id(report_id)
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


@router.get("/{report_id}/download")
async def download_report_pdf(report_id: str) -> StreamingResponse:
    """
    Download a PDF version of the analysis report.
    This endpoint generates a professional PDF document containing all analysis results.
    """
    try:
        # Get the report
        report = await get_report_by_id(report_id)
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        # Check if report is completed
        if report.status != ReportStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Report is not completed yet. Current status: {report.status.value}"
            )
        
        # Get report data in the format expected by PDF service
        report_data = report.to_dict()
        
        # Convert the MongoDB report structure to match the frontend API structure
        pdf_data = _convert_report_for_pdf(report_data)
        
        # Generate PDF
        pdf_service = PDFExportService()
        pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
        
        # Generate filename
        pdf_filename = pdf_service.generate_pdf_filename(report.original_filename)
        
        # Create streaming response
        pdf_stream = BytesIO(pdf_bytes)
        
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={pdf_filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF for report {report_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


def _convert_report_for_pdf(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB report structure to the format expected by PDF service.
    This adapts the backend data model to match the frontend API structure.
    """
    # Start with the report data
    pdf_data = {
        "job_id": report_data.get("_id", str(report_data.get("id", ""))),
        "filename": report_data.get("original_filename", "unknown.pcap"),
        "status": report_data.get("status", "completed"),
        "file_size": report_data.get("file_size", 0),
        "created_at": report_data.get("created_at", ""),
        "completed_at": report_data.get("completed_at", ""),
        "file_hash": report_data.get("file_hash", ""),
        "analysis_type": "comprehensive",
        "duration": 0,
        "total_packets": 0,
        "unique_ips": 0,
        "unique_ports": 0,
        "protocols": {},
        "packet_sizes": {
            "min": 0,
            "max": 0,
            "avg": 0,
            "total_bytes": 0
        }
    }
    
    # Add processing time
    if "processing_time" in report_data:
        pdf_data["processing_time"] = report_data["processing_time"]
    
    # Extract analysis results if present
    analysis_results = report_data.get("analysis_results", {})
    if analysis_results:
        # Extract traffic stats
        traffic_stats = analysis_results.get("traffic_stats", {})
        pdf_data["total_packets"] = traffic_stats.get("total_packets", 0)
        pdf_data["duration"] = traffic_stats.get("duration", 0)
        pdf_data["unique_ips"] = traffic_stats.get("unique_ips", 0)
        pdf_data["unique_ports"] = traffic_stats.get("unique_ports", 0)
        
        # Extract protocols
        top_protocols = analysis_results.get("top_protocols", [])
        protocols = {}
        for protocol_info in top_protocols:
            if isinstance(protocol_info, dict):
                protocols[protocol_info.get("name", "Unknown")] = protocol_info.get("count", 0)
            elif isinstance(protocol_info, str):
                protocols[protocol_info] = 1
        pdf_data["protocols"] = protocols
        
        # Extract packet size stats
        if "packet_size_distribution" in analysis_results:
            size_dist = analysis_results["packet_size_distribution"]
            pdf_data["packet_sizes"] = {
                "min": size_dist.get("min_size", 0),
                "max": size_dist.get("max_size", 0),
                "avg": size_dist.get("average_size", 0),
                "total_bytes": traffic_stats.get("total_bytes", 0)
            }
        
        # Convert protocol analysis
        protocol_analysis = {}
        
        # TCP Analysis
        tcp_conversations = analysis_results.get("top_tcp_conversations", [])
        if tcp_conversations:
            protocol_analysis["tcp"] = {
                "total_connections": len(tcp_conversations),
                "established_connections": len(tcp_conversations),  # Assume all are established
                "failed_connections": 0,
                "average_connection_duration": 30.0,  # Default value
                "top_conversations": [
                    {
                        "src_ip": conv.get("src_ip", "unknown"),
                        "dst_ip": conv.get("dst_ip", "unknown"),
                        "src_port": conv.get("src_port", 0),
                        "dst_port": conv.get("dst_port", 0),
                        "packets": conv.get("packet_count", 0),
                        "bytes": conv.get("bytes", 0)
                    }
                    for conv in tcp_conversations[:10]
                ]
            }
        
        # HTTP Analysis
        if "http_analysis" in analysis_results and analysis_results["http_analysis"] is not None:
            http_data = analysis_results["http_analysis"]
            protocol_analysis["http"] = {
                "total_requests": http_data.get("total_requests", 0),
                "status_codes": http_data.get("status_codes", {}),
                "methods": http_data.get("methods", {}),
                "top_domains": [
                    {"domain": domain, "requests": count}
                    for domain, count in http_data.get("top_domains", {}).items()
                ]
            }
        
        # DNS Analysis
        if "dns_analysis" in analysis_results and analysis_results["dns_analysis"] is not None:
            dns_data = analysis_results["dns_analysis"]
            protocol_analysis["dns"] = {
                "total_queries": dns_data.get("total_queries", 0),
                "query_types": dns_data.get("query_types", {}),
                "top_domains": [
                    {"domain": domain, "queries": count}
                    for domain, count in dns_data.get("top_domains", {}).items()
                ],
                "response_codes": dns_data.get("response_codes", {})
            }
        
        if protocol_analysis:
            pdf_data["protocol_analysis"] = protocol_analysis
        
        # Convert security analysis
        network_issues = analysis_results.get("network_issues", [])
        security_analysis = {
            "suspicious_ips": [],
            "port_scans": [],
            "anomalies": []
        }
        
        for issue in network_issues:
            issue_type = issue.get("type", "").lower()
            if "suspicious" in issue_type or "malicious" in issue_type:
                security_analysis["suspicious_ips"].append({
                    "ip": issue.get("details", {}).get("ip", "unknown"),
                    "reason": issue.get("description", "Suspicious activity"),
                    "severity": issue.get("severity", "medium"),
                    "count": 1
                })
            elif "scan" in issue_type:
                security_analysis["port_scans"].append({
                    "scanner_ip": issue.get("details", {}).get("src_ip", "unknown"),
                    "target_ip": issue.get("details", {}).get("dst_ip", "unknown"),
                    "ports_scanned": issue.get("details", {}).get("port_count", 1),
                    "scan_type": "TCP scan"
                })
            else:
                security_analysis["anomalies"].append({
                    "type": issue.get("type", "Unknown"),
                    "description": issue.get("description", "Network anomaly detected"),
                    "severity": issue.get("severity", "low"),
                    "timestamp": issue.get("timestamp", "")
                })
        
        if any(security_analysis.values()):
            pdf_data["security_analysis"] = security_analysis
        
        # Convert performance metrics
        top_talkers = analysis_results.get("top_talkers", [])
        if top_talkers:
            performance_metrics = {
                "top_talkers": [
                    {
                        "ip": talker.get("ip", "unknown"),
                        "bytes_sent": talker.get("bytes_sent", 0),
                        "bytes_received": talker.get("bytes_received", 0),
                        "total_bytes": talker.get("bytes_sent", 0) + talker.get("bytes_received", 0)
                    }
                    for talker in top_talkers
                ]
            }
            pdf_data["performance_metrics"] = performance_metrics
        
        # Include network diagrams if present
        if "network_diagrams" in analysis_results:
            pdf_data["analysis_results"] = {
                "network_diagrams": analysis_results["network_diagrams"]
            }
    
    return pdf_data 