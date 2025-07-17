"""
SIMPLE FIXED Celery tasks for PCAP analysis processing.
This version uses a simpler approach without asyncio threading conflicts.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio
import time

from celery import current_task
from celery.exceptions import Retry

from core.celery_app import celery_app
from core.database import get_database_client
from models.report import Report, ReportStatus
from models.analysis_job import AnalysisJob, JobStatus
from services.pcap_analysis_service import PcapAnalysisService
from services.network_diagram_generator import NetworkDiagramGenerator

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="analyze_pcap_file")
def analyze_pcap_file(self, report_id: str, file_path: str) -> Dict[str, Any]:
    """
    Analyze a PCAP file and update the report with results.
    SIMPLE version that avoids asyncio conflicts by running sync operations.
    
    Args:
        report_id: ID of the report to update
        file_path: Path to the PCAP file to analyze
        
    Returns:
        Dict containing analysis results and status
    """
    task_id = self.request.id
    logger.info(f"Starting PCAP analysis task {task_id} for report {report_id}")
    
    try:
        # Since database is initialized in worker startup, we can use sync operations
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Create a simple event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialize database in this event loop
            from core.config import get_settings
            settings = get_settings()
            
            # Create fresh database connection for this task
            client = AsyncIOMotorClient(settings.DATABASE_URL)
            database_name = settings.DATABASE_URL.split('/')[-1]
            database = client[database_name]
            
            # Initialize models
            from beanie import init_beanie
            
            async def setup_and_analyze():
                # Initialize Beanie for this task
                await init_beanie(
                    database=database,
                    document_models=[Report, AnalysisJob]
                )
                
                # Get the report
                report = await Report.get(report_id)
                if not report:
                    raise ValueError(f"Report not found: {report_id}")
                
                # Update report status
                report.status = ReportStatus.PROCESSING
                report.started_at = datetime.utcnow()
                await report.save()
                
                logger.info(f"Updated report {report_id} status to PROCESSING")
                
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
                
                logger.info(f"Created analysis job for task {task_id}")
                
                # Update progress
                analysis_job.progress = 10
                analysis_job.current_step = "Initializing analysis..."
                analysis_job.updated_at = datetime.utcnow()
                await analysis_job.save()
                
                # Get file information
                file_size = os.path.getsize(file_path)
                file_size_mb = file_size / (1024 * 1024)
                
                logger.info(f"Analyzing file {file_path} ({file_size_mb:.1f}MB)")
                
                # Update progress
                analysis_job.progress = 25
                analysis_job.current_step = "Analyzing PCAP file..."
                analysis_job.updated_at = datetime.utcnow()
                await analysis_job.save()
                
                # Use regular analysis service
                analysis_service = PcapAnalysisService()
                analysis_results = await analysis_service.analyze_pcap_file(file_path)
                
                logger.info(f"Analysis completed: {analysis_results.traffic_stats.total_packets} packets analyzed")
                
                # Update progress
                analysis_job.progress = 85
                analysis_job.current_step = "Generating network diagrams..."
                analysis_job.updated_at = datetime.utcnow()
                await analysis_job.save()
                
                # Generate network diagrams
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
                
                # Update progress
                analysis_job.progress = 90
                analysis_job.current_step = "Finalizing results..."
                analysis_job.updated_at = datetime.utcnow()
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
            
            # Run the analysis
            result = loop.run_until_complete(setup_and_analyze())
            
            # Update Celery task state
            self.update_state(
                state="SUCCESS",
                meta=result
            )
            
            return result
            
        finally:
            # Clean up the event loop
            loop.close()
            if client:
                client.close()
            
    except Exception as e:
        logger.error(f"Error in PCAP analysis task {task_id}: {e}")
        
        # Try to update report status with error
        try:
            # Create new event loop for error handling
            error_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(error_loop)
            
            try:
                from core.config import get_settings
                settings = get_settings()
                
                error_client = AsyncIOMotorClient(settings.DATABASE_URL)
                database_name = settings.DATABASE_URL.split('/')[-1]
                error_database = error_client[database_name]
                
                async def update_error_status():
                    from beanie import init_beanie
                    await init_beanie(
                        database=error_database,
                        document_models=[Report, AnalysisJob]
                    )
                    
                    report = await Report.get(report_id)
                    if report:
                        report.status = ReportStatus.FAILED
                        report.error_message = str(e)
                        await report.save()
                        
                    analysis_job = await AnalysisJob.find_one({"celery_task_id": task_id})
                    if analysis_job:
                        analysis_job.status = JobStatus.FAILURE
                        analysis_job.error = str(e)
                        analysis_job.updated_at = datetime.utcnow()
                        await analysis_job.save()
                
                error_loop.run_until_complete(update_error_status())
                
            finally:
                error_loop.close()
                if 'error_client' in locals():
                    error_client.close()
                    
        except Exception as save_error:
            logger.error(f"Failed to update error status: {save_error}")
        
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