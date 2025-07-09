# PCAP Reporter

A comprehensive MCP (Model Context Protocol) server for network packet capture analysis and reporting. This tool ingests PCAP files and produces detailed network analysis reports with modern web interface.

## 🚀 Features

- **Hybrid Analysis Engine**: Combines tshark and Scapy for comprehensive PCAP analysis
- **Asynchronous Processing**: Celery-based task queue for handling large PCAP files
- **Modern Web Interface**: React/Next.js frontend with real-time progress tracking
- **MCP Server Integration**: Exposes analysis capabilities via Model Context Protocol
- **Comprehensive Reports**: Network statistics, protocol analysis, security insights
- **Docker Deployment**: Fully containerized with production-ready configuration

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- At least 4GB RAM (recommended 8GB for large PCAP files)

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd pcap-reporter
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Database
MONGODB_USERNAME=pcap_user
MONGODB_PASSWORD=your_secure_password
MONGODB_DATABASE=pcap_reporter

# Redis
REDIS_PASSWORD=your_redis_password

# API
API_SECRET_KEY=your_very_secure_secret_key_here
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access the Application

- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Celery Monitoring**: http://localhost:5555
- **Health Check**: http://localhost:8000/health

## 🧪 Testing the Setup

Before deploying, you can test the backend setup:

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies (optional for testing)
pip install -r requirements.txt

# Run basic tests
python test_basic.py
```

## 📁 Project Structure

```
pcap-reporter/
├── backend/                 # FastAPI backend
│   ├── api/                # API endpoints
│   ├── core/               # Core configuration
│   ├── models/             # Data models
│   ├── services/           # Business logic
│   ├── tasks/              # Celery tasks
│   ├── main.py             # FastAPI app
│   └── mcp_server.py       # MCP server
├── frontend/               # Next.js frontend
│   ├── src/                # Source code
│   └── public/             # Static assets
├── nginx/                  # Nginx configuration
├── scripts/                # Utility scripts
├── tests/                  # Test files
└── docs/                   # Documentation
```

## 🔧 Development

### Backend Development

```bash
# Start backend services only
docker-compose up -d mongodb redis

# Run backend locally
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A core.celery_app worker --loglevel=info

# Run Celery beat (scheduler)
celery -A core.celery_app beat --loglevel=info
```

### Frontend Development

```bash
# Start backend services
docker-compose up -d api mongodb redis celery-worker

# Run frontend locally
cd frontend
npm install
npm run dev
```

### MCP Server

The MCP server can be used independently:

```bash
cd backend
python mcp_server.py
```

## 📊 Usage

### Via Web Interface

1. Navigate to http://localhost:3000
2. Upload a PCAP file
3. Monitor analysis progress
4. View comprehensive reports

### Via API

```bash
# Upload PCAP file
curl -X POST "http://localhost:8000/api/v1/analysis/upload" \
     -F "file=@sample.pcap"

# Check analysis status
curl "http://localhost:8000/api/v1/analysis/status/{job_id}"

# Get analysis report
curl "http://localhost:8000/api/v1/reports/{report_id}"
```

### Via MCP Protocol

The MCP server exposes tools for:
- `upload_pcap`: Upload and analyze PCAP files
- `get_analysis_status`: Check analysis progress
- `get_report`: Retrieve analysis reports
- `list_reports`: List all available reports

## 🔍 Analysis Features

### Network Statistics
- Packet counts and sizes
- Protocol distribution
- Traffic patterns
- Bandwidth utilization

### Protocol Analysis
- HTTP/HTTPS traffic analysis
- DNS query analysis
- TCP connection tracking
- UDP traffic patterns

### Security Insights
- Suspicious traffic detection
- Port scanning identification
- Protocol anomalies
- Potential security threats

### Performance Metrics
- Response times
- Connection patterns
- Throughput analysis
- Network efficiency

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80, 443 | Reverse proxy and load balancer |
| api | 8000 | FastAPI backend |
| frontend | 3000 | Next.js frontend |
| mongodb | 27017 | Database |
| redis | 6379 | Cache and message broker |
| celery-worker | - | Background task processor |
| celery-beat | - | Task scheduler |
| flower | 5555 | Celery monitoring |

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

### MongoDB Collections

- `reports`: Analysis reports and metadata
- `analysis_jobs`: Celery job tracking
- `users`: User management (future feature)

### Celery Queues

- `analysis`: PCAP analysis tasks
- `reports`: Report generation tasks
- `cleanup`: Maintenance tasks

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 8000, 5555 are available
2. **Memory issues**: Large PCAP files require adequate RAM
3. **Permission errors**: Check Docker permissions and file ownership

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs celery-worker

# Follow logs in real-time
docker-compose logs -f
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Detailed system health
curl http://localhost:8000/health/detailed

# Database health
curl http://localhost:8000/health/database
```

## 📈 Monitoring

- **Celery Tasks**: http://localhost:5555
- **API Metrics**: http://localhost:8000/health/detailed
- **Container Stats**: `docker stats`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Create an issue with detailed information

## 🚀 Roadmap

- [ ] Real-time PCAP analysis
- [ ] Advanced ML-based anomaly detection
- [ ] PCAP anonymization features
- [ ] Multi-tenant support
- [ ] Advanced visualization dashboards
- [ ] Integration with SIEM systems 