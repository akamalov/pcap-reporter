# Project Structure

## Root Directory
```
pcap-reporter/
├── backend/           # FastAPI backend application
├── frontend/          # Next.js frontend application
├── docs/              # Project documentation
├── nginx/             # Nginx configuration
├── mongodb/           # MongoDB initialization scripts
├── tests/             # End-to-end tests
├── docker-compose.yml # Docker services configuration
├── .env.example       # Environment variables template
└── README.md          # Project overview and setup
```

## Backend Structure
```
backend/
├── api/               # API routes and endpoints
│   └── v1/
│       ├── endpoints/ # Individual endpoint modules
│       └── api.py     # API router aggregation
├── core/              # Core application components
│   ├── config.py      # Configuration settings
│   ├── database.py    # Database connection
│   └── celery_app.py  # Celery configuration
├── models/            # Data models
│   ├── analysis_job.py
│   ├── report.py
│   └── [other models]
├── services/          # Business logic services
│   ├── pcap_analyzer.py
│   ├── validation_service.py
│   └── [other services]
├── tasks/             # Celery background tasks
│   └── analysis_tasks.py
├── tests/             # Test suite
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── fixtures/      # Test data
├── main.py            # FastAPI application entry
├── mcp_server.py      # MCP server implementation
└── requirements.txt   # Python dependencies
```

## Frontend Structure
```
frontend/
├── src/
│   ├── app/           # Next.js app directory (13+)
│   │   ├── layout.tsx # Root layout
│   │   ├── page.tsx   # Home page
│   │   ├── upload/    # Upload functionality
│   │   └── reports/   # Report viewing
│   ├── components/    # Reusable components
│   ├── lib/           # Utility functions
│   └── types/         # TypeScript definitions
├── public/            # Static assets
├── package.json       # Node.js dependencies
└── next.config.js     # Next.js configuration
```

## Docker Services
- **nginx**: Reverse proxy (ports 80, 443)
- **api**: FastAPI backend (port 8000)
- **celery-worker**: Background task processor
- **celery-beat**: Task scheduler
- **flower**: Celery monitoring (port 5555)
- **mongodb**: Database (port 27017)
- **redis**: Cache and message broker (port 6379)
- **frontend**: Next.js development server (port 3000)