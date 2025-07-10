# Essential Development Commands

## Docker Operations
```bash
# Start all services
docker-compose up -d

# Start with logs visible
docker-compose up

# View logs for specific service
docker-compose logs api
docker-compose logs celery-worker
docker-compose logs frontend

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Rebuild services
docker-compose build
```

## Backend Development
```bash
# Run backend locally (with services running)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker locally
cd backend
celery -A main.celery worker --loglevel=info

# Run tests
cd backend
pytest
pytest -v  # verbose
pytest tests/unit/  # unit tests only
pytest tests/integration/  # integration tests only

# Code quality
black .  # format code
isort .  # sort imports
flake8  # linting
mypy .  # type checking
```

## Frontend Development
```bash
# Run frontend locally
cd frontend
npm install
npm run dev

# Build for production
npm run build
npm start

# Linting and type checking
npm run lint
npm run type-check
```

## Testing & Verification
```bash
# Backend basic tests
cd backend
python test_basic.py

# API health check
curl http://localhost:8000/health

# Frontend verification
curl http://localhost:3000
```

## System Commands (Linux/WSL2)
```bash
# File operations
ls -la
find . -name "*.py" -type f
grep -r "search_term" .

# Process management
ps aux | grep python
kill -9 <pid>

# Docker debugging
docker ps -a
docker logs <container_id>
docker exec -it <container_id> /bin/bash
```