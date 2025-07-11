#!/bin/bash

# PCAP Reporter Production Deployment Script
# This script handles the complete deployment process for production

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_FILE="${PROJECT_DIR}/logs/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env.prod exists
    if [[ ! -f "${PROJECT_DIR}/.env.prod" ]]; then
        error ".env.prod file not found. Please create it from env.prod.example"
        exit 1
    fi
    
    # Check if SSL certificates exist
    if [[ ! -f "${PROJECT_DIR}/nginx/ssl/fullchain.pem" ]] || [[ ! -f "${PROJECT_DIR}/nginx/ssl/privkey.pem" ]]; then
        warn "SSL certificates not found. HTTPS will not work until certificates are installed."
    fi
    
    log "Prerequisites check completed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p "${PROJECT_DIR}/logs"
    mkdir -p "${PROJECT_DIR}/backups"
    mkdir -p "${PROJECT_DIR}/backend/uploads"
    mkdir -p "${PROJECT_DIR}/backend/logs"
    mkdir -p "${PROJECT_DIR}/nginx/logs"
    mkdir -p "${PROJECT_DIR}/nginx/ssl"
    mkdir -p "${PROJECT_DIR}/mongodb/logs"
    mkdir -p "${PROJECT_DIR}/redis/logs"
    
    log "Directories created"
}

# Backup existing data
backup_data() {
    log "Creating backup of existing data..."
    
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="${BACKUP_DIR}/backup_${BACKUP_TIMESTAMP}"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup database
    if docker ps | grep -q pcap-reporter-mongodb; then
        log "Backing up MongoDB data..."
        docker exec pcap-reporter-mongodb mongodump --out /backup
        docker cp pcap-reporter-mongodb:/backup "${BACKUP_PATH}/mongodb"
    fi
    
    # Backup uploads
    if [[ -d "${PROJECT_DIR}/backend/uploads" ]]; then
        log "Backing up uploads..."
        cp -r "${PROJECT_DIR}/backend/uploads" "${BACKUP_PATH}/"
    fi
    
    # Backup configuration
    if [[ -f "${PROJECT_DIR}/.env.prod" ]]; then
        log "Backing up configuration..."
        cp "${PROJECT_DIR}/.env.prod" "${BACKUP_PATH}/"
    fi
    
    log "Backup completed: ${BACKUP_PATH}"
}

# Pull latest images
pull_images() {
    log "Pulling latest Docker images..."
    
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.prod.yml pull
    
    log "Images pulled successfully"
}

# Build application images
build_images() {
    log "Building application images..."
    
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    log "Images built successfully"
}

# Stop existing services
stop_services() {
    log "Stopping existing services..."
    
    cd "$PROJECT_DIR"
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        docker-compose -f docker-compose.prod.yml down
    fi
    
    log "Services stopped"
}

# Start services
start_services() {
    log "Starting services..."
    
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.prod.yml up -d
    
    log "Services started"
}

# Health check
health_check() {
    log "Performing health checks..."
    
    # Wait for services to start
    sleep 30
    
    # Check backend health
    if curl -f http://localhost:8000/health &> /dev/null; then
        log "Backend health check: PASSED"
    else
        error "Backend health check: FAILED"
        return 1
    fi
    
    # Check frontend health
    if curl -f http://localhost:3000/health &> /dev/null; then
        log "Frontend health check: PASSED"
    else
        warn "Frontend health check: FAILED (may still be starting)"
    fi
    
    # Check nginx health
    if curl -f http://localhost/health &> /dev/null; then
        log "Nginx health check: PASSED"
    else
        error "Nginx health check: FAILED"
        return 1
    fi
    
    log "Health checks completed"
}

# Setup SSL certificates (Let's Encrypt)
setup_ssl() {
    log "Setting up SSL certificates..."
    
    if [[ ! -f "${PROJECT_DIR}/nginx/ssl/fullchain.pem" ]]; then
        info "SSL certificates not found. You can set them up manually or use Let's Encrypt."
        info "For Let's Encrypt, run: certbot certonly --webroot -w /var/www/certbot -d your-domain.com"
    else
        log "SSL certificates already exist"
    fi
}

# Cleanup old images and containers
cleanup() {
    log "Cleaning up old images and containers..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused volumes (be careful with this)
    # docker volume prune -f
    
    log "Cleanup completed"
}

# Main deployment function
deploy() {
    log "Starting PCAP Reporter production deployment..."
    
    check_root
    check_prerequisites
    create_directories
    backup_data
    pull_images
    build_images
    stop_services
    start_services
    
    if health_check; then
        log "Deployment completed successfully!"
        info "Access your application at: https://your-domain.com"
        info "Grafana monitoring: http://your-domain.com:3001"
        info "Prometheus metrics: http://your-domain.com:9090"
    else
        error "Deployment completed with errors. Check the logs and service status."
        exit 1
    fi
    
    setup_ssl
    cleanup
    
    log "All deployment tasks completed!"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTION]"
    echo "Options:"
    echo "  deploy      Full deployment (default)"
    echo "  backup      Create backup only"
    echo "  start       Start services"
    echo "  stop        Stop services"
    echo "  restart     Restart services"
    echo "  health      Health check"
    echo "  logs        Show logs"
    echo "  cleanup     Cleanup old images"
    echo "  help        Show this help"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "backup")
        backup_data
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        start_services
        ;;
    "health")
        health_check
        ;;
    "logs")
        cd "$PROJECT_DIR"
        docker-compose -f docker-compose.prod.yml logs -f
        ;;
    "cleanup")
        cleanup
        ;;
    "help")
        usage
        ;;
    *)
        echo "Invalid option: $1"
        usage
        exit 1
        ;;
esac 