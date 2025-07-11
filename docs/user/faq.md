# PCAP Reporter FAQ

Frequently asked questions about PCAP Reporter installation, usage, and troubleshooting.

## 📋 Table of Contents

1. [General Questions](#general-questions)
2. [Installation and Setup](#installation-and-setup)
3. [File Upload and Processing](#file-upload-and-processing)
4. [Features and Capabilities](#features-and-capabilities)
5. [Performance and Limitations](#performance-and-limitations)
6. [Security and Privacy](#security-and-privacy)
7. [Troubleshooting](#troubleshooting)
8. [Development and Customization](#development-and-customization)

## 🌟 General Questions

### What is PCAP Reporter?

PCAP Reporter is a comprehensive web-based network packet capture analysis tool that provides:
- Real-time analysis of PCAP files
- Interactive web interface
- Advanced protocol analysis
- Security insights and anomaly detection
- Performance metrics and visualization
- Production-ready deployment with monitoring

### What file formats are supported?

PCAP Reporter supports these network capture formats:
- `.pcap` - Standard PCAP format
- `.pcapng` - Next Generation PCAP format  
- `.cap` - Alternative PCAP extension

### Is PCAP Reporter free to use?

Yes, PCAP Reporter is open-source software released under the MIT License. You can use, modify, and distribute it freely.

### How does PCAP Reporter compare to Wireshark?

| Feature | PCAP Reporter | Wireshark |
|---------|---------------|-----------|
| Interface | Web-based | Desktop application |
| Real-time Analysis | ✅ | ✅ |
| Batch Processing | ✅ | Limited |
| Remote Access | ✅ | ❌ |
| Automated Reports | ✅ | ❌ |
| Multi-user Support | ✅ | ❌ |
| Large File Handling | ✅ (streaming) | Limited |

## 🚀 Installation and Setup

### What are the system requirements?

**Minimum Requirements:**
- CPU: 2 cores, 2.0 GHz
- RAM: 4GB (8GB recommended)
- Storage: 10GB free space
- Docker 20.10+ and Docker Compose 2.0+

**Supported Operating Systems:**
- Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- macOS (10.15+)
- Windows 10/11 with WSL2

### Can I install PCAP Reporter without Docker?

While Docker is the recommended installation method, you can install components manually:
- Backend: Python 3.9+ with FastAPI
- Frontend: Node.js 16+ with Next.js
- Database: MongoDB 5.0+
- Cache: Redis 6.0+
- Queue: Celery with Redis broker

See the [Development Installation](../user/installation.md#development-installation) guide for details.

### How do I update PCAP Reporter?

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check health
curl http://localhost:8000/api/health
```

### Can I run PCAP Reporter on a different port?

Yes, edit the `docker-compose.yml` file:

```yaml
services:
  frontend:
    ports:
      - "8080:3000"  # Change from 3000:3000
  
  backend:
    ports:
      - "8001:8000"  # Change from 8000:8000
```

## 📁 File Upload and Processing

### What's the maximum file size I can upload?

The default maximum file size is **2GB**. You can increase this by:

1. Editing `nginx/nginx.conf`:
```nginx
client_max_body_size 4G;
```

2. Updating backend settings in `.env`:
```bash
MAX_FILE_SIZE=4294967296  # 4GB in bytes
```

### How long does analysis take?

Processing time depends on several factors:
- **File size**: ~1-2 minutes per 100MB
- **Analysis depth**: Basic vs. deep inspection
- **System resources**: CPU, memory, and disk speed
- **File complexity**: Number of protocols and connections

Large files (>100MB) use streaming processing for better performance.

### Can I analyze multiple files simultaneously?

Yes! PCAP Reporter supports concurrent processing:
- Upload multiple files through the web interface
- Each file is processed independently
- Monitor progress in real-time
- Default: 2-4 concurrent workers (configurable)

### Why is my report stuck in "pending" status?

Common causes and solutions:

1. **No Celery workers running**:
```bash
docker-compose logs celery-worker
docker-compose restart celery-worker
```

2. **Redis connection issues**:
```bash
docker-compose logs redis
docker-compose restart redis
```

3. **System resource exhaustion**:
```bash
docker stats
# Add more workers or increase memory
```

### Can I cancel a running analysis?

Currently, there's no cancel feature in the UI, but you can:

1. **Delete the report** (stops processing)
2. **Restart Celery workers**:
```bash
docker-compose restart celery-worker
```

This feature is planned for future releases.

## ⚙️ Features and Capabilities

### What analysis features are available?

**Protocol Analysis:**
- Protocol distribution and statistics
- Layer 2-7 protocol breakdown
- Custom protocol detection

**Traffic Analysis:**
- Bandwidth utilization over time
- Peak traffic periods
- Connection patterns

**Security Analysis:**
- Anomaly detection
- Suspicious traffic patterns
- Port scanning detection

**Performance Metrics:**
- Response times and latency
- Throughput measurements
- Quality of service indicators

### Can I customize analysis options?

Yes, when uploading files you can configure:
- **Analysis depth**: Basic, standard, or deep inspection
- **Security analysis**: Enable/disable security checks
- **Time range filtering**: Analyze specific time periods
- **Protocol filtering**: Focus on specific protocols

### Does PCAP Reporter support real-time monitoring?

PCAP Reporter provides real-time features for analysis:
- **Live progress updates** during processing
- **WebSocket-based notifications**
- **Real-time status monitoring**

For live network monitoring, consider integrating with tools like:
- tcpdump for live capture
- Network taps or SPAN ports
- Continuous file ingestion workflows

### Can I export analysis results?

Yes, reports can be exported in multiple formats:
- **JSON**: Complete data export
- **CSV**: Tabular data for spreadsheets
- **PDF**: Formatted reports (planned feature)

Access via API:
```bash
curl "http://localhost:8000/api/reports/{report_id}/download?format=json"
```

## 🚀 Performance and Limitations

### How much memory does PCAP Reporter use?

Memory usage depends on file size and analysis depth:
- **Backend**: 256MB-1GB per worker
- **Database**: 128MB-512MB base + data storage
- **Frontend**: 64MB-128MB
- **Total system**: 2GB-4GB recommended for normal operation

Large files use streaming to limit memory usage to ~512MB per worker.

### Can PCAP Reporter handle very large files?

Yes, with optimizations for large files:
- **Streaming processing**: Files >100MB processed in chunks
- **Parallel processing**: Multiple workers for different file segments
- **Memory limits**: Capped at 512MB per worker
- **Progress tracking**: Real-time updates for long operations

Successfully tested with files up to 10GB+.

### What are the current limitations?

**File Processing:**
- Maximum file size: 2GB (configurable to 10GB+)
- Concurrent uploads: Limited by system resources
- Processing time: Proportional to file size and complexity

**Analysis Features:**
- No real-time packet capture (file-based only)
- Limited custom protocol definitions
- No packet modification or replay

**User Interface:**
- Single-user sessions (multi-user planned)
- No collaborative features
- Limited customization options

### How can I improve performance?

**System Level:**
```bash
# Add more Celery workers
docker-compose up -d --scale celery-worker=6

# Increase memory limits
# Edit docker-compose.yml:
environment:
  - MEMORY_LIMIT=1g

# Use SSD storage for better I/O
# Mount uploads on fast storage
```

**Configuration:**
```bash
# Optimize chunk size for your system
CHUNK_SIZE=2097152  # 2MB chunks

# Increase worker processes
MAX_WORKERS=8

# Enable parallel processing
PARALLEL_PROCESSING=true
```

## 🔒 Security and Privacy

### Is my data secure?

PCAP Reporter implements several security measures:
- **Local processing**: Data stays on your infrastructure
- **No external transmission**: Files processed locally
- **Secure connections**: HTTPS/WSS in production
- **Container isolation**: Services run in isolated containers

### Can I use PCAP Reporter in a secure environment?

Yes, PCAP Reporter is designed for secure environments:
- **Air-gapped deployment**: No external dependencies
- **On-premises installation**: Complete local control
- **Security hardening**: Production configuration includes security measures
- **Audit logging**: Comprehensive activity logging

### How is sensitive data handled?

**Data Processing:**
- PCAP files processed in memory or temporary storage
- No permanent storage of packet contents
- Configurable data retention policies

**Analysis Results:**
- Only metadata and statistics stored
- No raw packet data in reports
- Configurable report retention

**Access Control:**
- Session-based authentication
- API access controls (planned)
- Role-based permissions (planned)

### Can I integrate with enterprise security tools?

Yes, through several methods:
- **API integration**: RESTful API for automation
- **Log export**: JSON/CSV export for SIEM integration
- **Webhook notifications**: Real-time alerts (planned)
- **LDAP/SSO integration**: Enterprise authentication (planned)

## 🔧 Troubleshooting

### The web interface won't load. What should I check?

1. **Service status**:
```bash
docker-compose ps
```

2. **Frontend logs**:
```bash
docker-compose logs frontend
```

3. **Network connectivity**:
```bash
curl http://localhost:3000
curl http://localhost:8000/api/health
```

4. **Browser compatibility**: Use Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+

### Uploads fail with "File too large" error. How do I fix this?

1. **Check current limits**:
```bash
curl -I http://localhost:8000/api/health
```

2. **Increase nginx limits** in `nginx/nginx.conf`:
```nginx
client_max_body_size 4G;
```

3. **Update backend limits** in `.env`:
```bash
MAX_FILE_SIZE=4294967296  # 4GB
```

4. **Restart services**:
```bash
docker-compose restart nginx backend
```

### Reports show "Invalid PCAP file" error. What's wrong?

1. **Verify file integrity**:
```bash
tcpdump -r yourfile.pcap -c 1
file yourfile.pcap
```

2. **Check file format**: Ensure it's a valid PCAP/PCAPNG file

3. **Test with known good file**: Try a sample PCAP from the internet

4. **Check file permissions**: Ensure the file is readable

### How do I reset everything if something goes wrong?

**Complete reset** (WARNING: Deletes all data):
```bash
# Stop services
docker-compose down

# Remove data volumes
docker volume rm pcap-reporter_mongodb_data
docker volume rm pcap-reporter_redis_data

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

**Backup first**:
```bash
# Backup database
docker-compose exec mongodb mongodump --out /tmp/backup
docker cp $(docker-compose ps -q mongodb):/tmp/backup ./backup

# Backup uploads
cp -r ./uploads ./uploads_backup
```

## 🛠️ Development and Customization

### Can I modify PCAP Reporter for my needs?

Yes! PCAP Reporter is open-source:
- **Frontend**: React/Next.js for UI customization
- **Backend**: Python/FastAPI for analysis logic
- **Docker**: Easy deployment and scaling
- **MIT License**: Permissive for commercial use

See the [Development Setup](../development/setup.md) guide.

### How do I add custom analysis features?

1. **Backend analysis**: Add new analysis modules in `backend/services/`
2. **Frontend display**: Create new components in `frontend/components/`
3. **API endpoints**: Extend `backend/routers/` for new functionality
4. **Database models**: Update `backend/models/` for new data structures

### Can I integrate PCAP Reporter with other tools?

Yes, through several integration points:
- **REST API**: Programmatic access to all features
- **WebSocket API**: Real-time notifications
- **Database access**: Direct MongoDB integration
- **File system**: Direct access to uploads and results

### How do I contribute to PCAP Reporter?

1. **Fork the repository** on GitHub
2. **Create a feature branch** for your changes
3. **Follow coding standards** (see [Contributing Guide](../development/contributing.md))
4. **Add tests** for new functionality
5. **Submit a pull request** with detailed description

### Is commercial support available?

Currently, PCAP Reporter is community-supported through:
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community help
- **Documentation**: Comprehensive guides and references

Commercial support and consulting may be available through the maintainers.

---

*Don't see your question? Check the [Troubleshooting Guide](troubleshooting.md) or ask in [GitHub Discussions](https://github.com/your-org/pcap-reporter/discussions)* 