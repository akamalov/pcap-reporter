# PCAP Reporter Installation Guide

This guide provides step-by-step instructions for installing and setting up PCAP Reporter in different environments.

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start with Docker](#quick-start-with-docker)
3. [Development Installation](#development-installation)
4. [Production Installation](#production-installation)
5. [Configuration](#configuration)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

## 🖥️ System Requirements

### Minimum Requirements
- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 4GB (8GB recommended for large files)
- **Storage**: 10GB free space (more for PCAP storage)
- **Network**: Stable internet connection

### Software Requirements
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **Git**: For source code management

### Supported Operating Systems
- Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- macOS (10.15+)
- Windows 10/11 with WSL2

## 🚀 Quick Start with Docker

The fastest way to get PCAP Reporter running is using Docker Compose.

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/pcap-reporter.git
cd pcap-reporter
```

### Step 2: Start Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 3: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Step 4: Verify Installation

1. Open http://localhost:3000 in your browser
2. Upload a small PCAP file to test functionality
3. Check that the analysis completes successfully

## 🛠️ Development Installation

For development or customization, you can install components separately.

### Prerequisites

```bash
# Install Node.js (16+)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python (3.9+)
sudo apt-get install python3.9 python3.9-pip python3.9-venv

# Install Docker
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start backend services
docker-compose up -d mongodb redis

# Run database migrations
python -m alembic upgrade head

# Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev
```

### Celery Worker Setup

```bash
# In backend directory with virtual environment activated
celery -A core.celery_app worker --loglevel=info

# In another terminal, start Celery Beat (for scheduled tasks)
celery -A core.celery_app beat --loglevel=info
```

## 🏭 Production Installation

For production deployment, follow the comprehensive production guide.

### Step 1: Prepare Environment

```bash
# Clone repository
git clone https://github.com/your-org/pcap-reporter.git
cd pcap-reporter

# Copy production environment template
cp env.prod.example .env.prod
```

### Step 2: Configure Environment

Edit `.env.prod` with your production settings:

```bash
# Domain and SSL
DOMAIN=pcap-reporter.yourdomain.com
SSL_EMAIL=admin@yourdomain.com

# Security
SECRET_KEY=your-super-secret-key-here
MONGODB_PASSWORD=secure-mongodb-password
REDIS_PASSWORD=secure-redis-password

# Performance
MAX_WORKERS=4
MEMORY_LIMIT=512m
```

### Step 3: Deploy with Script

```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Run production deployment
./scripts/deploy.sh
```

### Step 4: SSL Certificate Setup

```bash
# Generate SSL certificates (if not using external certificates)
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d pcap-reporter.yourdomain.com
```

For detailed production setup, see the [Production Deployment Guide](../deployment/production.md).

## ⚙️ Configuration

### Environment Variables

Key configuration options:

#### Backend Configuration
```bash
# Database
MONGODB_URL=mongodb://localhost:27017/pcap_reporter
MONGODB_DATABASE=pcap_reporter

# Redis
REDIS_URL=redis://localhost:6379/0

# File Upload
UPLOAD_PATH=./uploads
MAX_FILE_SIZE=2147483648  # 2GB in bytes

# Processing
MAX_WORKERS=4
MEMORY_LIMIT=512m
CHUNK_SIZE=1048576  # 1MB

# Security
SECRET_KEY=your-secret-key
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

### Advanced Configuration

#### Nginx Configuration
For custom nginx setup, modify `nginx/conf.d/pcap-reporter.conf`:

```nginx
# Custom upload limits
client_max_body_size 4G;

# Custom timeouts
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

#### MongoDB Configuration
For production MongoDB tuning:

```yaml
# docker-compose.prod.yml
mongodb:
  command: mongod --wiredTigerCacheSizeGB 2 --maxConns 1000
```

## ✅ Verification

### Health Checks

```bash
# Check service status
docker-compose ps

# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# Check database connection
docker-compose exec backend python -c "from core.database import check_db_connection; print(check_db_connection())"
```

### Test Upload

1. Access the web interface
2. Upload a test PCAP file
3. Verify analysis completes successfully
4. Check logs for any errors

### Performance Test

```bash
# Monitor resource usage
docker stats

# Check processing performance
time curl -X POST -F "file=@test.pcap" http://localhost:8000/api/reports/upload
```

## 🔧 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check port usage
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :8000

# Stop conflicting services
sudo systemctl stop apache2  # If using port 80/443
```

#### Permission Issues
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# Fix file permissions
sudo chown -R $USER:$USER ./uploads
sudo chmod 755 ./uploads
```

#### Memory Issues
```bash
# Increase Docker memory limit
# Edit Docker Desktop settings or /etc/docker/daemon.json
{
  "default-runtime": "runc",
  "default-shm-size": "1G"
}
```

#### Database Connection Issues
```bash
# Reset MongoDB
docker-compose down
docker volume rm pcap-reporter_mongodb_data
docker-compose up -d mongodb

# Check MongoDB logs
docker-compose logs mongodb
```

### Log Analysis

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs celery-worker

# Follow logs in real-time
docker-compose logs -f backend
```

### Getting Help

If you encounter issues during installation:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the [FAQ](faq.md)
3. Check Docker and system logs
4. Verify system requirements are met
5. Report issues on the GitHub repository

## 📚 Next Steps

After successful installation:

1. Read the [User Guide](user-guide.md) to learn how to use PCAP Reporter
2. Explore the [API Reference](../api/api-reference.md) for automation
3. Set up [monitoring](../deployment/monitoring.md) for production use
4. Configure [security](../deployment/security.md) settings

---

*Installation complete? Continue with the [User Guide](user-guide.md)* 