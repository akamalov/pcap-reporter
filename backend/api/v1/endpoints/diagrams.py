"""
Network Diagram API Endpoints.

Provides endpoints for generating network diagrams from PCAP analysis results.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pathlib import Path

from core.database import get_database
from services.network_diagram_generator import NetworkDiagramGenerator
from services.pcap_analysis_service import PcapAnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
diagram_generator = NetworkDiagramGenerator()
pcap_analysis_service = PcapAnalysisService()


@router.get("/generate/{job_id}")
async def generate_network_diagrams(
    job_id: str,
    diagram_type: Optional[str] = "all"
) -> Dict[str, Any]:
    """
    Generate network diagrams for a completed analysis.
    
    Args:
        job_id: The analysis job ID
        diagram_type: Type of diagram (topology, security, protocol, sequence, all)
        
    Returns:
        Dict containing generated diagrams and metadata
    """
    try:
        logger.info(f"Generating network diagrams for job {job_id}, type: {diagram_type}")
        
        # Get database connection
        db = get_database()
        reports_collection = db["reports"]
        
        # Find the analysis results
        report = reports_collection.find_one({"job_id": job_id})
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Analysis results not found"
            )
        
        if report.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Analysis is not completed. Status: {report.get('status')}"
            )
        
        # Convert analysis results to the format expected by diagram generator
        analysis_dict = await _convert_report_to_analysis_dict(report)
        
        # Generate diagrams based on type
        if diagram_type == "all":
            diagrams = diagram_generator.generate_comprehensive_diagram_set(analysis_dict)
        elif diagram_type == "topology":
            diagrams = {
                "network_topology": diagram_generator.generate_network_topology_diagram(analysis_dict)
            }
        elif diagram_type == "security":
            diagrams = {
                "security_incidents": diagram_generator.generate_security_incident_diagram(analysis_dict)
            }
        elif diagram_type == "protocol":
            diagrams = {
                "protocol_flow": diagram_generator.generate_protocol_flow_diagram(analysis_dict)
            }
        elif diagram_type == "performance":
            diagrams = {
                "performance_analysis": diagram_generator.generate_performance_analysis_diagram(analysis_dict)
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid diagram type: {diagram_type}. Use 'topology', 'security', 'protocol', 'performance', or 'all'"
            )
        
        # Store diagrams in the report for future retrieval
        reports_collection.update_one(
            {"job_id": job_id},
            {"$set": {"network_diagrams": diagrams}}
        )
        
        return {
            "status": "success",
            "job_id": job_id,
            "diagram_type": diagram_type,
            "diagrams": diagrams,
            "diagram_count": len([k for k in diagrams.keys() if not k.startswith('_')])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating network diagrams for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate network diagrams: {str(e)}"
        )


@router.get("/view/{job_id}")
async def view_network_diagrams(job_id: str) -> Dict[str, Any]:
    """
    View previously generated network diagrams for an analysis.
    
    Args:
        job_id: The analysis job ID
        
    Returns:
        Dict containing stored diagrams
    """
    try:
        # Get database connection
        db = get_database()
        reports_collection = db["reports"]
        
        # Find the analysis results
        report = reports_collection.find_one({"job_id": job_id})
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Analysis results not found"
            )
        
        # Get stored diagrams
        diagrams = report.get("network_diagrams", {})
        
        if not diagrams:
            return {
                "status": "no_diagrams",
                "message": "No network diagrams found. Generate them first using /generate endpoint.",
                "job_id": job_id
            }
        
        return {
            "status": "success",
            "job_id": job_id,
            "diagrams": diagrams,
            "diagram_count": len([k for k in diagrams.keys() if not k.startswith('_')])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing network diagrams for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve network diagrams: {str(e)}"
        )


@router.get("/types")
async def get_diagram_types() -> Dict[str, Any]:
    """
    Get information about available diagram types.
    
    Returns:
        Dict containing available diagram types and their descriptions
    """
    try:
        diagram_types = {
            "topology": {
                "name": "Network Topology",
                "description": "Shows hosts, connections, and network structure",
                "features": ["Host identification", "Connection mapping", "Traffic volume visualization"]
            },
            "security": {
                "name": "Security Incidents",
                "description": "Highlights security threats and suspicious activities",
                "features": ["Threat detection", "Risk assessment", "Security alerts"]
            },
            "protocol": {
                "name": "Protocol Flow",
                "description": "Visualizes protocol communication patterns and sequences",
                "features": ["Protocol analysis", "Communication flows", "Sequence diagrams"]
            },
            "performance": {
                "name": "Performance Analysis",
                "description": "Shows performance issues and network bottlenecks",
                "features": ["Latency analysis", "Bandwidth usage", "Performance bottlenecks"]
            },
            "all": {
                "name": "Comprehensive Set",
                "description": "Generates all available diagram types",
                "features": ["Complete analysis", "Multiple perspectives", "Comprehensive overview"]
            }
        }
        
        return {
            "status": "success",
            "diagram_types": diagram_types,
            "total_types": len(diagram_types)
        }
        
    except Exception as e:
        logger.error(f"Error getting diagram types: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get diagram types: {str(e)}"
        )


@router.post("/config")
async def update_diagram_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update diagram generation configuration.
    
    Args:
        config: Configuration parameters for diagram generation
        
    Returns:
        Dict containing updated configuration
    """
    try:
        # Update diagram generator configuration
        diagram_generator.config.update(config)
        
        return {
            "status": "success",
            "message": "Diagram configuration updated",
            "config": diagram_generator.config
        }
        
    except Exception as e:
        logger.error(f"Error updating diagram config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.get("/config")
async def get_diagram_config() -> Dict[str, Any]:
    """
    Get current diagram generation configuration.
    
    Returns:
        Dict containing current configuration
    """
    try:
        return {
            "status": "success",
            "config": diagram_generator.config
        }
        
    except Exception as e:
        logger.error(f"Error getting diagram config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get configuration: {str(e)}"
        )


async def _convert_report_to_analysis_dict(report: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB report to analysis dictionary for diagram generation."""
    try:
        analysis_results = report.get("analysis_results", {})
        
        # Extract conversations from TCP analysis
        conversations = []
        tcp_conversations = analysis_results.get("top_tcp_conversations", [])
        
        for conv in tcp_conversations:
            conversations.append({
                'src_ip': conv.get('src_ip', 'unknown'),
                'dst_ip': conv.get('dst_ip', 'unknown'),
                'protocol': 'TCP',
                'packet_count': conv.get('packet_count', 0),
                'byte_count': conv.get('bytes', 0),
                'src_port': conv.get('src_port', 0),
                'dst_port': conv.get('dst_port', 0)
            })
        
        # Extract top talkers
        top_talkers = analysis_results.get("top_talkers", [])
        
        # Build security alerts from network issues
        security_alerts = []
        network_issues = analysis_results.get("network_issues", [])
        
        for issue in network_issues:
            security_alerts.append({
                'type': issue.get('type', 'UNKNOWN'),
                'severity': issue.get('severity', 'MEDIUM'),
                'description': issue.get('description', 'Network issue detected')
            })
        
        # Build performance issues
        performance_issues = []
        for issue in network_issues:
            if 'performance' in issue.get('description', '').lower():
                performance_issues.append({
                    'type': issue.get('type', 'PERFORMANCE'),
                    'severity': issue.get('severity', 'MEDIUM'),
                    'description': issue.get('description', 'Performance issue detected')
                })
        
        # Build analysis dictionary
        analysis_dict = {
            'conversations': conversations,
            'top_talkers': top_talkers,
            'security_analysis': {
                'security_alerts': security_alerts
            },
            'performance_analysis': {
                'performance_issues': performance_issues,
                'bandwidth_usage': analysis_results.get("traffic_stats", {}).get("total_bytes", 0),
                'connection_rate': len(conversations),
                'latency_indicators': len(performance_issues)
            }
        }
        
        return analysis_dict
        
    except Exception as e:
        logger.error(f"Error converting report to analysis dict: {e}")
        return {
            'conversations': [],
            'top_talkers': [],
            'security_analysis': {'security_alerts': []},
            'performance_analysis': {'performance_issues': []}
        }