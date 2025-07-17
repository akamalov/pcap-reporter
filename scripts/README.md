# PCAP Reporter Management Scripts

This directory contains comprehensive environment management scripts for the PCAP Reporter project. These scripts provide easy startup, shutdown, monitoring, and logging capabilities for both development and production environments.

## 📁 Scripts Overview

### 🚀 **Primary Management Scripts**

#### `pcap-reporter.sh` (Linux/macOS)
The main environment management script with full functionality:
- **Start/Stop/Restart** services
- **Service status monitoring** with health checks
- **Component-specific logging** with follow mode
- **Production and development** environment support
- **Cleanup functionality** for complete teardown
- **🆕 Automated frontend issue detection and remediation**

#### `pcap-reporter.bat` (Windows)
Windows-compatible version of the management script:
- **Basic start/stop/restart** functionality
- **Service status** monitoring
- **Log viewing** capabilities
- **Cross-platform compatibility**

### 🔍 **Monitoring & Health Scripts**

#### `health-check.sh`
Comprehensive health monitoring script:
- **Quick or detailed** health assessments
- **JSON output** for automation
- **Service endpoint verification**
- **Database and cache connectivity** checks
- **Overall system health** scoring

#### `log-viewer.sh`
Advanced log viewing and analysis:
- **Multi-service log aggregation**
- **Real-time log following**
- **Log filtering** by pattern, level, and time
- **Colorized output** for better readability
- **Log statistics** and summaries

#### `frontend-diagnostics.sh` 🆕
Comprehensive frontend troubleshooting and diagnostics:
- **Automated issue detection** for common frontend problems
- **Container health analysis** with detailed status reporting
- **Dependency verification** (node_modules, package.json, etc.)
- **Network connectivity testing** (backend API, external access)
- **Resource monitoring** (disk space, memory usage)
- **Actionable remediation suggestions**

## 🛠️ Usage Examples

### Basic Operations

```bash
# Start development environment
./scripts/pcap-reporter.sh start

# Start production environment
./scripts/pcap-reporter.sh start --prod

# Stop services with cleanup
./scripts/pcap-reporter.sh stop --cleanup

# Restart services
./scripts/pcap-reporter.sh restart

# Show service status
./scripts/pcap-reporter.sh status
# or
./scripts/pcap-reporter.sh -s

# Fix frontend issues automatically
./scripts/pcap-reporter.sh fix-frontend
# or
./scripts/pcap-reporter.sh -f
```

### Frontend Troubleshooting 🆕

```bash
# Run comprehensive frontend diagnostics
./scripts/frontend-diagnostics.sh

# Automatic frontend issue detection and remediation
./scripts/pcap-reporter.sh fix-frontend

# View frontend troubleshooting guide
cat ./scripts/FRONTEND_TROUBLESHOOTING.md
```

### Advanced Logging

```bash
# View backend logs
./scripts/pcap-reporter.sh logs --service backend

# Follow frontend logs in real-time
./scripts/pcap-reporter.sh logs --service frontend --follow

# View all logs with filtering
./scripts/log-viewer.sh --filter "error" --level ERROR

# Follow nginx logs since 1 hour ago
./scripts/log-viewer.sh nginx --follow --since "1 hour ago"
```

### Health Monitoring

```bash
# Quick health check
./scripts/health-check.sh

# Detailed health assessment
./scripts/health-check.sh --detailed

# JSON output for automation
./scripts/health-check.sh --json
```

## 🔧 Service Management

### Available Services

| Service | Description | Port |
|---------|-------------|------|
| `nginx` | Reverse proxy and load balancer | 80/443 |
| `frontend` | React/Next.js web interface | 3000 |
| `backend` | FastAPI server | 8000 |
| `celery-worker` | Background task processor | - |
| `mongodb` | Document database | 27017 |
| `redis` | Cache and message queue | 6379 |

### Service URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## 📊 Status Monitoring

### Service Status Indicators

The status script provides comprehensive health monitoring:

```bash
./scripts/pcap-reporter.sh status
```

**Output includes:**
- ✅ **Container Status**: Running/Stopped state
- 🔗 **Endpoint Health**: HTTP connectivity verification
- 📊 **Resource Usage**: CPU, memory, and disk utilization
- 🔍 **Service Details**: Individual component health

### Health Check Levels

1. **Quick Check**: Basic service availability
2. **Detailed Check**: Comprehensive health assessment
3. **JSON Output**: Machine-readable status for automation

## 📋 Logging Capabilities

### Log Levels

- **ERROR**: Critical errors requiring immediate attention
- **WARN**: Warning messages about potential issues
- **INFO**: Informational messages about normal operations
- **DEBUG**: Detailed debugging information

### Log Filtering

```bash
# Filter by pattern
./scripts/log-viewer.sh --filter "authentication"

# Filter by log level
./scripts/log-viewer.sh --level ERROR

# Filter by time range
./scripts/log-viewer.sh --since "2024-01-01T10:00:00"

# Combine filters
./scripts/log-viewer.sh backend --filter "error" --level ERROR --follow
```

### Log Colorization

Logs are automatically colorized for better readability:
- 🔴 **Red**: Error messages
- 🟡 **Yellow**: Warning messages
- 🟢 **Green**: Info messages
- 🔵 **Blue**: Debug messages
- 🟣 **Purple**: Service names
- 🟦 **Cyan**: Timestamps

## 🌐 Environment Support

### Development Environment

```bash
# Default development setup
./scripts/pcap-reporter.sh start

# Uses: docker-compose.yml
# Features: Hot reload, debug mode, development tools
```

### Production Environment

```bash
# Production-ready deployment
./scripts/pcap-reporter.sh start --prod

# Uses: docker-compose.prod.yml
# Features: Optimized builds, security hardening, monitoring
```

## 🔧 Configuration

### Environment Variables

The scripts respect these environment variables:

```bash
# Docker Compose file selection
COMPOSE_FILE=docker-compose.yml
COMPOSE_PROD_FILE=docker-compose.prod.yml

# Logging configuration
LOG_DIR=./logs
LOG_LEVEL=INFO

# Health check timeouts
HEALTH_CHECK_TIMEOUT=30
```

### Script Configuration

Edit the script headers to customize:

```bash
# Timeout settings
TIMEOUT=10

# Service definitions
SERVICES=(
    "nginx:reverse-proxy"
    "frontend:web-interface"
    "backend:api-server"
    "celery-worker:task-processor"
    "mongodb:database"
    "redis:cache-queue"
)
```

## 🚨 Troubleshooting

### Common Issues

1. **Docker Not Running**
   ```bash
   [ERROR] Docker daemon is not running
   ```
   **Solution**: Start Docker Desktop or Docker daemon

2. **Port Conflicts**
   ```bash
   [ERROR] Port 3000 already in use
   ```
   **Solution**: Stop conflicting services or change ports

3. **Permission Errors**
   ```bash
   [ERROR] Permission denied
   ```
   **Solution**: Make scripts executable: `chmod +x scripts/*.sh`

4. **Frontend Won't Start** 🆕
   ```bash
   [ERROR] Frontend container has exited
   ```
   **Solution**: Run automated diagnostics and fixes:
   ```bash
   # Comprehensive frontend fix
   ./scripts/pcap-reporter.sh fix-frontend
   
   # Detailed diagnostics
   ./scripts/frontend-diagnostics.sh
   
   # View troubleshooting guide
   cat ./scripts/FRONTEND_TROUBLESHOOTING.md
   ```

5. **Missing Dependencies**
   ```bash
   [ERROR] Module not found
   ```
   **Solution**: Automatically handled by `fix-frontend` command

### Debug Mode

Enable debug logging in scripts:

```bash
# Add to script
set -x  # Enable debug mode
set +x  # Disable debug mode
```

### Log Analysis

Common log patterns to search for:

```bash
# Authentication errors
./scripts/log-viewer.sh --filter "authentication failed"

# Database connection issues
./scripts/log-viewer.sh --filter "database.*connection"

# Performance issues
./scripts/log-viewer.sh --filter "slow.*query"

# Security events
./scripts/log-viewer.sh --filter "security.*event"
```

## 📈 Performance Monitoring

### Resource Usage

Monitor system resources:

```bash
# Check container resource usage
docker stats

# Check disk usage
df -h

# Check memory usage
free -h
```

### Health Metrics

The health check script provides:

- **Response Time**: Service response times
- **Error Rate**: Error frequency and patterns
- **Availability**: Service uptime percentage
- **Resource Usage**: CPU, memory, and disk utilization

## 🔐 Security Considerations

### Script Security

- Scripts validate input parameters
- Environment variables are sanitized
- Secure defaults are used
- Sensitive information is not logged

### Production Security

For production deployments:

```bash
# Use production environment
./scripts/pcap-reporter.sh start --prod

# Enable security monitoring
./scripts/health-check.sh --detailed

# Monitor for security events
./scripts/log-viewer.sh --filter "security"
```

## 📝 Integration with CI/CD

### GitHub Actions

```yaml
- name: Start PCAP Reporter
  run: ./scripts/pcap-reporter.sh start --prod

- name: Health Check
  run: ./scripts/health-check.sh --json

- name: View Logs on Failure
  if: failure()
  run: ./scripts/log-viewer.sh --level ERROR
```

### Docker Compose Integration

Scripts work seamlessly with Docker Compose:

```bash
# Scripts use docker-compose commands internally
docker-compose up -d    # Equivalent to: ./scripts/pcap-reporter.sh start
docker-compose down     # Equivalent to: ./scripts/pcap-reporter.sh stop
```

## 🔄 Automation Examples

### Automated Health Monitoring

```bash
#!/bin/bash
# monitoring-cron.sh

# Run health check every 5 minutes
*/5 * * * * /path/to/scripts/health-check.sh --json >> /var/log/pcap-health.log

# Restart if unhealthy
if ! /path/to/scripts/health-check.sh --json | jq -e '.overall_status == "healthy"'; then
    /path/to/scripts/pcap-reporter.sh restart
fi
```

### Log Rotation

```bash
# Rotate logs daily
0 0 * * * /path/to/scripts/log-viewer.sh --since "24 hours ago" > /var/log/pcap-daily.log
```

## 📚 Additional Resources

- **Main Documentation**: `/docs/README.md`
- **Installation Guide**: `/docs/user/installation.md`
- **Troubleshooting**: `/docs/user/troubleshooting.md`
- **API Documentation**: `/docs/api/api-reference.md`

## 🆘 Support

For issues with the management scripts:

1. Check the troubleshooting section above
2. Review the logs using `./scripts/log-viewer.sh --level ERROR`
3. Verify Docker and Docker Compose installation
4. Check the health status with `./scripts/health-check.sh --detailed`

---

**Last Updated**: 2024-01-15  
**Version**: 1.0.0  
**Compatibility**: Linux, macOS, Windows