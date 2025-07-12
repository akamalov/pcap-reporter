"""
Unit tests for NetworkDiagramGenerator service.

Tests the generation of Mermaid.js diagrams from PCAP analysis results,
including network topology, protocol flows, security incidents, and performance analysis.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from services.network_diagram_generator import NetworkDiagramGenerator


class TestNetworkDiagramGenerator:
    """Test suite for NetworkDiagramGenerator service."""
    
    @pytest.fixture
    def generator(self):
        """Create a NetworkDiagramGenerator instance for testing."""
        return NetworkDiagramGenerator()
    
    @pytest.fixture
    def sample_analysis_results(self):
        """Sample analysis results for testing."""
        return {
            'conversations': [
                {
                    'src_ip': '192.168.1.100',
                    'dst_ip': '8.8.8.8',
                    'src_port': 54321,
                    'dst_port': 53,
                    'protocol': 'UDP',
                    'packet_count': 150,
                    'byte_count': 12000
                },
                {
                    'src_ip': '192.168.1.100',
                    'dst_ip': '192.168.1.1',
                    'src_port': 45678,
                    'dst_port': 80,
                    'protocol': 'TCP',
                    'packet_count': 500,
                    'byte_count': 450000
                },
                {
                    'src_ip': '10.0.0.50',
                    'dst_ip': '192.168.1.100',
                    'src_port': 22,
                    'dst_port': 54321,
                    'protocol': 'TCP',
                    'packet_count': 25,
                    'byte_count': 2500
                }
            ],
            'top_talkers': [
                {
                    'ip': '192.168.1.100',
                    'packet_count': 675,
                    'byte_count': 464500
                },
                {
                    'ip': '8.8.8.8',
                    'packet_count': 150,
                    'byte_count': 12000
                }
            ],
            'security_analysis': {
                'security_alerts': [
                    {
                        'type': 'PORT_SCAN',
                        'description': 'Port scan detected from 10.0.0.50',
                        'severity': 'HIGH'
                    },
                    {
                        'type': 'DNS_TUNNELING',
                        'description': 'Suspicious DNS query pattern from 192.168.1.100',
                        'severity': 'MEDIUM'
                    }
                ],
                'risk_score': 0.6
            },
            'performance_analysis': {
                'bandwidth_usage': 464500,
                'connection_rate': 3,
                'latency_indicators': 2,
                'performance_issues': [
                    {
                        'type': 'HIGH_BANDWIDTH',
                        'description': 'High bandwidth usage detected: 464500 bytes',
                        'severity': 'HIGH'
                    },
                    {
                        'type': 'DUPLICATE_ACKS',
                        'description': 'Duplicate ACKs detected: 2',
                        'severity': 'MEDIUM'
                    }
                ]
            }
        }
    
    @pytest.fixture
    def empty_analysis_results(self):
        """Empty analysis results for testing edge cases."""
        return {
            'conversations': [],
            'top_talkers': [],
            'security_analysis': {'security_alerts': []},
            'performance_analysis': {'performance_issues': []}
        }
    
    def test_initialization(self):
        """Test NetworkDiagramGenerator initialization."""
        generator = NetworkDiagramGenerator()
        
        assert generator.config['max_nodes'] == 50
        assert generator.config['diagram_direction'] == 'TD'
        assert 'internal' in generator.config['node_styles']
        assert 'normal' in generator.config['connection_styles']
    
    def test_initialization_with_custom_config(self):
        """Test NetworkDiagramGenerator initialization with custom config."""
        custom_config = {
            'max_nodes': 25,
            'diagram_direction': 'LR',
            'min_packet_threshold': 5
        }
        
        generator = NetworkDiagramGenerator(custom_config)
        
        assert generator.config['max_nodes'] == 25
        assert generator.config['diagram_direction'] == 'LR'
        assert generator.config['min_packet_threshold'] == 5
        # Should preserve other default values
        assert generator.config['max_connections'] == 100
    
    def test_sanitize_node_id(self, generator):
        """Test node ID sanitization for Mermaid.js compatibility."""
        # Test normal IP address
        assert generator._sanitize_node_id('192.168.1.1') == 'node_192_168_1_1'
        
        # Test string starting with letter
        assert generator._sanitize_node_id('server1') == 'server1'
        
        # Test special characters
        assert generator._sanitize_node_id('test-server.local') == 'test_server_local'
        
        # Test empty string
        assert generator._sanitize_node_id('') == 'unknown_node'
        
        # Test None input
        assert generator._sanitize_node_id(None) == 'unknown_node'
    
    def test_classify_ip_address(self, generator):
        """Test IP address classification."""
        # Test private IPs
        assert generator._classify_ip_address('192.168.1.1') == 'internal'
        assert generator._classify_ip_address('10.0.0.1') == 'internal'
        assert generator._classify_ip_address('172.16.0.1') == 'internal'
        
        # Test public IPs
        assert generator._classify_ip_address('8.8.8.8') == 'external'
        assert generator._classify_ip_address('1.1.1.1') == 'external'
        
        # Test multicast
        assert generator._classify_ip_address('224.0.0.1') == 'multicast'
        
        # Test invalid IP
        assert generator._classify_ip_address('invalid.ip') == 'unknown'
    
    def test_determine_node_role(self, generator, sample_analysis_results):
        """Test node role determination based on communication patterns."""
        conversations = sample_analysis_results['conversations']
        
        # Test client (more outgoing connections)
        role = generator._determine_node_role('192.168.1.100', conversations)
        assert role in ['client', 'peer']  # Could be either based on ratio
        
        # Test server (more incoming connections)
        role = generator._determine_node_role('8.8.8.8', conversations)
        assert role in ['server', 'peer']
    
    def test_generate_node_label(self, generator):
        """Test node label generation."""
        # Test internal node with role
        node_info = {
            'role': 'server',
            'packet_count': 150
        }
        label = generator._generate_node_label('192.168.1.100', node_info)
        assert '100' in label  # Should show last octet
        assert 'server' in label
        assert '150' in label
        
        # Test external node
        node_info = {
            'role': 'client',
            'packet_count': 50000
        }
        label = generator._generate_node_label('8.8.8.8', node_info)
        assert '8.8.8.8' in label
        assert 'client' in label
        assert '50k' in label  # Should abbreviate large numbers
    
    def test_generate_connection_label(self, generator):
        """Test connection label generation."""
        # Test basic connection
        connection = {
            'protocol': 'TCP',
            'packet_count': 100,
            'src_port': 54321,
            'dst_port': 80
        }
        label = generator._generate_connection_label(connection)
        assert 'TCP' in label
        assert '100' in label
        
        # Test high packet count
        connection['packet_count'] = 15000
        label = generator._generate_connection_label(connection)
        assert '15k' in label
        
        # Test with port numbers enabled
        generator.config['include_port_numbers'] = True
        connection['dst_port'] = 443
        label = generator._generate_connection_label(connection)
        assert ':443' in label
    
    def test_network_topology_diagram_generation(self, generator, sample_analysis_results):
        """Test network topology diagram generation."""
        diagram = generator.generate_network_topology_diagram(sample_analysis_results)
        
        # Should be a valid Mermaid.js graph
        assert diagram.startswith('graph TD')
        
        # Should contain node definitions
        assert 'node_192_168_1_100[' in diagram
        assert 'node_8_8_8_8[' in diagram
        
        # Should contain connections
        assert '-->' in diagram
        
        # Should contain styling
        assert 'classDef' in diagram
        assert 'class' in diagram
    
    def test_network_topology_diagram_with_empty_data(self, generator, empty_analysis_results):
        """Test network topology diagram generation with empty data."""
        diagram = generator.generate_network_topology_diagram(empty_analysis_results)
        
        # Should generate empty diagram with message
        assert 'graph TD' in diagram
        assert 'No network conversations found' in diagram
    
    def test_protocol_flow_diagram_generation(self, generator, sample_analysis_results):
        """Test protocol flow diagram generation."""
        diagram = generator.generate_protocol_flow_diagram(sample_analysis_results)
        
        # Should be a valid Mermaid.js sequence diagram
        assert diagram.startswith('sequenceDiagram')
        
        # Should contain participant definitions
        assert 'participant' in diagram
        
        # Should contain sequence arrows
        assert '->>' in diagram or '-->' in diagram
        
        # Should contain protocol information
        assert 'UDP' in diagram or 'TCP' in diagram
    
    def test_protocol_flow_diagram_with_empty_data(self, generator, empty_analysis_results):
        """Test protocol flow diagram generation with empty data."""
        diagram = generator.generate_protocol_flow_diagram(empty_analysis_results)
        
        # Should generate empty sequence diagram
        assert 'sequenceDiagram' in diagram
        assert 'No protocol flows found' in diagram
    
    def test_security_incident_diagram_generation(self, generator, sample_analysis_results):
        """Test security incident diagram generation."""
        diagram = generator.generate_security_incident_diagram(sample_analysis_results)
        
        # Should be a valid Mermaid.js graph
        assert diagram.startswith('graph TD')
        
        # Should contain security analysis node
        assert 'Security Analysis' in diagram or 'SecAnalysis' in diagram
        
        # Should contain threat information
        assert 'PORT_SCAN' in diagram or 'DNS_TUNNELING' in diagram
        
        # Should contain styling for security issues
        assert 'suspicious' in diagram
    
    def test_security_incident_diagram_with_no_threats(self, generator, empty_analysis_results):
        """Test security incident diagram generation with no threats."""
        diagram = generator.generate_security_incident_diagram(empty_analysis_results)
        
        # Should generate empty diagram
        assert 'graph TD' in diagram
        assert 'No security incidents detected' in diagram
    
    def test_performance_analysis_diagram_generation(self, generator, sample_analysis_results):
        """Test performance analysis diagram generation."""
        diagram = generator.generate_performance_analysis_diagram(sample_analysis_results)
        
        # Should be a valid Mermaid.js graph
        assert diagram.startswith('graph TD')
        
        # Should contain performance overview
        assert 'Performance Overview' in diagram or 'PerfOverview' in diagram
        
        # Should contain performance metrics
        assert '464500' in diagram  # bandwidth usage
        assert '3' in diagram  # connection rate
        
        # Should contain issue information
        assert 'HIGH_BANDWIDTH' in diagram or 'DUPLICATE_ACKS' in diagram
        
        # Should contain severity styling
        assert 'highSeverity' in diagram or 'mediumSeverity' in diagram
    
    def test_performance_analysis_diagram_with_no_issues(self, generator, empty_analysis_results):
        """Test performance analysis diagram generation with no issues."""
        diagram = generator.generate_performance_analysis_diagram(empty_analysis_results)
        
        # Should generate empty diagram
        assert 'graph TD' in diagram
        assert 'No performance issues detected' in diagram
    
    def test_comprehensive_diagram_set_generation(self, generator, sample_analysis_results):
        """Test comprehensive diagram set generation."""
        diagrams = generator.generate_comprehensive_diagram_set(sample_analysis_results)
        
        # Should contain all diagram types
        assert 'network_topology' in diagrams
        assert 'protocol_flow' in diagrams
        assert 'security_incidents' in diagrams
        assert 'performance_analysis' in diagrams
        
        # Should contain metadata
        assert '_metadata' in diagrams
        metadata = diagrams['_metadata']
        assert 'generated_at' in metadata
        assert 'generator_version' in metadata
        assert 'diagram_count' in metadata
        assert metadata['diagram_count'] == 4
        
        # All diagrams should be valid Mermaid.js
        for key, diagram in diagrams.items():
            if not key.startswith('_'):
                assert isinstance(diagram, str)
                assert len(diagram) > 0
                assert 'graph' in diagram or 'sequenceDiagram' in diagram
    
    def test_diagram_node_limit_enforcement(self, generator):
        """Test that diagram generation respects node limits."""
        # Create analysis results with many nodes
        conversations = []
        for i in range(100):  # More than max_nodes (50)
            conversations.append({
                'src_ip': f'192.168.1.{i}',
                'dst_ip': f'10.0.0.{i}',
                'protocol': 'TCP',
                'packet_count': 100,
                'byte_count': 10000
            })
        
        analysis_results = {'conversations': conversations, 'top_talkers': []}
        diagram = generator.generate_network_topology_diagram(analysis_results)
        
        # Should limit nodes and still generate valid diagram
        assert diagram.startswith('graph TD')
        
        # Count node definitions (simplified check)
        node_count = diagram.count('[')
        assert node_count <= generator.config['max_nodes'] + 5  # Some tolerance for formatting
    
    def test_diagram_connection_limit_enforcement(self, generator):
        """Test that diagram generation respects connection limits."""
        # Set low connection limit
        generator.config['max_connections'] = 5
        
        # Create analysis results with many connections
        conversations = []
        for i in range(20):  # More than max_connections
            conversations.append({
                'src_ip': f'192.168.1.{i}',
                'dst_ip': f'10.0.0.{i}',
                'protocol': 'TCP',
                'packet_count': 100,
                'byte_count': 10000
            })
        
        analysis_results = {'conversations': conversations, 'top_talkers': []}
        diagram = generator.generate_network_topology_diagram(analysis_results)
        
        # Should limit connections and still generate valid diagram
        assert diagram.startswith('graph TD')
        
        # Should process only limited number of conversations
        arrow_count = diagram.count('-->')
        assert arrow_count <= generator.config['max_connections']
    
    def test_min_packet_threshold_filtering(self, generator):
        """Test that low-traffic connections are filtered out."""
        generator.config['min_packet_threshold'] = 50
        
        conversations = [
            {
                'src_ip': '192.168.1.1',
                'dst_ip': '192.168.1.2',
                'protocol': 'TCP',
                'packet_count': 100,  # Above threshold
                'byte_count': 10000
            },
            {
                'src_ip': '192.168.1.3',
                'dst_ip': '192.168.1.4',
                'protocol': 'UDP',
                'packet_count': 25,   # Below threshold
                'byte_count': 2500
            }
        ]
        
        analysis_results = {'conversations': conversations, 'top_talkers': []}
        diagram = generator.generate_network_topology_diagram(analysis_results)
        
        # Should include high-traffic connection
        assert 'node_192_168_1_1' in diagram
        assert 'node_192_168_1_2' in diagram
        
        # Should exclude low-traffic connection
        assert 'node_192_168_1_3' not in diagram
        assert 'node_192_168_1_4' not in diagram
    
    @patch('services.network_diagram_generator.NetworkDiagramGenerator.generate_network_topology_diagram')
    def test_error_handling_in_comprehensive_generation(self, mock_topology, generator, sample_analysis_results):
        """Test error handling in comprehensive diagram generation."""
        # Mock one diagram type to raise an exception
        mock_topology.side_effect = Exception("Test error")
        
        diagrams = generator.generate_comprehensive_diagram_set(sample_analysis_results)
        
        # Should contain error diagram
        assert 'error' in diagrams
        assert 'Test error' in diagrams['error']
        
        # Should contain error metadata
        assert '_metadata' in diagrams
        assert 'error' in diagrams['_metadata']
    
    def test_empty_diagram_generation(self, generator):
        """Test empty diagram generation utility."""
        diagram = generator._generate_empty_diagram("Test message")
        
        assert diagram.startswith('graph TD')
        assert 'Test message' in diagram
        assert 'EmptyNode' in diagram
        assert 'classDef empty' in diagram
    
    def test_empty_sequence_diagram_generation(self, generator):
        """Test empty sequence diagram generation utility."""
        diagram = generator._generate_empty_sequence_diagram("Test message")
        
        assert diagram.startswith('sequenceDiagram')
        assert 'Test message' in diagram
        assert 'participant A as No Data' in diagram


class TestNetworkDiagramGeneratorIntegration:
    """Integration tests for NetworkDiagramGenerator with real-world scenarios."""
    
    @pytest.fixture
    def generator(self):
        """Create a NetworkDiagramGenerator instance for testing."""
        return NetworkDiagramGenerator()
    
    def test_large_network_analysis(self, generator):
        """Test diagram generation with a large network scenario."""
        # Simulate a corporate network with multiple subnets
        conversations = []
        
        # Internal traffic
        for i in range(1, 21):
            for j in range(1, 6):
                conversations.append({
                    'src_ip': f'192.168.{i}.{j}',
                    'dst_ip': f'192.168.{i}.{j+1 if j < 5 else 1}',
                    'protocol': 'TCP',
                    'packet_count': 50 + i * j,
                    'byte_count': (50 + i * j) * 1000
                })
        
        # External traffic
        external_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222']
        for server in external_servers:
            conversations.append({
                'src_ip': '192.168.1.100',
                'dst_ip': server,
                'protocol': 'UDP',
                'packet_count': 200,
                'byte_count': 20000
            })
        
        analysis_results = {
            'conversations': conversations,
            'top_talkers': [],
            'security_analysis': {'security_alerts': []},
            'performance_analysis': {'performance_issues': []}
        }
        
        diagrams = generator.generate_comprehensive_diagram_set(analysis_results)
        
        # Should successfully generate all diagrams
        assert len(diagrams) >= 4
        assert all(isinstance(d, str) for k, d in diagrams.items() if not k.startswith('_'))
        
        # Network topology should be generated
        topology = diagrams['network_topology']
        assert topology.startswith('graph TD')
        assert 'node_192_168_' in topology
        assert 'node_8_8_8_8' in topology
    
    def test_security_focused_analysis(self, generator):
        """Test diagram generation focused on security incidents."""
        analysis_results = {
            'conversations': [
                {
                    'src_ip': '203.0.113.50',  # External attacker
                    'dst_ip': '192.168.1.100',
                    'protocol': 'TCP',
                    'packet_count': 1000,
                    'byte_count': 50000
                }
            ],
            'top_talkers': [],
            'security_analysis': {
                'security_alerts': [
                    {
                        'type': 'PORT_SCAN',
                        'description': 'Port scan detected from 203.0.113.50',
                        'severity': 'CRITICAL'
                    },
                    {
                        'type': 'BRUTE_FORCE',
                        'description': 'SSH brute force attack from 203.0.113.50',
                        'severity': 'HIGH'
                    },
                    {
                        'type': 'MALWARE_COMMUNICATION',
                        'description': 'Suspected malware communication to 203.0.113.50',
                        'severity': 'CRITICAL'
                    }
                ]
            },
            'performance_analysis': {'performance_issues': []}
        }
        
        diagrams = generator.generate_comprehensive_diagram_set(analysis_results)
        
        # Security incident diagram should highlight threats
        security_diagram = diagrams['security_incidents']
        assert 'Security Analysis' in security_diagram
        assert 'PORT_SCAN' in security_diagram or 'BRUTE_FORCE' in security_diagram
        assert 'suspicious' in security_diagram
    
    def test_performance_bottleneck_analysis(self, generator):
        """Test diagram generation focused on performance issues."""
        analysis_results = {
            'conversations': [
                {
                    'src_ip': '192.168.1.100',
                    'dst_ip': '192.168.1.1',
                    'protocol': 'TCP',
                    'packet_count': 50000,  # High traffic
                    'byte_count': 50000000
                }
            ],
            'top_talkers': [],
            'security_analysis': {'security_alerts': []},
            'performance_analysis': {
                'bandwidth_usage': 50000000,
                'connection_rate': 1000,
                'latency_indicators': 500,
                'performance_issues': [
                    {
                        'type': 'HIGH_BANDWIDTH',
                        'description': 'Extremely high bandwidth usage detected',
                        'severity': 'CRITICAL'
                    },
                    {
                        'type': 'HIGH_CONNECTION_RATE',
                        'description': 'Abnormally high connection rate',
                        'severity': 'HIGH'
                    },
                    {
                        'type': 'HIGH_LATENCY',
                        'description': 'Network latency exceeds threshold',
                        'severity': 'MEDIUM'
                    }
                ]
            }
        }
        
        diagrams = generator.generate_comprehensive_diagram_set(analysis_results)
        
        # Performance diagram should highlight issues
        perf_diagram = diagrams['performance_analysis']
        assert 'Performance Overview' in perf_diagram
        assert '50000000' in perf_diagram  # Bandwidth usage
        assert 'HIGH_BANDWIDTH' in perf_diagram
        assert 'highSeverity' in perf_diagram or 'CRITICAL' in perf_diagram