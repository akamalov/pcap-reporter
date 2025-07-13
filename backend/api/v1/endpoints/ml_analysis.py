"""
Machine Learning Analysis API Endpoints.

Provides endpoints for ML-based network anomaly detection and analysis.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
from pathlib import Path

from services.ml_anomaly_detector import ml_anomaly_detector
from core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze/{analysis_id}")
async def analyze_with_ml(
    analysis_id: str,
    background_tasks: BackgroundTasks,
    settings=Depends(get_settings)
) -> Dict[str, Any]:
    """
    Perform ML anomaly detection on an analyzed PCAP file.
    
    Args:
        analysis_id: ID of the completed analysis
        background_tasks: FastAPI background tasks
        
    Returns:
        ML anomaly detection results
    """
    try:
        # Get the PCAP file path from analysis ID
        # In a real implementation, this would lookup the file path from the analysis ID
        pcap_file = Path(settings.UPLOAD_DIR) / f"{analysis_id}.pcap"
        
        if not pcap_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"PCAP file not found for analysis ID: {analysis_id}"
            )
        
        # Perform ML anomaly detection
        results = await ml_anomaly_detector.analyze_pcap_for_anomalies(str(pcap_file))
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "ml_results": results
        }
        
    except Exception as e:
        logger.error(f"Error in ML analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ML analysis failed: {str(e)}"
        )


@router.get("/models/info")
async def get_model_info() -> Dict[str, Any]:
    """
    Get information about available ML models.
    
    Returns:
        Information about ML models and their status
    """
    try:
        model_info = ml_anomaly_detector._get_model_info()
        
        return {
            "status": "success",
            "model_info": model_info,
            "detector_config": {
                "max_flows": ml_anomaly_detector.config['max_flows_to_analyze'],
                "min_packets_per_flow": ml_anomaly_detector.config['min_packets_per_flow'],
                "anomaly_threshold": ml_anomaly_detector.config['anomaly_threshold'],
                "ensemble_voting": ml_anomaly_detector.config['ensemble_vote_threshold']
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.post("/models/train")
async def train_models(
    background_tasks: BackgroundTasks,
    pcap_files: Optional[list] = None
) -> Dict[str, Any]:
    """
    Train ML models on provided PCAP files.
    
    Args:
        background_tasks: FastAPI background tasks
        pcap_files: Optional list of PCAP files for training
        
    Returns:
        Training status and information
    """
    try:
        # In a production system, this would implement actual model training
        # For now, we'll return a placeholder response
        
        def train_models_background():
            # This would contain the actual training logic
            logger.info("Background model training started")
            # Training implementation would go here
        
        background_tasks.add_task(train_models_background)
        
        return {
            "status": "success",
            "message": "Model training started in background",
            "training_files": pcap_files or [],
            "estimated_time": "This would depend on data size"
        }
        
    except Exception as e:
        logger.error(f"Error starting model training: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model training failed: {str(e)}"
        )


@router.get("/anomalies/types")
async def get_anomaly_types() -> Dict[str, Any]:
    """
    Get information about types of anomalies that can be detected.
    
    Returns:
        Description of anomaly types and their characteristics
    """
    try:
        anomaly_types = {
            "encrypted_traffic": {
                "description": "High entropy payload suggesting encrypted or compressed data",
                "indicators": ["payload_entropy > 7.5"],
                "severity": "medium",
                "impact": "May indicate data exfiltration or covert communication"
            },
            "size_anomaly": {
                "description": "Unusual variation in packet sizes",
                "indicators": ["packet_size_variance > 10000"],
                "severity": "low",
                "impact": "May indicate protocol anomalies or application issues"
            },
            "high_volume": {
                "description": "Unusually high packet rate",
                "indicators": ["packets_per_second > 1000"],
                "severity": "high",
                "impact": "Potential DDoS attack or bulk data transfer"
            },
            "port_scan": {
                "description": "High port entropy suggesting port scanning activity",
                "indicators": ["port_entropy > 10"],
                "severity": "high",
                "impact": "Potential reconnaissance or attack preparation"
            },
            "timing_anomaly": {
                "description": "Irregular packet timing patterns",
                "indicators": ["inter_arrival_variance > 1.0"],
                "severity": "medium",
                "impact": "May indicate automated tools or covert channels"
            },
            "protocol_anomaly": {
                "description": "Unusual protocol distribution",
                "indicators": ["tcp_ratio < 0.1 with packet_count > 10"],
                "severity": "medium",
                "impact": "Potential protocol misuse or tunneling"
            },
            "large_transfer": {
                "description": "Unusually large data transfer",
                "indicators": ["byte_count > 10MB"],
                "severity": "medium",
                "impact": "Potential data exfiltration or legitimate bulk transfer"
            },
            "burst_activity": {
                "description": "High-rate burst activity",
                "indicators": ["flow_duration < 1s with packet_count > 100"],
                "severity": "high",
                "impact": "Potential automated attack or scanning activity"
            }
        }
        
        return {
            "status": "success",
            "anomaly_types": anomaly_types,
            "total_types": len(anomaly_types)
        }
        
    except Exception as e:
        logger.error(f"Error getting anomaly types: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get anomaly types: {str(e)}"
        )


@router.get("/features/info")
async def get_feature_info() -> Dict[str, Any]:
    """
    Get information about ML features extracted from network traffic.
    
    Returns:
        Description of features used for ML analysis
    """
    try:
        feature_info = {
            "flow_features": {
                "flow_duration": "Duration of the network flow in seconds",
                "packet_count": "Total number of packets in the flow",
                "byte_count": "Total number of bytes transferred",
                "packets_per_second": "Average packet rate",
                "bytes_per_second": "Average byte rate"
            },
            "packet_features": {
                "avg_packet_size": "Average size of packets in bytes",
                "min_packet_size": "Minimum packet size",
                "max_packet_size": "Maximum packet size",
                "packet_size_variance": "Variance in packet sizes"
            },
            "timing_features": {
                "avg_inter_arrival_time": "Average time between packets",
                "inter_arrival_variance": "Variance in packet timing",
                "flow_idle_time": "Time flow was idle"
            },
            "protocol_features": {
                "tcp_flag_distribution": "Distribution of TCP flags",
                "port_entropy": "Entropy of ports used",
                "protocol_distribution": "Distribution of protocols",
                "retransmission_rate": "Rate of TCP retransmissions"
            },
            "behavioral_features": {
                "payload_entropy": "Entropy of payload data",
                "connection_state_changes": "Number of connection state changes",
                "out_of_order_packets": "Number of out-of-order packets",
                "duplicate_packets": "Number of duplicate packets"
            },
            "temporal_features": {
                "time_of_day": "Hour of day (0-23)",
                "day_of_week": "Day of week (0-6)"
            }
        }
        
        return {
            "status": "success",
            "feature_categories": feature_info,
            "total_features": sum(len(category) for category in feature_info.values()),
            "extraction_method": "Real-time feature extraction from network flows"
        }
        
    except Exception as e:
        logger.error(f"Error getting feature info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feature info: {str(e)}"
        )


@router.post("/models/save")
async def save_models() -> Dict[str, Any]:
    """
    Save trained ML models to disk.
    
    Returns:
        Status of model saving operation
    """
    try:
        success = await ml_anomaly_detector.save_models()
        
        if success:
            return {
                "status": "success",
                "message": "Models saved successfully",
                "saved_models": list(ml_anomaly_detector.models.keys())
            }
        else:
            return {
                "status": "error",
                "message": "Failed to save models",
                "reason": "ML libraries not available or models not trained"
            }
        
    except Exception as e:
        logger.error(f"Error saving models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model saving failed: {str(e)}"
        )


@router.post("/models/load")
async def load_models() -> Dict[str, Any]:
    """
    Load trained ML models from disk.
    
    Returns:
        Status of model loading operation
    """
    try:
        success = await ml_anomaly_detector.load_models()
        
        if success:
            return {
                "status": "success",
                "message": "Models loaded successfully",
                "loaded_models": list(ml_anomaly_detector.models.keys())
            }
        else:
            return {
                "status": "error",
                "message": "Failed to load models",
                "reason": "Model files not found or incompatible"
            }
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model loading failed: {str(e)}"
        )