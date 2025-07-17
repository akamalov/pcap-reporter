#!/usr/bin/env python3
"""
Test script to verify PDF export fix.
"""

import requests
import json

def test_pdf_export():
    """Test upload and PDF export functionality."""
    
    # Create a simple test file since we don't have a real PCAP
    test_content = b"Simple test content for upload"
    
    # Upload a test file  
    files = {'file': ('test.pcap', test_content, 'application/octet-stream')}
    
    print("🔄 Uploading test file...")
    response = requests.post('http://localhost:9090/api/v1/analysis/submit', files=files)
    print(f'Upload response: {response.status_code}')
    
    if response.status_code in [200, 201]:
        data = response.json()
        job_id = data.get('job_id')
        print(f'✅ Job ID: {job_id}')
        
        # Test PDF export
        print("🔄 Testing PDF export...")
        pdf_response = requests.get(f'http://localhost:9090/api/v1/export/pdf/{job_id}')
        print(f'PDF export response: {pdf_response.status_code}')
        
        if pdf_response.status_code != 200:
            print(f'❌ PDF export error: {pdf_response.text}')
            return False
        else:
            print(f'✅ PDF export successful, size: {len(pdf_response.content)} bytes')
            return True
    else:
        print(f'❌ Upload failed: {response.text}')
        return False

if __name__ == "__main__":
    success = test_pdf_export()
    if success:
        print("\n🎉 PDF export fix verified successfully!")
    else:
        print("\n💥 PDF export fix needs more work.")