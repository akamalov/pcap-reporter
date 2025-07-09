"""
MCP (Model Context Protocol) Server for PCAP Reporter.

This server exposes PCAP analysis functionality as MCP tools that can be used
by AI assistants and other applications.
"""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, 
    TextContent, 
    ImageContent, 
    EmbeddedResource,
    CallToolResult
)

# Import our application components
from core.database import init_database
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob
from tasks.analysis_tasks import analyze_pcap_file, validate_pcap_file
from services.pcap_analyzer import analyzer

logger = logging.getLogger(__name__)

# Initialize the MCP server
app = Server("pcap-reporter")

# Global variables for async context
_db_initialized = False

async def ensure_database():
    """Ensure database is initialized."""
    global _db_initialized
    if not _db_initialized:
        await init_database()
        _db_initialized = True


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="upload_pcap_file",
            description="Upload and analyze a PCAP file. Returns analysis job ID for tracking progress.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the PCAP file to analyze"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Original filename of the PCAP file"
                    },
                    "validate_only": {
                        "type": "boolean",
                        "description": "If true, only validate the file without running full analysis",
                        "default": False
                    }
                },
                "required": ["file_path", "filename"]
            }
        ),
        Tool(
            name="get_analysis_status",
            description="Get the status of a PCAP analysis job.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The analysis job ID returned from upload_pcap_file"
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="get_analysis_report",
            description="Get the complete analysis report for a completed job.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "The report ID to retrieve"
                    }
                },
                "required": ["report_id"]
            }
        ),
        Tool(
            name="list_reports",
            description="List all analysis reports with optional filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status (pending, processing, completed, failed)",
                        "enum": ["pending", "processing", "completed", "failed"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of reports to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of reports to skip",
                        "default": 0,
                        "minimum": 0
                    }
                }
            }
        ),
        Tool(
            name="cancel_analysis",
            description="Cancel a running analysis job.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The analysis job ID to cancel"
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="delete_report",
            description="Delete a report and its associated data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "The report ID to delete"
                    }
                },
                "required": ["report_id"]
            }
        ),
        Tool(
            name="analyze_pcap_direct",
            description="Directly analyze a PCAP file without using the job queue (for small files).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the PCAP file to analyze"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    await ensure_database()
    
    try:
        if name == "upload_pcap_file":
            return await handle_upload_pcap_file(arguments)
        elif name == "get_analysis_status":
            return await handle_get_analysis_status(arguments)
        elif name == "get_analysis_report":
            return await handle_get_analysis_report(arguments)
        elif name == "list_reports":
            return await handle_list_reports(arguments)
        elif name == "cancel_analysis":
            return await handle_cancel_analysis(arguments)
        elif name == "delete_report":
            return await handle_delete_report(arguments)
        elif name == "analyze_pcap_direct":
            return await handle_analyze_pcap_direct(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )],
                isError=True
            )
    except Exception as e:
        logger.error(f"Error in tool call {name}: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )],
            isError=True
        )


async def handle_upload_pcap_file(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle PCAP file upload and analysis."""
    file_path = arguments["file_path"]
    filename = arguments["filename"]
    validate_only = arguments.get("validate_only", False)
    
    # Validate file exists
    if not os.path.exists(file_path):
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"File not found: {file_path}"
            )],
            isError=True
        )
    
    # Get file info
    file_size = os.path.getsize(file_path)
    
    if validate_only:
        # Just validate the file
        validation_result = validate_pcap_file.delay(file_path)
        result = validation_result.get(timeout=30)  # Wait up to 30 seconds
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        )
    
    # Create report entry
    report = Report(
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        status=ReportStatus.PENDING
    )
    await report.save()
    
    # Start analysis task
    task = analyze_pcap_file.delay(str(report.id), file_path)
    
    # Update report with job ID
    report.job_id = task.id
    await report.save()
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps({
                "status": "started",
                "report_id": str(report.id),
                "job_id": task.id,
                "filename": filename,
                "file_size": file_size,
                "message": "PCAP analysis started. Use get_analysis_status to check progress."
            }, indent=2)
        )]
    )


async def handle_get_analysis_status(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle getting analysis status."""
    job_id = arguments["job_id"]
    
    # Get analysis job from database
    analysis_job = await AnalysisJob.find_one({"job_id": job_id})
    
    if not analysis_job:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Analysis job not found: {job_id}"
            )],
            isError=True
        )
    
    # Get Celery task status
    from celery.result import AsyncResult
    task_result = AsyncResult(job_id)
    
    status_info = {
        "job_id": job_id,
        "report_id": analysis_job.report_id,
        "status": analysis_job.status.value,
        "progress": analysis_job.progress,
        "message": analysis_job.message,
        "created_at": analysis_job.created_at.isoformat(),
        "updated_at": analysis_job.updated_at.isoformat(),
        "celery_state": task_result.state,
        "celery_info": task_result.info if task_result.info else None
    }
    
    if analysis_job.completed_at:
        status_info["completed_at"] = analysis_job.completed_at.isoformat()
    
    if analysis_job.error_message:
        status_info["error_message"] = analysis_job.error_message
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(status_info, indent=2)
        )]
    )


async def handle_get_analysis_report(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle getting analysis report."""
    report_id = arguments["report_id"]
    
    report = await Report.get(report_id)
    if not report:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Report not found: {report_id}"
            )],
            isError=True
        )
    
    if report.status != ReportStatus.COMPLETED:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "report_id": report_id,
                    "status": report.status.value,
                    "message": "Report is not completed yet. Use get_analysis_status to check progress."
                }, indent=2)
            )]
        )
    
    # Return the complete report
    report_data = report.to_dict()
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(report_data, indent=2, default=str)
        )]
    )


async def handle_list_reports(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle listing reports."""
    status_filter = arguments.get("status")
    limit = arguments.get("limit", 10)
    offset = arguments.get("offset", 0)
    
    # Build query filters
    filters = {}
    if status_filter:
        try:
            status_enum = ReportStatus(status_filter)
            filters["status"] = status_enum
        except ValueError:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Invalid status: {status_filter}"
                )],
                isError=True
            )
    
    # Get reports
    reports = await Report.find(filters).sort("-created_at").skip(offset).limit(limit).to_list()
    total_count = await Report.find(filters).count()
    
    # Format response
    report_list = []
    for report in reports:
        report_summary = {
            "report_id": str(report.id),
            "filename": report.original_filename,
            "file_size": report.file_size,
            "status": report.status.value,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        }
        
        if report.completed_at:
            report_summary["completed_at"] = report.completed_at.isoformat()
            report_summary["processing_time"] = report.get_processing_time()
        
        if report.error_message:
            report_summary["error_message"] = report.error_message
        
        # Add basic analysis summary if available
        if report.analysis_results:
            report_summary["analysis_summary"] = {
                "total_packets": report.analysis_results.traffic_stats.get("total_packets", 0),
                "duration": report.analysis_results.traffic_stats.get("duration", 0),
                "top_protocol": report.analysis_results.top_protocols[0].protocol if report.analysis_results.top_protocols else "Unknown",
                "issues_found": len(report.analysis_results.network_issues),
                "security_alerts": len(report.analysis_results.security_alerts)
            }
        
        report_list.append(report_summary)
    
    response = {
        "reports": report_list,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": total_count > offset + limit
        }
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
    )


async def handle_cancel_analysis(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle canceling analysis."""
    job_id = arguments["job_id"]
    
    # Get analysis job
    analysis_job = await AnalysisJob.find_one({"job_id": job_id})
    if not analysis_job:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Analysis job not found: {job_id}"
            )],
            isError=True
        )
    
    # Cancel Celery task
    from celery.result import AsyncResult
    task_result = AsyncResult(job_id)
    task_result.revoke(terminate=True)
    
    # Update job status
    analysis_job.status = JobStatus.CANCELLED
    analysis_job.message = "Analysis cancelled by user"
    analysis_job.updated_at = datetime.utcnow()
    await analysis_job.save()
    
    # Update report status
    report = await Report.get(analysis_job.report_id)
    if report:
        report.status = ReportStatus.CANCELLED
        await report.save()
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps({
                "status": "cancelled",
                "job_id": job_id,
                "message": "Analysis job cancelled successfully"
            }, indent=2)
        )]
    )


async def handle_delete_report(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle deleting a report."""
    report_id = arguments["report_id"]
    
    report = await Report.get(report_id)
    if not report:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Report not found: {report_id}"
            )],
            isError=True
        )
    
    # Delete associated analysis job
    if report.job_id:
        analysis_job = await AnalysisJob.find_one({"job_id": report.job_id})
        if analysis_job:
            await analysis_job.delete()
    
    # Clean up file if it exists
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {report.file_path}: {e}")
    
    # Delete the report
    await report.delete()
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps({
                "status": "deleted",
                "report_id": report_id,
                "message": "Report deleted successfully"
            }, indent=2)
        )]
    )


async def handle_analyze_pcap_direct(arguments: Dict[str, Any]) -> CallToolResult:
    """Handle direct PCAP analysis (synchronous)."""
    file_path = arguments["file_path"]
    
    if not os.path.exists(file_path):
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"File not found: {file_path}"
            )],
            isError=True
        )
    
    try:
        # Perform direct analysis
        analysis_results = await analyzer.analyze_pcap(file_path)
        
        # Convert to dict for JSON serialization
        results_dict = {
            "file_path": file_path,
            "analysis_completed_at": datetime.utcnow().isoformat(),
            "executive_summary": analysis_results.executive_summary,
            "traffic_stats": analysis_results.traffic_stats,
            "top_protocols": [
                {
                    "protocol": p.protocol,
                    "packet_count": p.packet_count,
                    "percentage": p.percentage
                }
                for p in analysis_results.top_protocols
            ],
            "top_hosts": [
                {
                    "ip_address": h.ip_address,
                    "packet_count": h.packet_count,
                    "bytes_sent": h.bytes_sent,
                    "bytes_received": h.bytes_received
                }
                for h in analysis_results.top_hosts
            ],
            "network_issues": [
                {
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "description": i.description,
                    "affected_hosts": i.affected_hosts,
                    "recommendation": i.recommendation
                }
                for i in analysis_results.network_issues
            ],
            "security_alerts": [
                {
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "description": a.description,
                    "source_ip": a.source_ip,
                    "timestamp": a.timestamp
                }
                for a in analysis_results.security_alerts
            ],
            "dns_analysis": analysis_results.dns_analysis,
            "tcp_analysis": analysis_results.tcp_analysis
        }
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(results_dict, indent=2, default=str)
            )]
        )
        
    except Exception as e:
        logger.error(f"Direct analysis failed: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Analysis failed: {str(e)}"
            )],
            isError=True
        )


def main():
    """Main entry point for the MCP server."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    asyncio.run(stdio_server(app))


if __name__ == "__main__":
    main() 