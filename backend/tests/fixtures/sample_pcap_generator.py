"""
Generate sample PCAP files for testing.
"""
import os
from scapy.all import wrpcap, IP, TCP, UDP, DNS, DNSQR, Ether
from scapy.layers.http import HTTP, HTTPRequest


def create_sample_pcap(filename: str = "sample.pcap") -> str:
    """
    Create a small sample PCAP file with various packet types for testing.
    
    Args:
        filename: Name of the PCAP file to create
        
    Returns:
        Path to the created PCAP file
    """
    packets = []
    
    # Create some basic TCP packets
    tcp_packet1 = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="S")
    tcp_packet2 = Ether() / IP(src="192.168.1.1", dst="192.168.1.10") / TCP(sport=80, dport=12345, flags="SA")
    tcp_packet3 = Ether() / IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=12345, dport=80, flags="A")
    
    packets.extend([tcp_packet1, tcp_packet2, tcp_packet3])
    
    # Create some UDP packets
    udp_packet1 = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53000, dport=53)
    udp_packet2 = Ether() / IP(src="8.8.8.8", dst="192.168.1.10") / UDP(sport=53, dport=53000)
    
    packets.extend([udp_packet1, udp_packet2])
    
    # Create DNS query packets
    dns_query = Ether() / IP(src="192.168.1.10", dst="8.8.8.8") / UDP(sport=53000, dport=53) / DNS(rd=1, qd=DNSQR(qname="example.com"))
    dns_response = Ether() / IP(src="8.8.8.8", dst="192.168.1.10") / UDP(sport=53, dport=53000) / DNS(id=dns_query[DNS].id, qr=1, aa=0, rcode=0, qd=DNSQR(qname="example.com"))
    
    packets.extend([dns_query, dns_response])
    
    # Create HTTP-like packets (simplified)
    http_request = Ether() / IP(src="192.168.1.10", dst="93.184.216.34") / TCP(sport=54321, dport=80, flags="PA") / "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
    http_response = Ether() / IP(src="93.184.216.34", dst="192.168.1.10") / TCP(sport=80, dport=54321, flags="PA") / "HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello, World!"
    
    packets.extend([http_request, http_response])
    
    # Get the full path
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    pcap_path = os.path.join(fixtures_dir, filename)
    
    # Write packets to PCAP file
    wrpcap(pcap_path, packets)
    
    return pcap_path


def create_large_sample_pcap(filename: str = "large_sample.pcap", num_packets: int = 1000) -> str:
    """
    Create a larger sample PCAP file for performance testing.
    
    Args:
        filename: Name of the PCAP file to create
        num_packets: Number of packets to generate
        
    Returns:
        Path to the created PCAP file
    """
    packets = []
    
    for i in range(num_packets):
        # Vary the packet types
        if i % 4 == 0:
            # TCP packet
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="192.168.1.1") / TCP(sport=12345+i, dport=80, flags="A")
        elif i % 4 == 1:
            # UDP packet
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="8.8.8.8") / UDP(sport=53000+i, dport=53)
        elif i % 4 == 2:
            # DNS query
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="8.8.8.8") / UDP(sport=53000+i, dport=53) / DNS(rd=1, qd=DNSQR(qname=f"test{i}.com"))
        else:
            # ICMP packet
            packet = Ether() / IP(src=f"192.168.1.{(i % 254) + 1}", dst="8.8.8.8")
        
        packets.append(packet)
    
    # Get the full path
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    pcap_path = os.path.join(fixtures_dir, filename)
    
    # Write packets to PCAP file
    wrpcap(pcap_path, packets)
    
    return pcap_path


if __name__ == "__main__":
    # Generate sample files when run directly
    print("Creating sample PCAP files...")
    
    small_pcap = create_sample_pcap()
    print(f"Created small sample PCAP: {small_pcap}")
    
    large_pcap = create_large_sample_pcap()
    print(f"Created large sample PCAP: {large_pcap}")
    
    print("Sample PCAP files created successfully!") 