"""
Generate sample PCAP files for testing the PCAP analysis engine.
"""
import os
import time
from scapy.all import wrpcap, IP, TCP, UDP, DNS, DNSQR, DNSRR, Ether, ICMP, ARP
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
from typing import List, Dict, Any
import random


class PcapFixtureGenerator:
    """Generate various types of PCAP files for comprehensive testing."""
    
    def __init__(self, fixtures_dir: str = None):
        """Initialize the generator with the fixtures directory."""
        if fixtures_dir is None:
            self.fixtures_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.fixtures_dir = fixtures_dir
    
    def create_normal_traffic(self, filename: str = "normal_traffic.pcap") -> str:
        """
        Create a PCAP file with normal, healthy network traffic.
        
        Returns:
            Path to the created PCAP file
        """
        packets = []
        
        # Normal TCP handshake and data transfer
        tcp_syn = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="S", seq=1000)
        tcp_synack = Ether() / IP(src="192.168.1.1", dst="192.168.1.10") / TCP(sport=80, dport=12345, flags="SA", seq=2000, ack=1001)
        tcp_ack = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="A", seq=1001, ack=2001)
        
        packets.extend([tcp_syn, tcp_synack, tcp_ack])
        
        # Normal HTTP request/response
        http_request = Ether() / IP(src="192.168.1.10", dst="93.184.216.34") / TCP(sport=54321, dport=80, flags="PA", seq=3000, ack=4000) / "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
        http_response = Ether() / IP(src="93.184.216.34", dst="192.168.1.10") / TCP(sport=80, dport=54321, flags="PA", seq=4000, ack=3100) / "HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello, World!"
        
        packets.extend([http_request, http_response])
        
        # Normal DNS queries
        dns_query = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53000, dport=53) / DNS(rd=1, qd=DNSQR(qname="example.com"))
        dns_response = Ether() / IP(src="8.8.8.8", dst="192.168.1.10") / UDP(sport=53, dport=53000) / DNS(id=dns_query[DNS].id, qr=1, aa=0, rcode=0, qd=DNSQR(qname="example.com"), an=DNSRR(rrname="example.com", rdata="93.184.216.34"))
        
        packets.extend([dns_query, dns_response])
        
        return self._write_pcap(packets, filename)
    
    def create_dns_issues(self, filename: str = "dns_issues.pcap") -> str:
        """
        Create a PCAP file with various DNS-related issues.
        
        Returns:
            Path to the created PCAP file
        """
        packets = []
        
        # DNS query with no response (timeout)
        dns_timeout = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53001, dport=53) / DNS(rd=1, qd=DNSQR(qname="timeout.example.com"))
        packets.append(dns_timeout)
        
        # DNS query with NXDOMAIN response
        dns_nxdomain_query = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53002, dport=53) / DNS(rd=1, qd=DNSQR(qname="nonexistent.example.com"))
        dns_nxdomain_response = Ether() / IP(src="8.8.8.8", dst="192.168.1.10") / UDP(sport=53, dport=53002) / DNS(id=dns_nxdomain_query[DNS].id, qr=1, aa=0, rcode=3, qd=DNSQR(qname="nonexistent.example.com"))
        
        packets.extend([dns_nxdomain_query, dns_nxdomain_response])
        
        # DNS query with slow response (high latency)
        dns_slow_query = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53003, dport=53) / DNS(rd=1, qd=DNSQR(qname="slow.example.com"))
        # Simulate 2-second delay in response
        dns_slow_response = Ether() / IP(src="8.8.8.8", dst="192.168.1.10") / UDP(sport=53, dport=53003) / DNS(id=dns_slow_query[DNS].id, qr=1, aa=0, rcode=0, qd=DNSQR(qname="slow.example.com"), an=DNSRR(rrname="slow.example.com", rdata="1.2.3.4"))
        
        packets.extend([dns_slow_query, dns_slow_response])
        
        # Multiple DNS queries to different servers (DNS amplification pattern)
        for i in range(10):
            dns_amp = Ether() / IP(src="192.168.1.10", dst=f"8.8.{i}.{i}") / UDP(sport=53010+i, dport=53) / DNS(rd=1, qd=DNSQR(qname=f"amp{i}.example.com"))
            packets.append(dns_amp)
        
        return self._write_pcap(packets, filename)
    
    def create_tcp_retransmissions(self, filename: str = "tcp_retransmissions.pcap") -> str:
        """
        Create a PCAP file with TCP retransmissions and connection issues.
        
        Returns:
            Path to the created PCAP file
        """
        packets = []
        
        # Initial TCP handshake
        tcp_syn = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="S", seq=1000)
        tcp_synack = Ether() / IP(src="192.168.1.1", dst="192.168.1.10") / TCP(sport=80, dport=12345, flags="SA", seq=2000, ack=1001)
        tcp_ack = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="A", seq=1001, ack=2001)
        
        packets.extend([tcp_syn, tcp_synack, tcp_ack])
        
        # Data packet that will be retransmitted
        data_packet = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="PA", seq=1001, ack=2001) / "GET /data HTTP/1.1\r\n\r\n"
        packets.append(data_packet)
        
        # Retransmission of the same data packet (same sequence number)
        retrans_packet = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="PA", seq=1001, ack=2001) / "GET /data HTTP/1.1\r\n\r\n"
        packets.append(retrans_packet)
        
        # Another retransmission
        retrans_packet2 = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="PA", seq=1001, ack=2001) / "GET /data HTTP/1.1\r\n\r\n"
        packets.append(retrans_packet2)
        
        # TCP Reset (connection terminated abruptly)
        tcp_rst = Ether() / IP(src="192.168.1.1", dst="192.168.1.10") / TCP(sport=80, dport=12345, flags="R", seq=2001)
        packets.append(tcp_rst)
        
        # TCP Zero Window (flow control issue)
        tcp_zero_win = Ether() / IP(src="192.168.1.1", dst="192.168.1.10") / TCP(sport=80, dport=12346, flags="A", seq=3000, ack=4000, window=0)
        packets.append(tcp_zero_win)
        
        return self._write_pcap(packets, filename)
    
    def create_security_issues(self, filename: str = "security_issues.pcap") -> str:
        """
        Create a PCAP file with potential security issues and suspicious patterns.
        
        Returns:
            Path to the created PCAP file
        """
        packets = []
        
        # Port scan pattern (multiple SYN packets to different ports)
        for port in [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 993, 995, 1433, 1521, 3389, 5432, 5900]:
            syn_packet = Ether() / IP(src="10.0.0.100", dst="192.168.1.1") / TCP(sport=random.randint(20000, 60000), dport=port, flags="S", seq=random.randint(1000, 9999))
            packets.append(syn_packet)
        
        # Suspicious HTTP requests (potential web attacks)
        malicious_requests = [
            "GET /../../../etc/passwd HTTP/1.1\r\nHost: target.com\r\n\r\n",
            "GET /admin/config.php HTTP/1.1\r\nHost: target.com\r\n\r\n", 
            "POST /login.php HTTP/1.1\r\nHost: target.com\r\nContent-Length: 50\r\n\r\nadmin'; DROP TABLE users; --",
            "GET /cgi-bin/test.cgi?param=|id; HTTP/1.1\r\nHost: target.com\r\n\r\n"
        ]
        
        for i, request in enumerate(malicious_requests):
            http_attack = Ether() / IP(src="10.0.0.100", dst="192.168.1.1") / TCP(sport=40000+i, dport=80, flags="PA", seq=5000+i*100, ack=6000) / request
            packets.append(http_attack)
        
        # Suspicious DNS queries (potential DGA or C&C)
        suspicious_domains = [
            "a1b2c3d4e5f6.com",
            "x7y8z9w0v1u2.net", 
            "m9n8b7v6c5x4.org",
            "p3q4r5s6t7u8.info"
        ]
        
        for i, domain in enumerate(suspicious_domains):
            dns_query = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53100+i, dport=53) / DNS(rd=1, qd=DNSQR(qname=domain))
            packets.append(dns_query)
        
        # Large number of ARP requests (potential ARP scanning)
        for i in range(20):
            arp_request = Ether() / ARP(op=1, psrc="192.168.1.10", pdst=f"192.168.1.{i+1}")
            packets.append(arp_request)
        
        return self._write_pcap(packets, filename)
    
    def create_performance_issues(self, filename: str = "performance_issues.pcap") -> str:
        """
        Create a PCAP file with performance-related network issues.
        
        Returns:
            Path to the created PCAP file
        """
        packets = []
        
        # High bandwidth usage (large data transfers)
        base_seq = 10000
        for i in range(50):
            # Large data packet
            large_packet = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=8080, dport=80, flags="A", seq=base_seq + i*1460, ack=20000) / ("X" * 1460)
            packets.append(large_packet)
        
        # High connection rate (many short-lived connections)
        for i in range(30):
            # SYN
            syn = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=30000+i, dport=80, flags="S", seq=30000+i)
            # SYN-ACK
            synack = Ether() / IP(src="192.168.1.1", dst="192.168.1.10") / TCP(sport=80, dport=30000+i, flags="SA", seq=40000+i, ack=30001+i)
            # ACK
            ack = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=30000+i, dport=80, flags="A", seq=30001+i, ack=40001+i)
            # FIN (quick disconnect)
            fin = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=30000+i, dport=80, flags="F", seq=30001+i, ack=40001+i)
            
            packets.extend([syn, synack, ack, fin])
        
        # High latency indicators (duplicate ACKs)
        for i in range(10):
            dup_ack = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="A", seq=50000, ack=60000+i)
            packets.append(dup_ack)
        
        return self._write_pcap(packets, filename)
    
    def create_mixed_scenario(self, filename: str = "mixed_scenario.pcap") -> str:
        """
        Create a PCAP file with a mix of normal and problematic traffic.
        
        Returns:
            Path to the created PCAP file
        """
        packets = []
        
        # Start with normal traffic
        normal_packets = self._get_normal_packets(count=20)
        packets.extend(normal_packets)
        
        # Add some DNS issues
        dns_issue_packets = self._get_dns_issue_packets(count=5)
        packets.extend(dns_issue_packets)
        
        # Add some TCP retransmissions
        tcp_issue_packets = self._get_tcp_issue_packets(count=8)
        packets.extend(tcp_issue_packets)
        
        # Add some security-related packets
        security_packets = self._get_security_packets(count=12)
        packets.extend(security_packets)
        
        # End with more normal traffic
        normal_packets_end = self._get_normal_packets(count=15)
        packets.extend(normal_packets_end)
        
        return self._write_pcap(packets, filename)
    
    def _get_normal_packets(self, count: int) -> List:
        """Generate normal traffic packets."""
        packets = []
        for i in range(count):
            if i % 3 == 0:
                packet = Ether() / IP(src=f"192.168.1.{(i % 10) + 10}", dst="192.168.1.1") / TCP(sport=12345+i, dport=80, flags="A", seq=1000+i, ack=2000+i)
            elif i % 3 == 1:
                packet = Ether() / IP(src=f"192.168.1.{(i % 10) + 10}", dst="8.8.8.8") / UDP(sport=53000+i, dport=53) / DNS(rd=1, qd=DNSQR(qname=f"normal{i}.com"))
            else:
                packet = Ether() / IP(src=f"192.168.1.{(i % 10) + 10}", dst="8.8.8.8") / ICMP()
            packets.append(packet)
        return packets
    
    def _get_dns_issue_packets(self, count: int) -> List:
        """Generate DNS issue packets."""
        packets = []
        for i in range(count):
            packet = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53100+i, dport=53) / DNS(rd=1, qd=DNSQR(qname=f"issue{i}.com"))
            packets.append(packet)
        return packets
    
    def _get_tcp_issue_packets(self, count: int) -> List:
        """Generate TCP issue packets."""
        packets = []
        for i in range(count):
            # Retransmission pattern
            packet = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="PA", seq=5000, ack=6000) / f"Data packet {i}"
            packets.append(packet)
        return packets
    
    def _get_security_packets(self, count: int) -> List:
        """Generate security-related packets."""
        packets = []
        for i in range(count):
            # Port scan pattern
            packet = Ether() / IP(src="10.0.0.100", dst="192.168.1.1") / TCP(sport=40000+i, dport=80+i, flags="S", seq=7000+i)
            packets.append(packet)
        return packets
    
    def _write_pcap(self, packets: List, filename: str) -> str:
        """Write packets to a PCAP file."""
        pcap_path = os.path.join(self.fixtures_dir, filename)
        wrpcap(pcap_path, packets)
        return pcap_path
    
    def generate_all_fixtures(self) -> Dict[str, str]:
        """
        Generate all test fixture PCAP files.
        
        Returns:
            Dictionary mapping fixture names to file paths
        """
        fixtures = {}
        
        print("Generating PCAP test fixtures...")
        
        fixtures['normal_traffic'] = self.create_normal_traffic()
        print(f"✓ Created normal traffic PCAP: {fixtures['normal_traffic']}")
        
        fixtures['dns_issues'] = self.create_dns_issues()
        print(f"✓ Created DNS issues PCAP: {fixtures['dns_issues']}")
        
        fixtures['tcp_retransmissions'] = self.create_tcp_retransmissions()
        print(f"✓ Created TCP retransmissions PCAP: {fixtures['tcp_retransmissions']}")
        
        fixtures['security_issues'] = self.create_security_issues()
        print(f"✓ Created security issues PCAP: {fixtures['security_issues']}")
        
        fixtures['performance_issues'] = self.create_performance_issues()
        print(f"✓ Created performance issues PCAP: {fixtures['performance_issues']}")
        
        fixtures['mixed_scenario'] = self.create_mixed_scenario()
        print(f"✓ Created mixed scenario PCAP: {fixtures['mixed_scenario']}")
        
        print(f"\nGenerated {len(fixtures)} test fixture PCAP files!")
        return fixtures


# Legacy functions for backward compatibility
def create_sample_pcap(filename: str = "sample.pcap") -> str:
    """Legacy function - create a basic sample PCAP file."""
    generator = PcapFixtureGenerator()
    return generator.create_normal_traffic(filename)


def create_large_sample_pcap(filename: str = "large_sample.pcap", num_packets: int = 1000) -> str:
    """Legacy function - create a large sample PCAP file."""
    generator = PcapFixtureGenerator()
    packets = []
    
    for i in range(num_packets):
        if i % 4 == 0:
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="192.168.1.1") / TCP(sport=12345+i, dport=80, flags="A")
        elif i % 4 == 1:
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="8.8.8.8") / UDP(sport=53000+i, dport=53)
        elif i % 4 == 2:
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="8.8.8.8") / UDP(sport=53000+i, dport=53) / DNS(rd=1, qd=DNSQR(qname=f"test{i}.com"))
        else:
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="8.8.8.8") / ICMP()
        
        packets.append(packet)
    
    return generator._write_pcap(packets, filename)


if __name__ == "__main__":
    # Generate all fixture files when run directly
    generator = PcapFixtureGenerator()
    fixtures = generator.generate_all_fixtures()
    
    # Also create legacy files for backward compatibility
    print("\nCreating legacy sample files...")
    small_pcap = create_sample_pcap()
    print(f"✓ Created legacy small sample PCAP: {small_pcap}")
    
    large_pcap = create_large_sample_pcap()
    print(f"✓ Created legacy large sample PCAP: {large_pcap}")
    
    print("\n🎉 All PCAP test fixtures created successfully!") 