#!/usr/bin/env python3
"""
Debug script to test the API directly and catch the exact error
"""

import requests
import traceback
import sys

def test_api():
    url = "http://localhost:9090/api/v1/analysis/submit"
    
    # Create a minimal PCAP file
    pcap_header = b'\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00'
    
    try:
        print("Testing API call...")
        
        files = {'file': ('test.pcap', pcap_header, 'application/octet-stream')}
        data = {
            'analysis_type': 'comprehensive',
            'priority': 'normal'
        }
        
        response = requests.post(url, files=files, data=data, timeout=10)
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 500:
            print("500 ERROR DETECTED")
            try:
                error_data = response.json()
                print(f"Error detail: {error_data.get('detail', 'No detail')}")
            except:
                print("Could not parse error response as JSON")
        
    except Exception as e:
        print(f"Request failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_api()