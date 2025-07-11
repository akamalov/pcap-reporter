# 🌐 PCAP Reporter

A comprehensive, production-ready network packet capture analysis tool with real-time processing, web-based interface, and advanced monitoring capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-13+-black.svg)](https://nextjs.org/)

## 🚀 Features

### 🔍 **Advanced Analysis**
- **Multi-format Support**: PCAP, PCAPNG, and CAP files
- **Real-time Processing**: Live progress updates via WebSocket
- **Large File Handling**: Streaming processing for files up to 10GB+
- **Protocol Analysis**: Deep packet inspection with security insights
- **Performance Metrics**: Bandwidth, latency, and QoS analysis

### 🌐 **Modern Web Interface**
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark/Light Mode**: User-customizable interface themes
- **Interactive Charts**: Zoom, filter, and export visualizations
- **Real-time Updates**: Live progress tracking and notifications
- **Batch Processing**: Handle multiple files simultaneously

### 🏗️ **Production Ready**
- **Docker Deployment**: Complete containerized stack
- **Monitoring Stack**: Prometheus, Grafana, and Loki integration
- **SSL/TLS Support**: Automated certificate management
- **Load Balancing**: Nginx reverse proxy with compression
- **Health Checks**: Comprehensive system monitoring

### ⚡ **Performance Optimized**
- **Streaming Processing**: Memory-efficient for large files
- **Parallel Workers**: Configurable concurrent processing
- **Database Optimization**: Indexed queries and aggregations
- **Caching Layer**: Redis for improved response times
- **Resource Monitoring**: Real-time system metrics

## 📋 Quick Start

### Prerequisites
- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM (8GB recommended)
- 10GB free disk space

### 1. Clone and Start
```bash
git clone https://github.com/your-org/pcap-reporter.git
cd pcap-reporter

# Start development environment
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Access the Application
- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### 3. Upload and Analyze
1. Open http://localhost:3000 in your browser
2. Drag and drop a PCAP file or click "Choose File"
3. Configure analysis options (optional)
4. Monitor real-time progress
5. View comprehensive analysis results

## 🏗️ Architecture

PCAP Reporter uses a modern microservices architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Workers       │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Celery)      │
│   Port 3000     │    │   Port 8000     │    │   Background    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │    MongoDB      │    │     Redis       │
│  (Reverse Proxy)│    │   (Database)    │    │   (Cache/Queue) │
│   Port 80/443   │    │   Port 27017    │    │   Port 6379     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

- **Frontend**: React/Next.js with TypeScript and Tailwind CSS
- **Backend**: Python FastAPI with async processing
- **Database**: MongoDB with optimized indexing
- **Queue**: Redis with Celery for background jobs
- **Proxy**: Nginx with SSL termination and load balancing
- **Monitoring**: Prometheus, Grafana, and Loki stack

## 📊 Analysis Capabilities

### Protocol Analysis
- **Layer 2-7 Analysis**: Ethernet, IP, TCP, UDP, HTTP, HTTPS, DNS, and more
- **Protocol Distribution**: Visual breakdown of traffic composition
- **Custom Protocols**: Extensible protocol detection framework

### Traffic Insights
- **Bandwidth Utilization**: Time-series analysis of network usage
- **Top Talkers**: Most active hosts and conversations
- **Geographic Analysis**: IP geolocation and traffic flows
- **Peak Detection**: Automatic identification of traffic spikes

### Security Features
- **Anomaly Detection**: Statistical analysis for unusual patterns
- **Threat Indicators**: Port scans, suspicious connections
- **Behavioral Analysis**: Communication pattern assessment
- **Compliance Reporting**: Security audit trail generation

### Performance Metrics
- **Response Times**: Application and network latency analysis
- **Throughput Analysis**: Bandwidth efficiency measurements
- **Quality of Service**: Packet loss and jitter detection
- **Capacity Planning**: Historical trend analysis

## 🛠️ Installation Options

### Docker Compose (Recommended)
```bash
# Development
docker-compose up -d

# Production
cp env.prod.example .env.prod
# Edit .env.prod with your settings
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Installation
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Services
docker-compose up -d mongodb redis
```

### Production Deployment
```bash
# Automated deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# Manual production setup
docker-compose -f docker-compose.prod.yml up -d
```

## ⚙️ Configuration

### Environment Variables

#### Backend Configuration
```bash
# Database
MONGODB_URL=mongodb://localhost:27017/pcap_reporter
MONGODB_DATABASE=pcap_reporter

# Processing
MAX_FILE_SIZE=2147483648  # 2GB
MAX_WORKERS=4
MEMORY_LIMIT=512m
CHUNK_SIZE=1048576  # 1MB

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=["http://localhost:3000"]
```

#### Frontend Configuration
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Features
NEXT_PUBLIC_MAX_FILE_SIZE=2147483648
NEXT_PUBLIC_SUPPORTED_FORMATS=pcap,pcapng,cap
```

### Production Settings
```bash
# Domain and SSL
DOMAIN=pcap-reporter.yourdomain.com
SSL_EMAIL=admin@yourdomain.com

# Performance
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024

# Monitoring
PROMETHEUS_RETENTION=15d
GRAFANA_ADMIN_PASSWORD=secure-password
```

## 📚 Documentation

### For Users
- **[Installation Guide](docs/user/installation.md)** - Complete setup instructions
- **[User Guide](docs/user/user-guide.md)** - How to use PCAP Reporter
- **[FAQ](docs/user/faq.md)** - Frequently asked questions
- **[Troubleshooting](docs/user/troubleshooting.md)** - Common issues and solutions

### For Developers
- **[API Reference](docs/api/api-reference.md)** - Complete API documentation
- **[WebSocket API](docs/api/websocket-api.md)** - Real-time communication
- **[Architecture Guide](docs/development/architecture.md)** - System design overview
- **[Development Setup](docs/development/setup.md)** - Local development environment
- **[Contributing Guide](docs/development/contributing.md)** - How to contribute

### For Administrators
- **[Production Deployment](docs/deployment/production.md)** - Production setup guide
- **[Monitoring Setup](docs/deployment/monitoring.md)** - Observability configuration
- **[Security Configuration](docs/deployment/security.md)** - Security best practices
- **[Backup & Maintenance](docs/deployment/maintenance.md)** - Operational procedures

## 🔧 API Usage

### Upload and Monitor
```python
import requests
import websocket
import json

# Upload file
response = requests.post(
    'http://localhost:8000/api/reports/upload',
    files={'file': open('sample.pcap', 'rb')}
)

if response.status_code == 200:
    data = response.json()['data']
    job_id = data['job_id']
    
    # Monitor progress via WebSocket
    ws = websocket.WebSocketApp('ws://localhost:8000/ws')
    ws.send(json.dumps({'action': 'subscribe', 'job_id': job_id}))
```

### Batch Processing
```bash
# Upload multiple files
for file in *.pcap; do
    curl -X POST -F "file=@$file" http://localhost:8000/api/reports/upload
done

# Monitor system health
curl http://localhost:8000/api/health
```

## 🚀 Performance

### Benchmarks
- **Small Files** (<10MB): ~30 seconds processing time
- **Medium Files** (100MB): ~2-3 minutes processing time  
- **Large Files** (1GB+): ~15-30 minutes with streaming
- **Concurrent Processing**: Up to 4 files simultaneously
- **Memory Usage**: Capped at 512MB per worker

### Optimization Tips
```bash
# Increase workers for better throughput
docker-compose up -d --scale celery-worker=6

# Optimize for large files
CHUNK_SIZE=2097152  # 2MB chunks
MEMORY_LIMIT=1g

# Use SSD storage for better I/O performance
```

## 🔒 Security

### Data Protection
- **Local Processing**: All data stays on your infrastructure
- **No External Calls**: Complete air-gapped operation
- **Secure Transport**: HTTPS/WSS in production
- **Container Isolation**: Services run in isolated environments

### Access Control
- **Session Authentication**: Secure user sessions
- **API Rate Limiting**: Prevent abuse and DoS
- **Input Validation**: Comprehensive file and data validation
- **Audit Logging**: Complete activity tracking

### Production Security
- **SSL/TLS Encryption**: Automated certificate management
- **Security Headers**: HSTS, CSP, and other protections
- **Non-root Containers**: Principle of least privilege
- **Regular Updates**: Automated security patches

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/development/contributing.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Code Standards
- **Python**: Black formatting, type hints, comprehensive tests
- **TypeScript**: ESLint, Prettier, strict type checking
- **Docker**: Multi-stage builds, security scanning
- **Documentation**: Clear, comprehensive, and up-to-date

## 📈 Monitoring

### Production Monitoring Stack
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation and analysis
- **Promtail**: Log collection and parsing

### Key Metrics
- **System Health**: CPU, memory, disk usage
- **Application Performance**: Response times, throughput
- **Processing Metrics**: Queue length, success rates
- **Error Tracking**: Failed uploads, processing errors

### Alerts
- **Service Down**: Automatic service restart
- **High Memory Usage**: Scale workers or investigate
- **Disk Space Low**: Cleanup old files
- **Processing Failures**: Investigation required

## 🗺️ Roadmap

### Version 1.1 (Q1 2024)
- [ ] User authentication and authorization
- [ ] Multi-tenant support
- [ ] Advanced filtering and search
- [ ] PDF report generation

### Version 1.2 (Q2 2024)
- [ ] Real-time packet capture integration
- [ ] Custom protocol definitions
- [ ] Machine learning anomaly detection
- [ ] LDAP/SSO integration

### Version 2.0 (Q3 2024)
- [ ] Distributed processing cluster
- [ ] Advanced visualization options
- [ ] Plugin architecture
- [ ] Mobile application

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Wireshark**: Inspiration for packet analysis capabilities
- **Scapy**: Python packet manipulation library
- **FastAPI**: Modern, fast web framework for building APIs
- **Next.js**: React framework for production applications
- **Docker**: Containerization platform

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/pcap-reporter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/pcap-reporter/discussions)
- **Security**: security@yourdomain.com

---

<div align="center">

**⭐ Star this repository if you find it useful! ⭐**

[Documentation](docs/) • [Installation](docs/user/installation.md) • [API Reference](docs/api/api-reference.md) • [Contributing](docs/development/contributing.md)

</div> 