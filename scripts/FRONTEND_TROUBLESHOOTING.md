# Frontend Troubleshooting Guide

## Quick Commands

```bash
# Check frontend status
./scripts/pcap-reporter.sh status

# Run automated frontend diagnostics and fixes
./scripts/pcap-reporter.sh fix-frontend

# Detailed frontend diagnostics
./scripts/frontend-diagnostics.sh

# View frontend logs
./scripts/pcap-reporter.sh logs --service frontend --follow
```

## Common Issues and Solutions

### 1. Container Won't Start
**Symptoms:**
- Container status shows "Exited"
- Error: "Frontend container not found"

**Solutions:**
```bash
# Restart the container
./scripts/pcap-reporter.sh restart

# If that fails, rebuild
docker-compose stop frontend
docker-compose rm -f frontend
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### 2. Missing Dependencies
**Symptoms:**
- Error: "ENOENT: no such file or directory, open 'node_modules'"
- Error: "Module not found"

**Solutions:**
```bash
# Install dependencies
docker-compose exec frontend npm install

# Or rebuild with fresh dependencies
./scripts/pcap-reporter.sh fix-frontend
```

### 3. Port Conflicts
**Symptoms:**
- Error: "EADDRINUSE: address already in use :::3000"
- Error: "Port 3000 is already in use"

**Solutions:**
```bash
# Kill processes using port 3000
lsof -ti:3000 | xargs kill -9

# Or let the script handle it
./scripts/pcap-reporter.sh fix-frontend
```

### 4. Permission Issues
**Symptoms:**
- Error: "permission denied"
- Error: "EACCES: permission denied"

**Solutions:**
```bash
# Fix permissions manually
sudo chown -R $USER:$USER ./frontend

# Or use the fix script
./scripts/pcap-reporter.sh fix-frontend
```

### 5. Backend Connection Issues
**Symptoms:**
- Error: "ECONNREFUSED: Connection refused to backend"
- Frontend loads but API calls fail

**Solutions:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Restart backend if needed
docker-compose restart api

# Or run comprehensive fix
./scripts/pcap-reporter.sh fix-frontend
```

### 6. Compilation Errors
**Symptoms:**
- Error: "Failed to compile"
- Error: "Webpack compilation failed"

**Solutions:**
```bash
# Clear cache and rebuild
docker-compose exec frontend npm cache clean --force
docker-compose exec frontend rm -rf .next
docker-compose restart frontend

# Or use automated fix
./scripts/pcap-reporter.sh fix-frontend
```

## Automated Remediation

The enhanced startup script includes automatic detection and remediation for:

- ✅ Container status issues
- ✅ Missing node_modules
- ✅ Port conflicts
- ✅ Permission problems
- ✅ NPM errors
- ✅ Backend connectivity issues
- ✅ Low disk space
- ✅ Memory issues

### Usage:
```bash
# Run automatic diagnostics and fixes
./scripts/pcap-reporter.sh fix-frontend

# Start services with automatic frontend health checking
./scripts/pcap-reporter.sh start
```

## Manual Recovery Steps

If automated remediation fails:

### 1. Complete Container Reset
```bash
# Stop and remove containers
docker-compose stop frontend
docker-compose rm -f frontend

# Remove volumes
docker volume rm $(docker volume ls -q | grep frontend) 2>/dev/null || true

# Rebuild from scratch
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### 2. Clean System Reset
```bash
# Clean Docker system
docker system prune -f

# Clean project files
rm -rf frontend/node_modules
rm -rf frontend/.next
rm -rf frontend/package-lock.json

# Rebuild everything
./scripts/pcap-reporter.sh stop --cleanup
./scripts/pcap-reporter.sh start
```

### 3. Host System Issues
```bash
# Check available disk space
df -h

# Check memory usage
free -h

# Check port usage
netstat -tlnp | grep 3000

# Check Docker daemon
docker info
```

## Monitoring and Logs

### View Real-time Logs
```bash
# Follow frontend logs
./scripts/pcap-reporter.sh logs --service frontend --follow

# View container stats
docker stats pcap-reporter-frontend
```

### Health Checks
```bash
# Quick health check
curl -s http://localhost:3000/health

# Comprehensive status
./scripts/pcap-reporter.sh status

# Detailed diagnostics
./scripts/frontend-diagnostics.sh
```

## Prevention Tips

1. **Regular Updates**: Keep dependencies updated
2. **Monitoring**: Use `./scripts/pcap-reporter.sh status` regularly
3. **Cleanup**: Run `docker system prune -f` periodically
4. **Logs**: Monitor logs for early warning signs
5. **Resources**: Ensure adequate disk space and memory

## Emergency Contacts

If issues persist:
1. Check the project's GitHub issues
2. Review Docker and Node.js documentation
3. Consult the development team
4. Run full system diagnostics: `./scripts/frontend-diagnostics.sh`

---

**Last Updated**: 2025-07-15
**Version**: 1.0.0