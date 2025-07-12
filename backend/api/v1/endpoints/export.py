"""
Export endpoints for generating downloadable reports in various formats.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import logging
from io import BytesIO

from core.database import get_database
from services.pdf_export import PDFExportService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pdf/{job_id}")
async def export_pdf(job_id: str) -> StreamingResponse:
    """
    Export analysis report as PDF.
    
    Args:
        job_id: The analysis job ID to export
        
    Returns:
        StreamingResponse: PDF file download
        
    Raises:
        HTTPException: 404 if report not found, 400 if not completed, 500 if generation fails
    """
    try:
        logger.info(f"Starting PDF export for job {job_id}")
        
        # Get database connection
        db = get_database()
        
        # Query the reports collection for the job
        reports_collection = db["reports"]
        report = reports_collection.find_one({"job_id": job_id})
        
        if not report:
            logger.warning(f"Report not found for job {job_id}")
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        # Check if report is completed
        if report.get("status") != "completed":
            logger.warning(f"Report {job_id} is not completed, status: {report.get('status')}")
            raise HTTPException(
                status_code=400,
                detail=f"Report is not completed yet. Current status: {report.get('status', 'unknown')}"
            )
        
        # Convert MongoDB document to PDF-compatible format
        pdf_data = _convert_mongodb_report_to_pdf_format(report)
        
        # Generate PDF
        pdf_service = PDFExportService()
        pdf_bytes = pdf_service.generate_pdf_report(pdf_data)
        
        # Generate filename
        original_filename = report.get("original_filename", report.get("filename", "report.pcap"))
        pdf_filename = pdf_service.generate_pdf_filename(original_filename)
        
        logger.info(f"PDF generated successfully for job {job_id}, size: {len(pdf_bytes)} bytes")
        
        # Return streaming response
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={pdf_filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


def _convert_mongodb_report_to_pdf_format(mongo_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB report document to the format expected by PDFExportService.
    
    Args:
        mongo_report: Raw MongoDB document
        
    Returns:
        Dict formatted for PDF generation
    """
    # Base report structure
    pdf_data = {
        "job_id": mongo_report.get("job_id", str(mongo_report.get("_id", ""))),
        "filename": mongo_report.get("original_filename", mongo_report.get("filename", "unknown.pcap")),
        "status": mongo_report.get("status", "completed"),
        "file_size": mongo_report.get("file_size", 0),
        "created_at": mongo_report.get("created_at", ""),
        "completed_at": mongo_report.get("completed_at", ""),
        "file_hash": mongo_report.get("file_hash", ""),
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
    if "processing_time" in mongo_report:
        pdf_data["processing_time"] = mongo_report["processing_time"]
    
    # Extract analysis results if present
    analysis_results = mongo_report.get("analysis_results", {})
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
        if "http_analysis" in analysis_results:
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
        if "dns_analysis" in analysis_results:
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