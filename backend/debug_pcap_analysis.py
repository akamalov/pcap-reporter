#!/usr/bin/env python3
"""
Debug PCAP analysis to understand the actual structure.
"""

import asyncio
import os
import tempfile
import struct
from datetime import datetime
from pathlib import Path
import sys

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

async def debug_pcap_analysis():
    """Debug the actual PCAP analysis process."""
    
    print("🔍 Debugging PCAP Analysis Process")
    print("=" * 50)
    
    # Create a simple PCAP file
    pcap_path = "/tmp/debug_test.pcap"
    
    # PCAP Global Header
    global_header = struct.pack(
        '<IHHIIII',
        0xa1b2c3d4,  # Magic number
        2,           # Version major
        4,           # Version minor
        0,           # Thiszone
        0,           # Sigfigs
        65535,       # Snaplen
        1            # Network (Ethernet)
    )
    
    # Simple packet data (Ethernet + IP + TCP)
    packet_data = b'\x00\x01\x02\x03\x04\x05\x00\x06\x07\x08\x09\x0a\x08\x00' + b'\x00' * 60
    
    # Write PCAP file
    with open(pcap_path, 'wb') as f:
        f.write(global_header)
        # Write multiple packets
        for i in range(10):
            timestamp = int(datetime.now().timestamp())
            packet_header = struct.pack('<IIII', timestamp, 0, len(packet_data), len(packet_data))
            f.write(packet_header)
            f.write(packet_data)
    
    print(f"✅ Created test PCAP: {pcap_path}")
    print(f"   Size: {os.path.getsize(pcap_path)} bytes")
    
    # Test the analysis service
    try:
        from services.pcap_analysis_service import PcapAnalysisService
        
        service = PcapAnalysisService()
        print("\n🔍 Running PCAP analysis...")
        
        results = await service.analyze_pcap_file(pcap_path)
        
        print(f"\n✅ Analysis completed!")
        print(f"   Type: {type(results)}")
        print(f"   Fields: {list(results.__dict__.keys())}")
        
        # Check traffic stats
        if hasattr(results, 'traffic_stats'):
            print(f"\n📊 Traffic Stats:")
            print(f"   Total packets: {results.traffic_stats.total_packets}")
            print(f"   Total bytes: {results.traffic_stats.total_bytes}")
            print(f"   Duration: {results.traffic_stats.duration}")
            print(f"   Avg packet size: {results.traffic_stats.avg_packet_size}")
            print(f"   Packets per second: {results.traffic_stats.packets_per_second}")
        
        # Check protocol stats
        if hasattr(results, 'protocol_stats'):
            print(f"\n🔌 Protocol Stats:")
            print(f"   TCP packets: {results.protocol_stats.tcp_packets}")
            print(f"   UDP packets: {results.protocol_stats.udp_packets}")
            print(f"   ICMP packets: {results.protocol_stats.icmp_packets}")
            print(f"   HTTP sessions: {results.protocol_stats.http_sessions}")
            print(f"   DNS queries: {results.protocol_stats.dns_queries}")
        
        # Check issues
        if hasattr(results, 'issues'):
            print(f"\n⚠️  Issues Found: {len(results.issues)}")
            for issue in results.issues:
                print(f"   - {issue.type}: {issue.description}")
        
        # Check conversations
        if hasattr(results, 'top_conversations'):
            print(f"\n💬 Conversations: {len(results.top_conversations)}")
            for conv in results.top_conversations[:3]:
                print(f"   - {conv.src_ip}:{conv.src_port} -> {conv.dst_ip}:{conv.dst_port}")
        
        # Check legacy properties
        print(f"\n🔄 Legacy Properties:")
        print(f"   protocols: {results.protocols}")
        print(f"   total_packets: {results.total_packets}")
        print(f"   total_bytes: {results.total_bytes}")
        print(f"   duration: {results.duration}")
        
        # Check if it can be converted to dict
        try:
            results_dict = results.dict()
            print(f"\n📋 Can convert to dict: ✅")
            print(f"   Dict keys: {list(results_dict.keys())}")
        except Exception as e:
            print(f"\n📋 Can convert to dict: ❌ {e}")
        
        return results
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Clean up
        if os.path.exists(pcap_path):
            os.unlink(pcap_path)

if __name__ == "__main__":
    asyncio.run(debug_pcap_analysis())