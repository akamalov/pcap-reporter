"""
Celery tasks for PCAP analysis processing.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

from celery import current_task
from celery.exceptions import Retry

from core.celery_app import celery_app
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from services.pcap_analyzer import analyzer

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="analyze_pcap_file")
def analyze_pcap_file(self, report_id: str, file_path: str) -> Dict[str, Any]:
    """
    Analyze a PCAP file and update the report with results.
    
    Args:
        report_id: ID of the report to update
        file_path: Path to the PCAP file to analyze
        
    Returns:
        Dict containing analysis results and status
    """
    task_id = self.request.id
    logger.info(f"Starting PCAP analysis task {task_id} for report {report_id}")
    
    async def run_analysis():
        try:
            # Get the report
            report = await Report.get(report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            # Update report status
            report.status = ReportStatus.PROCESSING
            report.started_at = datetime.utcnow()
            await report.save()
            
            # Create or update analysis job
            analysis_job = await AnalysisJob.find_one({"job_id": task_id})
            if not analysis_job:
                analysis_job = AnalysisJob(
                    job_id=task_id,
                    report_id=report_id,
                    status=JobStatus.RUNNING,
                    progress=0,
                    message="Starting analysis..."
                )
                await analysis_job.save()
            
            # Progress callback to update job status
            async def progress_callback(progress: int, message: str):
                analysis_job.progress = progress
                analysis_job.message = message
                analysis_job.updated_at = datetime.utcnow()
                await analysis_job.save()
                
                # Update Celery task state
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "progress": progress,
                        "message": message,
                        "report_id": report_id
                    }
                )
            
            # Perform the analysis
            analysis_results = await analyzer.analyze_pcap(file_path, progress_callback)
            
            # Update report with results
            report.analysis_results = analysis_results
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            await report.save()
            
            # Update analysis job
            analysis_job.status = JobStatus.COMPLETED
            analysis_job.progress = 100
            analysis_job.message = "Analysis completed successfully"
            analysis_job.completed_at = datetime.utcnow()
            await analysis_job.save()
            
            logger.info(f"PCAP analysis completed for report {report_id}")
            
            return {
                "status": "completed",
                "report_id": report_id,
                "task_id": task_id,
                "message": "Analysis completed successfully",
                "results_summary": {
                    "total_packets": analysis_results.traffic_stats.get("total_packets", 0),
                    "duration": analysis_results.traffic_stats.get("duration", 0),
                    "unique_ips": analysis_results.traffic_stats.get("unique_ip_addresses", 0),
                    "top_protocol": analysis_results.top_protocols[0].protocol if analysis_results.top_protocols else "Unknown",
                    "issues_found": len(analysis_results.network_issues),
                    "security_alerts": len(analysis_results.security_alerts)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in PCAP analysis task {task_id}: {e}")
            
            # Update report status
            try:
                report = await Report.get(report_id)
                if report:
                    report.status = ReportStatus.FAILED
                    report.error_message = str(e)
                    await report.save()
            except Exception as save_error:
                logger.error(f"Failed to update report status: {save_error}")
            
            # Update analysis job
            try:
                analysis_job = await AnalysisJob.find_one({"job_id": task_id})
                if analysis_job:
                    analysis_job.status = JobStatus.FAILED
                    analysis_job.error_message = str(e)
                    analysis_job.updated_at = datetime.utcnow()
                    await analysis_job.save()
            except Exception as save_error:
                logger.error(f"Failed to update analysis job: {save_error}")
            
            # Update Celery task state
            self.update_state(
                state="FAILURE",
                meta={
                    "error": str(e),
                    "report_id": report_id,
                    "task_id": task_id
                }
            )
            
            raise
    
    # Run the async analysis
    import asyncio
    try:
        return asyncio.run(run_analysis())
    except Exception as e:
        logger.error(f"Failed to run analysis task: {e}")
        raise


@celery_app.task(bind=True, name="cleanup_old_reports")
def cleanup_old_reports(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old reports and associated files.
    
    Args:
        days_old: Number of days after which reports should be cleaned up
        
    Returns:
        Dict containing cleanup results
    """
    task_id = self.request.id
    logger.info(f"Starting cleanup task {task_id} for reports older than {days_old} days")
    
    async def run_cleanup():
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old reports
            old_reports = await Report.find(
                {"created_at": {"$lt": cutoff_date}}
            ).to_list()
            
            cleaned_count = 0
            errors = []
            
            for report in old_reports:
                try:
                    # Clean up associated files
                    if report.file_path and os.path.exists(report.file_path):
                        os.remove(report.file_path)
                        logger.info(f"Deleted file: {report.file_path}")
                    
                    # Delete associated analysis jobs
                    if report.job_id:
                        analysis_job = await AnalysisJob.find_one({"job_id": report.job_id})
                        if analysis_job:
                            await analysis_job.delete()
                    
                    # Delete the report
                    await report.delete()
                    cleaned_count += 1
                    
                    logger.info(f"Cleaned up report: {report.id}")
                    
                except Exception as e:
                    error_msg = f"Failed to cleanup report {report.id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(f"Cleanup completed: {cleaned_count} reports cleaned, {len(errors)} errors")
            
            return {
                "status": "completed",
                "task_id": task_id,
                "cleaned_count": cleaned_count,
                "errors": errors,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in cleanup task {task_id}: {e}")
            raise
    
    # Run the async cleanup
    import asyncio
    from datetime import timedelta
    try:
        return asyncio.run(run_cleanup())
    except Exception as e:
        logger.error(f"Failed to run cleanup task: {e}")
        raise


@celery_app.task(bind=True, name="validate_pcap_file")
def validate_pcap_file(self, file_path: str) -> Dict[str, Any]:
    """
    Validate a PCAP file before analysis.
    
    Args:
        file_path: Path to the PCAP file to validate
        
    Returns:
        Dict containing validation results
    """
    task_id = self.request.id
    logger.info(f"Starting PCAP validation task {task_id} for file {file_path}")
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PCAP file not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("PCAP file is empty")
        
        # Check if file is readable
        try:
            with open(file_path, 'rb') as f:
                # Read first few bytes to check file format
                header = f.read(24)
                if len(header) < 24:
                    raise ValueError("PCAP file too small to contain valid header")
                
                # Check for PCAP magic numbers
                magic_numbers = [
                    b'\xd4\xc3\xb2\xa1',  # Standard PCAP
                    b'\xa1\xb2\xc3\xd4',  # Standard PCAP (swapped)
                    b'\x4d\x3c\xb2\xa1',  # PCAP-NG
                    b'\xa1\xb2\x3c\x4d',  # PCAP-NG (swapped)
                ]
                
                if not any(header.startswith(magic) for magic in magic_numbers):
                    raise ValueError("File does not appear to be a valid PCAP file")
        
        except Exception as e:
            raise ValueError(f"Failed to read PCAP file: {e}")
        
        # Try to validate with tshark if available
        tshark_validation = None
        try:
            import subprocess
            result = subprocess.run(
                ["tshark", "-r", file_path, "-c", "1"],
                capture_output=True,
                text=True,
                timeout=10
            )
            tshark_validation = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            logger.warning(f"tshark validation failed: {e}")
        
        logger.info(f"PCAP validation completed for {file_path}")
        
        return {
            "status": "valid",
            "task_id": task_id,
            "file_path": file_path,
            "file_size": file_size,
            "tshark_validation": tshark_validation,
            "message": "PCAP file is valid and ready for analysis"
        }
        
    except Exception as e:
        logger.error(f"PCAP validation failed for {file_path}: {e}")
        
        return {
            "status": "invalid",
            "task_id": task_id,
            "file_path": file_path,
            "error": str(e),
            "message": "PCAP file validation failed"
        }


@celery_app.task(bind=True, name="generate_report_summary")
def generate_report_summary(self, report_id: str) -> Dict[str, Any]:
    """
    Generate an enhanced summary for a completed report.
    
    Args:
        report_id: ID of the report to summarize
        
    Returns:
        Dict containing enhanced summary
    """
    task_id = self.request.id
    logger.info(f"Starting report summary task {task_id} for report {report_id}")
    
    async def run_summary():
        try:
            # Get the report
            report = await Report.get(report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            if report.status != ReportStatus.COMPLETED:
                raise ValueError(f"Report is not completed: {report.status}")
            
            if not report.analysis_results:
                raise ValueError("No analysis results found")
            
            # Generate enhanced summary
            results = report.analysis_results
            
            # Traffic analysis
            traffic_summary = {
                "total_packets": results.traffic_stats.get("total_packets", 0),
                "total_bytes": results.traffic_stats.get("total_bytes", 0),
                "duration": results.traffic_stats.get("duration", 0),
                "average_packet_size": 0,
                "packets_per_second": 0
            }
            
            if traffic_summary["total_packets"] > 0:
                traffic_summary["average_packet_size"] = (
                    traffic_summary["total_bytes"] / traffic_summary["total_packets"]
                )
            
            if traffic_summary["duration"] > 0:
                traffic_summary["packets_per_second"] = (
                    traffic_summary["total_packets"] / traffic_summary["duration"]
                )
            
            # Protocol analysis
            protocol_summary = {
                "total_protocols": len(results.top_protocols),
                "dominant_protocol": results.top_protocols[0].protocol if results.top_protocols else "Unknown",
                "protocol_diversity": 0.0  # Shannon entropy could be calculated here
            }
            
            # Security analysis
            security_summary = {
                "total_alerts": len(results.security_alerts),
                "alert_severity_distribution": {},
                "total_issues": len(results.network_issues),
                "issue_severity_distribution": {}
            }
            
            # Count alert severities
            for alert in results.security_alerts:
                severity = alert.severity
                security_summary["alert_severity_distribution"][severity] = (
                    security_summary["alert_severity_distribution"].get(severity, 0) + 1
                )
            
            # Count issue severities
            for issue in results.network_issues:
                severity = issue.severity
                security_summary["issue_severity_distribution"][severity] = (
                    security_summary["issue_severity_distribution"].get(severity, 0) + 1
                )
            
            # DNS analysis
            dns_summary = {
                "total_queries": results.dns_analysis.get("total_queries", 0),
                "unique_domains": results.dns_analysis.get("unique_domains", 0),
                "top_domains": results.dns_analysis.get("top_queried_domains", [])[:5]
            }
            
            # Host analysis
            host_summary = {
                "total_hosts": len(results.top_hosts),
                "most_active_host": results.top_hosts[0].ip_address if results.top_hosts else "Unknown",
                "internal_hosts": 0,
                "external_hosts": 0
            }
            
            # Classify hosts as internal/external (simple heuristic)
            for host in results.top_hosts:
                ip = host.ip_address
                if (ip.startswith("10.") or ip.startswith("192.168.") or 
                    ip.startswith("172.") or ip.startswith("127.")):
                    host_summary["internal_hosts"] += 1
                else:
                    host_summary["external_hosts"] += 1
            
            enhanced_summary = {
                "report_id": report_id,
                "generated_at": datetime.utcnow().isoformat(),
                "executive_summary": results.executive_summary,
                "traffic_summary": traffic_summary,
                "protocol_summary": protocol_summary,
                "security_summary": security_summary,
                "dns_summary": dns_summary,
                "host_summary": host_summary,
                "recommendations": [
                    "Monitor high-volume hosts for potential security issues",
                    "Investigate any security alerts flagged in the analysis",
                    "Review DNS queries to suspicious domains",
                    "Analyze protocol distribution for anomalies"
                ]
            }
            
            logger.info(f"Report summary generated for {report_id}")
            
            return {
                "status": "completed",
                "task_id": task_id,
                "report_id": report_id,
                "summary": enhanced_summary
            }
            
        except Exception as e:
            logger.error(f"Error generating report summary {report_id}: {e}")
            raise
    
    # Run the async summary generation
    import asyncio
    try:
        return asyncio.run(run_summary())
    except Exception as e:
        logger.error(f"Failed to run summary task: {e}")
        raise 