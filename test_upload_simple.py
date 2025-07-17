#!/usr/bin/env python3
"""
Simple test to upload a file and check if it gets processed
"""
import requests
import time
import os
from pathlib import Path

def test_upload_and_processing():
    api_base_url = "http://localhost:9090/api/v1"
    
    # Step 1: Check API health
    try:
        response = requests.get(f"{api_base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API not responding: {e}")
        return False
    
    # Step 2: Find a test file
    uploads_dir = Path("/home/akamalov/projects/pcap-reporter/uploads")
    pcap_files = list(uploads_dir.glob("*.pcap*"))
    
    if not pcap_files:
        print("❌ No PCAP files found for testing")
        return False
        
    test_file = pcap_files[0]
    print(f"📁 Using test file: {test_file.name}")
    
    # Step 3: Upload the file
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'application/octet-stream')}
            data = {
                'analysis_type': 'comprehensive',
                'priority': 'normal'
            }
            
            response = requests.post(
                f"{api_base_url}/analysis/submit",
                files=files,
                data=data,
                timeout=30
            )
            
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Upload successful, job_id: {job_id}")
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload exception: {e}")
        return False
    
    # Step 4: Wait for processing
    print("🔄 Waiting for processing...")
    start_time = time.time()
    timeout = 60
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{api_base_url}/reports/by-job-id/{job_id}", timeout=5)
            
            if response.status_code == 200:
                report = response.json()
                status = report.get('status')
                
                if status == 'completed':
                    print(f"✅ Processing completed successfully in {time.time() - start_time:.1f}s")
                    
                    # Check if we can generate PDF
                    pdf_response = requests.get(f"{api_base_url}/reports/{job_id}/pdf", timeout=30)
                    if pdf_response.status_code == 200 and pdf_response.headers.get('content-type') == 'application/pdf':
                        print(f"✅ PDF generated successfully ({len(pdf_response.content)} bytes)")
                        return True
                    else:
                        print(f"❌ PDF generation failed: {pdf_response.status_code}")
                        return False
                        
                elif status == 'failed':
                    error = report.get('error_message', 'Unknown error')
                    print(f"❌ Processing failed: {error}")
                    return False
                else:
                    print(f"🔄 Status: {status}, waiting...")
                    time.sleep(3)
                    continue
                    
            elif response.status_code == 404:
                print(f"🔄 Job not found yet, waiting...")
                time.sleep(3)
                continue
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"🔄 Error checking status: {e}, retrying...")
            time.sleep(3)
            continue
    
    print(f"❌ Processing timed out after {timeout}s")
    return False

if __name__ == "__main__":
    print("🚀 Testing PCAP Upload and Processing Pipeline")
    print("=" * 50)
    
    success = test_upload_and_processing()
    
    if success:
        print("\n🎉 SUCCESS: Full pipeline is working!")
        print("✅ Upload → Processing → PDF Generation: ALL WORKING")
        exit(0)
    else:
        print("\n❌ FAILURE: Pipeline is still broken")
        exit(1)