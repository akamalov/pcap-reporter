"""
FIXED Celery tasks for PCAP analysis processing.
This version properly handles asyncio event loops in Celery worker context.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from celery import current_task
from celery.exceptions import Retry

from core.celery_app import celery_app
from core.database import init_db
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from services.pcap_analysis_service import PcapAnalysisService
from services.streaming_pcap_service import StreamingPcapService, StreamingConfig
from services.websocket_service import websocket_service
from services.network_diagram_generator import NetworkDiagramGenerator

logger = logging.getLogger(__name__)

# Thread-local storage for event loops
_thread_local = threading.local()

def get_or_create_event_loop():
    """Get or create an event loop for the current thread"""
    if not hasattr(_thread_local, 'loop'):
        _thread_local.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_thread_local.loop)
    return _thread_local.loop

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

def run_async_in_thread(coro):
    """Run an async coroutine in a dedicated thread to avoid event loop conflicts"""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_thread)
        return future.result()

@celery_app.task(bind=True, name="analyze_pcap_file")
def analyze_pcap_file(self, report_id: str, file_path: str) -> Dict[str, Any]:
    """
    Analyze a PCAP file and update the report with results.
    FIXED version that properly handles asyncio in Celery worker context.
    
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
            analysis_job = await AnalysisJob.find_one({"celery_task_id": task_id})
            if not analysis_job:
                analysis_job = AnalysisJob(
                    job_id=task_id,
                    report_id=report_id,
                    status=JobStatus.STARTED,
                    progress=0,
                    current_step="Starting analysis...",
                    celery_task_id=task_id
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
                
                # Send real-time WebSocket update (skip if it fails)
                try:
                    await websocket_service.send_progress_update(
                        job_id=task_id,
                        progress=progress,
                        message=message,
                        status="processing",
                        details={
                            "report_id": report_id,
                            "file_size_mb": file_size_mb if 'file_size_mb' in locals() else 0
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"Failed to send WebSocket update: {ws_error}")
            
            # Determine file size and choose appropriate service
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            await progress_callback(10, "Initializing analysis...")
            
            # Use streaming service for large files (>100MB)
            if file_size_mb > 100:
                logger.info(f"Using streaming analysis for large file: {file_size_mb:.1f}MB")
                
                # Configure streaming service based on file size
                config = StreamingConfig(
                    chunk_size_mb=min(100, max(50, int(file_size_mb / 8))),
                    parallel_workers=min(4, max(2, int(file_size_mb / 200))),
                    max_memory_mb=512,
                    enable_progress_updates=True
                )
                
                streaming_service = StreamingPcapService(config)
                analysis_results = await streaming_service.analyze_large_pcap(
                    file_path, 
                    progress_callback
                )
                
                # Get streaming statistics
                streaming_stats = streaming_service.get_processing_stats()
                logger.info(f"Streaming analysis completed: {streaming_stats}")
                
            else:
                # Use regular analysis service for smaller files
                logger.info(f"Using regular analysis for file: {file_size_mb:.1f}MB")
                analysis_service = PcapAnalysisService()
                
                await progress_callback(25, "Extracting basic statistics...")
                analysis_results = await analysis_service.analyze_pcap_file(
                    file_path, 
                    options=getattr(analysis_job, 'options', {})
                )
            
            await progress_callback(85, "Generating network diagrams...")
            
            # Generate network diagrams from analysis results
            try:
                diagram_generator = NetworkDiagramGenerator()
                
                # Create diagram input from analysis results
                diagram_input = {
                    'conversations': [],
                    'top_talkers': [],
                    'security_analysis': {'security_alerts': []},
                    'performance_analysis': {'performance_issues': []}
                }
                
                # Extract conversation data if available
                if hasattr(analysis_results, 'top_conversations') and analysis_results.top_conversations:
                    diagram_input['conversations'] = [
                        {
                            'src_ip': conv.src_ip,
                            'dst_ip': conv.dst_ip,
                            'src_port': conv.src_port,
                            'dst_port': conv.dst_port,
                            'protocol': conv.protocol,
                            'packet_count': conv.packets_sent + conv.packets_received,
                            'byte_count': conv.bytes_sent + conv.bytes_received
                        }
                        for conv in analysis_results.top_conversations[:50]
                    ]
                
                # Extract security issues
                if hasattr(analysis_results, 'issues') and analysis_results.issues:
                    security_alerts = []
                    for issue in analysis_results.issues:
                        if hasattr(issue, 'type') and 'security' in issue.type.value.lower():
                            security_alerts.append({
                                'type': issue.type.value,
                                'description': issue.description,
                                'severity': issue.severity.value.upper(),
                                'affected_hosts': getattr(issue, 'affected_hosts', [])
                            })
                    diagram_input['security_analysis']['security_alerts'] = security_alerts
                
                # Extract performance issues
                performance_issues = []
                if hasattr(analysis_results, 'issues') and analysis_results.issues:
                    for issue in analysis_results.issues:
                        if hasattr(issue, 'type') and 'performance' in issue.type.value.lower():
                            performance_issues.append({
                                'type': issue.type.value,
                                'description': issue.description,
                                'severity': issue.severity.value.upper()
                            })
                
                # Add bandwidth and connection rate from performance metrics
                if hasattr(analysis_results, 'performance_metrics'):
                    perf_metrics = analysis_results.performance_metrics
                    diagram_input['performance_analysis'].update({
                        'bandwidth_usage': int(analysis_results.traffic_stats.bytes_per_second * analysis_results.traffic_stats.duration) if hasattr(analysis_results, 'traffic_stats') else 0,
                        'connection_rate': len(diagram_input['conversations']),
                        'latency_indicators': int(perf_metrics.avg_latency * 1000) if perf_metrics.avg_latency else 0,
                        'performance_issues': performance_issues
                    })
                
                # Generate comprehensive diagram set
                diagrams = diagram_generator.generate_comprehensive_diagram_set(diagram_input)
                
                logger.info(f"Generated {len([k for k in diagrams.keys() if not k.startswith('_')])} network diagrams")
                
            except Exception as diagram_error:
                logger.warning(f"Failed to generate diagrams: {diagram_error}")
                diagrams = {
                    'error': f"Diagram generation failed: {str(diagram_error)}",
                    '_metadata': {'error': str(diagram_error)}
                }
            
            await progress_callback(90, "Finalizing results...")
            
            # Convert AnalysisResults to the format expected by the Report model
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
                "processing_time": analysis_results.processing_time,
                "analysis_options": analysis_results.analysis_options,
                "network_diagrams": diagrams
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
                    "total_packets": analysis_results.traffic_stats.total_packets,
                    "duration": analysis_results.traffic_stats.duration,
                    "unique_protocols": len([p for p in [
                        analysis_results.protocol_stats.tcp_packets,
                        analysis_results.protocol_stats.udp_packets,
                        analysis_results.protocol_stats.icmp_packets
                    ] if p > 0]),
                    "issues_found": len(analysis_results.issues),
                    "throughput_mbps": analysis_results.performance_metrics.throughput_mbps,
                    "file_size_mb": file_size_mb,
                    "processing_method": "streaming" if file_size_mb > 100 else "regular"
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
                analysis_job = await AnalysisJob.find_one({"celery_task_id": task_id})
                if analysis_job:
                    analysis_job.status = JobStatus.FAILURE
                    analysis_job.error = str(e)
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
    
    # Run the async analysis in a dedicated thread to avoid event loop conflicts
    try:
        logger.info("Running async analysis in dedicated thread")
        return run_async_in_thread(run_analysis())
    except Exception as e:
        logger.error(f"Failed to run analysis task: {e}")
        raise

# Keep the same pattern for other tasks...
@celery_app.task(bind=True, name="cleanup_old_reports")
def cleanup_old_reports(self, days_old: int = 30) -> Dict[str, Any]:
    """Clean up old reports and associated files."""
    task_id = self.request.id
    logger.info(f"Starting cleanup task {task_id} for reports older than {days_old} days")
    
    async def run_cleanup():
        try:
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
    
    # Run the async cleanup in a dedicated thread
    try:
        logger.info("Running async cleanup in dedicated thread")
        return run_async_in_thread(run_cleanup())
    except Exception as e:
        logger.error(f"Failed to run cleanup task: {e}")
        raise