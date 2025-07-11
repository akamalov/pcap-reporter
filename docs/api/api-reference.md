# PCAP Reporter API Reference

This document provides comprehensive API documentation for PCAP Reporter's REST API and WebSocket endpoints.

## 📋 Table of Contents

1. [Base Information](#base-information)
2. [Authentication](#authentication)
3. [Reports API](#reports-api)
4. [Health Check API](#health-check-api)
5. [WebSocket API](#websocket-api)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

## 🌐 Base Information

### Base URL
```
Production: https://pcap-reporter.yourdomain.com/api
Development: http://localhost:8000/api
```

### Content Types
- **Request**: `multipart/form-data` (file uploads), `application/json` (other requests)
- **Response**: `application/json`

### API Versioning
Current version: `v1` (included in base URL)

## 🔐 Authentication

Currently, PCAP Reporter uses session-based authentication. Future versions will support API keys and JWT tokens.

### Session Authentication
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

## 📊 Reports API

### Upload PCAP File

Upload a PCAP file for analysis.

```http
POST /api/reports/upload
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (required): PCAP file (max 2GB)
- `analysis_options` (optional): JSON string with analysis configuration

**Example Request:**
```bash
curl -X POST \
  -F "file=@sample.pcap" \
  -F 'analysis_options={"deep_inspection": true, "security_analysis": true}' \
  http://localhost:8000/api/reports/upload
```

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": "60f7b1234567890abcdef123",
    "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "filename": "sample.pcap",
    "file_size": 1048576,
    "status": "pending",
    "created_at": "2023-12-01T10:30:00Z",
    "estimated_completion": "2023-12-01T10:35:00Z"
  }
}
```

### Get Report Status

Retrieve the current status of a report.

```http
GET /api/reports/{report_id}/status
```

**Parameters:**
- `report_id` (required): Report identifier

**Example Request:**
```bash
curl http://localhost:8000/api/reports/60f7b1234567890abcdef123/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": "60f7b1234567890abcdef123",
    "status": "processing",
    "progress": 45,
    "current_step": "Protocol Analysis",
    "estimated_remaining": "00:02:30",
    "created_at": "2023-12-01T10:30:00Z",
    "updated_at": "2023-12-01T10:32:15Z"
  }
}
```

### Get Report Details

Retrieve complete report information and results.

```http
GET /api/reports/{report_id}
```

**Parameters:**
- `report_id` (required): Report identifier

**Example Request:**
```bash
curl http://localhost:8000/api/reports/60f7b1234567890abcdef123
```

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": "60f7b1234567890abcdef123",
    "filename": "sample.pcap",
    "file_size": 1048576,
    "status": "completed",
    "progress": 100,
    "created_at": "2023-12-01T10:30:00Z",
    "completed_at": "2023-12-01T10:35:42Z",
    "processing_time": 342,
    "results": {
      "summary": {
        "total_packets": 15420,
        "total_bytes": 12485760,
        "duration": 300.5,
        "protocols": ["TCP", "UDP", "HTTP", "HTTPS", "DNS"]
      },
      "protocol_distribution": {
        "TCP": 85.3,
        "UDP": 12.1,
        "ICMP": 2.6
      },
      "traffic_analysis": {
        "peak_time": "2023-12-01T10:25:30Z",
        "peak_bandwidth": 1250000,
        "average_bandwidth": 415252
      },
      "security_findings": [
        {
          "type": "suspicious_traffic",
          "severity": "medium",
          "description": "Unusual port scanning detected",
          "timestamp": "2023-12-01T10:23:15Z"
        }
      ],
      "top_talkers": [
        {
          "ip": "192.168.1.100",
          "bytes_sent": 2048576,
          "bytes_received": 1536000,
          "connections": 45
        }
      ]
    }
  }
}
```

### List Reports

Retrieve a list of reports with filtering and pagination.

```http
GET /api/reports
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status (`pending`, `processing`, `completed`, `failed`)
- `created_after` (optional): ISO 8601 timestamp
- `created_before` (optional): ISO 8601 timestamp

**Example Request:**
```bash
curl "http://localhost:8000/api/reports?status=completed&limit=10&page=1"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reports": [
      {
        "report_id": "60f7b1234567890abcdef123",
        "filename": "sample.pcap",
        "file_size": 1048576,
        "status": "completed",
        "created_at": "2023-12-01T10:30:00Z",
        "completed_at": "2023-12-01T10:35:42Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "total_items": 89,
      "items_per_page": 20,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

### Delete Report

Delete a report and its associated files.

```http
DELETE /api/reports/{report_id}
```

**Parameters:**
- `report_id` (required): Report identifier

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/api/reports/60f7b1234567890abcdef123
```

**Response:**
```json
{
  "success": true,
  "message": "Report deleted successfully"
}
```

### Download Report Data

Download report results in various formats.

```http
GET /api/reports/{report_id}/download
```

**Query Parameters:**
- `format` (optional): Download format (`json`, `csv`, `pdf`) (default: `json`)

**Example Request:**
```bash
curl -o report.json "http://localhost:8000/api/reports/60f7b1234567890abcdef123/download?format=json"
```

## 🏥 Health Check API

### System Health

Check overall system health and status.

```http
GET /api/health
```

**Example Request:**
```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2023-12-01T10:30:00Z",
    "version": "1.0.0",
    "uptime": 86400,
    "services": {
      "database": {
        "status": "healthy",
        "response_time": 12,
        "last_check": "2023-12-01T10:29:55Z"
      },
      "redis": {
        "status": "healthy",
        "response_time": 3,
        "last_check": "2023-12-01T10:29:55Z"
      },
      "celery": {
        "status": "healthy",
        "active_workers": 2,
        "queued_jobs": 5,
        "last_check": "2023-12-01T10:29:55Z"
      }
    },
    "system": {
      "cpu_usage": 25.5,
      "memory_usage": 68.2,
      "disk_usage": 45.8
    }
  }
}
```

### Service Status

Check status of individual services.

```http
GET /api/health/{service}
```

**Parameters:**
- `service`: Service name (`database`, `redis`, `celery`, `storage`)

**Example Request:**
```bash
curl http://localhost:8000/api/health/database
```

## 🔌 WebSocket API

### Connection

Connect to WebSocket for real-time updates.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### Subscribe to Job Updates

Subscribe to updates for a specific analysis job.

**Message Format:**
```json
{
  "action": "subscribe",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Unsubscribe from Job Updates

```json
{
  "action": "unsubscribe",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Progress Updates

Receive real-time progress updates during analysis.

**Message Format:**
```json
{
  "type": "progress_update",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": {
    "status": "processing",
    "progress": 65,
    "current_step": "Security Analysis",
    "estimated_remaining": "00:01:45",
    "timestamp": "2023-12-01T10:33:30Z"
  }
}
```

### Completion Notification

```json
{
  "type": "job_complete",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": {
    "status": "completed",
    "report_id": "60f7b1234567890abcdef123",
    "processing_time": 342,
    "timestamp": "2023-12-01T10:35:42Z"
  }
}
```

### Error Notification

```json
{
  "type": "job_error",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "data": {
    "status": "failed",
    "error": "Invalid PCAP file format",
    "error_code": "INVALID_FORMAT",
    "timestamp": "2023-12-01T10:32:15Z"
  }
}
```

## ❌ Error Handling

### Error Response Format

All API errors follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error details"
    },
    "timestamp": "2023-12-01T10:30:00Z"
  }
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `413` - Payload Too Large
- `422` - Unprocessable Entity
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_FILE_TYPE` | Unsupported file format | 400 |
| `FILE_TOO_LARGE` | File exceeds size limit | 413 |
| `INVALID_PCAP` | Corrupted or invalid PCAP file | 422 |
| `REPORT_NOT_FOUND` | Report does not exist | 404 |
| `PROCESSING_ERROR` | Error during analysis | 500 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INSUFFICIENT_STORAGE` | Not enough disk space | 507 |

## 🚦 Rate Limiting

API endpoints are rate limited to ensure fair usage:

- **File Upload**: 10 requests per hour per IP
- **Status Checks**: 100 requests per minute per IP
- **Report Retrieval**: 50 requests per minute per IP
- **General API**: 1000 requests per hour per IP

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1701432000
```

## 📝 Examples

### Complete Upload and Monitor Workflow

```python
import requests
import websocket
import json
import time

# 1. Upload file
upload_response = requests.post(
    'http://localhost:8000/api/reports/upload',
    files={'file': open('sample.pcap', 'rb')},
    data={'analysis_options': json.dumps({'deep_inspection': True})}
)

if upload_response.status_code == 200:
    data = upload_response.json()['data']
    report_id = data['report_id']
    job_id = data['job_id']
    
    print(f"Upload successful. Report ID: {report_id}")
    
    # 2. Connect to WebSocket for real-time updates
    def on_message(ws, message):
        data = json.loads(message)
        if data['type'] == 'progress_update':
            print(f"Progress: {data['data']['progress']}% - {data['data']['current_step']}")
        elif data['type'] == 'job_complete':
            print("Analysis completed!")
            ws.close()
    
    ws = websocket.WebSocketApp(
        'ws://localhost:8000/ws',
        on_message=on_message
    )
    
    # Subscribe to job updates
    ws.send(json.dumps({
        'action': 'subscribe',
        'job_id': job_id
    }))
    
    ws.run_forever()
    
    # 3. Retrieve completed report
    report_response = requests.get(f'http://localhost:8000/api/reports/{report_id}')
    if report_response.status_code == 200:
        report_data = report_response.json()['data']
        print(f"Total packets: {report_data['results']['summary']['total_packets']}")
```

### Batch Processing Multiple Files

```python
import requests
import os

def upload_pcap_files(directory):
    results = []
    
    for filename in os.listdir(directory):
        if filename.endswith(('.pcap', '.pcapng')):
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'rb') as f:
                response = requests.post(
                    'http://localhost:8000/api/reports/upload',
                    files={'file': f}
                )
                
                if response.status_code == 200:
                    data = response.json()['data']
                    results.append({
                        'filename': filename,
                        'report_id': data['report_id'],
                        'job_id': data['job_id']
                    })
                    print(f"Uploaded {filename} - Report ID: {data['report_id']}")
                else:
                    print(f"Failed to upload {filename}: {response.text}")
    
    return results

# Upload all PCAP files in a directory
uploaded_files = upload_pcap_files('./pcap_files')
```

### Monitoring System Health

```python
import requests
import time

def monitor_system_health():
    while True:
        response = requests.get('http://localhost:8000/api/health')
        
        if response.status_code == 200:
            health_data = response.json()['data']
            
            print(f"System Status: {health_data['status']}")
            print(f"CPU Usage: {health_data['system']['cpu_usage']}%")
            print(f"Memory Usage: {health_data['system']['memory_usage']}%")
            print(f"Active Workers: {health_data['services']['celery']['active_workers']}")
            print("---")
        else:
            print("Health check failed")
        
        time.sleep(30)  # Check every 30 seconds

monitor_system_health()
```

## 📚 Additional Resources

- [WebSocket API Documentation](websocket-api.md)
- [Authentication Guide](../user/authentication.md)
- [Error Handling Best Practices](../development/error-handling.md)
- [API Client Libraries](../development/client-libraries.md)

---

*For more examples and detailed guides, visit our [GitHub repository](https://github.com/your-org/pcap-reporter)* 