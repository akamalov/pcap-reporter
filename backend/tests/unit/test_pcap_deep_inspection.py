"""
Test Deep Packet Inspection functionality.

This module contains comprehensive tests for the PcapDeepInspector class,
which performs detailed analysis of network packets flagged by the triage analyzer.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os
import json

# Import PCAP test fixtures
from tests.fixtures.test_helpers import (
    normal_traffic_pcap, dns_issues_pcap, tcp_retransmissions_pcap,
    security_issues_pcap, performance_issues_pcap, mixed_scenario_pcap,
    large_sample_pcap
)


class TestPcapDeepInspection:
    """Test cases for deep packet inspection functionality."""
    
    def test_deep_inspector_initialization(self):
        """Test that the deep inspector can be initialized with default config."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        
        assert inspector is not None
        assert hasattr(inspector, 'config')
        assert hasattr(inspector, 'logger')
        
        # Check default configuration
        assert inspector.config['max_payload_size'] > 0
        assert inspector.config['enable_http_analysis'] is True
        assert inspector.config['enable_dns_analysis'] is True
        assert inspector.config['enable_tcp_reconstruction'] is True
    
    def test_deep_inspector_custom_config(self):
        """Test deep inspector initialization with custom configuration."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        custom_config = {
            'max_payload_size': 2048,
            'enable_http_analysis': False,
            'timeout_seconds': 120
        }
        
        inspector = PcapDeepInspector(config=custom_config)
        
        assert inspector.config['max_payload_size'] == 2048
        assert inspector.config['enable_http_analysis'] is False
        assert inspector.config['timeout_seconds'] == 120
    
    def test_http_analysis_basic(self, normal_traffic_pcap):
        """Test basic HTTP request/response analysis."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_http_traffic(normal_traffic_pcap)
        
        assert isinstance(result, dict)
        assert 'http_requests' in result
        assert 'http_responses' in result
        assert 'http_sessions' in result
        assert 'http_anomalies' in result
        
        # Should find HTTP traffic in normal traffic PCAP
        assert isinstance(result['http_requests'], list)
        assert isinstance(result['http_responses'], list)
        assert isinstance(result['http_sessions'], list)
    
    def test_http_request_parsing(self, security_issues_pcap):
        """Test detailed HTTP request parsing and header extraction."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_http_traffic(security_issues_pcap)
        
        # Check for HTTP request structure
        if result['http_requests']:
            request = result['http_requests'][0]
            expected_fields = ['method', 'uri', 'version', 'headers', 'payload', 'timestamp', 'src_ip', 'dst_ip']
            
            for field in expected_fields:
                assert field in request
            
            assert request['method'] in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']
            assert isinstance(request['headers'], dict)
            assert isinstance(request['timestamp'], (int, float))
    
    def test_http_security_analysis(self, security_issues_pcap):
        """Test HTTP security pattern detection."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_http_security_patterns(security_issues_pcap)
        
        assert isinstance(result, dict)
        assert 'security_issues' in result
        assert 'attack_patterns' in result
        assert 'risk_score' in result
        
        # Check for security issue detection
        security_issues = result['security_issues']
        assert isinstance(security_issues, list)
        
        # Should detect common attack patterns
        attack_types = [issue.get('type') for issue in security_issues]
        expected_patterns = ['SQL_INJECTION', 'XSS', 'PATH_TRAVERSAL', 'COMMAND_INJECTION']
        
        # At least one pattern should be detected in security issues PCAP
        if security_issues:
            assert any(pattern in attack_types for pattern in expected_patterns)
    
    def test_dns_deep_analysis(self, dns_issues_pcap):
        """Test deep DNS analysis and pattern detection."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_dns_patterns(dns_issues_pcap)
        
        assert isinstance(result, dict)
        assert 'dns_queries' in result
        assert 'dns_responses' in result
        assert 'dns_patterns' in result
        assert 'tunneling_indicators' in result
        
        # Check DNS query analysis
        dns_queries = result['dns_queries']
        assert isinstance(dns_queries, list)
        
        if dns_queries:
            query = dns_queries[0]
            expected_fields = ['query_name', 'query_type', 'query_class', 'timestamp', 'src_ip', 'query_id']
            
            for field in expected_fields:
                assert field in query
    
    def test_dns_tunneling_detection(self, mixed_scenario_pcap):
        """Test DNS tunneling and exfiltration detection."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_dns_patterns(mixed_scenario_pcap)
        
        tunneling_indicators = result['tunneling_indicators']
        assert isinstance(tunneling_indicators, list)
        
        # Check for tunneling detection fields
        if tunneling_indicators:
            indicator = tunneling_indicators[0]
            expected_fields = ['type', 'description', 'severity', 'evidence']
            
            for field in expected_fields:
                assert field in indicator
            
            assert indicator['type'] in ['LONG_SUBDOMAIN', 'HIGH_ENTROPY', 'UNUSUAL_RECORDS', 'DATA_PATTERNS']
    
    def test_tcp_stream_reconstruction(self, tcp_retransmissions_pcap):
        """Test TCP stream reconstruction and session analysis."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.reconstruct_tcp_streams(tcp_retransmissions_pcap)
        
        assert isinstance(result, dict)
        assert 'tcp_streams' in result
        assert 'stream_statistics' in result
        assert 'anomalies' in result
        
        # Check stream reconstruction
        tcp_streams = result['tcp_streams']
        assert isinstance(tcp_streams, list)
        
        if tcp_streams:
            stream = tcp_streams[0]
            expected_fields = ['stream_id', 'src_ip', 'src_port', 'dst_ip', 'dst_port', 
                             'data_client_to_server', 'data_server_to_client', 'start_time', 'end_time']
            
            for field in expected_fields:
                assert field in stream
    
    def test_tcp_anomaly_detection(self, tcp_retransmissions_pcap):
        """Test TCP protocol anomaly detection."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_tcp_anomalies(tcp_retransmissions_pcap)
        
        assert isinstance(result, dict)
        assert 'protocol_anomalies' in result
        assert 'timing_anomalies' in result
        assert 'sequence_anomalies' in result
        
        # Should detect retransmission anomalies in the test PCAP
        anomalies = result['protocol_anomalies'] + result['timing_anomalies'] + result['sequence_anomalies']
        assert len(anomalies) > 0
        
        if anomalies:
            anomaly = anomalies[0]
            expected_fields = ['type', 'description', 'severity', 'packet_info']
            
            for field in expected_fields:
                assert field in anomaly
    
    def test_payload_analysis(self, security_issues_pcap):
        """Test payload content analysis and pattern matching."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.analyze_payload_patterns(security_issues_pcap)
        
        assert isinstance(result, dict)
        assert 'payload_analysis' in result
        assert 'suspicious_patterns' in result
        assert 'file_signatures' in result
        
        payload_analysis = result['payload_analysis']
        assert 'total_payloads' in payload_analysis
        assert 'payload_sizes' in payload_analysis
        assert 'content_types' in payload_analysis
        
        # Check suspicious pattern detection
        suspicious_patterns = result['suspicious_patterns']
        assert isinstance(suspicious_patterns, list)
    
    def test_metadata_extraction(self, performance_issues_pcap):
        """Test metadata extraction and timing analysis."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.extract_metadata(performance_issues_pcap)
        
        assert isinstance(result, dict)
        assert 'timing_analysis' in result
        assert 'flow_characteristics' in result
        assert 'protocol_distribution' in result
        assert 'bandwidth_analysis' in result
        
        # Check timing analysis
        timing_analysis = result['timing_analysis']
        expected_timing_fields = ['packet_intervals', 'burst_patterns', 'idle_periods']
        
        for field in expected_timing_fields:
            assert field in timing_analysis
        
        # Check flow characteristics
        flow_characteristics = result['flow_characteristics']
        expected_flow_fields = ['connection_duration', 'data_transfer_patterns', 'session_patterns']
        
        for field in expected_flow_fields:
            assert field in flow_characteristics
    
    def test_comprehensive_deep_inspection(self, mixed_scenario_pcap):
        """Test comprehensive deep inspection combining all analysis types."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.perform_deep_inspection(mixed_scenario_pcap)
        
        assert isinstance(result, dict)
        
        # Should include all analysis types
        expected_sections = [
            'http_analysis', 'dns_analysis', 'tcp_analysis', 
            'payload_analysis', 'metadata_analysis', 'summary'
        ]
        
        for section in expected_sections:
            assert section in result
        
        # Check summary section
        summary = result['summary']
        expected_summary_fields = [
            'total_packets_analyzed', 'analysis_duration', 'issues_found', 
            'risk_assessment', 'recommendations'
        ]
        
        for field in expected_summary_fields:
            assert field in summary
    
    def test_deep_inspector_with_invalid_file(self):
        """Test deep inspector behavior with invalid PCAP file."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        
        with pytest.raises(FileNotFoundError):
            inspector.perform_deep_inspection(Path("/nonexistent/file.pcap"))
    
    def test_deep_inspector_with_empty_pcap(self):
        """Test deep inspector behavior with empty PCAP file."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        # Create temporary empty file
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            inspector = PcapDeepInspector()
            result = inspector.perform_deep_inspection(tmp_path)
            
            # Should handle empty file gracefully
            assert isinstance(result, dict)
            assert result['summary']['total_packets_analyzed'] == 0
            
        finally:
            os.unlink(tmp_path)
    
    def test_deep_inspection_performance(self, large_sample_pcap):
        """Test deep inspection performance with large PCAP file."""
        from services.pcap_deep_inspector import PcapDeepInspector
        import time
        
        inspector = PcapDeepInspector()
        
        start_time = time.time()
        result = inspector.perform_deep_inspection(large_sample_pcap)
        analysis_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert analysis_time < 30.0  # 30 seconds for large file
        
        # Should have analyzed packets
        assert result['summary']['total_packets_analyzed'] > 0
        assert result['summary']['analysis_duration'] > 0
    
    def test_deep_inspection_output_format(self, normal_traffic_pcap):
        """Test that deep inspection output follows expected JSON format."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        inspector = PcapDeepInspector()
        result = inspector.perform_deep_inspection(normal_traffic_pcap)
        
        # Should be JSON serializable
        json_str = json.dumps(result, default=str)
        assert isinstance(json_str, str)
        
        # Should be able to parse back
        parsed_result = json.loads(json_str)
        assert isinstance(parsed_result, dict)
    
    def test_deep_inspector_configuration_options(self):
        """Test various configuration options for the deep inspector."""
        from services.pcap_deep_inspector import PcapDeepInspector
        
        # Test with different configurations
        configs = [
            {'enable_http_analysis': False},
            {'enable_dns_analysis': False},
            {'enable_tcp_reconstruction': False},
            {'max_payload_size': 512},
            {'timeout_seconds': 30}
        ]
        
        for config in configs:
            inspector = PcapDeepInspector(config=config)
            
            # Should merge with defaults
            for key, value in config.items():
                assert inspector.config[key] == value
    
    def test_integration_with_triage_results(self, mixed_scenario_pcap):
        """Test integration between triage analysis and deep inspection."""
        from services.pcap_triage_analyzer import PcapTriageAnalyzer
        from services.pcap_deep_inspector import PcapDeepInspector
        
        # First run triage analysis
        triage_analyzer = PcapTriageAnalyzer()
        triage_result = triage_analyzer.perform_triage_analysis(mixed_scenario_pcap)
        
        # Then run deep inspection with triage context
        deep_inspector = PcapDeepInspector()
        deep_result = deep_inspector.perform_deep_inspection(
            mixed_scenario_pcap, 
            triage_context=triage_result
        )
        
        # Deep inspection should reference triage findings
        assert 'triage_context' in deep_result
        assert deep_result['triage_context'] is not None
        
        # Should have focused analysis based on triage findings
        summary = deep_result['summary']
        assert 'triage_correlation' in summary
        assert 'focused_analysis' in summary 