"""
WebSocket service for real-time progress updates.

Provides real-time updates for PCAP analysis progress, system status,
and other live data to connected clients.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Progress update message structure."""
    job_id: str
    progress: int
    message: str
    timestamp: str
    status: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemStatus:
    """System status message structure."""
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_memory_usage: float
    cpu_usage: float
    disk_usage: float
    timestamp: str


class WebSocketConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        # Store active connections by client ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Track subscriptions by job ID
        self.job_subscriptions: Dict[str, Set[str]] = {}
        
        # Track system status subscriptions
        self.system_subscriptions: Set[str] = set()
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Connect a new WebSocket client.
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            
        Returns:
            bool: True if connection successful
        """
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = {
                'connected_at': datetime.utcnow().isoformat(),
                'last_ping': datetime.utcnow().isoformat(),
                'subscriptions': []
            }
            
            self.logger.info(f"WebSocket client {client_id} connected")
            
            # Send welcome message
            await self.send_personal_message(client_id, {
                'type': 'connection_established',
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'WebSocket connection established'
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect WebSocket client {client_id}: {e}")
            return False
    
    def disconnect(self, client_id: str):
        """
        Disconnect a WebSocket client and clean up subscriptions.
        
        Args:
            client_id: Client identifier to disconnect
        """
        try:
            # Remove from active connections
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            # Clean up job subscriptions
            for job_id, subscribers in self.job_subscriptions.items():
                subscribers.discard(client_id)
            
            # Remove empty job subscriptions
            self.job_subscriptions = {
                job_id: subscribers 
                for job_id, subscribers in self.job_subscriptions.items() 
                if subscribers
            }
            
            # Remove from system subscriptions
            self.system_subscriptions.discard(client_id)
            
            # Clean up metadata
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            
            self.logger.info(f"WebSocket client {client_id} disconnected")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting client {client_id}: {e}")
    
    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client identifier
            message: Message to send
        """
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
                
                # Update last activity
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]['last_ping'] = datetime.utcnow().isoformat()
                    
            except WebSocketDisconnect:
                self.disconnect(client_id)
            except Exception as e:
                self.logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_to_job_subscribers(self, job_id: str, message: Dict[str, Any]):
        """
        Broadcast a message to all clients subscribed to a specific job.
        
        Args:
            job_id: Job identifier
            message: Message to broadcast
        """
        if job_id in self.job_subscriptions:
            subscribers = self.job_subscriptions[job_id].copy()
            
            for client_id in subscribers:
                await self.send_personal_message(client_id, message)
    
    async def broadcast_system_status(self, status: SystemStatus):
        """
        Broadcast system status to all subscribed clients.
        
        Args:
            status: System status information
        """
        message = {
            'type': 'system_status',
            'data': asdict(status)
        }
        
        subscribers = self.system_subscriptions.copy()
        for client_id in subscribers:
            await self.send_personal_message(client_id, message)
    
    async def subscribe_to_job(self, client_id: str, job_id: str):
        """
        Subscribe a client to job progress updates.
        
        Args:
            client_id: Client identifier
            job_id: Job identifier to subscribe to
        """
        if job_id not in self.job_subscriptions:
            self.job_subscriptions[job_id] = set()
        
        self.job_subscriptions[job_id].add(client_id)
        
        # Update client metadata
        if client_id in self.connection_metadata:
            if 'subscriptions' not in self.connection_metadata[client_id]:
                self.connection_metadata[client_id]['subscriptions'] = []
            self.connection_metadata[client_id]['subscriptions'].append(job_id)
        
        self.logger.info(f"Client {client_id} subscribed to job {job_id}")
        
        # Send subscription confirmation
        await self.send_personal_message(client_id, {
            'type': 'subscription_confirmed',
            'job_id': job_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def unsubscribe_from_job(self, client_id: str, job_id: str):
        """
        Unsubscribe a client from job progress updates.
        
        Args:
            client_id: Client identifier
            job_id: Job identifier to unsubscribe from
        """
        if job_id in self.job_subscriptions:
            self.job_subscriptions[job_id].discard(client_id)
            
            # Remove empty subscription
            if not self.job_subscriptions[job_id]:
                del self.job_subscriptions[job_id]
        
        # Update client metadata
        if client_id in self.connection_metadata:
            subscriptions = self.connection_metadata[client_id].get('subscriptions', [])
            if job_id in subscriptions:
                subscriptions.remove(job_id)
        
        self.logger.info(f"Client {client_id} unsubscribed from job {job_id}")
    
    async def subscribe_to_system_status(self, client_id: str):
        """
        Subscribe a client to system status updates.
        
        Args:
            client_id: Client identifier
        """
        self.system_subscriptions.add(client_id)
        self.logger.info(f"Client {client_id} subscribed to system status")
        
        # Send subscription confirmation
        await self.send_personal_message(client_id, {
            'type': 'system_subscription_confirmed',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def unsubscribe_from_system_status(self, client_id: str):
        """
        Unsubscribe a client from system status updates.
        
        Args:
            client_id: Client identifier
        """
        self.system_subscriptions.discard(client_id)
        self.logger.info(f"Client {client_id} unsubscribed from system status")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        return {
            'active_connections': len(self.active_connections),
            'job_subscriptions': len(self.job_subscriptions),
            'system_subscriptions': len(self.system_subscriptions),
            'total_subscriptions': sum(len(subs) for subs in self.job_subscriptions.values()),
            'connections': [
                {
                    'client_id': client_id,
                    'metadata': self.connection_metadata.get(client_id, {})
                }
                for client_id in self.active_connections.keys()
            ]
        }
    
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """
        Handle incoming message from a WebSocket client.
        
        Args:
            client_id: Client identifier
            message: Received message
        """
        try:
            message_type = message.get('type')
            
            if message_type == 'subscribe_job':
                job_id = message.get('job_id')
                if job_id:
                    await self.subscribe_to_job(client_id, job_id)
                    
            elif message_type == 'unsubscribe_job':
                job_id = message.get('job_id')
                if job_id:
                    await self.unsubscribe_from_job(client_id, job_id)
                    
            elif message_type == 'subscribe_system':
                await self.subscribe_to_system_status(client_id)
                
            elif message_type == 'unsubscribe_system':
                await self.unsubscribe_from_system_status(client_id)
                
            elif message_type == 'ping':
                await self.send_personal_message(client_id, {
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif message_type == 'get_stats':
                stats = self.get_connection_stats()
                await self.send_personal_message(client_id, {
                    'type': 'stats',
                    'data': stats
                })
                
            else:
                await self.send_personal_message(client_id, {
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })
                
        except Exception as e:
            self.logger.error(f"Error handling message from {client_id}: {e}")
            await self.send_personal_message(client_id, {
                'type': 'error',
                'message': 'Failed to process message'
            })


class WebSocketService:
    """Service for managing WebSocket connections and real-time updates."""
    
    def __init__(self):
        self.manager = WebSocketConnectionManager()
        self.logger = logging.getLogger(__name__)
    
    async def send_progress_update(self, job_id: str, progress: int, message: str, 
                                 status: str = "processing", details: Optional[Dict[str, Any]] = None):
        """
        Send a progress update for a specific job.
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            message: Progress message
            status: Job status
            details: Additional details
        """
        update = ProgressUpdate(
            job_id=job_id,
            progress=progress,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            status=status,
            details=details
        )
        
        await self.manager.broadcast_to_job_subscribers(job_id, {
            'type': 'progress_update',
            'data': asdict(update)
        })
    
    async def send_job_completed(self, job_id: str, results: Dict[str, Any]):
        """
        Send job completion notification.
        
        Args:
            job_id: Job identifier
            results: Job results
        """
        await self.manager.broadcast_to_job_subscribers(job_id, {
            'type': 'job_completed',
            'job_id': job_id,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def send_job_failed(self, job_id: str, error: str):
        """
        Send job failure notification.
        
        Args:
            job_id: Job identifier
            error: Error message
        """
        await self.manager.broadcast_to_job_subscribers(job_id, {
            'type': 'job_failed',
            'job_id': job_id,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def send_system_status(self, status: SystemStatus):
        """
        Send system status update.
        
        Args:
            status: System status information
        """
        await self.manager.broadcast_system_status(status)
    
    def get_manager(self) -> WebSocketConnectionManager:
        """Get the WebSocket connection manager."""
        return self.manager


# Global WebSocket service instance
websocket_service = WebSocketService() 