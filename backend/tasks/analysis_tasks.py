"""
Celery tasks for PCAP analysis processing.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import current_task
from celery.exceptions import Retry

from core.celery_app import celery_app
from core.database import init_db
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from services.pcap_analysis_service import PcapAnalysisService

logger = logging.getLogger(__name__)


async def ensure_db_initialized():
    """
    Ensure database is initialized for Celery tasks.
    """
    try:
        await init_db()
        logger.info("Database initialized for Celery task")
    except Exception as e:
        logger.error(f"Failed to initialize database for Celery task: {e}")
        raise


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
            # Initialize database connection
            await ensure_db_initialized()
            
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
                    status=JobStatus.STARTED,  # Updated to use correct enum value
                    progress=0,
                    current_step="Starting analysis..."
                )
                await analysis_job.save()
            
            # Progress callback to update job status
            async def progress_callback(progress: int, message: str):
                analysis_job.progress = progress
                analysis_job.current_step = message
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
            
            # Initialize the new PCAP analysis service
            analysis_service = PcapAnalysisService()
            
            # Update progress
            await progress_callback(10, "Initializing analysis...")
            
            # Perform the analysis using the new service
            await progress_callback(25, "Extracting basic statistics...")
            analysis_results = await analysis_service.analyze_pcap_file(
                file_path, 
                options=getattr(analysis_job, 'options', {})
            )
            
            await progress_callback(90, "Finalizing results...")
            
            # Convert AnalysisResults to the format expected by the Report model
            # For now, we'll store the results as a dict until we update the Report model
            results_dict = {
                "file_path": analysis_results.file_path,
                "file_size": analysis_results.file_size,
                "analysis_timestamp": analysis_results.analysis_timestamp,
                "traffic_stats": {
                    "total_packets": analysis_results.traffic_stats.total_packets,
                    "total_bytes": analysis_results.traffic_stats.total_bytes,
                    "duration": analysis_results.traffic_stats.duration,
                    "avg_packet_size": analysis_results.traffic_stats.avg_packet_size,
                    "packets_per_second": analysis_results.traffic_stats.packets_per_second,
                    "bytes_per_second": analysis_results.traffic_stats.bytes_per_second
                },
                "performance_metrics": {
                    "avg_latency": analysis_results.performance_metrics.avg_latency,
                    "max_latency": analysis_results.performance_metrics.max_latency,
                    "packet_loss_rate": analysis_results.performance_metrics.packet_loss_rate,
                    "throughput_mbps": analysis_results.performance_metrics.throughput_mbps
                },
                "protocol_stats": {
                    "tcp_packets": analysis_results.protocol_stats.tcp_packets,
                    "udp_packets": analysis_results.protocol_stats.udp_packets,
                    "icmp_packets": analysis_results.protocol_stats.icmp_packets,
                    "http_sessions": analysis_results.protocol_stats.http_sessions,
                    "https_sessions": analysis_results.protocol_stats.https_sessions,
                    "dns_queries": analysis_results.protocol_stats.dns_queries
                },
                "issues": [
                    {
                        "type": issue.type.value,
                        "severity": issue.severity.value,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                        "confidence": issue.confidence
                    }
                    for issue in analysis_results.issues
                ],
                "start_time": analysis_results.start_time,
                "end_time": analysis_results.end_time,
                "processing_time": analysis_results.processing_time
            }
            
            # Update report with results
            report.analysis_results = results_dict
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.utcnow()
            await report.save()
            
            # Update analysis job
            analysis_job.status = JobStatus.SUCCESS
            analysis_job.progress = 100
            analysis_job.current_step = "Analysis completed successfully"
            analysis_job.completed_at = datetime.utcnow()
            await analysis_job.save()
            
            logger.info(f"PCAP analysis completed for report {report_id}")
            
            return {
                "status": "completed",
                "report_id": report_id,
                "task_id": task_id,
                "message": "Analysis completed successfully",
                "results_summary": {
                    "total_packets": analysis_results.total_packets,
                    "duration": analysis_results.duration,
                    "unique_protocols": len([p for p in analysis_results.protocols.values() if p > 0]),
                    "top_protocol": max(analysis_results.protocols.items(), key=lambda x: x[1])[0] if analysis_results.protocols else "Unknown",
                    "issues_found": len(analysis_results.issues),
                    "throughput_mbps": analysis_results.performance_metrics.throughput_mbps
                }
            }
            
        except Exception as e:
            logger.error(f"Error in PCAP analysis task {task_id}: {e}")
            
            # Update report status
            try:
                await ensure_db_initialized()
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
                    analysis_job.status = JobStatus.FAILURE
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
            # Initialize database connection
            await ensure_db_initialized()
            
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
                    error_msg = f"Error cleaning up report {report.id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(f"Cleanup task {task_id} completed: {cleaned_count} reports cleaned")
            
            return {
                "status": "completed",
                "task_id": task_id,
                "cleaned_count": cleaned_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in cleanup task {task_id}: {e}")
            self.update_state(
                state="FAILURE",
                meta={"error": str(e), "task_id": task_id}
            )
            raise
    
    # Run the async cleanup
    import asyncio
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
    
    async def run_validation():
        try:
            # Initialize database connection
            await ensure_db_initialized()
            
            # Initialize the analysis service for validation
            analysis_service = PcapAnalysisService()
            
            # Validate the file
            await analysis_service._validate_pcap_file(file_path)
            
            # Get basic file information
            import os
            from pathlib import Path
            
            file_info = Path(file_path)
            file_size = file_info.stat().st_size
            
            logger.info(f"PCAP validation completed for file {file_path}")
            
            return {
                "status": "valid",
                "task_id": task_id,
                "file_path": file_path,
                "file_size": file_size,
                "message": "File validation successful"
            }
            
        except Exception as e:
            logger.error(f"Error in PCAP validation task {task_id}: {e}")
            
            self.update_state(
                state="FAILURE",
                meta={
                    "error": str(e),
                    "file_path": file_path,
                    "task_id": task_id
                }
            )
            
            return {
                "status": "invalid",
                "task_id": task_id,
                "file_path": file_path,
                "error": str(e),
                "message": "File validation failed"
            }
    
    # Run the async validation
    import asyncio
    try:
        return asyncio.run(run_validation())
    except Exception as e:
        logger.error(f"Failed to run validation task: {e}")
        raise


@celery_app.task(bind=True, name="generate_report_summary")
def generate_report_summary(self, report_id: str) -> Dict[str, Any]:
    """
    Generate a summary for a completed analysis report.
    
    Args:
        report_id: ID of the report to summarize
        
    Returns:
        Dict containing summary information
    """
    task_id = self.request.id
    logger.info(f"Starting report summary generation task {task_id} for report {report_id}")
    
    async def run_summary():
        try:
            # Initialize database connection
            await ensure_db_initialized()
            
            # Get the report
            report = await Report.get(report_id)
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            
            if not report.analysis_results:
                raise ValueError(f"Report {report_id} has no analysis results")
            
            # Extract key metrics from analysis results
            results = report.analysis_results
            traffic_stats = results.get("traffic_stats", {})
            performance_metrics = results.get("performance_metrics", {})
            protocol_stats = results.get("protocol_stats", {})
            issues = results.get("issues", [])
            
            # Generate summary
            summary = {
                "report_id": report_id,
                "file_info": {
                    "file_path": results.get("file_path", ""),
                    "file_size": results.get("file_size", 0),
                    "analysis_date": results.get("analysis_timestamp", "")
                },
                "traffic_overview": {
                    "total_packets": traffic_stats.get("total_packets", 0),
                    "total_bytes": traffic_stats.get("total_bytes", 0),
                    "duration_seconds": traffic_stats.get("duration", 0),
                    "avg_packet_size": traffic_stats.get("avg_packet_size", 0),
                    "throughput_mbps": performance_metrics.get("throughput_mbps", 0)
                },
                "protocol_distribution": protocol_stats,
                "performance_summary": {
                    "avg_latency_ms": performance_metrics.get("avg_latency", 0) * 1000,
                    "packet_loss_rate": performance_metrics.get("packet_loss_rate", 0),
                    "quality_score": max(0, 100 - (performance_metrics.get("packet_loss_rate", 0) * 100))
                },
                "issues_summary": {
                    "total_issues": len(issues),
                    "critical_issues": len([i for i in issues if i.get("severity") == "critical"]),
                    "high_issues": len([i for i in issues if i.get("severity") == "high"]),
                    "medium_issues": len([i for i in issues if i.get("severity") == "medium"]),
                    "low_issues": len([i for i in issues if i.get("severity") == "low"])
                },
                "recommendations": [
                    issue.get("recommendation", "")
                    for issue in issues
                    if issue.get("recommendation") and issue.get("severity") in ["critical", "high"]
                ][:5]  # Top 5 recommendations
            }
            
            # Update report with summary
            report.summary = summary
            await report.save()
            
            logger.info(f"Report summary generated for report {report_id}")
            
            return {
                "status": "completed",
                "task_id": task_id,
                "report_id": report_id,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error in report summary task {task_id}: {e}")
            
            self.update_state(
                state="FAILURE",
                meta={
                    "error": str(e),
                    "report_id": report_id,
                    "task_id": task_id
                }
            )
            
            raise
    
    # Run the async summary generation
    import asyncio
    try:
        return asyncio.run(run_summary())
    except Exception as e:
        logger.error(f"Failed to run summary task: {e}")
        raise 