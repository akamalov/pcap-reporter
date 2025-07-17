#!/usr/bin/env python3
"""
Test script to debug the PCAP upload issue.
"""

import requests
import sys

def test_upload():
    """Test the upload endpoint with a minimal request."""
    
    url = "http://localhost:8000/api/v1/analysis/submit"
    
    # Test 1: Simple POST without file
    print("Test 1: POST without file")
    try:
        response = requests.post(url, json={"test": "data"})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: POST with empty file
    print("Test 2: POST with empty file data")
    try:
        response = requests.post(url, data={"analysis_type": "comprehensive"})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Check if endpoint exists
    print("Test 3: HEAD request to check endpoint")
    try:
        response = requests.head(url)
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_upload()