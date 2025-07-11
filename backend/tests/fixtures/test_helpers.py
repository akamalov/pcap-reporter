"""
Test helpers for PCAP analysis testing.
"""
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import pytest

# Handle relative imports for direct execution
try:
    from .sample_pcap_generator import PcapFixtureGenerator
except ImportError:
    from sample_pcap_generator import PcapFixtureGenerator


class PcapTestHelper:
    """Helper class for PCAP analysis testing."""
    
    def __init__(self):
        """Initialize the test helper."""
        self.fixtures_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.fixture_files = {
            'normal_traffic': 'normal_traffic.pcap',
            'dns_issues': 'dns_issues.pcap',
            'tcp_retransmissions': 'tcp_retransmissions.pcap',
            'security_issues': 'security_issues.pcap',
            'performance_issues': 'performance_issues.pcap',
            'mixed_scenario': 'mixed_scenario.pcap',
            'sample': 'sample.pcap',
            'large_sample': 'large_sample.pcap'
        }
        
    def get_fixture_path(self, fixture_name: str) -> Path:
        """
        Get the full path to a test fixture file.
        
        Args:
            fixture_name: Name of the fixture (e.g., 'normal_traffic')
            
        Returns:
            Path to the fixture file
            
        Raises:
            FileNotFoundError: If the fixture file doesn't exist
            KeyError: If the fixture name is not recognized
        """
        if fixture_name not in self.fixture_files:
            raise KeyError(f"Unknown fixture: {fixture_name}. Available: {list(self.fixture_files.keys())}")
        
        fixture_path = self.fixtures_dir / self.fixture_files[fixture_name]
        
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture file not found: {fixture_path}")
            
        return fixture_path
    
    def get_all_fixture_paths(self) -> Dict[str, Path]:
        """
        Get paths to all available test fixtures.
        
        Returns:
            Dictionary mapping fixture names to their paths
        """
        fixtures = {}
        for name in self.fixture_files:
            try:
                fixtures[name] = self.get_fixture_path(name)
            except FileNotFoundError:
                # Skip missing fixtures
                pass
        return fixtures
    
    def get_fixture_info(self, fixture_name: str) -> Dict[str, Any]:
        """
        Get information about a test fixture.
        
        Args:
            fixture_name: Name of the fixture
            
        Returns:
            Dictionary with fixture metadata
        """
        fixture_path = self.get_fixture_path(fixture_name)
        
        info = {
            'name': fixture_name,
            'path': str(fixture_path),
            'exists': fixture_path.exists(),
            'size': fixture_path.stat().st_size if fixture_path.exists() else 0,
            'description': self._get_fixture_description(fixture_name)
        }
        
        return info
    
    def _get_fixture_description(self, fixture_name: str) -> str:
        """Get a description of what the fixture contains."""
        descriptions = {
            'normal_traffic': 'Normal, healthy network traffic with TCP handshakes, HTTP requests, and DNS queries',
            'dns_issues': 'DNS-related issues including timeouts, NXDOMAIN responses, and slow queries',
            'tcp_retransmissions': 'TCP retransmissions, connection resets, and zero-window situations',
            'security_issues': 'Security-related patterns including port scans, web attacks, and suspicious DNS',
            'performance_issues': 'Performance problems including high bandwidth usage and connection rates',
            'mixed_scenario': 'Mixed scenario with normal traffic and various network issues',
            'sample': 'Legacy basic sample with various packet types',
            'large_sample': 'Legacy large sample with 1000+ packets for performance testing'
        }
        return descriptions.get(fixture_name, 'Test fixture for PCAP analysis')
    
    def verify_all_fixtures(self) -> Dict[str, bool]:
        """
        Verify that all expected fixture files exist.
        
        Returns:
            Dictionary mapping fixture names to existence status
        """
        status = {}
        for name in self.fixture_files:
            try:
                path = self.get_fixture_path(name)
                status[name] = path.exists() and path.stat().st_size > 0
            except (FileNotFoundError, KeyError):
                status[name] = False
        return status
    
    def regenerate_fixtures(self) -> Dict[str, str]:
        """
        Regenerate all test fixtures.
        
        Returns:
            Dictionary mapping fixture names to file paths
        """
        generator = PcapFixtureGenerator(str(self.fixtures_dir))
        return generator.generate_all_fixtures()
    
    def get_expected_analysis_results(self, fixture_name: str) -> Dict[str, Any]:
        """
        Get expected analysis results for a fixture for testing purposes.
        
        Args:
            fixture_name: Name of the fixture
            
        Returns:
            Dictionary with expected analysis results
        """
        expected_results = {
            'normal_traffic': {
                'total_packets': 8,
                'protocols': ['TCP', 'UDP', 'DNS', 'HTTP'],
                'issues_found': [],
                'severity': 'LOW',
                'top_talkers': ['192.168.1.10', '192.168.1.1', '93.184.216.34', '8.8.8.8']
            },
            'dns_issues': {
                'total_packets': 15,  # Approximate
                'protocols': ['UDP', 'DNS'],
                'issues_found': ['DNS_TIMEOUT', 'DNS_NXDOMAIN', 'DNS_HIGH_LATENCY'],
                'severity': 'MEDIUM',
                'dns_queries': 12,
                'dns_responses': 2
            },
            'tcp_retransmissions': {
                'total_packets': 8,
                'protocols': ['TCP'],
                'issues_found': ['TCP_RETRANSMISSION', 'TCP_RESET', 'TCP_ZERO_WINDOW'],
                'severity': 'HIGH',
                'retransmissions': 2,
                'tcp_issues': 3
            },
            'security_issues': {
                'total_packets': 42,  # Approximate
                'protocols': ['TCP', 'UDP', 'DNS', 'ARP', 'HTTP'],
                'issues_found': ['PORT_SCAN', 'WEB_ATTACK', 'SUSPICIOUS_DNS', 'ARP_SCAN'],
                'severity': 'CRITICAL',
                'security_events': 4
            },
            'performance_issues': {
                'total_packets': 210,  # Approximate
                'protocols': ['TCP'],
                'issues_found': ['HIGH_BANDWIDTH', 'HIGH_CONNECTION_RATE', 'DUPLICATE_ACKS'],
                'severity': 'HIGH',
                'performance_issues': 3
            },
            'mixed_scenario': {
                'total_packets': 60,  # Approximate
                'protocols': ['TCP', 'UDP', 'DNS', 'ICMP'],
                'issues_found': ['DNS_ISSUES', 'TCP_RETRANSMISSION', 'SECURITY_EVENTS'],
                'severity': 'MEDIUM',
                'mixed_issues': True
            }
        }
        
        return expected_results.get(fixture_name, {
            'total_packets': 0,
            'protocols': [],
            'issues_found': [],
            'severity': 'UNKNOWN'
        })


# Global test helper instance
pcap_helper = PcapTestHelper()


# Pytest fixtures for easy access in tests
@pytest.fixture
def normal_traffic_pcap():
    """Fixture providing path to normal traffic PCAP."""
    return pcap_helper.get_fixture_path('normal_traffic')


@pytest.fixture
def dns_issues_pcap():
    """Fixture providing path to DNS issues PCAP."""
    return pcap_helper.get_fixture_path('dns_issues')


@pytest.fixture
def tcp_retransmissions_pcap():
    """Fixture providing path to TCP retransmissions PCAP."""
    return pcap_helper.get_fixture_path('tcp_retransmissions')


@pytest.fixture
def security_issues_pcap():
    """Fixture providing path to security issues PCAP."""
    return pcap_helper.get_fixture_path('security_issues')


@pytest.fixture
def performance_issues_pcap():
    """Fixture providing path to performance issues PCAP."""
    return pcap_helper.get_fixture_path('performance_issues')


@pytest.fixture
def mixed_scenario_pcap():
    """Fixture providing path to mixed scenario PCAP."""
    return pcap_helper.get_fixture_path('mixed_scenario')


@pytest.fixture
def large_sample_pcap():
    """Fixture providing path to large sample PCAP."""
    return pcap_helper.get_fixture_path('large_sample')


@pytest.fixture
def all_test_pcaps():
    """Fixture providing all test PCAP file paths."""
    return pcap_helper.get_all_fixture_paths()


@pytest.fixture
def pcap_test_helper():
    """Fixture providing the test helper instance."""
    return pcap_helper


# Utility functions for common test operations
def assert_pcap_file_exists(fixture_name: str):
    """Assert that a PCAP fixture file exists and is not empty."""
    path = pcap_helper.get_fixture_path(fixture_name)
    assert path.exists(), f"PCAP fixture {fixture_name} does not exist at {path}"
    assert path.stat().st_size > 0, f"PCAP fixture {fixture_name} is empty"


def get_pcap_packet_count(pcap_path: Path) -> int:
    """
    Get the number of packets in a PCAP file using scapy.
    
    Args:
        pcap_path: Path to the PCAP file
        
    Returns:
        Number of packets in the file
    """
    try:
        from scapy.all import rdpcap
        packets = rdpcap(str(pcap_path))
        return len(packets)
    except ImportError:
        # Fallback if scapy is not available
        return 0


def validate_fixture_integrity():
    """Validate that all fixtures exist and have expected characteristics."""
    status = pcap_helper.verify_all_fixtures()
    missing_fixtures = [name for name, exists in status.items() if not exists]
    
    if missing_fixtures:
        raise AssertionError(f"Missing fixture files: {missing_fixtures}")
    
    return True


if __name__ == "__main__":
    # Run verification when called directly
    print("Verifying PCAP test fixtures...")
    
    try:
        validate_fixture_integrity()
        print("✓ All fixtures verified successfully")
        
        # Print fixture information
        print("\nFixture Information:")
        for name in pcap_helper.fixture_files:
            info = pcap_helper.get_fixture_info(name)
            print(f"  {name}: {info['size']} bytes - {info['description']}")
            
    except Exception as e:
        print(f"✗ Fixture verification failed: {e}")
        exit(1) 