# Frontend Health Check Implementation

## Overview

The frontend health check endpoint provides comprehensive monitoring capabilities for the PCAP Reporter frontend service. This endpoint is used by Docker health checks, load balancers, and monitoring systems to verify service availability and performance.

## Endpoint Details

### URL
- **GET** `/health`
- **HEAD** `/health` (for simple status checks)

### Response Format

```json
{
  "status": "healthy|degraded|unhealthy",
  "service": "pcap-reporter-frontend",
  "timestamp": "2025-07-13T18:18:22.578Z",
  "uptime": 124.977587231,
  "environment": "development|production",
  "version": "1.0.0",
  "checks": {
    "server": "ok",
    "memory": {
      "used": 86,     // MB
      "total": 104,   // MB
      "external": 7,  // MB
      "rss": 150      // MB
    },
    "backend": {
      "status": "healthy|degraded|unreachable",
      "responseTime": 45,
      "lastCheck": "2025-07-13T18:18:22.578Z"
    }
  },
  "performance": {
    "responseTime": 15,
    "memoryUsagePercent": 83
  },
  "warnings": [
    "High memory usage detected"  // Optional warnings
  ]
}
```

## Status Codes

- **200 OK**: Service is healthy and all checks pass
- **503 Service Unavailable**: Service is unhealthy or critical checks fail

## Health Check Features

### 1. **Basic Service Health**
- Service uptime monitoring
- Memory usage tracking (in MB)
- Server availability verification

### 2. **Backend Connectivity Check**
- Tests connection to backend API
- Measures backend response time
- Non-blocking (frontend health doesn't depend on backend)
- 3-second timeout for backend checks

### 3. **Performance Monitoring**
- Health check response time
- Memory usage percentage
- Performance degradation warnings

### 4. **Alerting & Warnings**
- High memory usage detection (>1GB)
- Slow response time alerts (>5 seconds)
- Service degradation notifications

## Docker Integration

### Health Check Configuration

The health check is configured in both Dockerfile and docker-compose.yml:

#### Dockerfile
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
```

#### docker-compose.yml
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Response Headers

The health endpoint includes performance and caching headers:

```http
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
X-Response-Time: 15ms
```

## Usage Examples

### Basic Health Check
```bash
curl -f http://localhost:3000/health
```

### Simple Status Check (HEAD)
```bash
curl -I http://localhost:3000/health
```

### Monitoring Script
```bash
#!/bin/bash
response=$(curl -s http://localhost:3000/health)
status=$(echo "$response" | jq -r '.status')

if [ "$status" = "healthy" ]; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health issue: $status"
    echo "$response" | jq '.warnings // []'
fi
```

## Configuration

### Environment Variables

- `NODE_ENV`: Controls environment detection
- `REACT_APP_API_URL`: Backend API URL for connectivity checks
- `npm_package_version`: Application version

### Thresholds

- **Memory Alert**: >1GB usage
- **Response Time Alert**: >5 seconds
- **Backend Timeout**: 3 seconds

## Monitoring Integration

### Prometheus Metrics (Future Enhancement)
The health endpoint provides data that can be converted to Prometheus metrics:
- `frontend_memory_usage_bytes`
- `frontend_response_time_seconds`
- `backend_connectivity_status`

### Log Monitoring
Health check failures are logged with structured information for monitoring systems.

## Development & Testing

### Local Testing
```bash
# Start the development server
npm run dev

# Test health endpoint
curl http://localhost:3000/health | jq .
```

### Production Testing
```bash
# Build and run production container
docker build -t pcap-reporter-frontend .
docker run -p 3000:3000 pcap-reporter-frontend

# Verify health check
docker exec <container_id> wget -qO- http://localhost:3000/health
```

## Troubleshooting

### Common Issues

1. **503 Service Unavailable**
   - Check application startup logs
   - Verify environment configuration
   - Ensure sufficient memory allocation

2. **Backend Connectivity Issues**
   - Verify `REACT_APP_API_URL` configuration
   - Check network connectivity between services
   - Review backend service health

3. **High Memory Usage Warnings**
   - Monitor for memory leaks
   - Consider increasing container memory limits
   - Review application resource usage

### Debug Information

The health endpoint provides detailed debug information including:
- Memory breakdown (heap, external, RSS)
- Backend connectivity details
- Performance metrics
- Timestamp information

## Security Considerations

- Health endpoint doesn't expose sensitive information
- Backend connectivity errors are sanitized
- Response headers prevent caching of health data
- No authentication required (suitable for monitoring systems)

## Implementation Notes

- Health checks are non-blocking and fast (<100ms typical)
- Backend connectivity is optional and doesn't fail frontend health
- Memory usage is tracked in human-readable MB format
- All timestamps are ISO 8601 formatted
- Graceful error handling with structured error responses

This implementation provides comprehensive monitoring capabilities while maintaining performance and security best practices.