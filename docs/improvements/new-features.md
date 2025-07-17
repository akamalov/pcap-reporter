# New Features and Enhancements

## Overview
This document outlines new features that will significantly enhance the PCAP Reporter's capabilities and user experience.

## 🎯 ADVANCED ANALYSIS FEATURES

### 1. Machine Learning Anomaly Detection
**Priority**: High  
**Impact**: Intelligent threat detection and pattern recognition

```python
# backend/ml/anomaly_detection.py
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import joblib
from typing import Dict, List, Any, Tuple
import asyncio

class NetworkAnomalyDetector:
    def __init__(self):
        self.isolation_forest = None
        self.scaler = StandardScaler()
        self.dbscan = None
        self.is_trained = False
        
    async def extract_features(self, packets: List[Dict]) -> pd.DataFrame:
        """Extract features from network packets for ML analysis"""
        
        features = []
        
        for packet in packets:
            feature_vector = {
                # Temporal features
                'timestamp': packet.get('timestamp', 0),
                'inter_arrival_time': packet.get('inter_arrival_time', 0),
                'flow_duration': packet.get('flow_duration', 0),
                
                # Size features
                'packet_size': packet.get('size', 0),
                'payload_size': packet.get('payload_size', 0),
                'header_size': packet.get('header_size', 0),
                
                # Protocol features
                'protocol_type': self._encode_protocol(packet.get('protocol')),
                'port_src': packet.get('src_port', 0),
                'port_dst': packet.get('dst_port', 0),
                
                # TCP specific features
                'tcp_flags': packet.get('tcp_flags', 0),
                'tcp_window_size': packet.get('tcp_window_size', 0),
                'tcp_ack_num': packet.get('tcp_ack_num', 0),
                
                # Flow features
                'packets_per_second': packet.get('pps', 0),
                'bytes_per_second': packet.get('bps', 0),
                'avg_packet_size': packet.get('avg_size', 0),
                
                # Statistical features
                'entropy': packet.get('entropy', 0),
                'packet_size_variance': packet.get('size_variance', 0),
                'timing_variance': packet.get('timing_variance', 0)
            }
            
            features.append(feature_vector)
        
        return pd.DataFrame(features)
    
    async def train_models(self, training_data: List[Dict]) -> Dict[str, Any]:
        """Train anomaly detection models"""
        
        # Extract features
        feature_df = await self.extract_features(training_data)
        
        # Scale features
        scaled_features = self.scaler.fit_transform(feature_df)
        
        # Train Isolation Forest for anomaly detection
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        self.isolation_forest.fit(scaled_features)
        
        # Train DBSCAN for clustering
        self.dbscan = DBSCAN(
            eps=0.5,
            min_samples=5
        )
        cluster_labels = self.dbscan.fit_predict(scaled_features)
        
        # Calculate training metrics
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = list(cluster_labels).count(-1)
        
        self.is_trained = True
        
        # Save models
        await self._save_models()
        
        return {
            'model_trained': True,
            'n_features': len(feature_df.columns),
            'n_samples': len(feature_df),
            'n_clusters': n_clusters,
            'n_noise_points': n_noise,
            'contamination_rate': 0.1
        }
    
    async def detect_anomalies(self, packets: List[Dict]) -> Dict[str, Any]:
        """Detect anomalies in network traffic"""
        
        if not self.is_trained:
            await self._load_models()
        
        # Extract features
        feature_df = await self.extract_features(packets)
        scaled_features = self.scaler.transform(feature_df)
        
        # Detect anomalies
        anomaly_scores = self.isolation_forest.decision_function(scaled_features)
        anomaly_labels = self.isolation_forest.predict(scaled_features)
        
        # Cluster analysis
        cluster_labels = self.dbscan.fit_predict(scaled_features)
        
        # Identify anomalous packets
        anomalous_indices = np.where(anomaly_labels == -1)[0]
        anomalous_packets = []
        
        for idx in anomalous_indices:
            anomalous_packets.append({
                'packet_index': int(idx),
                'anomaly_score': float(anomaly_scores[idx]),
                'cluster_label': int(cluster_labels[idx]),
                'packet_data': packets[idx],
                'features': feature_df.iloc[idx].to_dict()
            })
        
        # Calculate anomaly statistics
        anomaly_stats = {
            'total_packets': len(packets),
            'anomalous_packets': len(anomalous_packets),
            'anomaly_rate': len(anomalous_packets) / len(packets) * 100,
            'avg_anomaly_score': float(np.mean(anomaly_scores)),
            'min_anomaly_score': float(np.min(anomaly_scores)),
            'max_anomaly_score': float(np.max(anomaly_scores))
        }
        
        return {
            'anomaly_statistics': anomaly_stats,
            'anomalous_packets': anomalous_packets,
            'clustering_info': {
                'n_clusters': len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0),
                'n_noise': int(list(cluster_labels).count(-1))
            }
        }
    
    def _encode_protocol(self, protocol: str) -> int:
        """Encode protocol as numeric value"""
        protocol_map = {
            'TCP': 1, 'UDP': 2, 'ICMP': 3, 'HTTP': 4, 
            'HTTPS': 5, 'DNS': 6, 'SSH': 7, 'FTP': 8
        }
        return protocol_map.get(protocol, 0)
    
    async def _save_models(self):
        """Save trained models to disk"""
        models = {
            'isolation_forest': self.isolation_forest,
            'scaler': self.scaler,
            'dbscan': self.dbscan
        }
        
        joblib.dump(models, 'models/anomaly_detection_models.pkl')
    
    async def _load_models(self):
        """Load trained models from disk"""
        try:
            models = joblib.load('models/anomaly_detection_models.pkl')
            self.isolation_forest = models['isolation_forest']
            self.scaler = models['scaler']
            self.dbscan = models['dbscan']
            self.is_trained = True
        except FileNotFoundError:
            raise ValueError("Models not found. Please train models first.")

# Integration with analysis pipeline
class EnhancedPCAPAnalyzer:
    def __init__(self):
        self.anomaly_detector = NetworkAnomalyDetector()
    
    async def analyze_with_ml(self, file_path: str) -> Dict[str, Any]:
        """Enhanced analysis with ML anomaly detection"""
        
        # Standard analysis
        basic_analysis = await self.standard_pcap_analysis(file_path)
        
        # Extract packets for ML analysis
        packets = await self.extract_packet_data(file_path)
        
        # ML anomaly detection
        anomaly_results = await self.anomaly_detector.detect_anomalies(packets)
        
        # Combine results
        enhanced_analysis = {
            **basic_analysis,
            'ml_analysis': {
                'anomaly_detection': anomaly_results,
                'threat_assessment': await self._assess_threats(anomaly_results),
                'recommendations': await self._generate_recommendations(anomaly_results)
            }
        }
        
        return enhanced_analysis
    
    async def _assess_threats(self, anomaly_results: Dict) -> Dict[str, Any]:
        """Assess threat level based on anomalies"""
        
        anomaly_rate = anomaly_results['anomaly_statistics']['anomaly_rate']
        anomalous_packets = anomaly_results['anomalous_packets']
        
        # Calculate threat score
        threat_score = 0
        
        # Rate-based scoring
        if anomaly_rate > 20:
            threat_score += 30
        elif anomaly_rate > 10:
            threat_score += 15
        elif anomaly_rate > 5:
            threat_score += 5
        
        # Pattern-based scoring
        for packet in anomalous_packets:
            features = packet['features']
            
            # Suspicious port combinations
            if features.get('port_dst') in [22, 23, 3389]:  # SSH, Telnet, RDP
                threat_score += 10
            
            # Unusual packet sizes
            if features.get('packet_size', 0) > 1500 or features.get('packet_size', 0) < 64:
                threat_score += 5
            
            # High entropy (potential encryption/compression)
            if features.get('entropy', 0) > 7.5:
                threat_score += 5
        
        # Determine threat level
        if threat_score > 70:
            threat_level = 'CRITICAL'
        elif threat_score > 50:
            threat_level = 'HIGH'
        elif threat_score > 30:
            threat_level = 'MEDIUM'
        elif threat_score > 10:
            threat_level = 'LOW'
        else:
            threat_level = 'MINIMAL'
        
        return {
            'threat_score': min(threat_score, 100),
            'threat_level': threat_level,
            'confidence': 0.8,  # Model confidence
            'indicators': self._extract_threat_indicators(anomalous_packets)
        }
    
    async def _generate_recommendations(self, anomaly_results: Dict) -> List[str]:
        """Generate security recommendations"""
        
        recommendations = []
        anomaly_rate = anomaly_results['anomaly_statistics']['anomaly_rate']
        
        if anomaly_rate > 15:
            recommendations.append("High anomaly rate detected. Investigate for potential security threats.")
        
        if anomaly_rate > 5:
            recommendations.append("Consider implementing additional network monitoring.")
        
        # Add specific recommendations based on anomaly patterns
        for packet in anomaly_results['anomalous_packets'][:5]:  # Top 5
            features = packet['features']
            
            if features.get('port_dst') == 22:
                recommendations.append("SSH connections detected in anomalous traffic. Verify authentication logs.")
            
            if features.get('entropy', 0) > 7.5:
                recommendations.append("High entropy packets detected. Possible encrypted communication or malware.")
        
        return list(set(recommendations))  # Remove duplicates
```

### 2. Live Network Capture Integration
**Priority**: Medium  
**Impact**: Real-time network monitoring capabilities

```python
# backend/capture/live_capture.py
import asyncio
import scapy.all as scapy
from scapy.all import sniff, AsyncSniffer
from typing import AsyncGenerator, Dict, Any, List
import threading
import queue
import time

class LiveNetworkCapture:
    def __init__(self, interface: str = None):
        self.interface = interface or self._get_default_interface()
        self.is_capturing = False
        self.packet_queue = queue.Queue()
        self.sniffer = None
        
    def _get_default_interface(self) -> str:
        """Get default network interface"""
        try:
            return scapy.conf.iface
        except:
            return "eth0"  # Fallback
    
    async def start_capture(
        self, 
        filter_expr: str = None,
        duration: int = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Start live packet capture"""
        
        self.is_capturing = True
        
        # Configure packet filter
        capture_filter = filter_expr or "ip"
        
        # Start asynchronous sniffer
        self.sniffer = AsyncSniffer(
            iface=self.interface,
            filter=capture_filter,
            prn=self._packet_callback,
            store=False
        )
        
        self.sniffer.start()
        
        start_time = time.time()
        
        try:
            while self.is_capturing:
                # Check duration limit
                if duration and (time.time() - start_time) > duration:
                    break
                
                # Yield captured packets
                if not self.packet_queue.empty():
                    packet_data = self.packet_queue.get()
                    yield packet_data
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
        finally:
            await self.stop_capture()
    
    def _packet_callback(self, packet):
        """Process captured packet"""
        
        try:
            packet_info = self._extract_packet_info(packet)
            self.packet_queue.put(packet_info)
        except Exception as e:
            # Log error but continue capturing
            print(f"Error processing packet: {e}")
    
    def _extract_packet_info(self, packet) -> Dict[str, Any]:
        """Extract useful information from packet"""
        
        info = {
            'timestamp': time.time(),
            'size': len(packet),
            'protocols': []
        }
        
        # Extract layer information
        for layer in packet.layers():
            info['protocols'].append(layer.__name__)
        
        # IP layer information
        if packet.haslayer(scapy.IP):
            ip_layer = packet[scapy.IP]
            info.update({
                'src_ip': ip_layer.src,
                'dst_ip': ip_layer.dst,
                'protocol': ip_layer.proto,
                'ttl': ip_layer.ttl
            })
        
        # TCP layer information
        if packet.haslayer(scapy.TCP):
            tcp_layer = packet[scapy.TCP]
            info.update({
                'src_port': tcp_layer.sport,
                'dst_port': tcp_layer.dport,
                'tcp_flags': tcp_layer.flags,
                'seq_num': tcp_layer.seq,
                'ack_num': tcp_layer.ack
            })
        
        # UDP layer information
        if packet.haslayer(scapy.UDP):
            udp_layer = packet[scapy.UDP]
            info.update({
                'src_port': udp_layer.sport,
                'dst_port': udp_layer.dport,
                'udp_length': udp_layer.len
            })
        
        # HTTP layer information
        if packet.haslayer(scapy.Raw):
            payload = packet[scapy.Raw].load.decode('utf-8', errors='ignore')
            if 'HTTP' in payload:
                info['http_data'] = payload[:200]  # First 200 chars
        
        return info
    
    async def stop_capture(self):
        """Stop packet capture"""
        
        self.is_capturing = False
        
        if self.sniffer:
            self.sniffer.stop()
            self.sniffer = None

# WebSocket endpoint for live capture
@app.websocket("/ws/live-capture")
async def live_capture_websocket(
    websocket: WebSocket,
    interface: str = "eth0",
    filter_expr: str = "ip"
):
    """WebSocket endpoint for live network capture"""
    
    await websocket.accept()
    
    capture = LiveNetworkCapture(interface)
    
    try:
        async for packet_data in capture.start_capture(
            filter_expr=filter_expr,
            duration=300  # 5 minutes max
        ):
            # Send packet data to client
            await websocket.send_json({
                "type": "packet",
                "data": packet_data
            })
            
            # Check for client disconnect
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.1
                )
                
                if message == "stop":
                    break
                    
            except asyncio.TimeoutError:
                continue  # No message from client, continue capturing
            
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    
    finally:
        await capture.stop_capture()
        await websocket.close()

# API endpoint for capture management
@app.post("/api/capture/start")
async def start_network_capture(
    interface: str = "eth0",
    duration: int = 60,
    filter_expr: str = "ip",
    current_user: User = Depends(get_current_user)
):
    """Start network capture session"""
    
    # Check permissions
    if Permission.ADMIN_ACCESS not in get_user_permissions(current_user):
        raise HTTPException(403, "Insufficient permissions for live capture")
    
    capture_id = str(uuid.uuid4())
    
    # Start capture in background
    capture_task = asyncio.create_task(
        run_background_capture(capture_id, interface, duration, filter_expr)
    )
    
    # Store capture session
    await store_capture_session(capture_id, {
        "user_id": current_user.id,
        "interface": interface,
        "duration": duration,
        "filter": filter_expr,
        "started_at": datetime.utcnow(),
        "status": "running",
        "task": capture_task
    })
    
    return {
        "capture_id": capture_id,
        "status": "started",
        "interface": interface,
        "duration": duration
    }

async def run_background_capture(
    capture_id: str,
    interface: str,
    duration: int,
    filter_expr: str
):
    """Run packet capture in background"""
    
    capture = LiveNetworkCapture(interface)
    captured_packets = []
    
    try:
        async for packet_data in capture.start_capture(
            filter_expr=filter_expr,
            duration=duration
        ):
            captured_packets.append(packet_data)
            
            # Update progress
            await update_capture_progress(capture_id, len(captured_packets))
        
        # Save captured data
        file_path = f"captures/{capture_id}.json"
        await save_capture_data(file_path, captured_packets)
        
        # Update session status
        await update_capture_session(capture_id, {
            "status": "completed",
            "packet_count": len(captured_packets),
            "file_path": file_path,
            "completed_at": datetime.utcnow()
        })
        
    except Exception as e:
        await update_capture_session(capture_id, {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.utcnow()
        })
```

### 3. Protocol Deep Inspection Engine
**Priority**: Medium  
**Impact**: Advanced protocol analysis capabilities

```python
# backend/analysis/protocol_inspection.py
import struct
import dpkt
from typing import Dict, List, Any, Optional
import re

class ProtocolInspector:
    def __init__(self):
        self.protocol_parsers = {
            'HTTP': self._analyze_http,
            'DNS': self._analyze_dns,
            'SSH': self._analyze_ssh,
            'TLS': self._analyze_tls,
            'SMTP': self._analyze_smtp,
            'FTP': self._analyze_ftp
        }
    
    async def deep_inspect_protocols(self, packets: List[bytes]) -> Dict[str, Any]:
        """Perform deep protocol inspection"""
        
        protocol_analysis = {}
        
        for packet_data in packets:
            try:
                # Parse Ethernet frame
                eth = dpkt.ethernet.Ethernet(packet_data)
                
                # Only process IP packets
                if isinstance(eth.data, dpkt.ip.IP):
                    ip = eth.data
                    
                    # Analyze based on transport protocol
                    if isinstance(ip.data, dpkt.tcp.TCP):
                        tcp_analysis = await self._analyze_tcp_payload(ip.data)
                        self._merge_analysis(protocol_analysis, tcp_analysis)
                    
                    elif isinstance(ip.data, dpkt.udp.UDP):
                        udp_analysis = await self._analyze_udp_payload(ip.data)
                        self._merge_analysis(protocol_analysis, udp_analysis)
                        
            except Exception as e:
                # Skip malformed packets
                continue
        
        return protocol_analysis
    
    async def _analyze_tcp_payload(self, tcp: dpkt.tcp.TCP) -> Dict[str, Any]:
        """Analyze TCP payload for application protocols"""
        
        analysis = {'TCP': {'connections': 1, 'flags': {}}}
        
        # Analyze TCP flags
        flag_names = ['FIN', 'SYN', 'RST', 'PSH', 'ACK', 'URG', 'ECE', 'CWR']
        for i, flag_name in enumerate(flag_names):
            if tcp.flags & (1 << i):
                analysis['TCP']['flags'][flag_name] = analysis['TCP']['flags'].get(flag_name, 0) + 1
        
        # Try to identify application protocol
        if len(tcp.data) > 0:
            payload = tcp.data
            
            # HTTP detection
            if self._is_http_traffic(payload):
                http_analysis = await self._analyze_http(payload)
                analysis['HTTP'] = http_analysis
            
            # HTTPS/TLS detection
            elif self._is_tls_traffic(payload):
                tls_analysis = await self._analyze_tls(payload)
                analysis['TLS'] = tls_analysis
            
            # SSH detection
            elif self._is_ssh_traffic(payload):
                ssh_analysis = await self._analyze_ssh(payload)
                analysis['SSH'] = ssh_analysis
        
        return analysis
    
    async def _analyze_udp_payload(self, udp: dpkt.udp.UDP) -> Dict[str, Any]:
        """Analyze UDP payload for application protocols"""
        
        analysis = {'UDP': {'packets': 1}}
        
        if len(udp.data) > 0:
            payload = udp.data
            
            # DNS detection (port 53)
            if udp.sport == 53 or udp.dport == 53:
                try:
                    dns_analysis = await self._analyze_dns(payload)
                    analysis['DNS'] = dns_analysis
                except:
                    pass
            
            # DHCP detection (ports 67/68)
            elif udp.sport in [67, 68] or udp.dport in [67, 68]:
                dhcp_analysis = await self._analyze_dhcp(payload)
                analysis['DHCP'] = dhcp_analysis
        
        return analysis
    
    def _is_http_traffic(self, payload: bytes) -> bool:
        """Detect HTTP traffic"""
        try:
            text = payload.decode('utf-8', errors='ignore')
            http_methods = ['GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ']
            return any(text.startswith(method) for method in http_methods) or 'HTTP/' in text
        except:
            return False
    
    def _is_tls_traffic(self, payload: bytes) -> bool:
        """Detect TLS traffic"""
        # TLS record header: content_type(1) + version(2) + length(2)
        if len(payload) < 5:
            return False
        
        content_type = payload[0]
        version = struct.unpack('>H', payload[1:3])[0]
        
        # TLS content types: 20=change_cipher_spec, 21=alert, 22=handshake, 23=application_data
        if content_type in [20, 21, 22, 23] and version in [0x0301, 0x0302, 0x0303, 0x0304]:
            return True
        
        return False
    
    def _is_ssh_traffic(self, payload: bytes) -> bool:
        """Detect SSH traffic"""
        try:
            text = payload.decode('utf-8', errors='ignore')
            return text.startswith('SSH-')
        except:
            return False
    
    async def _analyze_http(self, payload: bytes) -> Dict[str, Any]:
        """Analyze HTTP traffic"""
        
        try:
            text = payload.decode('utf-8', errors='ignore')
            lines = text.split('\\r\\n')
            
            analysis = {
                'requests': 0,
                'responses': 0,
                'methods': {},
                'status_codes': {},
                'user_agents': [],
                'hosts': [],
                'urls': []
            }
            
            # Parse first line
            first_line = lines[0] if lines else ""
            
            # HTTP request
            if any(first_line.startswith(method) for method in ['GET', 'POST', 'PUT', 'DELETE']):
                analysis['requests'] += 1
                
                # Extract method and URL
                parts = first_line.split(' ')
                if len(parts) >= 2:
                    method = parts[0]
                    url = parts[1]
                    analysis['methods'][method] = analysis['methods'].get(method, 0) + 1
                    analysis['urls'].append(url)
            
            # HTTP response
            elif first_line.startswith('HTTP/'):
                analysis['responses'] += 1
                
                # Extract status code
                parts = first_line.split(' ')
                if len(parts) >= 2:
                    status_code = parts[1]
                    analysis['status_codes'][status_code] = analysis['status_codes'].get(status_code, 0) + 1
            
            # Parse headers
            for line in lines[1:]:
                if ': ' in line:
                    header, value = line.split(': ', 1)
                    
                    if header.lower() == 'user-agent':
                        analysis['user_agents'].append(value)
                    elif header.lower() == 'host':
                        analysis['hosts'].append(value)
            
            return analysis
            
        except Exception:
            return {'parse_error': True}
    
    async def _analyze_dns(self, payload: bytes) -> Dict[str, Any]:
        """Analyze DNS traffic"""
        
        try:
            dns = dpkt.dns.DNS(payload)
            
            analysis = {
                'queries': 0,
                'responses': 0,
                'query_types': {},
                'domains': [],
                'response_codes': {}
            }
            
            # Query or response
            if dns.qr == 0:  # Query
                analysis['queries'] += 1
            else:  # Response
                analysis['responses'] += 1
                analysis['response_codes'][dns.rcode] = analysis['response_codes'].get(dns.rcode, 0) + 1
            
            # Process questions
            for question in dns.qd:
                domain = question.name
                qtype = question.type
                
                analysis['domains'].append(domain)
                analysis['query_types'][qtype] = analysis['query_types'].get(qtype, 0) + 1
            
            return analysis
            
        except Exception:
            return {'parse_error': True}
    
    async def _analyze_tls(self, payload: bytes) -> Dict[str, Any]:
        """Analyze TLS traffic"""
        
        analysis = {
            'handshakes': 0,
            'application_data': 0,
            'alerts': 0,
            'versions': {},
            'cipher_suites': []
        }
        
        try:
            offset = 0
            
            while offset < len(payload):
                if offset + 5 > len(payload):
                    break
                
                content_type = payload[offset]
                version = struct.unpack('>H', payload[offset+1:offset+3])[0]
                length = struct.unpack('>H', payload[offset+3:offset+5])[0]
                
                # Record version
                version_name = {
                    0x0301: 'TLSv1.0',
                    0x0302: 'TLSv1.1', 
                    0x0303: 'TLSv1.2',
                    0x0304: 'TLSv1.3'
                }.get(version, f'Unknown-{version:04x}')
                
                analysis['versions'][version_name] = analysis['versions'].get(version_name, 0) + 1
                
                # Count by content type
                if content_type == 22:  # Handshake
                    analysis['handshakes'] += 1
                elif content_type == 23:  # Application data
                    analysis['application_data'] += 1
                elif content_type == 21:  # Alert
                    analysis['alerts'] += 1
                
                offset += 5 + length
            
            return analysis
            
        except Exception:
            return {'parse_error': True}
    
    async def _analyze_ssh(self, payload: bytes) -> Dict[str, Any]:
        """Analyze SSH traffic"""
        
        try:
            text = payload.decode('utf-8', errors='ignore')
            
            analysis = {
                'version_exchanges': 0,
                'key_exchanges': 0,
                'versions': [],
                'algorithms': []
            }
            
            if text.startswith('SSH-'):
                analysis['version_exchanges'] += 1
                
                # Extract SSH version
                version_line = text.split('\\r\\n')[0]
                analysis['versions'].append(version_line)
            
            # Detect key exchange (binary data following version exchange)
            if len(payload) > 100 and not text.isprintable():
                analysis['key_exchanges'] += 1
            
            return analysis
            
        except Exception:
            return {'parse_error': True}
    
    def _merge_analysis(self, main_analysis: Dict, new_analysis: Dict):
        """Merge protocol analysis results"""
        
        for protocol, data in new_analysis.items():
            if protocol not in main_analysis:
                main_analysis[protocol] = data
            else:
                # Merge dictionaries
                for key, value in data.items():
                    if isinstance(value, dict):
                        if key not in main_analysis[protocol]:
                            main_analysis[protocol][key] = value
                        else:
                            for sub_key, sub_value in value.items():
                                main_analysis[protocol][key][sub_key] = (
                                    main_analysis[protocol][key].get(sub_key, 0) + sub_value
                                )
                    elif isinstance(value, list):
                        if key not in main_analysis[protocol]:
                            main_analysis[protocol][key] = value
                        else:
                            main_analysis[protocol][key].extend(value)
                    elif isinstance(value, (int, float)):
                        main_analysis[protocol][key] = main_analysis[protocol].get(key, 0) + value
```

---

## 🔍 ADVANCED REPORTING FEATURES

### 4. Automated Report Generation
**Priority**: Medium  
**Impact**: Comprehensive automated analysis reports

```python
# backend/reporting/automated_reports.py
from jinja2 import Environment, FileSystemLoader
import asyncio
from weasyprint import HTML, CSS
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

class AutomatedReportGenerator:
    def __init__(self):
        self.jinja_env = Environment(loader=FileSystemLoader('templates/reports'))
        
    async def generate_comprehensive_report(
        self, 
        analysis_result: Dict[str, Any],
        report_type: str = "full"
    ) -> Dict[str, Any]:
        """Generate comprehensive automated report"""
        
        # Generate visualizations
        charts = await self._generate_charts(analysis_result)
        
        # Analyze trends and patterns
        insights = await self._generate_insights(analysis_result)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(analysis_result)
        
        # Create executive summary
        executive_summary = await self._create_executive_summary(
            analysis_result, insights, recommendations
        )
        
        # Compile report data
        report_data = {
            'metadata': {
                'generated_at': datetime.utcnow(),
                'report_type': report_type,
                'version': '1.0'
            },
            'executive_summary': executive_summary,
            'technical_analysis': analysis_result,
            'insights': insights,
            'recommendations': recommendations,
            'visualizations': charts,
            'appendices': await self._generate_appendices(analysis_result)
        }
        
        # Generate different output formats
        outputs = {
            'json': report_data,
            'html': await self._generate_html_report(report_data),
            'pdf': await self._generate_pdf_report(report_data)
        }
        
        return outputs
    
    async def _generate_charts(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """Generate visualization charts"""
        
        charts = {}
        
        # Protocol distribution pie chart
        if 'protocol_analysis' in analysis_result:
            charts['protocol_distribution'] = await self._create_protocol_pie_chart(
                analysis_result['protocol_analysis']
            )
        
        # Traffic timeline
        if 'traffic_timeline' in analysis_result:
            charts['traffic_timeline'] = await self._create_timeline_chart(
                analysis_result['traffic_timeline']
            )
        
        # Top conversations bar chart
        if 'top_conversations' in analysis_result:
            charts['top_conversations'] = await self._create_conversations_chart(
                analysis_result['top_conversations']
            )
        
        # Security analysis radar chart
        if 'security_analysis' in analysis_result:
            charts['security_radar'] = await self._create_security_radar_chart(
                analysis_result['security_analysis']
            )
        
        return charts
    
    async def _create_protocol_pie_chart(self, protocol_data: Dict) -> str:
        """Create protocol distribution pie chart"""
        
        plt.figure(figsize=(10, 8))
        
        protocols = list(protocol_data.keys())
        sizes = [protocol_data[p].get('packet_count', 0) for p in protocols]
        
        plt.pie(sizes, labels=protocols, autopct='%1.1f%%', startangle=90)
        plt.title('Protocol Distribution')
        
        # Convert to base64 string
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        
        img_str = base64.b64encode(img_buffer.read()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_str}"
    
    async def _create_timeline_chart(self, timeline_data: List[Dict]) -> str:
        """Create traffic timeline chart"""
        
        plt.figure(figsize=(12, 6))
        
        timestamps = [item['timestamp'] for item in timeline_data]
        bytes_per_second = [item['bytes'] for item in timeline_data]
        
        plt.plot(timestamps, bytes_per_second, linewidth=2)
        plt.title('Network Traffic Timeline')
        plt.xlabel('Time')
        plt.ylabel('Bytes per Second')
        plt.xticks(rotation=45)
        
        # Convert to base64 string
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        
        img_str = base64.b64encode(img_buffer.read()).decode()
        plt.close()
        
        return f"data:image/png;base64,{img_str}"
    
    async def _generate_insights(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate automated insights from analysis"""
        
        insights = []
        
        # Traffic volume insights
        if 'executive_summary' in analysis_result:
            summary = analysis_result['executive_summary']
            total_bytes = summary.get('total_bytes', 0)
            
            if total_bytes > 1024**3:  # > 1GB
                insights.append({
                    'type': 'traffic_volume',
                    'severity': 'info',
                    'title': 'High Traffic Volume',
                    'description': f'Large amount of data transferred: {total_bytes / 1024**3:.2f} GB',
                    'recommendation': 'Monitor for potential data exfiltration or backup activities'
                })
        
        # Protocol anomalies
        if 'protocol_analysis' in analysis_result:
            protocols = analysis_result['protocol_analysis']
            
            # Check for unusual protocols
            unusual_protocols = ['IRC', 'P2P', 'TOR']
            for protocol in unusual_protocols:
                if protocol in protocols:
                    insights.append({
                        'type': 'protocol_anomaly',
                        'severity': 'warning',
                        'title': f'Unusual Protocol Detected: {protocol}',
                        'description': f'{protocol} traffic detected in network',
                        'recommendation': 'Investigate source and purpose of this traffic'
                    })
        
        # Security insights
        if 'security_analysis' in analysis_result:
            security = analysis_result['security_analysis']
            risk_score = security.get('risk_score', 0)
            
            if risk_score > 70:
                insights.append({
                    'type': 'security_risk',
                    'severity': 'critical',
                    'title': 'High Security Risk',
                    'description': f'Security risk score: {risk_score}/100',
                    'recommendation': 'Immediate security investigation required'
                })
            elif risk_score > 40:
                insights.append({
                    'type': 'security_risk',
                    'severity': 'warning',
                    'title': 'Moderate Security Risk',
                    'description': f'Security risk score: {risk_score}/100',
                    'recommendation': 'Review security events and implement additional monitoring'
                })
        
        return insights
    
    async def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate automated recommendations"""
        
        recommendations = []
        
        # Security recommendations
        if 'security_analysis' in analysis_result:
            security = analysis_result['security_analysis']
            
            if security.get('port_scanning'):
                recommendations.append({
                    'category': 'security',
                    'priority': 'high',
                    'title': 'Implement Port Scan Detection',
                    'description': 'Port scanning activity detected',
                    'actions': [
                        'Configure IDS/IPS rules for port scan detection',
                        'Review firewall rules and close unnecessary ports',
                        'Monitor for follow-up attacks'
                    ]
                })
        
        # Performance recommendations
        if 'protocol_analysis' in analysis_result:
            protocols = analysis_result['protocol_analysis']
            
            # Check for TCP retransmissions
            tcp_data = protocols.get('TCP', {})
            if tcp_data.get('retransmissions', 0) > 100:
                recommendations.append({
                    'category': 'performance',
                    'priority': 'medium',
                    'title': 'Network Performance Issues',
                    'description': 'High number of TCP retransmissions detected',
                    'actions': [
                        'Check network equipment for errors',
                        'Verify network bandwidth is sufficient',
                        'Consider network optimization'
                    ]
                })
        
        return recommendations
    
    async def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report"""
        
        template = self.jinja_env.get_template('comprehensive_report.html')
        
        html_content = template.render(
            report=report_data,
            generated_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        return html_content
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any]) -> bytes:
        """Generate PDF report"""
        
        # Generate HTML first
        html_content = await self._generate_html_report(report_data)
        
        # Convert to PDF
        pdf_css = CSS(string='''
            @page {
                margin: 2cm;
                @top-center {
                    content: "PCAP Analysis Report";
                }
                @bottom-center {
                    content: counter(page);
                }
            }
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
            }
            .chart {
                page-break-inside: avoid;
                margin: 1em 0;
            }
            .executive-summary {
                background-color: #f8f9fa;
                padding: 1em;
                border-left: 4px solid #007bff;
            }
        ''')
        
        pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[pdf_css])
        
        return pdf_bytes

# API endpoint for automated reports
@app.post("/api/reports/{job_id}/generate-report")
async def generate_automated_report(
    job_id: str,
    report_type: str = "full",
    format: str = "pdf",
    current_user: User = Depends(get_current_user)
):
    """Generate automated comprehensive report"""
    
    # Get analysis result
    analysis_result = await get_analysis_result(job_id)
    if not analysis_result:
        raise HTTPException(404, "Analysis result not found")
    
    # Generate report
    report_generator = AutomatedReportGenerator()
    reports = await report_generator.generate_comprehensive_report(
        analysis_result, report_type
    )
    
    if format == "pdf":
        return Response(
            content=reports['pdf'],
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_{job_id}.pdf"}
        )
    elif format == "html":
        return HTMLResponse(content=reports['html'])
    else:
        return reports['json']
```

---

## 📊 COMPARISON AND ANALYSIS TOOLS

### 5. PCAP Comparison Tool
**Priority**: Low  
**Impact**: Compare multiple PCAP files for differences

```python
# backend/analysis/comparison_tool.py
from typing import Dict, List, Any, Tuple
import difflib
from dataclasses import dataclass

@dataclass
class ComparisonMetric:
    name: str
    baseline_value: Any
    comparison_value: Any
    difference: Any
    percentage_change: float
    significance: str  # 'low', 'medium', 'high'

class PCAPComparisonTool:
    def __init__(self):
        self.comparison_metrics = [
            'total_packets',
            'total_bytes',
            'duration',
            'protocols',
            'top_conversations',
            'security_events'
        ]
    
    async def compare_analyses(
        self, 
        baseline_analysis: Dict[str, Any],
        comparison_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two PCAP analysis results"""
        
        comparison_result = {
            'baseline_info': self._extract_basic_info(baseline_analysis),
            'comparison_info': self._extract_basic_info(comparison_analysis),
            'metrics_comparison': [],
            'protocol_differences': {},
            'security_comparison': {},
            'summary': {}
        }
        
        # Compare basic metrics
        for metric in self.comparison_metrics:
            metric_comparison = await self._compare_metric(
                metric, baseline_analysis, comparison_analysis
            )
            if metric_comparison:
                comparison_result['metrics_comparison'].append(metric_comparison)
        
        # Compare protocols
        comparison_result['protocol_differences'] = await self._compare_protocols(
            baseline_analysis.get('protocol_analysis', {}),
            comparison_analysis.get('protocol_analysis', {})
        )
        
        # Compare security analysis
        comparison_result['security_comparison'] = await self._compare_security(
            baseline_analysis.get('security_analysis', {}),
            comparison_analysis.get('security_analysis', {})
        )
        
        # Generate summary
        comparison_result['summary'] = await self._generate_comparison_summary(
            comparison_result
        )
        
        return comparison_result
    
    async def _compare_metric(
        self, 
        metric_name: str,
        baseline: Dict[str, Any],
        comparison: Dict[str, Any]
    ) -> Optional[ComparisonMetric]:
        """Compare a specific metric between two analyses"""
        
        # Extract values based on metric type
        if metric_name == 'total_packets':
            baseline_val = baseline.get('executive_summary', {}).get('total_packets', 0)
            comparison_val = comparison.get('executive_summary', {}).get('total_packets', 0)
        
        elif metric_name == 'total_bytes':
            baseline_val = baseline.get('executive_summary', {}).get('total_bytes', 0)
            comparison_val = comparison.get('executive_summary', {}).get('total_bytes', 0)
        
        elif metric_name == 'duration':
            baseline_val = baseline.get('executive_summary', {}).get('duration', 0)
            comparison_val = comparison.get('executive_summary', {}).get('duration', 0)
        
        else:
            return None
        
        # Calculate difference and percentage change
        difference = comparison_val - baseline_val
        
        if baseline_val != 0:
            percentage_change = (difference / baseline_val) * 100
        else:
            percentage_change = 100 if comparison_val > 0 else 0
        
        # Determine significance
        if abs(percentage_change) > 50:
            significance = 'high'
        elif abs(percentage_change) > 20:
            significance = 'medium'
        else:
            significance = 'low'
        
        return ComparisonMetric(
            name=metric_name,
            baseline_value=baseline_val,
            comparison_value=comparison_val,
            difference=difference,
            percentage_change=percentage_change,
            significance=significance
        )
    
    async def _compare_protocols(
        self, 
        baseline_protocols: Dict[str, Any],
        comparison_protocols: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare protocol usage between analyses"""
        
        protocol_diff = {
            'new_protocols': [],
            'removed_protocols': [],
            'changed_protocols': []
        }
        
        baseline_set = set(baseline_protocols.keys())
        comparison_set = set(comparison_protocols.keys())
        
        # Find new and removed protocols
        protocol_diff['new_protocols'] = list(comparison_set - baseline_set)
        protocol_diff['removed_protocols'] = list(baseline_set - comparison_set)
        
        # Compare common protocols
        common_protocols = baseline_set & comparison_set
        
        for protocol in common_protocols:
            baseline_count = baseline_protocols[protocol].get('packet_count', 0)
            comparison_count = comparison_protocols[protocol].get('packet_count', 0)
            
            if baseline_count != comparison_count:
                change_pct = ((comparison_count - baseline_count) / baseline_count * 100) if baseline_count > 0 else 100
                
                protocol_diff['changed_protocols'].append({
                    'protocol': protocol,
                    'baseline_count': baseline_count,
                    'comparison_count': comparison_count,
                    'change_percentage': change_pct
                })
        
        return protocol_diff

# API endpoint for comparison
@app.post("/api/reports/compare")
async def compare_pcap_analyses(
    baseline_job_id: str,
    comparison_job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Compare two PCAP analysis results"""
    
    # Get both analyses
    baseline_analysis = await get_analysis_result(baseline_job_id)
    comparison_analysis = await get_analysis_result(comparison_job_id)
    
    if not baseline_analysis or not comparison_analysis:
        raise HTTPException(404, "One or both analysis results not found")
    
    # Perform comparison
    comparison_tool = PCAPComparisonTool()
    comparison_result = await comparison_tool.compare_analyses(
        baseline_analysis, comparison_analysis
    )
    
    # Store comparison result
    comparison_id = str(uuid.uuid4())
    await store_comparison_result(comparison_id, {
        'baseline_job_id': baseline_job_id,
        'comparison_job_id': comparison_job_id,
        'user_id': current_user.id,
        'result': comparison_result,
        'created_at': datetime.utcnow()
    })
    
    return {
        'comparison_id': comparison_id,
        'result': comparison_result
    }
```

---

## 📋 Implementation Priority

### Phase 1: ML Foundation (Month 1)
1. Machine Learning anomaly detection
2. Enhanced protocol inspection
3. Training data collection

### Phase 2: Live Capabilities (Month 2)
1. Live network capture integration
2. Real-time analysis pipeline
3. WebSocket streaming

### Phase 3: Advanced Reporting (Month 3)
1. Automated report generation
2. Comparison tools
3. Advanced visualizations

### Phase 4: Production Features (Month 4)
1. Performance optimization
2. Scalability improvements
3. User testing and feedback