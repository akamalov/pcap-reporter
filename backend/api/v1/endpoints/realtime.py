"""
Real-time analysis endpoints for WebSocket connections and live monitoring.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse

from services.websocket_service import websocket_service
from services.realtime_analysis_service import realtime_engine
from core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time updates and monitoring.
    
    Supports:
    - Real-time metrics streaming
    - Live alerts and notifications
    - Job progress updates
    - System status monitoring
    """
    manager = websocket_service.get_manager()
    
    # Connect the client
    if not await manager.connect(websocket, client_id):
        return
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            message_type = message.get('type')
            
            if message_type == 'subscribe_realtime':
                # Subscribe to real-time analysis updates
                await realtime_engine.subscribe_client(client_id)
                await manager.send_personal_message(client_id, {
                    'type': 'realtime_subscription_confirmed',
                    'timestamp': str(asyncio.get_event_loop().time())
                })
                
            elif message_type == 'unsubscribe_realtime':
                # Unsubscribe from real-time analysis updates
                await realtime_engine.unsubscribe_client(client_id)
                await manager.send_personal_message(client_id, {
                    'type': 'realtime_unsubscription_confirmed',
                    'timestamp': str(asyncio.get_event_loop().time())
                })
                
            elif message_type == 'get_current_metrics':
                # Send current metrics
                metrics = realtime_engine.get_current_metrics()
                if metrics:
                    await manager.send_personal_message(client_id, {
                        'type': 'current_metrics',
                        'data': metrics.__dict__,
                        'timestamp': str(asyncio.get_event_loop().time())
                    })
                else:
                    await manager.send_personal_message(client_id, {
                        'type': 'no_metrics',
                        'message': 'No metrics available yet'
                    })
                    
            elif message_type == 'get_metrics_history':
                # Send metrics history
                limit = message.get('limit', 50)
                history = realtime_engine.get_metrics_history(limit)
                await manager.send_personal_message(client_id, {
                    'type': 'metrics_history',
                    'data': [m.__dict__ for m in history],
                    'timestamp': str(asyncio.get_event_loop().time())
                })
                
            elif message_type == 'update_thresholds':
                # Update anomaly detection thresholds
                thresholds = message.get('thresholds', {})
                realtime_engine.update_thresholds(thresholds)
                await manager.send_personal_message(client_id, {
                    'type': 'thresholds_updated',
                    'thresholds': thresholds,
                    'timestamp': str(asyncio.get_event_loop().time())
                })
                
            else:
                # Handle other message types through the general handler
                await manager.handle_client_message(client_id, message)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        # Clean up subscriptions
        await realtime_engine.unsubscribe_client(client_id)
        manager.disconnect(client_id)


@router.post("/start-monitoring")
async def start_realtime_monitoring():
    """
    Start the real-time network monitoring engine.
    """
    try:
        if not realtime_engine.is_running:
            # Start monitoring in background
            asyncio.create_task(realtime_engine.start_realtime_monitoring())
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Real-time monitoring started",
                    "status": "running"
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Real-time monitoring already running",
                    "status": "running"
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to start real-time monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-monitoring")
async def stop_realtime_monitoring():
    """
    Stop the real-time network monitoring engine.
    """
    try:
        await realtime_engine.stop_realtime_monitoring()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Real-time monitoring stopped",
                "status": "stopped"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to stop real-time monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring-status")
async def get_monitoring_status():
    """
    Get the current status of real-time monitoring.
    """
    try:
        current_metrics = realtime_engine.get_current_metrics()
        
        return JSONResponse(
            status_code=200,
            content={
                "is_running": realtime_engine.is_running,
                "subscribers": len(realtime_engine.subscribers),
                "metrics_count": len(realtime_engine.metrics_history),
                "current_metrics": current_metrics.__dict__ if current_metrics else None,
                "thresholds": realtime_engine.thresholds
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inject-packet")
async def inject_test_packet(packet_data: Dict[str, Any]):
    """
    Inject a test packet for real-time analysis (testing/demo purposes).
    
    Expected packet_data format:
    {
        "src_ip": "192.168.1.100",
        "dst_ip": "192.168.1.1",
        "protocol": "TCP",
        "size": 1500,
        "dst_port": 80,
        "timestamp": 1234567890.0
    }
    """
    try:
        if not realtime_engine.is_running:
            raise HTTPException(
                status_code=400, 
                detail="Real-time monitoring is not running. Start monitoring first."
            )
        
        # Inject the packet into the analysis engine
        await realtime_engine.process_live_packet(packet_data)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Packet injected successfully",
                "packet_data": packet_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to inject packet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/current")
async def get_current_metrics():
    """
    Get the current real-time metrics.
    """
    try:
        metrics = realtime_engine.get_current_metrics()
        
        if metrics:
            return JSONResponse(
                status_code=200,
                content={
                    "metrics": metrics.__dict__,
                    "timestamp": metrics.timestamp
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "message": "No current metrics available"
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to get current metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/history")
async def get_metrics_history(limit: int = 100):
    """
    Get historical real-time metrics.
    
    Args:
        limit: Maximum number of metrics to return (default: 100)
    """
    try:
        if limit > 1000:
            limit = 1000  # Cap the limit
            
        history = realtime_engine.get_metrics_history(limit)
        
        return JSONResponse(
            status_code=200,
            content={
                "metrics": [m.__dict__ for m in history],
                "count": len(history),
                "limit": limit
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/thresholds")
async def update_thresholds(thresholds: Dict[str, float]):
    """
    Update anomaly detection thresholds.
    
    Expected thresholds format:
    {
        "high_pps": 10000,
        "high_bps": 100000000,
        "high_latency": 0.5,
        "high_packet_loss": 0.05,
        "suspicious_port_scan": 50,
        "ddos_threshold": 1000
    }
    """
    try:
        # Validate threshold values
        valid_keys = {
            'high_pps', 'high_bps', 'high_latency', 'high_packet_loss',
            'suspicious_port_scan', 'ddos_threshold'
        }
        
        invalid_keys = set(thresholds.keys()) - valid_keys
        if invalid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid threshold keys: {list(invalid_keys)}"
            )
        
        # Validate threshold values are positive
        for key, value in thresholds.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Threshold '{key}' must be a positive number"
                )
        
        # Update thresholds
        realtime_engine.update_thresholds(thresholds)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Thresholds updated successfully",
                "updated_thresholds": thresholds,
                "current_thresholds": realtime_engine.thresholds
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connection-stats")
async def get_connection_stats():
    """
    Get WebSocket connection statistics.
    """
    try:
        stats = websocket_service.get_manager().get_connection_stats()
        
        # Add real-time specific stats
        stats['realtime_subscribers'] = len(realtime_engine.subscribers)
        stats['monitoring_running'] = realtime_engine.is_running
        
        return JSONResponse(
            status_code=200,
            content=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get connection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))