#!/bin/bash

# Production Deployment Script for PCAP Reporter
# This script handles the complete production deployment process

set -euo pipefail  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env.production"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
BACKUP_DIR="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
   exit 1
fi

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if user is in docker group
    if ! groups "$USER" | grep -q "docker"; then
        error "User $USER is not in the docker group. Please add user to docker group and re-login."
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f "$ENV_FILE" ]]; then
        error "Production environment file not found: $ENV_FILE"
        error "Please copy .env.production.example to .env.production and configure it."
        exit 1
    fi
    
    # Check compose file
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Production compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Function to validate environment configuration
validate_environment() {
    log "Validating environment configuration..."
    
    # Source the environment file
    set -a
    source "$ENV_FILE"
    set +a
    
    # Check critical variables
    local required_vars=(
        "SECRET_KEY"
        "MONGO_PASSWORD"
        "ENVIRONMENT"
        "DATABASE_URL"
        "REDIS_URL"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables:"
        printf '  - %s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    # Check for default/insecure values
    if [[ "$SECRET_KEY" == *"change-this"* ]] || [[ ${#SECRET_KEY} -lt 32 ]]; then
        error "SECRET_KEY is not properly configured. Please use a strong, unique secret key."
        exit 1
    fi
    
    if [[ "$MONGO_PASSWORD" == *"change-this"* ]] || [[ ${#MONGO_PASSWORD} -lt 12 ]]; then
        error "MONGO_PASSWORD is not properly configured. Please use a strong password."
        exit 1
    fi
    
    if [[ "$ENVIRONMENT" != "production" ]]; then
        error "ENVIRONMENT must be set to 'production'"
        exit 1
    fi
    
    success "Environment configuration is valid"
}

# Function to create backup
create_backup() {
    if [[ -z "${SKIP_BACKUP:-}" ]]; then
        log "Creating backup..."
        mkdir -p "$BACKUP_DIR"
        
        # Backup database if it exists
        if docker ps --format "table {{.Names}}" | grep -q "pcap-reporter-mongodb"; then
            log "Backing up MongoDB database..."
            docker exec pcap-reporter-mongodb mongodump \
                --host localhost:27017 \
                --db pcap_reporter \
                --out /data/backup/$(date +%Y%m%d_%H%M%S) || true
        fi
        
        # Backup uploads directory
        if [[ -d "${PROJECT_ROOT}/uploads" ]]; then
            log "Backing up uploads directory..."
            cp -r "${PROJECT_ROOT}/uploads" "$BACKUP_DIR/"
        fi
        
        # Backup configuration
        log "Backing up configuration files..."
        cp "$ENV_FILE" "$BACKUP_DIR/"
        cp -r "${PROJECT_ROOT}/nginx" "$BACKUP_DIR/" 2>/dev/null || true
        cp -r "${PROJECT_ROOT}/mongodb" "$BACKUP_DIR/" 2>/dev/null || true
        
        success "Backup created at: $BACKUP_DIR"
    else
        warning "Skipping backup (SKIP_BACKUP is set)"
    fi
}

# Function to build and deploy
deploy() {
    log "Starting production deployment..."
    
    cd "$PROJECT_ROOT"
    
    # Pull latest images
    log "Pulling latest base images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    # Build application images
    log "Building application images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --parallel
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || true
    
    # Start infrastructure services first
    log "Starting infrastructure services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d mongodb redis
    
    # Wait for infrastructure to be ready
    log "Waiting for infrastructure services to be ready..."
    sleep 10
    
    # Start application services
    log "Starting application services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    # Wait for services to be healthy
    log "Waiting for all services to be healthy..."
    local timeout=300  # 5 minutes
    local count=0
    
    while [[ $count -lt $timeout ]]; do
        local healthy_services
        healthy_services=$(docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps --format json | jq -r 'select(.Health == "healthy" or .Health == "") | .Name' | wc -l)
        local total_services
        total_services=$(docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps --format json | wc -l)
        
        if [[ $healthy_services -eq $total_services ]]; then
            success "All services are healthy"
            break
        fi
        
        log "Waiting for services to be healthy... ($healthy_services/$total_services ready)"
        sleep 5
        ((count += 5))
    done
    
    if [[ $count -ge $timeout ]]; then
        error "Services did not become healthy within timeout"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
        exit 1
    fi
    
    success "Production deployment completed successfully"
}

# Function to run post-deployment checks
post_deployment_checks() {
    log "Running post-deployment checks..."
    
    # Check API health
    log "Checking API health..."
    local api_url="http://localhost:8000/health"
    if curl -f "$api_url" &>/dev/null; then
        success "API health check passed"
    else
        error "API health check failed"
        return 1
    fi
    
    # Check frontend health
    log "Checking frontend health..."
    local frontend_url="http://localhost:3000/health"
    if curl -f "$frontend_url" &>/dev/null; then
        success "Frontend health check passed"
    else
        error "Frontend health check failed"
        return 1
    fi
    
    # Check database connectivity
    log "Checking database connectivity..."
    if docker exec pcap-reporter-mongodb mongosh --eval "db.adminCommand('ping')" &>/dev/null; then
        success "Database connectivity check passed"
    else
        error "Database connectivity check failed"
        return 1
    fi
    
    # Check Redis connectivity
    log "Checking Redis connectivity..."
    if docker exec pcap-reporter-redis redis-cli ping | grep -q "PONG"; then
        success "Redis connectivity check passed"
    else
        error "Redis connectivity check failed"
        return 1
    fi
    
    # Check Celery worker
    log "Checking Celery worker..."
    if docker exec pcap-reporter-celery celery -A core.celery_app inspect ping &>/dev/null; then
        success "Celery worker check passed"
    else
        warning "Celery worker check failed - this may be normal during startup"
    fi
    
    success "Post-deployment checks completed"
}

# Function to display deployment summary
show_summary() {
    echo
    echo "================================================================="
    echo "           PCAP Reporter Production Deployment Summary"
    echo "================================================================="
    echo
    echo "🚀 Deployment Status: SUCCESS"
    echo
    echo "📊 Service Endpoints:"
    echo "   • Web Application: http://localhost (or your configured domain)"
    echo "   • API Documentation: http://localhost/api/docs"
    echo "   • Health Check: http://localhost/health"
    echo "   • Monitoring (Grafana): http://localhost:3001"
    echo "   • Metrics (Prometheus): http://localhost:9090"
    echo "   • Task Monitor (Flower): http://localhost:5555"
    echo
    echo "🔧 Management Commands:"
    echo "   • View logs: docker-compose -f $COMPOSE_FILE logs -f [service]"
    echo "   • Scale workers: docker-compose -f $COMPOSE_FILE up -d --scale celery-worker=N"
    echo "   • Restart service: docker-compose -f $COMPOSE_FILE restart [service]"
    echo "   • Stop all: docker-compose -f $COMPOSE_FILE down"
    echo
    echo "📂 Important Paths:"
    echo "   • Configuration: $ENV_FILE"
    echo "   • Logs: docker-compose -f $COMPOSE_FILE logs"
    echo "   • Backup: $BACKUP_DIR"
    echo
    echo "🔐 Security Reminders:"
    echo "   • Update default passwords in $ENV_FILE"
    echo "   • Configure SSL certificates in nginx/ssl/"
    echo "   • Review firewall settings"
    echo "   • Enable log rotation"
    echo
    echo "================================================================="
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --skip-backup     Skip backup creation"
    echo "  --skip-checks     Skip post-deployment checks"
    echo "  --help           Show this help message"
    echo
    echo "Environment Variables:"
    echo "  SKIP_BACKUP=1     Skip backup creation"
    echo "  SKIP_CHECKS=1     Skip post-deployment checks"
}

# Main function
main() {
    local skip_checks=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                export SKIP_BACKUP=1
                shift
                ;;
            --skip-checks)
                skip_checks=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "================================================================="
    echo "           PCAP Reporter Production Deployment"
    echo "================================================================="
    echo
    
    # Run deployment steps
    check_prerequisites
    validate_environment
    create_backup
    deploy
    
    if [[ "$skip_checks" != true ]] && [[ -z "${SKIP_CHECKS:-}" ]]; then
        if ! post_deployment_checks; then
            error "Post-deployment checks failed. Please review the deployment."
            exit 1
        fi
    fi
    
    show_summary
}

# Run main function with all arguments
main "$@"