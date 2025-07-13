"""
Machine Learning Anomaly Detection for Network Traffic Analysis.

Provides intelligent anomaly detection capabilities using various ML algorithms
to identify unusual network behavior patterns that traditional rule-based 
systems might miss.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import pickle
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

# Import ML libraries
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.decomposition import PCA
    from sklearn.svm import OneClassSVM
    from sklearn.covariance import EllipticEnvelope
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("Scikit-learn not available - ML anomaly detection will be limited")

# Import Scapy for packet analysis
try:
    from scapy.all import rdpcap, IP, TCP, UDP, DNS, Raw, Ether, ICMP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logging.warning("Scapy not available - packet feature extraction will be limited")

logger = logging.getLogger(__name__)


@dataclass
class NetworkFeatures:
    """Network traffic features for ML analysis."""
    
    # Flow-level features
    flow_duration: float
    packet_count: int
    byte_count: int
    packets_per_second: float
    bytes_per_second: float
    
    # Packet size features
    avg_packet_size: float
    min_packet_size: int
    max_packet_size: int
    packet_size_variance: float
    
    # Timing features
    avg_inter_arrival_time: float
    inter_arrival_variance: float
    flow_idle_time: float
    
    # Protocol features
    tcp_flag_distribution: Dict[str, int]
    port_entropy: float
    protocol_distribution: Dict[str, float]
    
    # Behavioral features
    connection_state_changes: int
    retransmission_rate: float
    out_of_order_packets: int
    duplicate_packets: int
    
    # Advanced features
    payload_entropy: float
    header_anomalies: int
    time_of_day: int  # Hour 0-23
    day_of_week: int  # 0-6


@dataclass
class AnomalyResult:
    """ML anomaly detection result."""
    
    flow_id: str
    anomaly_score: float
    is_anomaly: bool
    anomaly_type: str
    confidence: float
    features_contributing: List[str]
    description: str
    severity: str
    timestamp: str


class MLAnomalyDetector:
    """Machine learning-based network anomaly detector."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ML anomaly detector."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = {
            'model_save_path': '/tmp/ml_models',
            'enable_isolation_forest': True,
            'enable_dbscan': True,
            'enable_one_class_svm': True,
            'enable_elliptic_envelope': True,
            'enable_ensemble': True,
            
            # Model parameters
            'isolation_forest_contamination': 0.1,
            'isolation_forest_n_estimators': 100,
            'dbscan_eps': 0.5,
            'dbscan_min_samples': 5,
            'svm_gamma': 'scale',
            'svm_nu': 0.1,
            
            # Feature extraction
            'max_flows_to_analyze': 10000,
            'min_packets_per_flow': 5,
            'feature_normalization': 'standard',
            'enable_pca': True,
            'pca_components': 0.95,
            
            # Anomaly thresholds
            'anomaly_threshold': 0.5,
            'high_confidence_threshold': 0.8,
            'ensemble_vote_threshold': 0.6,
            
            # Training parameters
            'auto_retrain': True,
            'retrain_threshold': 1000,  # samples
            'model_update_interval': 3600,  # seconds
        }
        
        if config:
            self.config.update(config)
        
        # Initialize models
        self.models = {}
        self.scalers = {}
        self.feature_extractors = {}
        self.training_data = []
        self.model_last_updated = {}
        
        # Create model save directory
        Path(self.config['model_save_path']).mkdir(parents=True, exist_ok=True)
        
        self._initialize_models()
        self.logger.info("ML anomaly detector initialized")
    
    def _initialize_models(self):
        """Initialize ML models."""
        if not ML_AVAILABLE:
            self.logger.warning("ML libraries not available - models will not be initialized")
            return
        
        try:
            # Isolation Forest
            if self.config['enable_isolation_forest']:
                self.models['isolation_forest'] = IsolationForest(
                    contamination=self.config['isolation_forest_contamination'],
                    n_estimators=self.config['isolation_forest_n_estimators'],
                    random_state=42
                )
            
            # DBSCAN for density-based clustering
            if self.config['enable_dbscan']:
                self.models['dbscan'] = DBSCAN(
                    eps=self.config['dbscan_eps'],
                    min_samples=self.config['dbscan_min_samples']
                )
            
            # One-Class SVM
            if self.config['enable_one_class_svm']:
                self.models['one_class_svm'] = OneClassSVM(
                    gamma=self.config['svm_gamma'],
                    nu=self.config['svm_nu']
                )
            
            # Elliptic Envelope
            if self.config['enable_elliptic_envelope']:
                self.models['elliptic_envelope'] = EllipticEnvelope(
                    contamination=0.1,
                    random_state=42
                )
            
            # Scalers
            if self.config['feature_normalization'] == 'standard':
                self.scalers['standard'] = StandardScaler()
            elif self.config['feature_normalization'] == 'minmax':
                self.scalers['minmax'] = MinMaxScaler()
            
            # PCA for dimensionality reduction
            if self.config['enable_pca']:
                self.scalers['pca'] = PCA(n_components=self.config['pca_components'])
            
            self.logger.info("ML models initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing ML models: {e}")
    
    async def analyze_pcap_for_anomalies(self, pcap_path: str) -> Dict[str, Any]:
        """
        Analyze PCAP file for network anomalies using ML.
        
        Args:
            pcap_path: Path to PCAP file
            
        Returns:
            ML anomaly detection results
        """
        if not ML_AVAILABLE or not SCAPY_AVAILABLE:
            return {
                'error': 'ML or Scapy libraries not available',
                'anomalies': [],
                'model_info': {},
                'feature_statistics': {}
            }
        
        try:
            start_time = time.time()
            
            # Extract features from PCAP
            features_data = await self._extract_network_features(pcap_path)
            
            if not features_data:
                return {
                    'anomalies': [],
                    'model_info': {'error': 'No features extracted'},
                    'feature_statistics': {},
                    'processing_time': time.time() - start_time
                }
            
            # Prepare features for ML
            feature_matrix, flow_ids = self._prepare_feature_matrix(features_data)
            
            if feature_matrix.size == 0:
                return {
                    'anomalies': [],
                    'model_info': {'error': 'Empty feature matrix'},
                    'feature_statistics': {},
                    'processing_time': time.time() - start_time
                }
            
            # Detect anomalies using ensemble of models
            anomalies = await self._detect_anomalies_ensemble(
                feature_matrix, flow_ids, features_data
            )
            
            # Generate model information
            model_info = self._get_model_info()
            
            # Calculate feature statistics
            feature_stats = self._calculate_feature_statistics(feature_matrix)
            
            processing_time = time.time() - start_time
            
            return {
                'anomalies': [asdict(anomaly) for anomaly in anomalies],
                'model_info': model_info,
                'feature_statistics': feature_stats,
                'total_flows_analyzed': len(features_data),
                'anomalies_detected': len(anomalies),
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Error in ML anomaly analysis: {e}")
            return {
                'error': str(e),
                'anomalies': [],
                'model_info': {},
                'feature_statistics': {}
            }
    
    async def _extract_network_features(self, pcap_path: str) -> List[NetworkFeatures]:
        """Extract network features from PCAP file."""
        try:
            packets = rdpcap(pcap_path)
            self.logger.info(f"Loaded {len(packets)} packets for feature extraction")
            
            # Group packets by flow
            flows = defaultdict(list)
            
            for packet in packets:
                if packet.haslayer(IP):
                    # Create flow key (bidirectional)
                    src_ip = packet[IP].src
                    dst_ip = packet[IP].dst
                    
                    if packet.haslayer(TCP):
                        src_port = packet[TCP].sport
                        dst_port = packet[TCP].dport
                        protocol = 'TCP'
                    elif packet.haslayer(UDP):
                        src_port = packet[UDP].sport
                        dst_port = packet[UDP].dport
                        protocol = 'UDP'
                    else:
                        src_port = 0
                        dst_port = 0
                        protocol = 'OTHER'
                    
                    # Normalize flow key for bidirectional flows
                    flow_key = tuple(sorted([
                        (src_ip, src_port, dst_ip, dst_port, protocol)
                    ]))
                    
                    flows[flow_key].append(packet)
            
            # Extract features for each flow
            features_list = []
            
            for flow_key, flow_packets in flows.items():
                if len(flow_packets) >= self.config['min_packets_per_flow']:
                    features = await self._extract_flow_features(flow_key, flow_packets)
                    if features:
                        features_list.append(features)
                
                # Limit number of flows to prevent memory issues
                if len(features_list) >= self.config['max_flows_to_analyze']:
                    break
            
            self.logger.info(f"Extracted features for {len(features_list)} flows")
            return features_list
            
        except Exception as e:
            self.logger.error(f"Error extracting network features: {e}")
            return []
    
    async def _extract_flow_features(self, flow_key: Tuple, packets: List) -> Optional[NetworkFeatures]:
        """Extract features for a single network flow."""
        try:
            if not packets:
                return None
            
            # Basic flow statistics
            packet_count = len(packets)
            byte_count = sum(len(pkt) for pkt in packets)
            flow_duration = packets[-1].time - packets[0].time if len(packets) > 1 else 0
            
            # Calculate rates
            packets_per_second = packet_count / flow_duration if flow_duration > 0 else 0
            bytes_per_second = byte_count / flow_duration if flow_duration > 0 else 0
            
            # Packet size statistics
            packet_sizes = [len(pkt) for pkt in packets]
            avg_packet_size = np.mean(packet_sizes)
            min_packet_size = min(packet_sizes)
            max_packet_size = max(packet_sizes)
            packet_size_variance = np.var(packet_sizes)
            
            # Timing features
            if len(packets) > 1:
                inter_arrival_times = [packets[i].time - packets[i-1].time 
                                     for i in range(1, len(packets))]
                avg_inter_arrival_time = np.mean(inter_arrival_times)
                inter_arrival_variance = np.var(inter_arrival_times)
            else:
                avg_inter_arrival_time = 0
                inter_arrival_variance = 0
            
            # Protocol-specific features
            tcp_flags = defaultdict(int)
            ports = []
            protocols = defaultdict(int)
            retransmissions = 0
            out_of_order = 0
            duplicates = 0
            payload_data = b''
            
            for pkt in packets:
                if pkt.haslayer(TCP):
                    tcp_layer = pkt[TCP]
                    protocols['TCP'] += 1
                    ports.extend([tcp_layer.sport, tcp_layer.dport])
                    
                    # TCP flags
                    if tcp_layer.flags & 0x01: tcp_flags['FIN'] += 1
                    if tcp_layer.flags & 0x02: tcp_flags['SYN'] += 1
                    if tcp_layer.flags & 0x04: tcp_flags['RST'] += 1
                    if tcp_layer.flags & 0x08: tcp_flags['PSH'] += 1
                    if tcp_layer.flags & 0x10: tcp_flags['ACK'] += 1
                    if tcp_layer.flags & 0x20: tcp_flags['URG'] += 1
                    
                elif pkt.haslayer(UDP):
                    udp_layer = pkt[UDP]
                    protocols['UDP'] += 1
                    ports.extend([udp_layer.sport, udp_layer.dport])
                
                # Collect payload for entropy calculation
                if pkt.haslayer(Raw):
                    payload_data += pkt[Raw].load[:1024]  # Limit to prevent memory issues
            
            # Calculate port entropy
            if ports:
                port_counts = defaultdict(int)
                for port in ports:
                    port_counts[port] += 1
                port_probs = [count/len(ports) for count in port_counts.values()]
                port_entropy = -sum(p * np.log2(p) for p in port_probs if p > 0)
            else:
                port_entropy = 0
            
            # Calculate payload entropy
            if payload_data:
                byte_counts = defaultdict(int)
                for byte in payload_data:
                    byte_counts[byte] += 1
                byte_probs = [count/len(payload_data) for count in byte_counts.values()]
                payload_entropy = -sum(p * np.log2(p) for p in byte_probs if p > 0)
            else:
                payload_entropy = 0
            
            # Protocol distribution
            total_packets = sum(protocols.values())
            protocol_distribution = {
                proto: count/total_packets 
                for proto, count in protocols.items()
            }
            
            # Time-based features
            timestamp = packets[0].time
            dt = datetime.fromtimestamp(timestamp)
            time_of_day = dt.hour
            day_of_week = dt.weekday()
            
            return NetworkFeatures(
                flow_duration=flow_duration,
                packet_count=packet_count,
                byte_count=byte_count,
                packets_per_second=packets_per_second,
                bytes_per_second=bytes_per_second,
                avg_packet_size=avg_packet_size,
                min_packet_size=min_packet_size,
                max_packet_size=max_packet_size,
                packet_size_variance=packet_size_variance,
                avg_inter_arrival_time=avg_inter_arrival_time,
                inter_arrival_variance=inter_arrival_variance,
                flow_idle_time=0,  # Would need more complex calculation
                tcp_flag_distribution=dict(tcp_flags),
                port_entropy=port_entropy,
                protocol_distribution=protocol_distribution,
                connection_state_changes=0,  # Simplified
                retransmission_rate=retransmissions / packet_count,
                out_of_order_packets=out_of_order,
                duplicate_packets=duplicates,
                payload_entropy=payload_entropy,
                header_anomalies=0,  # Would need specific detection
                time_of_day=time_of_day,
                day_of_week=day_of_week
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting flow features: {e}")
            return None
    
    def _prepare_feature_matrix(self, features_data: List[NetworkFeatures]) -> Tuple[np.ndarray, List[str]]:
        """Prepare feature matrix for ML algorithms."""
        try:
            if not features_data:
                return np.array([]), []
            
            # Convert features to numerical matrix
            feature_vectors = []
            flow_ids = []
            
            for i, features in enumerate(features_data):
                flow_id = f"flow_{i}"
                flow_ids.append(flow_id)
                
                # Extract numerical features
                vector = [
                    features.flow_duration,
                    features.packet_count,
                    features.byte_count,
                    features.packets_per_second,
                    features.bytes_per_second,
                    features.avg_packet_size,
                    features.min_packet_size,
                    features.max_packet_size,
                    features.packet_size_variance,
                    features.avg_inter_arrival_time,
                    features.inter_arrival_variance,
                    features.port_entropy,
                    features.retransmission_rate,
                    features.payload_entropy,
                    features.time_of_day,
                    features.day_of_week,
                    
                    # TCP flags (simplified to counts)
                    features.tcp_flag_distribution.get('SYN', 0),
                    features.tcp_flag_distribution.get('ACK', 0),
                    features.tcp_flag_distribution.get('FIN', 0),
                    features.tcp_flag_distribution.get('RST', 0),
                    
                    # Protocol distribution (TCP percentage)
                    features.protocol_distribution.get('TCP', 0),
                    features.protocol_distribution.get('UDP', 0),
                ]
                
                # Handle NaN and infinity values
                vector = [0 if np.isnan(x) or np.isinf(x) else x for x in vector]
                feature_vectors.append(vector)
            
            feature_matrix = np.array(feature_vectors)
            
            # Apply scaling if configured
            if self.config['feature_normalization'] == 'standard' and 'standard' in self.scalers:
                if not hasattr(self.scalers['standard'], 'scale_'):
                    self.scalers['standard'].fit(feature_matrix)
                feature_matrix = self.scalers['standard'].transform(feature_matrix)
            
            return feature_matrix, flow_ids
            
        except Exception as e:
            self.logger.error(f"Error preparing feature matrix: {e}")
            return np.array([]), []
    
    async def _detect_anomalies_ensemble(self, feature_matrix: np.ndarray, 
                                       flow_ids: List[str], 
                                       features_data: List[NetworkFeatures]) -> List[AnomalyResult]:
        """Detect anomalies using ensemble of ML models."""
        try:
            anomalies = []
            
            if feature_matrix.size == 0:
                return anomalies
            
            # Individual model predictions
            model_predictions = {}
            model_scores = {}
            
            # Isolation Forest
            if 'isolation_forest' in self.models:
                try:
                    model = self.models['isolation_forest']
                    model.fit(feature_matrix)
                    predictions = model.predict(feature_matrix)
                    scores = model.score_samples(feature_matrix)
                    model_predictions['isolation_forest'] = predictions
                    model_scores['isolation_forest'] = scores
                except Exception as e:
                    self.logger.warning(f"Isolation Forest prediction failed: {e}")
            
            # One-Class SVM
            if 'one_class_svm' in self.models:
                try:
                    model = self.models['one_class_svm']
                    model.fit(feature_matrix)
                    predictions = model.predict(feature_matrix)
                    scores = model.score_samples(feature_matrix)
                    model_predictions['one_class_svm'] = predictions
                    model_scores['one_class_svm'] = scores
                except Exception as e:
                    self.logger.warning(f"One-Class SVM prediction failed: {e}")
            
            # Elliptic Envelope
            if 'elliptic_envelope' in self.models:
                try:
                    model = self.models['elliptic_envelope']
                    model.fit(feature_matrix)
                    predictions = model.predict(feature_matrix)
                    scores = model.score_samples(feature_matrix)
                    model_predictions['elliptic_envelope'] = predictions
                    model_scores['elliptic_envelope'] = scores
                except Exception as e:
                    self.logger.warning(f"Elliptic Envelope prediction failed: {e}")
            
            # Ensemble voting
            for i, flow_id in enumerate(flow_ids):
                anomaly_votes = 0
                total_models = 0
                avg_score = 0
                contributing_models = []
                
                for model_name, predictions in model_predictions.items():
                    total_models += 1
                    if predictions[i] == -1:  # Anomaly
                        anomaly_votes += 1
                        contributing_models.append(model_name)
                    
                    # Add to average score
                    if model_name in model_scores:
                        avg_score += abs(model_scores[model_name][i])
                
                if total_models > 0:
                    ensemble_confidence = anomaly_votes / total_models
                    avg_score = avg_score / total_models
                    
                    # Determine if anomaly based on ensemble vote
                    is_anomaly = ensemble_confidence >= self.config['ensemble_vote_threshold']
                    
                    if is_anomaly:
                        # Classify anomaly type based on features
                        anomaly_type, description = self._classify_anomaly_type(features_data[i])
                        
                        # Determine severity
                        if ensemble_confidence >= self.config['high_confidence_threshold']:
                            severity = 'high'
                        elif ensemble_confidence >= 0.7:
                            severity = 'medium'
                        else:
                            severity = 'low'
                        
                        anomaly = AnomalyResult(
                            flow_id=flow_id,
                            anomaly_score=avg_score,
                            is_anomaly=is_anomaly,
                            anomaly_type=anomaly_type,
                            confidence=ensemble_confidence,
                            features_contributing=contributing_models,
                            description=description,
                            severity=severity,
                            timestamp=datetime.utcnow().isoformat()
                        )
                        
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error in ensemble anomaly detection: {e}")
            return []
    
    def _classify_anomaly_type(self, features: NetworkFeatures) -> Tuple[str, str]:
        """Classify the type of anomaly based on features."""
        try:
            # High entropy payload
            if features.payload_entropy > 7.5:
                return "encrypted_traffic", "High entropy payload suggesting encrypted or compressed data"
            
            # Unusual packet sizes
            if features.packet_size_variance > 10000:
                return "size_anomaly", "Unusual variation in packet sizes"
            
            # High connection rate
            if features.packets_per_second > 1000:
                return "high_volume", "Unusually high packet rate"
            
            # Port scanning indicators
            if features.port_entropy > 10:
                return "port_scan", "High port entropy suggesting port scanning activity"
            
            # Timing anomalies
            if features.inter_arrival_variance > 1.0:
                return "timing_anomaly", "Irregular packet timing patterns"
            
            # Protocol anomalies
            tcp_ratio = features.protocol_distribution.get('TCP', 0)
            if tcp_ratio < 0.1 and features.packet_count > 10:
                return "protocol_anomaly", "Unusual protocol distribution"
            
            # Large flow
            if features.byte_count > 10_000_000:  # 10MB
                return "large_transfer", "Unusually large data transfer"
            
            # Short-lived high-rate flows
            if features.flow_duration < 1 and features.packet_count > 100:
                return "burst_activity", "High-rate burst activity"
            
            return "general_anomaly", "Anomalous network behavior detected"
            
        except Exception as e:
            self.logger.error(f"Error classifying anomaly type: {e}")
            return "unknown_anomaly", "Unclassified network anomaly"
    
    def _get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            'models_available': list(self.models.keys()),
            'ml_libraries_available': ML_AVAILABLE,
            'scapy_available': SCAPY_AVAILABLE,
            'feature_normalization': self.config['feature_normalization'],
            'ensemble_voting': self.config['ensemble_vote_threshold'],
            'last_updated': {
                model: self.model_last_updated.get(model, 'never')
                for model in self.models.keys()
            }
        }
    
    def _calculate_feature_statistics(self, feature_matrix: np.ndarray) -> Dict[str, Any]:
        """Calculate statistics about extracted features."""
        try:
            if feature_matrix.size == 0:
                return {}
            
            return {
                'feature_count': feature_matrix.shape[1],
                'sample_count': feature_matrix.shape[0],
                'feature_means': feature_matrix.mean(axis=0).tolist(),
                'feature_stds': feature_matrix.std(axis=0).tolist(),
                'feature_mins': feature_matrix.min(axis=0).tolist(),
                'feature_maxs': feature_matrix.max(axis=0).tolist()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating feature statistics: {e}")
            return {}
    
    async def save_models(self) -> bool:
        """Save trained models to disk."""
        try:
            if not ML_AVAILABLE:
                return False
            
            model_path = Path(self.config['model_save_path'])
            
            for model_name, model in self.models.items():
                if hasattr(model, 'fit'):  # Only save fitted models
                    model_file = model_path / f"{model_name}.pkl"
                    joblib.dump(model, model_file)
            
            # Save scalers
            for scaler_name, scaler in self.scalers.items():
                if hasattr(scaler, 'scale_') or hasattr(scaler, 'components_'):
                    scaler_file = model_path / f"{scaler_name}_scaler.pkl"
                    joblib.dump(scaler, scaler_file)
            
            self.logger.info("Models saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
            return False
    
    async def load_models(self) -> bool:
        """Load trained models from disk."""
        try:
            if not ML_AVAILABLE:
                return False
            
            model_path = Path(self.config['model_save_path'])
            
            if not model_path.exists():
                return False
            
            # Load models
            for model_name in list(self.models.keys()):
                model_file = model_path / f"{model_name}.pkl"
                if model_file.exists():
                    self.models[model_name] = joblib.load(model_file)
            
            # Load scalers
            for scaler_name in list(self.scalers.keys()):
                scaler_file = model_path / f"{scaler_name}_scaler.pkl"
                if scaler_file.exists():
                    self.scalers[scaler_name] = joblib.load(scaler_file)
            
            self.logger.info("Models loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
            return False


# Global instance
ml_anomaly_detector = MLAnomalyDetector()