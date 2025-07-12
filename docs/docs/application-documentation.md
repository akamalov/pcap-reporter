# MCP-PCAP Reporter: Complete Application Documentation v1.0

This document provides comprehensive documentation for the MCP-PCAP Reporter application, covering its architecture, setup, API, and usage. This is the final version 1.0 documentation after completing all implementation phases.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [Analysis Engine](#analysis-engine)
6. [API Endpoints](#api-endpoints)
7. [Report Generation](#report-generation)
8. [Development Environment](#development-environment)
9. [Production Deployment](#production-deployment)
10. [User Guide](#user-guide)
11. [Troubleshooting](#troubleshooting)

---

## Project Overview

The MCP-PCAP Reporter is a comprehensive web application for network packet capture analysis. It provides professional-grade PCAP file analysis with detailed reporting, security scanning, and network visualization capabilities.

### Key Features

- **Comprehensive PCAP Analysis**: Supports .pcap, .pcapng, and .cap file formats
- **Hybrid Analysis Engine**: Combines tshark (high-speed triage) and Scapy (deep packet inspection)
- **Professional Reporting**: Generates detailed PDF reports with executive summaries
- **Network Visualization**: Interactive network diagrams showing communication patterns
- **Security Analysis**: Advanced threat detection and anomaly identification
- **Web Interface**: Modern, responsive UI with dark/light theme support
- **Asynchronous Processing**: Celery-based background processing for scalability
- **MCP Integration**: Model Context Protocol server for AI-powered analysis

### Technology Stack

**Frontend:**
- Next.js 14 with TypeScript
- Ant Design 5 UI components
- Tailwind CSS for styling
- Recharts for data visualization
- Mermaid.js for network diagrams

**Backend:**
- FastAPI with Python 3.11
- Celery for asynchronous task processing
- MongoDB for data persistence
- Redis for task queue and caching
- Docker containerization

**Analysis Tools:**
- tshark (Wireshark CLI) for high-speed analysis
- Scapy for deep packet inspection
- Custom hybrid analysis engine

---

## Architecture

### System Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Browser   │    │    Nginx    │    │  Frontend   │
│             │◄──►│  (Reverse   │◄──►│  (Next.js)  │
│             │    │   Proxy)    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   MongoDB   │◄──►│  Backend    │◄──►│    Redis    │
│ (Database)  │    │  (FastAPI)  │    │  (Queue)    │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   Celery    │
                   │  (Workers)  │
                   └─────────────┘
```

### Service Architecture

1. **Frontend Service**: Next.js application serving the web interface
2. **Backend API**: FastAPI service handling REST endpoints
3. **Worker Service**: Celery workers for PCAP analysis processing
4. **Database**: MongoDB for storing reports and analysis results
5. **Cache/Queue**: Redis for task queuing and session storage
6. **Reverse Proxy**: Nginx for routing and load balancing

---

## Frontend Architecture

### Component Structure

```
frontend/src/
├── app/
│   ├── components/           # Shared UI components
│   │   ├── AppHeader.tsx     # Consistent header component
│   │   ├── ErrorBoundary.tsx # Error handling wrapper
│   │   ├── LoadingOverlay.tsx# Loading states
│   │   ├── MermaidDiagram.tsx# Network diagram renderer
│   │   ├── ThemeProvider.tsx # Theme context
│   │   └── ThemeToggle.tsx   # Dark/light mode toggle
│   ├── lib/
│   │   └── api.ts           # API service layer
│   ├── page.tsx             # Landing page
│   ├── layout.tsx           # Root layout
│   ├── globals.css          # Global styles
│   ├── upload/
│   │   └── page.tsx         # File upload interface
│   └── reports/
│       ├── page.tsx         # Reports listing
│       └── [id]/
│           └── page.tsx     # Individual report view
```

### Key Features

#### 1. Landing Page
- Professional hero section with feature highlights
- Responsive design with mobile optimization
- Clear call-to-action buttons
- Feature overview cards
- Performance statistics display

#### 2. Upload Interface
- Drag-and-drop file upload with validation
- Support for .pcap, .pcapng, .cap files (up to 100MB)
- Real-time upload progress tracking
- Comprehensive error handling and user feedback
- Automatic redirection to analysis report

#### 3. Reports Dashboard
- Searchable and filterable reports table
- Real-time status updates for processing jobs
- Bulk operations (delete, download)
- Advanced filtering by date range, status, filename
- Responsive table design with mobile support

#### 4. Report Viewer
- Comprehensive analysis results display
- Interactive network diagrams
- Detailed statistics tables
- Security findings with severity ratings
- PDF export functionality
- Real-time processing status updates

#### 5. Theme System
- Consistent dark/light mode implementation
- Persistent user preferences
- Smooth transitions between themes
- Accessible color schemes

---

## Backend Architecture

### API Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── analysis.py      # Analysis endpoints
│   │   ├── reports.py       # Report management
│   │   └── health.py        # Health checks
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # MongoDB connection
│   │   └── redis.py         # Redis connection
│   ├── models/
│   │   ├── analysis.py      # Analysis data models
│   │   ├── reports.py       # Report data models
│   │   └── jobs.py          # Job status models
│   ├── services/
│   │   ├── analysis.py      # Analysis service logic
│   │   ├── pcap_analyzer.py # PCAP analysis engine
│   │   └── report_generator.py # PDF generation
│   ├── tasks/
│   │   └── analysis.py      # Celery tasks
│   └── main.py              # FastAPI application
```

### Core Services

#### 1. Analysis Service
- File upload handling and validation
- Job creation and status tracking
- Result aggregation and storage
- Error handling and recovery

#### 2. PCAP Analyzer
- Hybrid analysis engine combining tshark and Scapy
- Protocol detection and classification
- Security threat identification
- Performance metric calculation
- Network topology mapping

#### 3. Report Generator
- Professional PDF report creation
- Executive summary generation
- Technical details formatting
- Chart and diagram integration

---

## Analysis Engine

### Hybrid Approach

The analysis engine uses a two-stage approach for optimal performance and accuracy:

#### Stage 1: High-Speed Triage (tshark)
- Basic packet statistics extraction
- Protocol distribution analysis
- Top talkers identification
- Conversation mapping
- Timeline reconstruction

#### Stage 2: Deep Packet Inspection (Scapy)
- Detailed protocol analysis
- Security threat detection
- Performance bottleneck identification
- Application layer analysis
- Custom rule application

### Analysis Capabilities

1. **Network Statistics**
   - Total packets and bytes processed
   - Protocol distribution breakdown
   - Top communication pairs
   - Traffic timeline analysis

2. **Security Analysis**
   - Port scan detection
   - Suspicious traffic patterns
   - Protocol anomalies
   - Potential security threats

3. **Performance Analysis**
   - Latency measurements
   - Bandwidth utilization
   - Retransmission analysis
   - Connection quality metrics

4. **Application Analysis**
   - HTTP/HTTPS traffic analysis
   - DNS query analysis
   - Email traffic patterns
   - File transfer detection

---

## API Endpoints

### Health Check
```
GET /api/health
Response: {
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "workers": "active"
}
```

### Analysis Submission
```
POST /api/analyze
Content-Type: multipart/form-data
Body: {
  "file": <PCAP_FILE>,
  "analysis_type": "comprehensive|basic",
  "priority": "high|normal|low"
}
Response: {
  "job_id": "uuid",
  "status": "pending",
  "filename": "capture.pcap",
  "file_size": 1024000,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Report Status
```
GET /api/report/{job_id}
Response: {
  "job_id": "uuid",
  "status": "pending|processing|completed|failed",
  "progress": 75,
  "filename": "capture.pcap",
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:05:00Z",
  "results": { ... }  // Only present when completed
}
```

### PDF Export
```
GET /api/export/pdf/{job_id}
Response: Binary PDF file
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"
```

### Reports Listing
```
GET /api/reports
Query Parameters:
  - limit: int = 20
  - offset: int = 0
  - status: str = "all"
  - search: str = ""
Response: {
  "jobs": [...],
  "stats": {
    "total_reports": 150,
    "completed_reports": 142,
    "processing_reports": 3,
    "failed_reports": 5,
    "total_packets_analyzed": 1500000,
    "total_data_processed": 5368709120
  }
}
```

---

## Report Generation

### Report Structure

1. **Executive Summary**
   - Key findings overview
   - Security assessment
   - Performance summary
   - Recommendations

2. **Network Overview**
   - Topology diagram
   - Communication patterns
   - Protocol distribution
   - Traffic statistics

3. **Security Analysis**
   - Threat detection results
   - Vulnerability assessment
   - Anomaly identification
   - Risk scoring

4. **Performance Metrics**
   - Latency analysis
   - Throughput measurements
   - Quality of service metrics
   - Bottleneck identification

5. **Technical Details**
   - Detailed packet statistics
   - Protocol-specific analysis
   - Application layer findings
   - Raw data tables

### PDF Generation Features

- Professional formatting with corporate styling
- Interactive table of contents
- High-resolution charts and diagrams
- Detailed appendices with raw data
- Customizable branding and headers

---

## Development Environment

### Prerequisites
- Docker Desktop 4.0+
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Git

### Quick Start

1. **Clone and Start**
   ```bash
   git clone <repository-url>
   cd pcap-reporter
   docker-compose up -d
   ```

2. **Access Services**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MongoDB: localhost:27017
   - Redis: localhost:6379

3. **Development Commands**
   ```bash
   # View logs
   docker-compose logs -f frontend
   docker-compose logs -f backend
   
   # Restart services
   docker-compose restart frontend
   docker-compose restart backend
   
   # Access containers
   docker-compose exec backend bash
   docker-compose exec frontend bash
   ```

### Testing

#### Frontend Testing
```bash
cd frontend
npm test                    # Unit tests
npm run test:e2e           # End-to-end tests
npm run lint               # Linting
npm run typecheck          # Type checking
```

#### Backend Testing
```bash
cd backend
pytest                     # Unit tests
pytest --cov              # Coverage report
python -m pytest tests/   # Specific test directory
```

---

## Production Deployment

### Docker Production Build

The application includes optimized production Docker configurations:

1. **Multi-stage builds** for minimal image sizes
2. **Non-root users** for enhanced security
3. **Health checks** for container monitoring
4. **Environment-based configuration**

### Environment Variables

```env
# Backend Configuration
DATABASE_URL=mongodb://mongodb:27017/pcap_reporter
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
CORS_ORIGINS=["http://localhost:3000"]

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=production

# Security
JWT_SECRET=your-jwt-secret
ALLOWED_HOSTS=["localhost", "your-domain.com"]
```

### Production Considerations

1. **Security**
   - Enable HTTPS with SSL certificates
   - Configure proper CORS settings
   - Use secure session management
   - Implement rate limiting

2. **Performance**
   - Configure Redis caching
   - Optimize database queries
   - Enable gzip compression
   - Use CDN for static assets

3. **Monitoring**
   - Implement health checks
   - Set up log aggregation
   - Monitor resource usage
   - Configure alerting

---

## User Guide

### Getting Started

1. **Upload a PCAP File**
   - Navigate to the upload page
   - Drag and drop your PCAP file or click to browse
   - Supported formats: .pcap, .pcapng, .cap (max 100MB)
   - Wait for upload and analysis to complete

2. **View Analysis Results**
   - Access reports from the dashboard
   - Filter and search through your reports
   - Click on any report to view detailed analysis
   - Export reports as PDF for sharing

3. **Understanding Reports**
   - **Overview Tab**: Executive summary and key metrics
   - **Network Tab**: Topology diagrams and communication patterns
   - **Security Tab**: Threat analysis and vulnerabilities
   - **Performance Tab**: Latency, throughput, and quality metrics
   - **Details Tab**: Technical specifications and raw data

### Best Practices

1. **File Preparation**
   - Ensure PCAP files are not corrupted
   - Use recent captures for relevant analysis
   - Consider file size limits for processing time

2. **Analysis Interpretation**
   - Review executive summary for quick insights
   - Check security findings for potential threats
   - Use performance metrics to identify bottlenecks
   - Refer to technical details for deep analysis

---

## Troubleshooting

### Common Issues

#### Upload Failures
- **File Too Large**: Maximum file size is 100MB
- **Invalid Format**: Only .pcap, .pcapng, .cap files supported
- **Network Issues**: Check internet connection and try again

#### Analysis Errors
- **Corrupted PCAP**: Ensure file integrity before upload
- **Processing Timeout**: Large files may take longer to process
- **Memory Errors**: Very large files may require server resources

#### Display Issues
- **Missing Charts**: Ensure JavaScript is enabled
- **Theme Problems**: Clear browser cache and refresh
- **Mobile Layout**: Use landscape orientation for better experience

### Getting Help

1. **Check Logs**
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. **Reset Environment**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. **Contact Support**
   - Check GitHub issues for known problems
   - Create new issue with detailed error information
   - Include log files and environment details

---

## Conclusion

The MCP-PCAP Reporter provides a comprehensive solution for network packet analysis with modern web technologies. This documentation covers all aspects of the application from development to production deployment.

For additional support or feature requests, please refer to the project repository and issue tracker.

---

*MCP-PCAP Reporter v1.0 - Complete Application Documentation*
*Last Updated: January 2025*