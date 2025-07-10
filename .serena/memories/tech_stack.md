# Technology Stack

## Backend Technologies
- **Framework**: FastAPI 0.104.1
- **Server**: Uvicorn with Gunicorn
- **Task Queue**: Celery 5.3.4 with Redis
- **Database**: MongoDB with Motor (async) and Beanie ODM
- **PCAP Analysis**: Scapy, PyShark, dpkt
- **Data Processing**: Pandas, NumPy, Matplotlib, Seaborn
- **Security**: python-jose, passlib
- **Configuration**: Pydantic Settings
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: black, isort, flake8, mypy

## Frontend Technologies
- **Framework**: Next.js 14.0.4
- **UI Library**: React 18.2.0
- **Component Library**: Ant Design 5.12.8
- **Data Fetching**: SWR 2.2.4
- **HTTP Client**: Axios 1.6.2
- **Charts**: Recharts 2.8.0
- **Diagrams**: Mermaid 10.6.1
- **Date Handling**: Day.js 1.11.10
- **TypeScript**: 5.3.3

## Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **Database**: MongoDB 7.0
- **Cache/Message Broker**: Redis 7
- **Monitoring**: Flower (Celery), Prometheus support
- **Operating System**: Linux (Python 3.11-slim base)