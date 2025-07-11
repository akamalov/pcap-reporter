# PCAP Reporter Troubleshooting Guide

This guide helps you diagnose and resolve common issues with PCAP Reporter.

## 📋 Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Upload Problems](#upload-problems)
4. [Processing Issues](#processing-issues)
5. [Performance Problems](#performance-problems)
6. [Network and Connectivity](#network-and-connectivity)
7. [Browser Issues](#browser-issues)
8. [Docker and Container Issues](#docker-and-container-issues)
9. [Database Problems](#database-problems)
10. [Getting Additional Help](#getting-additional-help)

## 🔍 Quick Diagnostics

### System Health Check

Before troubleshooting specific issues, check overall system health:

```bash
# Check service status
docker-compose ps

# Check system health via API
curl http://localhost:8000/api/health

# View recent logs
docker-compose logs --tail=50
```

### Common Status Indicators

| Status | Meaning | Action |
|--------|---------|--------|
| 🟢 Healthy | Service running normally | No action needed |
| 🟡 Warning | Service degraded but functional | Monitor closely |
| 🔴 Error | Service not functioning | Immediate attention required |
| 🔵 Starting | Service initializing | Wait for completion |

## 🚀 Installation Issues

### Docker Installation Problems

#### Issue: "docker: command not found"
```bash
# Install Docker on Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Issue: "Permission denied while trying to connect to Docker daemon"
```bash
# Fix Docker permissions
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Restart your session or run:
newgrp docker
```

#### Issue: "docker-compose: command not found"
```bash
# Install Docker Compose V2
sudo apt install docker-compose-plugin

# Or use standalone version
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Port Conflicts

#### Issue: "Port already in use"
```bash
# Check what's using the port
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :8000

# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx

# Or change ports in docker-compose.yml
```

### Environment Setup Issues

#### Issue: ".env file not found"
```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

#### Issue: "Invalid environment variables"
```bash
# Validate environment file
docker-compose config

# Check for syntax errors
cat .env | grep -v '^#' | grep -v '^$'
```

## 📁 Upload Problems

### File Upload Failures

#### Issue: "File too large"
**Symptoms**: Upload fails with 413 error
**Solution**:
```bash
# Check current limits
curl -I http://localhost:8000/api/health

# Increase limits in nginx.conf
client_max_body_size 4G;

# Restart services
docker-compose restart nginx
```

#### Issue: "Invalid file type"
**Symptoms**: Upload rejected with format error
**Solution**:
1. Verify file extension (`.pcap`, `.pcapng`, `.cap`)
2. Check file integrity:
```bash
# Verify PCAP file
tcpdump -r yourfile.pcap -c 1

# Check file type
file yourfile.pcap
```

#### Issue: "Upload timeout"
**Symptoms**: Upload hangs or times out
**Solution**:
```bash
# Increase timeout in nginx.conf
proxy_read_timeout 600s;
proxy_send_timeout 600s;

# Check network connection
ping your-server.com
```

### Browser Upload Issues

#### Issue: "Upload progress stuck"
**Solution**:
1. Refresh the browser page
2. Clear browser cache
3. Try incognito/private mode
4. Use a different browser

#### Issue: "JavaScript errors during upload"
**Solution**:
1. Open browser developer tools (F12)
2. Check console for errors
3. Disable browser extensions
4. Update your browser

## ⚙️ Processing Issues

### Analysis Stuck or Failing

#### Issue: "Report stuck in 'pending' status"
**Symptoms**: Reports never start processing
**Solution**:
```bash
# Check Celery workers
docker-compose logs celery-worker

# Restart Celery workers
docker-compose restart celery-worker

# Check Redis connection
docker-compose exec redis redis-cli ping
```

#### Issue: "Report fails with 'Invalid PCAP'"
**Symptoms**: Processing fails immediately
**Solution**:
1. Verify PCAP file integrity:
```bash
# Test with tcpdump
tcpdump -r yourfile.pcap -c 10

# Check file size
ls -lh yourfile.pcap
```

2. Try with a known good PCAP file
3. Check file permissions

#### Issue: "Processing takes too long"
**Symptoms**: Large files process very slowly
**Solution**:
```bash
# Check system resources
docker stats

# Increase worker memory
# Edit docker-compose.yml:
environment:
  - MEMORY_LIMIT=1g

# Add more workers
docker-compose up -d --scale celery-worker=4
```

### Memory Issues

#### Issue: "Out of memory errors"
**Symptoms**: Workers crash during processing
**Solution**:
```bash
# Monitor memory usage
docker stats --no-stream

# Increase Docker memory limits
# Edit /etc/docker/daemon.json:
{
  "default-runtime": "runc",
  "default-shm-size": "2G"
}

# Restart Docker
sudo systemctl restart docker
```

## 🐌 Performance Problems

### Slow Upload Speed

#### Issue: "Uploads are very slow"
**Solution**:
1. Check network bandwidth
2. Test with smaller files first
3. Use wired connection instead of WiFi
4. Check server location/latency

### Slow Processing

#### Issue: "Analysis takes too long"
**Solution**:
```bash
# Check CPU usage
top
htop

# Add more processing workers
docker-compose up -d --scale celery-worker=6

# Optimize for large files
# Edit backend/.env:
CHUNK_SIZE=2097152  # 2MB chunks
MAX_WORKERS=8
```

### Database Performance

#### Issue: "Slow report retrieval"
**Solution**:
```bash
# Check MongoDB performance
docker-compose exec mongodb mongo --eval "db.stats()"

# Add database indexes (done automatically)
# Monitor database logs
docker-compose logs mongodb
```

## 🌐 Network and Connectivity

### API Connection Issues

#### Issue: "Cannot connect to backend API"
**Symptoms**: Frontend shows connection errors
**Solution**:
```bash
# Test API directly
curl http://localhost:8000/api/health

# Check backend logs
docker-compose logs backend

# Verify network connectivity
docker network ls
docker network inspect pcap-reporter_default
```

#### Issue: "CORS errors in browser"
**Symptoms**: Browser blocks API requests
**Solution**:
```bash
# Update CORS settings in backend/.env
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# Restart backend
docker-compose restart backend
```

### WebSocket Issues

#### Issue: "Real-time updates not working"
**Symptoms**: No progress updates during processing
**Solution**:
```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/ws

# Check proxy configuration
# In nginx.conf:
location /ws {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 🌍 Browser Issues

### Compatibility Problems

#### Issue: "Interface not loading properly"
**Solution**:
1. Use supported browsers:
   - Chrome 90+
   - Firefox 88+
   - Safari 14+
   - Edge 90+

2. Clear browser cache and cookies
3. Disable browser extensions
4. Check JavaScript is enabled

#### Issue: "File drag and drop not working"
**Solution**:
1. Use file picker button instead
2. Check browser permissions
3. Try different browser
4. Ensure JavaScript is enabled

## 🐳 Docker and Container Issues

### Container Startup Problems

#### Issue: "Services won't start"
**Solution**:
```bash
# Check Docker daemon
sudo systemctl status docker

# View detailed logs
docker-compose logs --follow

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Issue: "Container keeps restarting"
**Solution**:
```bash
# Check container logs
docker-compose logs [service-name]

# Check resource limits
docker stats

# Verify configuration
docker-compose config
```

### Volume and Storage Issues

#### Issue: "Data not persisting"
**Solution**:
```bash
# Check volume mounts
docker volume ls
docker volume inspect pcap-reporter_mongodb_data

# Fix permissions
sudo chown -R $USER:$USER ./uploads
sudo chmod 755 ./uploads
```

#### Issue: "Disk space errors"
**Solution**:
```bash
# Check disk usage
df -h
docker system df

# Clean up Docker
docker system prune -a
docker volume prune
```

## 🗄️ Database Problems

### MongoDB Connection Issues

#### Issue: "Cannot connect to database"
**Solution**:
```bash
# Check MongoDB status
docker-compose logs mongodb

# Test connection
docker-compose exec mongodb mongo --eval "db.runCommand('ping')"

# Reset database
docker-compose down
docker volume rm pcap-reporter_mongodb_data
docker-compose up -d mongodb
```

#### Issue: "Database authentication failed"
**Solution**:
```bash
# Check credentials in .env
MONGODB_USERNAME=pcap_user
MONGODB_PASSWORD=your_password

# Recreate database user
docker-compose exec mongodb mongo -u admin -p admin_password
```

### Redis Connection Issues

#### Issue: "Redis connection failed"
**Solution**:
```bash
# Check Redis status
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis configuration
docker-compose exec redis redis-cli config get "*"
```

## 📊 Monitoring and Logging

### Log Analysis

#### Viewing Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs celery-worker

# Follow logs in real-time
docker-compose logs -f backend

# Last N lines
docker-compose logs --tail=100 backend
```

#### Log Levels
```bash
# Enable debug logging
# In backend/.env:
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart backend celery-worker
```

### Performance Monitoring

#### Resource Usage
```bash
# Container resource usage
docker stats

# System resource usage
htop
iotop
nethogs
```

#### Application Metrics
```bash
# Check processing queue
docker-compose exec redis redis-cli llen celery

# Monitor database connections
docker-compose exec mongodb mongo --eval "db.serverStatus().connections"
```

## 🆘 Getting Additional Help

### Collecting Diagnostic Information

Before seeking help, collect this information:

```bash
# System information
uname -a
docker --version
docker-compose --version

# Service status
docker-compose ps
curl -s http://localhost:8000/api/health | jq

# Recent logs
docker-compose logs --tail=100 > logs.txt

# Configuration
docker-compose config > config.yml
```

### Support Channels

1. **Documentation**: Check [FAQ](faq.md) and [User Guide](user-guide.md)
2. **GitHub Issues**: Report bugs at [GitHub Repository](https://github.com/your-org/pcap-reporter/issues)
3. **Discussions**: Ask questions at [GitHub Discussions](https://github.com/your-org/pcap-reporter/discussions)
4. **System Administrator**: Contact your local system administrator

### Creating Bug Reports

When reporting issues, include:

1. **Environment Details**:
   - Operating system and version
   - Docker and Docker Compose versions
   - Browser type and version (for frontend issues)

2. **Problem Description**:
   - What you were trying to do
   - What happened instead
   - Steps to reproduce the issue

3. **Error Information**:
   - Error messages (exact text)
   - Log files (relevant portions)
   - Screenshots (if applicable)

4. **Configuration**:
   - Environment variables (remove sensitive data)
   - Docker Compose configuration
   - Any customizations made

### Emergency Procedures

#### Complete System Reset
```bash
# Stop all services
docker-compose down

# Remove all data (WARNING: This deletes all reports!)
docker volume rm pcap-reporter_mongodb_data
docker volume rm pcap-reporter_redis_data

# Remove containers and images
docker-compose down --rmi all

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

#### Backup Before Reset
```bash
# Backup database
docker-compose exec mongodb mongodump --out /tmp/backup

# Copy backup out of container
docker cp $(docker-compose ps -q mongodb):/tmp/backup ./mongodb_backup

# Backup uploads
cp -r ./uploads ./uploads_backup
```

---

*Still having issues? Check our [FAQ](faq.md) or reach out for [support](#getting-additional-help)* 