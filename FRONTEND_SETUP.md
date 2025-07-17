# Frontend Setup - PCAP Reporter

## ✅ **FRONTEND ISSUE RESOLVED**

The frontend service was failing to start properly due to Docker build issues. The solution implemented provides a reliable way to run the frontend service.

## 🚀 **Current Status**

- **✅ Frontend Application**: Built and ready to run
- **✅ Health Endpoint**: Available at `http://localhost:3000/health`
- **✅ Next.js Server**: Configured for standalone operation
- **✅ Management Scripts**: Available for easy control

## 🔧 **Quick Start**

### Start Frontend Server
```bash
./scripts/start-frontend.sh start
```

### Check Frontend Status
```bash
./scripts/start-frontend.sh status
```

### Stop Frontend Server
```bash
./scripts/start-frontend.sh stop
```

## 📋 **Available Commands**

| Command | Description |
|---------|-------------|
| `install` | Install frontend dependencies |
| `build` | Build the frontend application |
| `start` | Start the frontend server |
| `stop` | Stop the frontend server |
| `restart` | Restart the frontend server |
| `status` | Check frontend server status |

## 🌐 **Access URLs**

- **Frontend Application**: http://localhost:3000
- **Frontend Health Check**: http://localhost:3000/health
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health

## 🔍 **Health Check Response**

When working properly, the frontend health endpoint returns:
```json
{
  "status": "healthy",
  "service": "pcap-reporter-frontend",
  "timestamp": "2025-07-14T17:41:46.056Z",
  "uptime": 8.107506397,
  "environment": "production",
  "version": "0.1.0",
  "checks": {
    "server": "ok",
    "memory": {
      "used": 14,
      "total": 21,
      "external": 3,
      "rss": 69
    },
    "backend": {
      "status": "healthy",
      "responseTime": 7,
      "lastCheck": "2025-07-14T17:41:46.063Z"
    }
  },
  "performance": {
    "responseTime": 7,
    "memoryUsagePercent": 64
  }
}
```

## 🛠️ **Technical Details**

### Build Process
The frontend is built using Next.js with standalone output:
- **Framework**: Next.js 14.0.4
- **Build Target**: Standalone server
- **Dependencies**: Ant Design, React, TypeScript
- **Build Output**: `.next/standalone/` directory

### Server Configuration
- **Runtime**: Node.js 18+
- **Port**: 3000
- **Environment**: Production
- **Health Check**: Built-in endpoint at `/health`

## 🔧 **Troubleshooting**

### Frontend Not Starting
1. Check if Node.js is installed: `node --version`
2. Install dependencies: `./scripts/start-frontend.sh install`
3. Build the application: `./scripts/start-frontend.sh build`
4. Start the server: `./scripts/start-frontend.sh start`

### Health Check Failing
1. Check if server is running: `./scripts/start-frontend.sh status`
2. Check server logs: `journalctl -f` or check terminal output
3. Verify backend connectivity: `curl http://localhost:8000/health`

### Port Already in Use
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Restart frontend
./scripts/start-frontend.sh restart
```

## 🔗 **Integration with Main Services**

The frontend integrates with the main PCAP Reporter services:
- **API Communication**: Configured to communicate with backend at `http://localhost:8000`
- **Health Monitoring**: Included in main status checks via `./scripts/pcap-reporter.sh status`
- **Service Management**: Separate from Docker services for reliability

## 📝 **Notes**

- The frontend runs as a standalone Node.js server (not in Docker)
- This approach avoids Docker build issues while maintaining full functionality
- The server automatically checks backend connectivity during health checks
- All UI features are functional including upload, analysis, and reporting

## 🎯 **Next Steps**

1. **Access the Application**: Visit http://localhost:3000
2. **Upload PCAP Files**: Use the upload interface
3. **View Analysis Results**: Check the reports section
4. **Monitor System Health**: Use the built-in health endpoints

The frontend is now fully operational and ready for use with the PCAP Reporter system.