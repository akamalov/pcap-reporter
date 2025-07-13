"""
Real-time Analysis Service for Live PCAP Processing.

Provides streaming analysis capabilities for real-time network monitoring,
live packet inspection, and continuous anomaly detection.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
import json

from services.websocket_service import websocket_service
from services.pcap_analysis_service import PcapAnalysisService
from models.analysis_results import NetworkIssue, SeverityLevel, IssueType

logger = logging.getLogger(__name__)


@dataclass
class RealTimeMetrics:
    """Real-time network metrics structure."""
    timestamp: str
    packets_per_second: float
    bytes_per_second: float
    active_connections: int
    protocol_distribution: Dict[str, int]
    top_talkers: List[Dict[str, Any]]
    anomalies_detected: int
    avg_latency: float
    packet_loss_rate: float


@dataclass
class LiveAlert:
    """Live security/performance alert structure."""
    id: str
    timestamp: str
    severity: str
    category: str
    title: str
    description: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    protocol: Optional[str] = None
    action_required: bool = False


class RealTimeAnalysisEngine:
    """Engine for real-time network analysis and monitoring."""
    
    def __init__(self):
        self.is_running = False
        self.analysis_queue = asyncio.Queue()
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 metrics
        self.active_streams = {}
        self.alert_rules = []
        self.subscribers = set()
        
        # Sliding window for metrics calculation
        self.packet_window = deque(maxlen=100)
        self.connection_tracker = {}
        self.protocol_stats = defaultdict(int)
        
        # Thresholds for anomaly detection
        self.thresholds = {
            'high_pps': 10000,           # packets per second
            'high_bps': 100_000_000,     # bytes per second (100 Mbps)
            'high_latency': 0.5,         # 500ms
            'high_packet_loss': 0.05,    # 5%
            'suspicious_port_scan': 50,   # connections to different ports
            'ddos_threshold': 1000,      # connections from single IP
        }
        
        self.pcap_analyzer = PcapAnalysisService()
        self.logger = logging.getLogger(__name__)
    
    async def start_realtime_monitoring(self):
        """Start the real-time monitoring engine."""
        if self.is_running:
            self.logger.warning("Real-time monitoring already running")
            return
        
        self.is_running = True
        self.logger.info("Starting real-time network monitoring")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._metrics_collector()),
            asyncio.create_task(self._anomaly_detector()),
            asyncio.create_task(self._alert_processor()),
            asyncio.create_task(self._metrics_broadcaster())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in real-time monitoring: {e}")
        finally:
            self.is_running = False
    
    async def stop_realtime_monitoring(self):
        """Stop the real-time monitoring engine."""
        self.is_running = False
        self.logger.info("Stopping real-time network monitoring")
    
    async def process_live_packet(self, packet_data: Dict[str, Any]):
        """
        Process a live network packet for real-time analysis.
        
        Args:
            packet_data: Packet information dictionary
        """
        try:
            timestamp = packet_data.get('timestamp', time.time())
            src_ip = packet_data.get('src_ip')
            dst_ip = packet_data.get('dst_ip')
            protocol = packet_data.get('protocol', 'unknown')
            size = packet_data.get('size', 0)
            
            # Add to sliding window
            self.packet_window.append({
                'timestamp': timestamp,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'protocol': protocol,
                'size': size
            })
            
            # Update protocol statistics
            self.protocol_stats[protocol] += 1
            
            # Track connections
            connection_key = f"{src_ip}:{dst_ip}"
            if connection_key not in self.connection_tracker:
                self.connection_tracker[connection_key] = {
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'packet_count': 0,
                    'total_bytes': 0
                }
            
            self.connection_tracker[connection_key]['last_seen'] = timestamp
            self.connection_tracker[connection_key]['packet_count'] += 1
            self.connection_tracker[connection_key]['total_bytes'] += size
            
            # Queue for analysis
            await self.analysis_queue.put(packet_data)
            
        except Exception as e:
            self.logger.error(f"Error processing live packet: {e}")
    
    async def _metrics_collector(self):
        """Collect and calculate real-time metrics."""
        while self.is_running:
            try:
                current_time = time.time()
                
                # Calculate metrics from sliding window
                if len(self.packet_window) > 0:
                    # Time-based calculations
                    time_window = 5.0  # 5 second window
                    recent_packets = [
                        p for p in self.packet_window 
                        if current_time - p['timestamp'] <= time_window
                    ]
                    
                    if recent_packets:
                        pps = len(recent_packets) / time_window
                        bps = sum(p['size'] for p in recent_packets) * 8 / time_window
                        
                        # Protocol distribution
                        protocol_dist = defaultdict(int)
                        for packet in recent_packets:
                            protocol_dist[packet['protocol']] += 1
                        
                        # Top talkers
                        talker_stats = defaultdict(lambda: {'packets': 0, 'bytes': 0})
                        for packet in recent_packets:
                            src_ip = packet['src_ip']
                            talker_stats[src_ip]['packets'] += 1
                            talker_stats[src_ip]['bytes'] += packet['size']
                        
                        top_talkers = [
                            {'ip': ip, **stats}
                            for ip, stats in sorted(
                                talker_stats.items(),
                                key=lambda x: x[1]['bytes'],
                                reverse=True
                            )[:10]
                        ]
                        
                        # Active connections
                        active_connections = len([
                            conn for conn, data in self.connection_tracker.items()
                            if current_time - data['last_seen'] <= 60  # Active in last minute
                        ])
                        
                        # Create metrics object
                        metrics = RealTimeMetrics(
                            timestamp=datetime.utcnow().isoformat(),
                            packets_per_second=pps,
                            bytes_per_second=bps,
                            active_connections=active_connections,
                            protocol_distribution=dict(protocol_dist),
                            top_talkers=top_talkers,
                            anomalies_detected=0,  # Will be calculated by anomaly detector
                            avg_latency=0.05,      # Placeholder - would need RTT calculation
                            packet_loss_rate=0.01  # Placeholder - would need packet sequence analysis
                        )
                        
                        # Store metrics
                        self.metrics_history.append(metrics)
                        
                        # Check thresholds and generate alerts
                        await self._check_thresholds(metrics)
                
                await asyncio.sleep(1)  # Collect metrics every second
                
            except Exception as e:
                self.logger.error(f"Error in metrics collector: {e}")
                await asyncio.sleep(1)
    
    async def _anomaly_detector(self):
        """Detect network anomalies using statistical analysis."""
        while self.is_running:
            try:
                if len(self.metrics_history) >= 10:  # Need some history for comparison
                    current_metrics = self.metrics_history[-1]
                    historical_avg = self._calculate_historical_average()
                    
                    anomalies = []
                    
                    # Traffic volume anomalies
                    if current_metrics.packets_per_second > historical_avg['pps'] * 3:
                        anomalies.append({
                            'type': 'traffic_spike',
                            'severity': 'high',
                            'description': f'Packet rate spike: {current_metrics.packets_per_second:.1f} pps (avg: {historical_avg["pps"]:.1f})'
                        })
                    
                    # Protocol anomalies
                    for protocol, count in current_metrics.protocol_distribution.items():
                        if protocol not in historical_avg['protocols']:
                            anomalies.append({
                                'type': 'new_protocol',
                                'severity': 'medium',
                                'description': f'New protocol detected: {protocol} ({count} packets)'
                            })
                    
                    # Connection anomalies
                    if current_metrics.active_connections > historical_avg['connections'] * 2:
                        anomalies.append({
                            'type': 'connection_surge',
                            'severity': 'medium',
                            'description': f'Connection surge: {current_metrics.active_connections} active (avg: {historical_avg["connections"]:.1f})'
                        })
                    
                    # Generate alerts for detected anomalies
                    for anomaly in anomalies:
                        alert = LiveAlert(
                            id=f"anomaly_{int(time.time())}_{anomaly['type']}",
                            timestamp=datetime.utcnow().isoformat(),
                            severity=anomaly['severity'],
                            category='anomaly_detection',
                            title=f"Network Anomaly: {anomaly['type'].replace('_', ' ').title()}",
                            description=anomaly['description'],
                            action_required=anomaly['severity'] == 'high'
                        )
                        
                        await self._send_alert(alert)
                
                await asyncio.sleep(5)  # Run anomaly detection every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in anomaly detector: {e}")
                await asyncio.sleep(5)
    
    async def _alert_processor(self):
        """Process and manage security/performance alerts."""
        alert_history = deque(maxlen=1000)
        
        while self.is_running:
            try:
                # Process queued packets for security analysis
                if not self.analysis_queue.empty():
                    packet_batch = []
                    
                    # Collect a batch of packets
                    for _ in range(min(100, self.analysis_queue.qsize())):
                        packet_batch.append(await self.analysis_queue.get())
                    
                    # Analyze batch for security patterns
                    security_alerts = await self._analyze_security_patterns(packet_batch)
                    
                    for alert in security_alerts:
                        await self._send_alert(alert)
                        alert_history.append(alert)
                
                await asyncio.sleep(0.1)  # Process alerts frequently
                
            except Exception as e:
                self.logger.error(f"Error in alert processor: {e}")
                await asyncio.sleep(1)
    
    async def _metrics_broadcaster(self):
        """Broadcast real-time metrics to WebSocket subscribers."""
        while self.is_running:
            try:
                if len(self.metrics_history) > 0:
                    latest_metrics = self.metrics_history[-1]
                    
                    # Broadcast to all real-time subscribers
                    message = {
                        'type': 'realtime_metrics',
                        'data': asdict(latest_metrics),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Send to WebSocket subscribers
                    for subscriber in self.subscribers:
                        try:
                            await websocket_service.manager.send_personal_message(
                                subscriber, message
                            )
                        except Exception as e:
                            self.logger.debug(f"Failed to send to subscriber {subscriber}: {e}")
                            self.subscribers.discard(subscriber)
                
                await asyncio.sleep(2)  # Broadcast every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Error in metrics broadcaster: {e}")
                await asyncio.sleep(2)
    
    async def _check_thresholds(self, metrics: RealTimeMetrics):
        """Check metrics against configured thresholds."""
        alerts = []
        
        if metrics.packets_per_second > self.thresholds['high_pps']:
            alerts.append(LiveAlert(
                id=f"threshold_{int(time.time())}_high_pps",
                timestamp=datetime.utcnow().isoformat(),
                severity='high',
                category='performance',
                title='High Packet Rate Detected',
                description=f'Packet rate: {metrics.packets_per_second:.1f} pps (threshold: {self.thresholds["high_pps"]})',
                action_required=True
            ))
        
        if metrics.bytes_per_second > self.thresholds['high_bps']:
            alerts.append(LiveAlert(
                id=f"threshold_{int(time.time())}_high_bps",
                timestamp=datetime.utcnow().isoformat(),
                severity='high',
                category='performance',
                title='High Bandwidth Utilization',
                description=f'Bandwidth: {metrics.bytes_per_second/1000000:.1f} Mbps (threshold: {self.thresholds["high_bps"]/1000000:.1f} Mbps)',
                action_required=True
            ))
        
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _analyze_security_patterns(self, packet_batch: List[Dict[str, Any]]) -> List[LiveAlert]:
        """Analyze packet batch for security patterns."""
        alerts = []
        
        try:
            # Group packets by source IP
            ip_activity = defaultdict(lambda: {'ports': set(), 'packet_count': 0})
            
            for packet in packet_batch:
                src_ip = packet.get('src_ip')
                dst_port = packet.get('dst_port')
                
                if src_ip and dst_port:
                    ip_activity[src_ip]['ports'].add(dst_port)
                    ip_activity[src_ip]['packet_count'] += 1
            
            # Detect port scanning
            for src_ip, activity in ip_activity.items():
                if len(activity['ports']) > self.thresholds['suspicious_port_scan']:
                    alerts.append(LiveAlert(
                        id=f"security_{int(time.time())}_port_scan_{src_ip.replace('.', '_')}",
                        timestamp=datetime.utcnow().isoformat(),
                        severity='high',
                        category='security',
                        title='Potential Port Scan Detected',
                        description=f'Source {src_ip} accessed {len(activity["ports"])} different ports',
                        source_ip=src_ip,
                        action_required=True
                    ))
                
                # Detect potential DDoS
                if activity['packet_count'] > self.thresholds['ddos_threshold']:
                    alerts.append(LiveAlert(
                        id=f"security_{int(time.time())}_ddos_{src_ip.replace('.', '_')}",
                        timestamp=datetime.utcnow().isoformat(),
                        severity='critical',
                        category='security',
                        title='Potential DDoS Attack',
                        description=f'Source {src_ip} sent {activity["packet_count"]} packets in short timeframe',
                        source_ip=src_ip,
                        action_required=True
                    ))
        
        except Exception as e:
            self.logger.error(f"Error analyzing security patterns: {e}")
        
        return alerts
    
    async def _send_alert(self, alert: LiveAlert):
        """Send alert to all subscribers."""
        message = {
            'type': 'live_alert',
            'data': asdict(alert)
        }
        
        # Send to WebSocket subscribers
        for subscriber in self.subscribers:
            try:
                await websocket_service.manager.send_personal_message(
                    subscriber, message
                )
            except Exception as e:
                self.logger.debug(f"Failed to send alert to subscriber {subscriber}: {e}")
                self.subscribers.discard(subscriber)
    
    def _calculate_historical_average(self) -> Dict[str, float]:
        """Calculate historical averages for anomaly detection."""
        if len(self.metrics_history) < 5:
            return {'pps': 0, 'bps': 0, 'connections': 0, 'protocols': {}}
        
        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 metrics
        
        avg_pps = sum(m.packets_per_second for m in recent_metrics) / len(recent_metrics)
        avg_bps = sum(m.bytes_per_second for m in recent_metrics) / len(recent_metrics)
        avg_connections = sum(m.active_connections for m in recent_metrics) / len(recent_metrics)
        
        # Aggregate protocol data
        all_protocols = set()
        for m in recent_metrics:
            all_protocols.update(m.protocol_distribution.keys())
        
        return {
            'pps': avg_pps,
            'bps': avg_bps,
            'connections': avg_connections,
            'protocols': all_protocols
        }
    
    async def subscribe_client(self, client_id: str):
        """Subscribe a client to real-time updates."""
        self.subscribers.add(client_id)
        self.logger.info(f"Client {client_id} subscribed to real-time analysis")
        
        # Send current metrics if available
        if self.metrics_history:
            latest_metrics = self.metrics_history[-1]
            await websocket_service.manager.send_personal_message(client_id, {
                'type': 'realtime_metrics',
                'data': asdict(latest_metrics),
                'timestamp': datetime.utcnow().isoformat()
            })
    
    async def unsubscribe_client(self, client_id: str):
        """Unsubscribe a client from real-time updates."""
        self.subscribers.discard(client_id)
        self.logger.info(f"Client {client_id} unsubscribed from real-time analysis")
    
    def get_current_metrics(self) -> Optional[RealTimeMetrics]:
        """Get the latest metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, limit: int = 100) -> List[RealTimeMetrics]:
        """Get historical metrics."""
        return list(self.metrics_history)[-limit:]
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update anomaly detection thresholds."""
        self.thresholds.update(new_thresholds)
        self.logger.info(f"Updated thresholds: {new_thresholds}")


# Global real-time analysis engine
realtime_engine = RealTimeAnalysisEngine()