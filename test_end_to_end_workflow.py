#!/usr/bin/env python3
"""
End-to-end workflow test for PCAP Reporter.
Tests the complete pipeline: Upload → Processing → Report Generation → Data Retrieval
"""

import requests
import time
import tempfile
import os
import json
from pathlib import Path

BASE_URL = "http://localhost:9090"
API_BASE = f"{BASE_URL}/api/v1"
UPLOAD_ENDPOINT = f"{API_BASE}/analysis/upload"
REPORTS_ENDPOINT = f"{API_BASE}/reports"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def create_realistic_pcap():
    """
    Create a more realistic PCAP file with actual packet structures.
    This should trigger more comprehensive analysis.
    """
    # PCAP Global Header
    pcap_header = bytes([
        0xD4, 0xC3, 0xB2, 0xA1,  # Magic number (little endian)
        0x02, 0x00,              # Version major
        0x04, 0x00,              # Version minor  
        0x00, 0x00, 0x00, 0x00,  # Thiszone
        0x00, 0x00, 0x00, 0x00,  # Sigfigs
        0xFF, 0xFF, 0x00, 0x00,  # Snaplen (65535)
        0x01, 0x00, 0x00, 0x00   # Data link type (Ethernet)
    ])
    
    # Create a packet record header + some fake ethernet packet data
    timestamp_sec = int(time.time())
    timestamp_usec = 0
    captured_len = 60
    original_len = 60
    
    packet_header = (
        timestamp_sec.to_bytes(4, 'little') +
        timestamp_usec.to_bytes(4, 'little') +
        captured_len.to_bytes(4, 'little') +
        original_len.to_bytes(4, 'little')
    )
    
    # Fake Ethernet frame (Ethernet header + IP header + TCP header)
    ethernet_frame = bytes([
        # Ethernet header (14 bytes)
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55,  # Destination MAC
        0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB,  # Source MAC
        0x08, 0x00,                           # EtherType (IPv4)
        
        # IP header (20 bytes)
        0x45, 0x00, 0x00, 0x2E,              # Version, IHL, ToS, Length
        0x00, 0x01, 0x40, 0x00,              # ID, Flags, Fragment
        0x40, 0x06, 0x00, 0x00,              # TTL, Protocol (TCP), Checksum
        0xC0, 0xA8, 0x01, 0x64,              # Source IP (192.168.1.100)
        0xC0, 0xA8, 0x01, 0x01,              # Dest IP (192.168.1.1)
        
        # TCP header (20 bytes)
        0x04, 0xD2, 0x00, 0x50,              # Source port (1234), Dest port (80)
        0x00, 0x00, 0x00, 0x01,              # Sequence number
        0x00, 0x00, 0x00, 0x00,              # Acknowledgment
        0x50, 0x02, 0x20, 0x00,              # Flags, Window
        0x00, 0x00, 0x00, 0x00,              # Checksum, Urgent pointer
        
        # Padding to reach 60 bytes
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ])
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pcap', delete=False) as f:
        f.write(pcap_header + packet_header + ethernet_frame)
        # Add a few more packets
        for i in range(5):
            # Modify source port slightly for each packet
            modified_frame = bytearray(ethernet_frame)
            modified_frame[34] = (0x04 + i) & 0xFF  # Modify source port
            f.write(packet_header + bytes(modified_frame))
        return f.name

def wait_for_complete_processing(job_id: str, max_wait: int = 120) -> tuple[bool, dict]:
    """
    Wait for complete processing and return the full report data.
    """
    print(f"    ⏳ Waiting for complete processing of {job_id} (max {max_wait}s)...")
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < max_wait:
        check_count += 1
        try:
            response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
            
            if response.status_code == 200:
                report_data = response.json()
                status = report_data.get('status', 'unknown')
                
                if check_count % 10 == 0:  # Print every 10 checks (roughly every 5 seconds)
                    elapsed = time.time() - start_time
                    print(f"      Check {check_count}: Status = {status} (elapsed: {elapsed:.1f}s)")
                
                # Check if processing is complete
                if status == 'completed':
                    elapsed = time.time() - start_time
                    print(f"    ✅ Processing completed in {elapsed:.2f}s")
                    return True, report_data
                elif status == 'failed':
                    print(f"    ❌ Processing failed")
                    return False, report_data
                
                # Continue waiting for other statuses ('pending', 'processing', etc.)
                
            elif response.status_code == 404:
                if check_count == 1:
                    print(f"    ⚠️  Report not immediately available (404)")
            else:
                print(f"    ❌ Unexpected status code: {response.status_code}")
                return False, {}
                
        except Exception as e:
            print(f"    ❌ Error checking status: {e}")
        
        time.sleep(0.5)  # Check every 500ms
    
    print(f"    ❌ Timeout: Processing did not complete within {max_wait}s")
    return False, {}

def validate_report_structure(report_data: dict) -> dict:
    """
    Validate that the report has the expected structure and data.
    Returns a validation result with details.
    """
    validation = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'found_sections': []
    }
    
    # Check required top-level fields
    required_fields = ['id', 'job_id', 'status', 'created_at']
    for field in required_fields:
        if field not in report_data:
            validation['errors'].append(f"Missing required field: {field}")
            validation['valid'] = False
        else:
            validation['found_sections'].append(field)
    
    # Check analysis results structure
    if 'analysis_results' in report_data:
        validation['found_sections'].append('analysis_results')
        analysis = report_data['analysis_results']
        
        # Check for expected analysis sections
        expected_sections = [
            'packet_summary',
            'protocol_distribution', 
            'top_conversations',
            'suspicious_ips',
            'temporal_analysis'
        ]
        
        for section in expected_sections:
            if section in analysis:
                validation['found_sections'].append(f"analysis.{section}")
                
                # Validate section has data
                section_data = analysis[section]
                if not section_data:
                    validation['warnings'].append(f"Section {section} is empty")
            else:
                validation['warnings'].append(f"Missing analysis section: {section}")
        
        # Check that conversations have required fields
        if 'top_conversations' in analysis and analysis['top_conversations']:
            conv = analysis['top_conversations'][0]
            conv_fields = ['src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol', 'packet_count']
            for field in conv_fields:
                if field not in conv:
                    validation['warnings'].append(f"Conversation missing field: {field}")
    else:
        validation['errors'].append("Missing analysis_results")
        validation['valid'] = False
    
    return validation

def test_complete_workflow():
    """Test the complete end-to-end workflow."""
    print(f"{Colors.BOLD}{Colors.BLUE}🔍 COMPLETE END-TO-END WORKFLOW TEST{Colors.END}")
    print("=" * 60)
    
    workflow_success = True
    
    # Step 1: Create realistic PCAP file
    print(f"{Colors.BLUE}📋 Step 1: Creating realistic PCAP file...{Colors.END}")
    pcap_file = create_realistic_pcap()
    file_size = os.path.getsize(pcap_file)
    print(f"    ✅ Created PCAP file: {file_size} bytes")
    
    try:
        # Step 2: Upload file
        print(f"\n{Colors.BLUE}📋 Step 2: Uploading PCAP file...{Colors.END}")
        upload_start = time.time()
        
        with open(pcap_file, 'rb') as f:
            files = {'file': ('test_workflow.pcap', f, 'application/octet-stream')}
            upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
        
        upload_time = time.time() - upload_start
        
        if upload_response.status_code != 201:
            print(f"    {Colors.RED}❌ Upload failed: {upload_response.status_code}{Colors.END}")
            workflow_success = False
            return workflow_success
        
        upload_data = upload_response.json()
        job_id = upload_data.get('job_id')
        
        if not job_id:
            print(f"    {Colors.RED}❌ No job_id in response{Colors.END}")
            workflow_success = False
            return workflow_success
        
        print(f"    ✅ Upload successful in {upload_time:.3f}s")
        print(f"    📝 Job ID: {job_id}")
        
        # Step 3: Wait for processing
        print(f"\n{Colors.BLUE}📋 Step 3: Waiting for analysis processing...{Colors.END}")
        processing_success, report_data = wait_for_complete_processing(job_id, max_wait=120)
        
        if not processing_success:
            print(f"    {Colors.RED}❌ Processing failed or timed out{Colors.END}")
            workflow_success = False
            return workflow_success
        
        # Step 4: Validate report structure
        print(f"\n{Colors.BLUE}📋 Step 4: Validating report structure...{Colors.END}")
        validation = validate_report_structure(report_data)
        
        if validation['valid']:
            print(f"    {Colors.GREEN}✅ Report structure is valid{Colors.END}")
            print(f"    📊 Found sections: {len(validation['found_sections'])}")
            for section in validation['found_sections'][:5]:  # Show first 5
                print(f"      - {section}")
            if len(validation['found_sections']) > 5:
                print(f"      ... and {len(validation['found_sections']) - 5} more")
        else:
            print(f"    {Colors.RED}❌ Report structure validation failed{Colors.END}")
            for error in validation['errors']:
                print(f"      {Colors.RED}Error: {error}{Colors.END}")
            workflow_success = False
        
        if validation['warnings']:
            print(f"    {Colors.YELLOW}⚠️  Warnings:{Colors.END}")
            for warning in validation['warnings'][:3]:  # Show first 3 warnings
                print(f"      {Colors.YELLOW}{warning}{Colors.END}")
        
        # Step 5: Test data retrieval and analysis quality
        print(f"\n{Colors.BLUE}📋 Step 5: Testing data retrieval and analysis quality...{Colors.END}")
        
        if 'analysis_results' in report_data:
            analysis = report_data['analysis_results']
            
            # Check packet summary
            if 'packet_summary' in analysis:
                packet_count = analysis['packet_summary'].get('total_packets', 0)
                print(f"    📊 Total packets analyzed: {packet_count}")
                if packet_count > 0:
                    print(f"    {Colors.GREEN}✅ Packet analysis successful{Colors.END}")
                else:
                    print(f"    {Colors.YELLOW}⚠️  No packets found in analysis{Colors.END}")
            
            # Check protocol distribution
            if 'protocol_distribution' in analysis:
                protocols = analysis['protocol_distribution']
                protocol_count = len(protocols) if protocols else 0
                print(f"    🔍 Protocols detected: {protocol_count}")
                if protocol_count > 0:
                    print(f"    {Colors.GREEN}✅ Protocol analysis successful{Colors.END}")
                    # Show top protocols
                    for i, (protocol, count) in enumerate(protocols.items()):
                        if i < 3:  # Show top 3
                            print(f"      - {protocol}: {count} packets")
                else:
                    print(f"    {Colors.YELLOW}⚠️  No protocols detected{Colors.END}")
            
            # Check conversations
            if 'top_conversations' in analysis:
                conversations = analysis['top_conversations']
                conv_count = len(conversations) if conversations else 0
                print(f"    🔄 Network conversations: {conv_count}")
                if conv_count > 0:
                    print(f"    {Colors.GREEN}✅ Conversation analysis successful{Colors.END}")
                    # Show sample conversation
                    if conversations:
                        conv = conversations[0]
                        src = f"{conv.get('src_ip', '?')}:{conv.get('src_port', '?')}"
                        dst = f"{conv.get('dst_ip', '?')}:{conv.get('dst_port', '?')}"
                        packets = conv.get('packet_count', 0)
                        print(f"      Sample: {src} → {dst} ({packets} packets)")
                else:
                    print(f"    {Colors.YELLOW}⚠️  No conversations detected{Colors.END}")
        
        # Step 6: Test retrieval via different endpoints
        print(f"\n{Colors.BLUE}📋 Step 6: Testing different retrieval methods...{Colors.END}")
        
        # Test all reports endpoint
        all_reports_response = requests.get(REPORTS_ENDPOINT)
        if all_reports_response.status_code == 200:
            all_reports = all_reports_response.json().get('reports', [])
            job_in_list = any(r.get('job_id') == job_id for r in all_reports)
            if job_in_list:
                print(f"    {Colors.GREEN}✅ Report found in all reports list{Colors.END}")
            else:
                print(f"    {Colors.RED}❌ Report not found in all reports list{Colors.END}")
                workflow_success = False
        else:
            print(f"    {Colors.RED}❌ Failed to retrieve all reports: {all_reports_response.status_code}{Colors.END}")
            workflow_success = False
        
        # Test direct ID retrieval (again to confirm consistency)
        direct_response = requests.get(f"{REPORTS_ENDPOINT}/by-job-id/{job_id}")
        if direct_response.status_code == 200:
            print(f"    {Colors.GREEN}✅ Direct retrieval by job_id successful{Colors.END}")
        else:
            print(f"    {Colors.RED}❌ Direct retrieval failed: {direct_response.status_code}{Colors.END}")
            workflow_success = False
        
    except Exception as e:
        print(f"    {Colors.RED}❌ Workflow exception: {str(e)}{Colors.END}")
        workflow_success = False
    
    finally:
        # Cleanup
        os.unlink(pcap_file)
    
    return workflow_success

def test_multiple_file_formats():
    """Test workflow with different file sizes and characteristics."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}🔍 MULTIPLE FILE FORMAT WORKFLOW TEST{Colors.END}")
    print("=" * 60)
    
    test_cases = [
        ("small", 1),
        ("medium", 10), 
        ("large", 50)
    ]
    
    results = []
    
    for test_name, size_kb in test_cases:
        print(f"\n{Colors.BLUE}📋 Testing {test_name} file ({size_kb}KB)...{Colors.END}")
        
        # Create test file
        pcap_file = create_realistic_pcap()
        
        # Extend file to desired size
        with open(pcap_file, 'ab') as f:
            current_size = f.tell()
            target_size = size_kb * 1024
            if target_size > current_size:
                f.write(b'\x00' * (target_size - current_size))
        
        try:
            # Upload
            start_time = time.time()
            with open(pcap_file, 'rb') as f:
                files = {'file': (f'test_{test_name}.pcap', f, 'application/octet-stream')}
                upload_response = requests.post(UPLOAD_ENDPOINT, files=files)
            
            if upload_response.status_code != 201:
                print(f"    {Colors.RED}❌ Upload failed: {upload_response.status_code}{Colors.END}")
                results.append((test_name, False, 0))
                continue
            
            job_id = upload_response.json().get('job_id')
            
            # Wait for processing
            success, report_data = wait_for_complete_processing(job_id, max_wait=180)  # Longer timeout for larger files
            
            processing_time = time.time() - start_time
            
            if success:
                print(f"    {Colors.GREEN}✅ {test_name} file processed successfully in {processing_time:.2f}s{Colors.END}")
                results.append((test_name, True, processing_time))
            else:
                print(f"    {Colors.RED}❌ {test_name} file processing failed{Colors.END}")
                results.append((test_name, False, processing_time))
        
        except Exception as e:
            print(f"    {Colors.RED}❌ Exception with {test_name} file: {e}{Colors.END}")
            results.append((test_name, False, 0))
        
        finally:
            os.unlink(pcap_file)
    
    # Summary
    print(f"\n{Colors.BOLD}📊 MULTIPLE FILE FORMAT RESULTS:{Colors.END}")
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, time_taken in results:
        status = f"{Colors.GREEN}✅ PASS" if success else f"{Colors.RED}❌ FAIL"
        print(f"  {test_name}: {status}{Colors.END} ({time_taken:.2f}s)")
    
    print(f"\nSuccess rate: {successful}/{total} ({successful/total*100:.1f}%)")
    
    return successful == total

def main():
    """Run all end-to-end workflow tests."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("=" * 80)
    print("PCAP REPORTER - END-TO-END WORKFLOW TEST SUITE")
    print("=" * 80)
    print(f"{Colors.END}")
    
    all_success = True
    
    # Test 1: Complete workflow
    workflow_success = test_complete_workflow()
    all_success &= workflow_success
    
    # Test 2: Multiple file formats
    format_success = test_multiple_file_formats()
    all_success &= format_success
    
    # Final summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("🏁 END-TO-END TEST SUMMARY")
    print(f"{'='*60}{Colors.END}")
    
    print(f"Complete workflow test: {'✅ PASS' if workflow_success else '❌ FAIL'}")
    print(f"Multiple format test: {'✅ PASS' if format_success else '❌ FAIL'}")
    
    if all_success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL END-TO-END TESTS PASSED{Colors.END}")
        print("The PCAP Reporter system is working correctly for complete workflows.")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}🔧 SOME END-TO-END TESTS FAILED{Colors.END}")
        print("Check the detailed output above for specific issues.")
    
    return all_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)