#!/bin/bash

# PCAP Reporter - Environment Management Script
# Usage: ./pcap-reporter.sh [start|stop|restart|status|logs] [options]

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
COMPOSE_PROD_FILE="$PROJECT_DIR/docker-compose.prod.yml"
LOG_DIR="$PROJECT_DIR/logs"
SCRIPT_LOG="$LOG_DIR/pcap-reporter-script.log"

# Colors for output (check if terminal supports colors or force color is set)
if [[ "${FORCE_COLOR}" == "true" ]] || ([[ -t 1 ]] && [[ "${TERM}" != "dumb" ]] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1); then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    PURPLE='\033[0;35m'
    CYAN='\033[0;36m'
    NC='\033[0m' # No Color
else
    # Terminal doesn't support colors, use empty strings
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    PURPLE=''
    CYAN=''
    NC=''
fi

# Service definitions
SERVICES=(
    "nginx:reverse-proxy"
    "frontend:web-interface"
    "api:api-server"
    "celery-worker:task-processor"
    "celery-beat:task-scheduler"
    "flower:task-monitor"
    "mongodb:database"
    "redis:cache-queue"
)

# Log function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Log to file
    echo "[$timestamp] [$level] $message" >> "$SCRIPT_LOG"
    
    # Log to console with colors
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
        *)
            echo -e "${CYAN}[$level]${NC} $message"
            ;;
    esac
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    log "INFO" "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log "ERROR" "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log "ERROR" "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    log "INFO" "Dependencies check passed"
}

# Get Docker Compose command with appropriate file
get_compose_cmd() {
    local env_type="${1:-dev}"
    
    if [[ "$env_type" == "prod" ]]; then
        echo "docker-compose -f $COMPOSE_PROD_FILE"
    else
        echo "docker-compose -f $COMPOSE_FILE"
    fi
}

# Start services
start_services() {
    local env_type="${1:-dev}"
    local compose_cmd=$(get_compose_cmd "$env_type")
    
    log "INFO" "Starting PCAP Reporter services ($env_type environment)..."
    
    # Check if services are already running
    if $compose_cmd ps | grep -q "Up"; then
        log "WARN" "Some services are already running. Use 'restart' to restart them."
        return 0
    fi
    
    # Create necessary directories
    mkdir -p "$PROJECT_DIR/uploads"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/mongodb/data"
    
    # Start services
    log "INFO" "Building and starting containers...This will take a while, please be patient!!"
    $compose_cmd up -d --build
    
    # Wait for services to be ready
    log "INFO" "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_service_health "$env_type"
    
    log "INFO" "PCAP Reporter services started successfully!"
    log "INFO" "Web interface: http://localhost:3000"
    log "INFO" "API documentation: http://localhost:9090/docs"
    log "INFO" "Health check: http://localhost:9090/health"
}

# Stop services
stop_services() {
    local env_type="${1:-dev}"
    local cleanup="${2:-false}"
    local compose_cmd=$(get_compose_cmd "$env_type")
    
    log "INFO" "Stopping PCAP Reporter services ($env_type environment)..."
    
    # Stop services
    $compose_cmd down
    
    if [[ "$cleanup" == "true" ]]; then
        log "INFO" "Performing cleanup..."
        
        # Remove volumes
        $compose_cmd down -v
        
        # Remove orphaned containers
        docker container prune -f
        
        # Remove unused networks
        docker network prune -f
        
        # Remove unused images (optional)
        read -p "Remove unused Docker images? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker image prune -f
        fi
        
        log "INFO" "Cleanup completed"
    fi
    
    log "INFO" "PCAP Reporter services stopped"
}

# Restart services
restart_services() {
    local env_type="${1:-dev}"
    
    log "INFO" "Restarting PCAP Reporter services..."
    stop_services "$env_type" false
    sleep 5
    start_services "$env_type"
}

# Frontend failure detection and remediation
check_and_fix_frontend() {
    local env_type="${1:-dev}"
    local compose_cmd=$(get_compose_cmd "$env_type")
    local frontend_issues=()
    
    log "INFO" "Performing comprehensive frontend health check..."
    
    # Check if frontend container is running
    local frontend_status=$($compose_cmd ps frontend 2>/dev/null | grep -E "(Up|Exited|Dead|Restarting)" | head -1)
    
    if [[ -z "$frontend_status" ]]; then
        frontend_issues+=("CONTAINER_NOT_FOUND")
        log "ERROR" "Frontend container not found"
    elif echo "$frontend_status" | grep -q "Exited"; then
        frontend_issues+=("CONTAINER_EXITED")
        log "ERROR" "Frontend container has exited"
    elif echo "$frontend_status" | grep -q "Restarting"; then
        frontend_issues+=("CONTAINER_RESTARTING")
        log "WARN" "Frontend container is restarting"
    fi
    
    # Check frontend logs for common issues
    local frontend_logs=$($compose_cmd logs --tail=50 frontend 2>/dev/null || echo "")
    
    if echo "$frontend_logs" | grep -qi "ENOENT.*node_modules"; then
        frontend_issues+=("MISSING_NODE_MODULES")
        log "ERROR" "Missing node_modules detected"
    fi
    
    if echo "$frontend_logs" | grep -qi "EADDRINUSE.*3000"; then
        frontend_issues+=("PORT_IN_USE")
        log "ERROR" "Port 3000 is already in use"
    fi
    
    if echo "$frontend_logs" | grep -qi "permission denied"; then
        frontend_issues+=("PERMISSION_DENIED")
        log "ERROR" "Permission denied error detected"
    fi
    
    if echo "$frontend_logs" | grep -qi "npm ERR"; then
        frontend_issues+=("NPM_ERROR")
        log "ERROR" "NPM error detected"
    fi
    
    if echo "$frontend_logs" | grep -qi "Module not found"; then
        frontend_issues+=("MODULE_NOT_FOUND")
        log "ERROR" "Module not found error detected"
    fi
    
    if echo "$frontend_logs" | grep -qi "ECONNREFUSED.*9090"; then
        frontend_issues+=("BACKEND_CONNECTION_REFUSED")
        log "WARN" "Backend connection refused (API may not be ready)"
    fi
    
    # Check disk space
    local disk_usage=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | tr -d '%')
    if [[ $disk_usage -gt 90 ]]; then
        frontend_issues+=("DISK_SPACE_LOW")
        log "ERROR" "Disk space low: ${disk_usage}% used"
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [[ $memory_usage -gt 90 ]]; then
        frontend_issues+=("MEMORY_LOW")
        log "WARN" "Memory usage high: ${memory_usage}%"
    fi
    
    # Apply remediation based on detected issues
    if [[ ${#frontend_issues[@]} -gt 0 ]]; then
        log "WARN" "Frontend issues detected: ${frontend_issues[*]}"
        apply_frontend_remediation "$env_type" "${frontend_issues[@]}"
    else
        log "INFO" "No frontend issues detected"
    fi
    
    # Final health check
    local max_retries=30
    local retry_count=0
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
            log "INFO" "Frontend is healthy after remediation"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        sleep 2
    done
    
    log "ERROR" "Frontend health check failed after remediation"
    return 1
}

# Apply frontend remediation
apply_frontend_remediation() {
    local env_type="$1"
    local compose_cmd=$(get_compose_cmd "$env_type")
    shift
    local issues=("$@")
    
    log "INFO" "Applying frontend remediation..."
    
    for issue in "${issues[@]}"; do
        case "$issue" in
            "CONTAINER_NOT_FOUND"|"CONTAINER_EXITED")
                log "INFO" "Restarting frontend container..."
                $compose_cmd up -d frontend
                sleep 5
                ;;
            "CONTAINER_RESTARTING")
                log "INFO" "Waiting for container to stabilize..."
                sleep 10
                ;;
            "MISSING_NODE_MODULES")
                log "INFO" "Rebuilding frontend container with fresh node_modules..."
                $compose_cmd stop frontend
                $compose_cmd rm -f frontend
                $compose_cmd build --no-cache frontend
                $compose_cmd up -d frontend
                sleep 10
                ;;
            "PORT_IN_USE")
                log "INFO" "Killing processes using port 3000..."
                lsof -ti:3000 | xargs kill -9 2>/dev/null || true
                sleep 2
                $compose_cmd restart frontend
                ;;
            "PERMISSION_DENIED")
                log "INFO" "Fixing frontend permissions..."
                # Check if we have a fix-permissions script
                if [[ -f "$SCRIPT_DIR/fix-permissions.sh" ]]; then
                    "$SCRIPT_DIR/fix-permissions.sh"
                else
                    # Basic permission fix
                    sudo chown -R $USER:$USER "$PROJECT_DIR/frontend"
                    sudo chmod -R 755 "$PROJECT_DIR/frontend"
                fi
                $compose_cmd restart frontend
                ;;
            "NPM_ERROR"|"MODULE_NOT_FOUND")
                log "INFO" "Clearing npm cache and reinstalling dependencies..."
                $compose_cmd exec frontend npm cache clean --force 2>/dev/null || true
                $compose_cmd exec frontend rm -rf node_modules package-lock.json 2>/dev/null || true
                $compose_cmd exec frontend npm install 2>/dev/null || true
                $compose_cmd restart frontend
                ;;
            "BACKEND_CONNECTION_REFUSED")
                log "INFO" "Checking backend availability..."
                # Wait for backend to be ready
                local backend_ready=false
                for i in {1..30}; do
                    if curl -sf http://localhost:9090/health > /dev/null 2>&1; then
                        backend_ready=true
                        break
                    fi
                    sleep 2
                done
                
                if [[ "$backend_ready" == "false" ]]; then
                    log "WARN" "Backend not ready, restarting backend service..."
                    $compose_cmd restart api
                fi
                ;;
            "DISK_SPACE_LOW")
                log "INFO" "Cleaning up disk space..."
                # Clean Docker system
                docker system prune -f
                # Clean node_modules and build artifacts
                find "$PROJECT_DIR/frontend" -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
                find "$PROJECT_DIR/frontend" -name ".next" -type d -exec rm -rf {} + 2>/dev/null || true
                # Rebuild frontend
                $compose_cmd build --no-cache frontend
                $compose_cmd up -d frontend
                ;;
            "MEMORY_LOW")
                log "INFO" "Attempting to free memory..."
                # Restart services to free memory
                $compose_cmd restart frontend
                # Give system time to recover
                sleep 5
                ;;
        esac
    done
}

# Check service health
check_service_health() {
    local env_type="${1:-dev}"
    local compose_cmd=$(get_compose_cmd "$env_type")
    
    log "INFO" "Checking service health..."
    
    # Check if containers are running
    local running_containers=$($compose_cmd ps | grep -c "Up" || echo "0")
    
    if [[ $running_containers -eq 0 ]]; then
        log "ERROR" "No containers are running"
        return 1
    fi
    
    # Check specific service endpoints
    local max_retries=30
    local retry_count=0
    
    # Check backend health
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -sf http://localhost:9090/health > /dev/null 2>&1; then
            log "INFO" "Backend API is healthy"
            break
        fi
        
        retry_count=$((retry_count + 1))
        sleep 2
    done
    
    if [[ $retry_count -eq $max_retries ]]; then
        log "WARN" "Backend API health check failed after $max_retries attempts"
    fi
    
    # Check and fix frontend with comprehensive remediation
    check_and_fix_frontend "$env_type"
}

# Get service status
get_service_status() {
    local env_type="${1:-dev}"
    local compose_cmd=$(get_compose_cmd "$env_type")
    
    echo -e "${CYAN}PCAP Reporter Service Status${NC}"
    echo -e "${CYAN}==============================${NC}"
    
    # Check if compose file exists
    if [[ "$env_type" == "prod" && ! -f "$COMPOSE_PROD_FILE" ]]; then
        log "ERROR" "Production compose file not found: $COMPOSE_PROD_FILE"
        return 1
    elif [[ "$env_type" == "dev" && ! -f "$COMPOSE_FILE" ]]; then
        log "ERROR" "Development compose file not found: $COMPOSE_FILE"
        return 1
    fi
    
    # Get container status
    local containers=$($compose_cmd ps 2>/dev/null || echo "")
    
    if [[ -z "$containers" ]]; then
        echo -e "${RED}No containers found${NC}"
        return 1
    fi
    
    # Display container status
    echo -e "${BLUE}Container Status:${NC}"
    $compose_cmd ps
    
    echo -e "\n${BLUE}Service Health:${NC}"
    
    # Check individual services
    for service_def in "${SERVICES[@]}"; do
        local service_name=$(echo "$service_def" | cut -d: -f1)
        local service_desc=$(echo "$service_def" | cut -d: -f2)
        
        local status=$($compose_cmd ps "$service_name" 2>/dev/null | grep -E "(Up|Exited|Dead)" | head -1)
        
        if echo "$status" | grep -q "Up"; then
            echo -e "  ${GREEN}✓${NC} $service_desc ($service_name): Running"
        elif echo "$status" | grep -q "Exited"; then
            echo -e "  ${RED}✗${NC} $service_desc ($service_name): Stopped"
        else
            echo -e "  ${YELLOW}?${NC} $service_desc ($service_name): Unknown"
        fi
    done
    
    # Check service endpoints
    echo -e "\n${BLUE}Endpoint Health:${NC}"
    
    # Backend API health
    if curl -sf http://localhost:9090/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Backend API: http://localhost:9090/health"
    else
        echo -e "  ${RED}✗${NC} Backend API: http://localhost:9090/health"
    fi
    
    # Frontend health
    if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Frontend: http://localhost:3000/health"
    else
        echo -e "  ${RED}✗${NC} Frontend: http://localhost:3000/health"
        echo -e "    ${YELLOW}→${NC} Run: ./scripts/pcap-reporter.sh fix-frontend"
        
        # Show quick diagnostic info
        local frontend_container_status=$($compose_cmd ps frontend 2>/dev/null | grep -E "(Up|Exited|Dead)" | head -1)
        if [[ -n "$frontend_container_status" ]]; then
            if echo "$frontend_container_status" | grep -q "Up"; then
                echo -e "    ${YELLOW}→${NC} Container is running but health check failed"
            elif echo "$frontend_container_status" | grep -q "Exited"; then
                echo -e "    ${YELLOW}→${NC} Container has exited"
            fi
        else
            echo -e "    ${YELLOW}→${NC} Container not found"
        fi
    fi
    
    # MongoDB health
    if $compose_cmd exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} MongoDB: Database connection"
    else
        echo -e "  ${RED}✗${NC} MongoDB: Database connection"
    fi
    
    # Redis health
    if $compose_cmd exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Redis: Cache connection"
    else
        echo -e "  ${RED}✗${NC} Redis: Cache connection"
    fi
    
    # System resources
    echo -e "\n${BLUE}System Resources:${NC}"
    local cpu_usage=$(docker stats --no-stream --format "table {{.CPUPerc}}" | tail -n +2 | head -1)
    local memory_usage=$(docker stats --no-stream --format "table {{.MemUsage}}" | tail -n +2 | head -1)
    
    echo -e "  CPU Usage: ${cpu_usage:-Unknown}"
    echo -e "  Memory Usage: ${memory_usage:-Unknown}"
    
    # Disk usage
    local disk_usage=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}')
    echo -e "  Disk Usage: ${disk_usage:-Unknown}"
}

# Display service logs
show_service_logs() {
    local service_name="$1"
    local env_type="${2:-dev}"
    local follow="${3:-false}"
    local compose_cmd=$(get_compose_cmd "$env_type")
    
    if [[ -z "$service_name" ]]; then
        echo -e "${YELLOW}Available services:${NC}"
        for service_def in "${SERVICES[@]}"; do
            local svc_name=$(echo "$service_def" | cut -d: -f1)
            local svc_desc=$(echo "$service_def" | cut -d: -f2)
            echo -e "  ${CYAN}$svc_name${NC} - $svc_desc"
        done
        return 0
    fi
    
    # Validate service name
    local valid_service=false
    for service_def in "${SERVICES[@]}"; do
        local svc_name=$(echo "$service_def" | cut -d: -f1)
        if [[ "$svc_name" == "$service_name" ]]; then
            valid_service=true
            break
        fi
    done
    
    if [[ "$valid_service" == "false" ]]; then
        log "ERROR" "Invalid service name: $service_name"
        show_service_logs ""
        return 1
    fi
    
    log "INFO" "Showing logs for service: $service_name"
    
    if [[ "$follow" == "true" ]]; then
        $compose_cmd logs -f "$service_name"
    else
        $compose_cmd logs --tail=100 "$service_name"
    fi
}

# Display help
show_help() {
    echo -e "${CYAN}PCAP Reporter Environment Management Script${NC}"
    echo
    echo -e "${YELLOW}Usage:${NC}"
    echo "    ./pcap-reporter.sh <command> [options]"
    echo
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "    ${GREEN}start${NC}       Start all services"
    echo -e "    ${GREEN}stop${NC}        Stop all services"
    echo -e "    ${GREEN}restart${NC}     Restart all services"
    echo -e "    ${GREEN}status${NC}      Show service status"
    echo -e "    ${GREEN}logs${NC}        Show service logs"
    echo -e "    ${GREEN}fix-frontend${NC} Run frontend diagnostic and remediation"
    echo -e "    ${GREEN}help${NC}        Show this help message"
    echo
    echo -e "${YELLOW}Options:${NC}"
    echo -e "    ${GREEN}--prod${NC}             Use production environment"
    echo -e "    ${GREEN}--cleanup${NC}          Clean up volumes and images when stopping"
    echo -e "    ${GREEN}--service <name>${NC}    Target specific service (for logs)"
    echo -e "    ${GREEN}--follow${NC}           Follow logs in real-time"
    echo -e "    ${GREEN}-s, --status${NC}       Show service status"
    echo -e "    ${GREEN}-l, --logs${NC}         Show service logs"
    echo -e "    ${GREEN}-f, --fix-frontend${NC} Run frontend diagnostic and remediation"
    echo
    echo -e "${YELLOW}Examples:${NC}"
    echo "    ./pcap-reporter.sh start                    # Start development environment"
    echo "    ./pcap-reporter.sh start --prod             # Start production environment"
    echo "    ./pcap-reporter.sh stop --cleanup           # Stop and cleanup"
    echo "    ./pcap-reporter.sh status                   # Show service status"
    echo "    ./pcap-reporter.sh logs --service backend   # Show backend logs"
    echo "    ./pcap-reporter.sh logs --service frontend --follow  # Follow frontend logs"
    echo "    ./pcap-reporter.sh fix-frontend             # Diagnose and fix frontend issues"
    echo
    echo -e "${YELLOW}Available Services:${NC}"

    for service_def in "${SERVICES[@]}"; do
        local svc_name=$(echo "$service_def" | cut -d: -f1)
        local svc_desc=$(echo "$service_def" | cut -d: -f2)
        echo -e "    ${CYAN}$svc_name${NC} - $svc_desc"
    done
    
    echo
    echo -e "${YELLOW}Service URLs:${NC}"
    echo -e "    ${GREEN}Frontend:${NC} http://localhost:3000"
    echo -e "    ${GREEN}Backend API:${NC} http://localhost:9090"
    echo -e "    ${GREEN}API Docs:${NC} http://localhost:9090/docs"
    echo -e "    ${GREEN}Health Check:${NC} http://localhost:9090/health"
}

# Main script logic
main() {
    # Check dependencies first
    check_dependencies
    
    # Parse command line arguments
    local command=""
    local env_type="dev"
    local cleanup=false
    local service_name=""
    local follow=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|help|fix-frontend)
                command="$1"
                shift
                ;;
            --prod)
                env_type="prod"
                shift
                ;;
            --cleanup)
                cleanup=true
                shift
                ;;
            --service)
                service_name="$2"
                shift 2
                ;;
            --follow)
                follow=true
                shift
                ;;
            -s|--status)
                command="status"
                shift
                ;;
            -l|--logs)
                command="logs"
                shift
                ;;
            -f|--fix-frontend)
                command="fix-frontend"
                shift
                ;;
            -h|--help)
                command="help"
                shift
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set default command if none provided
    if [[ -z "$command" ]]; then
        command="help"
    fi
    
    # Execute command
    case "$command" in
        start)
            start_services "$env_type"
            ;;
        stop)
            stop_services "$env_type" "$cleanup"
            ;;
        restart)
            restart_services "$env_type"
            ;;
        status)
            get_service_status "$env_type"
            ;;
        logs)
            show_service_logs "$service_name" "$env_type" "$follow"
            ;;
        fix-frontend)
            log "INFO" "Running frontend diagnostic and remediation..."
            check_and_fix_frontend "$env_type"
            ;;
        help)
            show_help
            ;;
        *)
            log "ERROR" "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
