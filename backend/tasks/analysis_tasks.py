"""
ROBUST Celery tasks for PCAP analysis processing.
Uses the sync/async bridge for proper event loop management.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

from core.celery_app import celery_app
from core.sync_async_bridge import celery_async_task, DatabaseContext, TaskStateManager

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="analyze_pcap_file")
@celery_async_task
async def analyze_pcap_file(
    self, 
    db_context: DatabaseContext, 
    state_manager: TaskStateManager,
    report_id: str, 
    file_path: str
) -> Dict[str, Any]:
    """
    Analyze a PCAP file and update the report with results.
    ROBUST version using sync/async bridge.
    
    Args:
        self: Celery task instance
        db_context: Database context manager
        state_manager: Task state manager
        report_id: ID of the report to update
        file_path: Path to the PCAP file to analyze
        
    Returns:
        Dict containing analysis results and status
    """
    task_id = self.request.id
    logger.info(f"Starting PCAP analysis task {task_id} for report {report_id}")
    
    # Import models in async context
    from models.report import Report, ReportStatus
    from models.analysis_job import AnalysisJob, JobStatus
    from services.pcap_analysis_service import PcapAnalysisService
    from services.network_diagram_generator import NetworkDiagramGenerator
    
    # Get the report
    report = await Report.get(report_id)
    if not report:
        raise ValueError(f"Report not found: {report_id}")
    
    # Update report status
    report.status = ReportStatus.PROCESSING
    report.started_at = datetime.utcnow()
    await report.save()
    
    logger.info(f"Updated report {report_id} status to PROCESSING")
    state_manager.update_progress(10, "Report status updated to PROCESSING")
    
    # Create analysis job
    analysis_job = AnalysisJob(
        job_id=report.job_id,  # Use report's job_id for consistency
        report_id=report_id,
        status=JobStatus.STARTED,
        progress=0,
        current_step="Starting analysis...",
        celery_task_id=task_id
    )
    await analysis_job.save()
    
    logger.info(f"Created analysis job for task {task_id}")
    state_manager.update_progress(20, "Analysis job created")
    
    # Update analysis job progress
    analysis_job.progress = 25
    analysis_job.current_step = "Initializing analysis..."
    await analysis_job.save()
    
    # Get file information
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    logger.info(f"Analyzing file {file_path} ({file_size_mb:.1f}MB)")
    state_manager.update_progress(30, f"Analyzing file ({file_size_mb:.1f}MB)")
    
    # Update analysis job progress
    analysis_job.progress = 40
    analysis_job.current_step = "Analyzing PCAP file..."
    await analysis_job.save()
    
    # Use analysis service
    analysis_service = PcapAnalysisService()
    analysis_results = await analysis_service.analyze_pcap_file(file_path)
    
    logger.info(f"Analysis completed: {analysis_results.traffic_stats.total_packets} packets analyzed")
    state_manager.update_progress(70, f"Analysis completed: {analysis_results.traffic_stats.total_packets} packets")
    
    # Update analysis job progress
    analysis_job.progress = 80
    analysis_job.current_step = "Generating network diagrams..."
    await analysis_job.save()
    
    # Generate network diagrams
    diagrams = {}
    try:
        diagram_generator = NetworkDiagramGenerator()
        
        # Create basic diagram input
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
        
        # Generate diagrams
        diagrams = diagram_generator.generate_comprehensive_diagram_set(diagram_input)
        logger.info(f"Generated {len([k for k in diagrams.keys() if not k.startswith('_')])} network diagrams")
        
    except Exception as diagram_error:
        logger.warning(f"Failed to generate diagrams: {diagram_error}")
        diagrams = {
            'error': f"Diagram generation failed: {str(diagram_error)}",
            '_metadata': {'error': str(diagram_error)}
        }
    
    state_manager.update_progress(85, "Network diagrams generated")
    
    # Update analysis job progress
    analysis_job.progress = 90
    analysis_job.current_step = "Finalizing results..."
    await analysis_job.save()
    
    # Convert results to dictionary
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
    
    logger.info(f"PCAP analysis completed successfully for report {report_id}")
    state_manager.update_progress(100, "Analysis completed successfully")
    
    return {
        "status": "completed",
        "report_id": report_id,
        "task_id": task_id,
        "message": "Analysis completed successfully",
        "results_summary": {
            "total_packets": analysis_results.traffic_stats.total_packets,
            "duration": analysis_results.traffic_stats.duration,
            "issues_found": len(analysis_results.issues),
            "throughput_mbps": analysis_results.performance_metrics.throughput_mbps,
            "file_size_mb": file_size_mb
        }
    }


@celery_app.task(bind=True, name="cleanup_old_reports")
@celery_async_task
async def cleanup_old_reports(
    self, 
    db_context: DatabaseContext, 
    state_manager: TaskStateManager,
    days_old: int = 30
) -> Dict[str, Any]:
    """
    Clean up old reports and associated files.
    ROBUST version using sync/async bridge.
    """
    task_id = self.request.id
    logger.info(f"Starting cleanup task {task_id} for reports older than {days_old} days")
    
    from datetime import timedelta
    from models.report import Report
    from models.analysis_job import AnalysisJob
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Find old reports
    old_reports = await Report.find(
        {"created_at": {"$lt": cutoff_date}}
    ).to_list()
    
    cleaned_count = 0
    errors = []
    
    for i, report in enumerate(old_reports):
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
            
            # Update progress
            progress = int((i + 1) / len(old_reports) * 100)
            state_manager.update_progress(progress, f"Cleaned {cleaned_count} reports")
            
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


@celery_app.task(bind=True, name="debug_task")
def debug_task(self):
    """
    Debug task for testing Celery functionality.
    Simple synchronous task for basic testing.
    """
    task_id = self.request.id
    logger.info(f"Debug task {task_id} starting")
    
    # Simple synchronous operations
    import time
    time.sleep(2)
    
    logger.info(f"Debug task {task_id} completed")
    return {
        "status": "success", 
        "task_id": task_id,
        "message": "Debug task completed"
    }