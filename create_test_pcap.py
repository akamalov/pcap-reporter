#!/usr/bin/env python3
"""
Create realistic test PCAP files that won't trigger security validation.
"""

import struct
import time
import tempfile
import os
from datetime import datetime

def create_realistic_pcap_file(filename: str = None, num_packets: int = 10) -> str:
    """
    Create a realistic PCAP file with actual network packets.
    This creates varied packet data that won't trigger security validation.
    """
    if filename is None:
        with tempfile.NamedTemporaryFile(suffix='.pcap', delete=False) as f:
            filename = f.name
    
    with open(filename, 'wb') as f:
        # Write PCAP global header
        global_header = struct.pack('<LHHLLLL',
            0xa1b2c3d4,  # Magic number
            2,           # Version major
            4,           # Version minor
            0,           # Thiszone
            0,           # Sigfigs
            65535,       # Snaplen
            1            # Network (Ethernet)
        )
        f.write(global_header)
        
        base_time = int(time.time())
        
        # Create various types of packets
        packets = []
        
        # TCP SYN packet (192.168.1.100:12345 -> 93.184.216.34:80)
        tcp_syn = create_tcp_packet(
            src_ip='192.168.1.100', dst_ip='93.184.216.34',
            src_port=12345, dst_port=80,
            flags=0x02  # SYN
        )
        packets.append(tcp_syn)
        
        # TCP SYN-ACK response
        tcp_syn_ack = create_tcp_packet(
            src_ip='93.184.216.34', dst_ip='192.168.1.100',
            src_port=80, dst_port=12345,
            flags=0x12  # SYN+ACK
        )
        packets.append(tcp_syn_ack)
        
        # TCP ACK
        tcp_ack = create_tcp_packet(
            src_ip='192.168.1.100', dst_ip='93.184.216.34',
            src_port=12345, dst_port=80,
            flags=0x10  # ACK
        )
        packets.append(tcp_ack)
        
        # HTTP GET request
        http_get_data = b"GET / HTTP/1.1\r\nHost: example.com\r\nUser-Agent: TestClient\r\n\r\n"
        http_get = create_tcp_packet(
            src_ip='192.168.1.100', dst_ip='93.184.216.34',
            src_port=12345, dst_port=80,
            flags=0x18,  # PSH+ACK
            data=http_get_data
        )
        packets.append(http_get)
        
        # DNS query
        dns_query = create_dns_packet(
            src_ip='192.168.1.100', dst_ip='8.8.8.8',
            query_name='example.com'
        )
        packets.append(dns_query)
        
        # ICMP ping
        icmp_ping = create_icmp_packet(
            src_ip='192.168.1.100', dst_ip='8.8.8.8'
        )
        packets.append(icmp_ping)
        
        # Add more varied packets to reach desired count
        while len(packets) < num_packets:
            # Random TCP packets to different ports/IPs
            import random
            src_port = random.randint(1024, 65535)
            dst_port = random.choice([80, 443, 22, 53, 25])
            dst_ip_last = random.randint(1, 254)
            
            tcp_packet = create_tcp_packet(
                src_ip='192.168.1.100', 
                dst_ip=f'192.168.1.{dst_ip_last}',
                src_port=src_port, 
                dst_port=dst_port,
                flags=random.choice([0x02, 0x10, 0x18])
            )
            packets.append(tcp_packet)
        
        # Write packet records
        for i, packet_data in enumerate(packets[:num_packets]):
            timestamp = base_time + i
            packet_len = len(packet_data)
            
            # Packet record header
            packet_header = struct.pack('<LLLL',
                timestamp,   # Timestamp seconds
                0,           # Timestamp microseconds
                packet_len,  # Captured length
                packet_len   # Original length
            )
            
            f.write(packet_header)
            f.write(packet_data)
    
    return filename

def create_ethernet_header(dst_mac: str = "00:11:22:33:44:55", 
                          src_mac: str = "66:77:88:99:aa:bb",
                          ethertype: int = 0x0800) -> bytes:
    """Create an Ethernet header."""
    dst = bytes.fromhex(dst_mac.replace(':', ''))
    src = bytes.fromhex(src_mac.replace(':', ''))
    return dst + src + struct.pack('>H', ethertype)

def create_ip_header(src_ip: str, dst_ip: str, protocol: int, data_len: int) -> bytes:
    """Create an IPv4 header."""
    def ip_to_bytes(ip: str) -> bytes:
        return b''.join(int(x).to_bytes(1, 'big') for x in ip.split('.'))
    
    version_ihl = 0x45  # IPv4, 20-byte header
    tos = 0
    total_len = 20 + data_len
    identification = 0x1234
    flags_frag = 0x4000  # Don't fragment
    ttl = 64
    checksum = 0  # Will be calculated
    
    header = struct.pack('>BBHHHBBH',
        version_ihl, tos, total_len, identification,
        flags_frag, ttl, protocol, checksum
    )
    header += ip_to_bytes(src_ip)
    header += ip_to_bytes(dst_ip)
    
    return header

def create_tcp_header(src_port: int, dst_port: int, flags: int, data: bytes = b'') -> bytes:
    """Create a TCP header."""
    seq = 0x12345678
    ack = 0x87654321 if flags & 0x10 else 0  # ACK number if ACK flag set
    header_len = 0x50  # 20 bytes
    window = 8192
    checksum = 0
    urgent = 0
    
    return struct.pack('>HHLLBBHHH',
        src_port, dst_port, seq, ack,
        header_len, flags, window, checksum, urgent
    )

def create_tcp_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int, 
                     flags: int, data: bytes = b'') -> bytes:
    """Create a complete TCP packet."""
    tcp_header = create_tcp_header(src_port, dst_port, flags, data)
    tcp_data = tcp_header + data
    
    ip_header = create_ip_header(src_ip, dst_ip, 6, len(tcp_data))  # 6 = TCP
    eth_header = create_ethernet_header()
    
    return eth_header + ip_header + tcp_data

def create_udp_header(src_port: int, dst_port: int, data: bytes = b'') -> bytes:
    """Create a UDP header."""
    length = 8 + len(data)
    checksum = 0
    
    return struct.pack('>HHHH',
        src_port, dst_port, length, checksum
    )

def create_dns_packet(src_ip: str, dst_ip: str, query_name: str) -> bytes:
    """Create a DNS query packet."""
    # DNS header
    dns_id = 0x1234
    flags = 0x0100  # Standard query
    questions = 1
    answers = 0
    authority = 0
    additional = 0
    
    dns_header = struct.pack('>HHHHHH',
        dns_id, flags, questions, answers, authority, additional
    )
    
    # DNS question
    query_parts = query_name.split('.')
    dns_question = b''
    for part in query_parts:
        dns_question += struct.pack('B', len(part)) + part.encode()
    dns_question += b'\x00'  # End of name
    dns_question += struct.pack('>HH', 1, 1)  # Type A, Class IN
    
    dns_data = dns_header + dns_question
    udp_header = create_udp_header(53, 53, dns_data)
    udp_data = udp_header + dns_data
    
    ip_header = create_ip_header(src_ip, dst_ip, 17, len(udp_data))  # 17 = UDP
    eth_header = create_ethernet_header()
    
    return eth_header + ip_header + udp_data

def create_icmp_packet(src_ip: str, dst_ip: str) -> bytes:
    """Create an ICMP ping packet."""
    icmp_type = 8  # Echo request
    icmp_code = 0
    icmp_checksum = 0
    icmp_id = 0x1234
    icmp_seq = 1
    
    icmp_data = b'Hello, World! This is a ping test packet.'
    
    icmp_header = struct.pack('>BBHHH',
        icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq
    )
    
    icmp_packet = icmp_header + icmp_data
    ip_header = create_ip_header(src_ip, dst_ip, 1, len(icmp_packet))  # 1 = ICMP
    eth_header = create_ethernet_header()
    
    return eth_header + ip_header + icmp_packet

def main():
    """Test the PCAP creation."""
    print("Creating test PCAP files...")
    
    # Create different sizes
    files = [
        ("small_test.pcap", 5),
        ("medium_test.pcap", 20),
        ("large_test.pcap", 100)
    ]
    
    for filename, packet_count in files:
        pcap_path = create_realistic_pcap_file(filename, packet_count)
        size = os.path.getsize(pcap_path)
        print(f"Created {filename}: {size} bytes with {packet_count} packets")
    
    print("Test PCAP files created successfully!")

if __name__ == "__main__":
    main()